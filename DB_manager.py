import streamlit as st
from supabase import create_client


class DBManager:
    def __init__(self):
        # Initialisation via les secrets Streamlit
        self.supabase = create_client(
            st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"]
        )

    def sign_up(self, email, password, username):
        """Crée un compte utilisateur et lie un profil avec le pseudo"""
        # 1. Création du compte sécurisé
        response = self.supabase.auth.sign_up({"email": email, "password": password})

        # 2. Si ça réussit, on crée l'entrée dans ta table 'profiles'
        if response.user:
            self.supabase.table("profiles").insert(
                {"id": response.user.id, "username": username}
            ).execute()
        return response

    def log_in(self, email, password):
        """Connecte l'utilisateur et récupère sa session"""
        return self.supabase.auth.sign_in_with_password(
            {"email": email, "password": password}
        )

    def send_password_reset(self, email):
        """Envoie un email avec un lien de réinitialisation de mot de passe."""
        try:
            # Supabase s'occupe de générer et d'envoyer l'email
            self.supabase.auth.reset_password_email(email)
            return True, "Email envoyé avec succès."
        except Exception as e:
            return False, f"Erreur lors de l'envoi : {e}"

    def update_password(self, new_password):
        """Met à jour le mot de passe de l'utilisateur actuellement connecté."""
        try:
            self.supabase.auth.update_user({"password": new_password})
            return True, "Mot de passe mis à jour avec succès !"
        except Exception as e:
            return False, f"Erreur de mise à jour : {e}"

    def get_user_profile(self, username):
        """Récupère toutes les infos d'un joueur (y compris son rôle admin)"""
        return (
            self.supabase.table("profiles")
            .select("*")
            .eq("username", username)
            .single()
            .execute()
        )

    def get_leaderboard(self, mode="1v1"):
        # On choisit la colonne de tri selon le mode
        sort_col = "elo_rating" if mode == "1v1" else "elo_2v2"

        return (
            self.supabase.table("profiles")
            .select("*")
            .order(sort_col, desc=True)
            .execute()
        )

    def declare_match(
        self,
        winner_id,
        loser_id,
        created_by_id,
        winner2_id=None,
        loser2_id=None,
        mode="1v1",
    ):
        data = {
            "winner_id": winner_id,
            "loser_id": loser_id,
            "created_by": created_by_id,
            "status": "pending",
            "mode": mode,  # Nouveau
            "winner2_id": winner2_id,  # Nouveau (peut être None)
            "loser2_id": loser2_id,  # Nouveau (peut être None)
        }
        return self.supabase.table("matches").insert(data).execute()

    def revoke_match(self, match_id):
        """Annule un match validé et rétablit les anciens scores Elo (Compatible 1v1 et 2v2)"""
        try:
            # 1. Récupérer le match
            match = (
                self.supabase.table("matches")
                .select("*")
                .eq("id", match_id)
                .single()
                .execute()
                .data
            )
            if not match or match["status"] != "validated":
                return (
                    False,
                    "Le match n'est pas dans un état permettant la révocation.",
                )

            mode = match.get("mode", "1v1")
            delta = match["elo_gain"]

            # --- CAS 1v1 ---
            if mode == "1v1":
                # On récupère les profils
                w_res = (
                    self.supabase.table("profiles")
                    .select("*")
                    .eq("id", match["winner_id"])
                    .single()
                    .execute()
                )
                l_res = (
                    self.supabase.table("profiles")
                    .select("*")
                    .eq("id", match["loser_id"])
                    .single()
                    .execute()
                )

                # On inverse les scores (On retire au gagnant, on rend au perdant)
                self.supabase.table("profiles").update(
                    {
                        "elo_rating": w_res.data["elo_rating"] - delta,
                        "matches_played": max(0, w_res.data["matches_played"] - 1),
                    }
                ).eq("id", match["winner_id"]).execute()

                self.supabase.table("profiles").update(
                    {
                        "elo_rating": l_res.data["elo_rating"] + delta,
                        "matches_played": max(0, l_res.data["matches_played"] - 1),
                    }
                ).eq("id", match["loser_id"]).execute()

            # --- CAS 2v2 ---
            elif mode == "2v2":
                # On identifie les 4 joueurs
                winners = [match["winner_id"], match["winner2_id"]]
                losers = [match["loser_id"], match["loser2_id"]]

                # On récupère les données actuelles
                all_ids = winners + losers
                profiles_res = (
                    self.supabase.table("profiles")
                    .select("*")
                    .in_("id", all_ids)
                    .execute()
                )
                p_map = {p["id"]: p for p in profiles_res.data}

                # On retire les points aux gagnants
                for wid in winners:
                    curr = p_map[wid]
                    self.supabase.table("profiles").update(
                        {
                            "elo_2v2": curr.get("elo_2v2", 1000) - delta,
                            "matches_2v2": max(0, curr.get("matches_2v2", 0) - 1),
                        }
                    ).eq("id", wid).execute()

                # On rend les points aux perdants
                for lid in losers:
                    curr = p_map[lid]
                    self.supabase.table("profiles").update(
                        {
                            "elo_2v2": curr.get("elo_2v2", 1000) + delta,
                            "matches_2v2": max(0, curr.get("matches_2v2", 0) - 1),
                        }
                    ).eq("id", lid).execute()

            # 4. Marquer le match comme révoqué
            self.supabase.table("matches").update({"status": "revoked"}).eq(
                "id", match_id
            ).execute()

            return True, "Match révoqué et scores rétablis."
        except Exception as e:
            return False, f"Erreur lors de la révocation : {str(e)}"

    def dispute_match(self, match_id):
        """Le gagnant conteste le refus du perdant et envoie le match à l'admin"""
        try:
            self.supabase.table("matches").update({"status": "disputed"}).eq(
                "id", match_id
            ).execute()
            return True, "Litige envoyé à l'administrateur."
        except Exception as e:
            return False, f"Erreur : {e}"

    def get_all_matches(self):
        """Récupère l'historique complet avec les noms des 4 joueurs potentiels"""
        return (
            self.supabase.table("matches")
            .select(
                # On utilise des alias (winner2:, loser2:) pour récupérer les pseudos supplémentaires
                "*, winner:profiles!winner_id(username), loser:profiles!loser_id(username), winner2:profiles!winner2_id(username), loser2:profiles!loser2_id(username)"
            )
            .order("created_at", desc=True)
            .execute()
        )

    def reject_match(self, match_id):
        """Refuse un match et change son statut pour qu'il n'apparaisse plus"""
        try:
            self.supabase.table("matches").update({"status": "rejected"}).eq(
                "id", match_id
            ).execute()
            return True, "Match refusé."
        except Exception as e:
            return False, f"Erreur lors du refus : {e}"

    def get_pending_matches(self, user_id):
        """Récupère les matchs en attente où l'utilisateur est l'un des perdants"""
        # On utilise une syntaxe spéciale "OR" de Supabase pour vérifier les deux colonnes
        return (
            self.supabase.table("matches")
            .select("*, profiles!winner_id(username)")
            .or_(
                f"loser_id.eq.{user_id},loser2_id.eq.{user_id}"
            )  # <--- La magie est ici
            .eq("status", "pending")
            .execute()
        )

    def accept_rejection(self, match_id):
        """Le gagnant accepte le rejet de l'adversaire, le match est classé sans suite"""
        try:
            self.supabase.table("matches").update(
                {"status": "rejected_confirmed"}  # Nouveau statut pour clore le dossier
            ).eq("id", match_id).execute()
            return True, "Rejet accepté."
        except Exception as e:
            return False, f"Erreur : {e}"

    def validate_match_logic(self, match_id):
        try:
            # Import du moteur (si ce n'est pas fait en haut du fichier)
            from elo_engine import EloEngine

            engine = EloEngine()

            # 1. Récupération sécurisée du match
            match_res = (
                self.supabase.table("matches")
                .select("*")
                .eq("id", match_id)
                .single()
                .execute()
            )
            match = match_res.data

            # Petite sécurité : si déjà validé, on ne refait pas le calcul
            if match["status"] == "validated":
                return True, "Ce match est déjà validé."

            # On récupère le mode (par défaut '1v1' si l'info manque)
            mode = match.get("mode", "1v1")
            delta = 0  # Variable pour stocker les points échangés

            # =========================================================
            # SCÉNARIO 1 : MODE 1 vs 1 (CLASSIQUE)
            # =========================================================
            if mode == "1v1":
                # Récupération des profils
                winner = (
                    self.supabase.table("profiles")
                    .select("*")
                    .eq("id", match["winner_id"])
                    .single()
                    .execute()
                    .data
                )
                loser = (
                    self.supabase.table("profiles")
                    .select("*")
                    .eq("id", match["loser_id"])
                    .single()
                    .execute()
                    .data
                )

                # Calcul Elo 1v1
                new_w_elo, new_l_elo, delta = engine.compute_new_ratings(
                    winner["elo_rating"],
                    loser["elo_rating"],
                    winner["matches_played"],
                    loser["matches_played"],
                )

                # Mise à jour GAGNANT (Colonne 1v1)
                self.supabase.table("profiles").update(
                    {
                        "elo_rating": new_w_elo,
                        "matches_played": winner["matches_played"] + 1,
                    }
                ).eq("id", winner["id"]).execute()

                # Mise à jour PERDANT (Colonne 1v1)
                self.supabase.table("profiles").update(
                    {
                        "elo_rating": new_l_elo,
                        "matches_played": loser["matches_played"] + 1,
                    }
                ).eq("id", loser["id"]).execute()

            # =========================================================
            # SCÉNARIO 2 : MODE 2 vs 2 (NOUVEAU)
            # =========================================================
            elif mode == "2v2":
                # On liste les 4 IDs concernés
                ids = [
                    match["winner_id"],
                    match["winner2_id"],
                    match["loser_id"],
                    match["loser2_id"],
                ]

                # On récupère les 4 profils en une seule requête
                profiles_res = (
                    self.supabase.table("profiles").select("*").in_("id", ids).execute()
                )
                # On crée un dictionnaire pour accéder aux infos facilement par ID
                p_map = {p["id"]: p for p in profiles_res.data}

                # Calcul de la MOYENNE Elo des équipes (sur le classement 2v2)
                # Note: On utilise .get(..., 1000) par sécurité si un champ est vide
                w1_elo = p_map[match["winner_id"]].get("elo_2v2", 1000)
                w2_elo = p_map[match["winner2_id"]].get("elo_2v2", 1000)
                l1_elo = p_map[match["loser_id"]].get("elo_2v2", 1000)
                l2_elo = p_map[match["loser2_id"]].get("elo_2v2", 1000)

                team_win_avg = (w1_elo + w2_elo) / 2
                team_lose_avg = (l1_elo + l2_elo) / 2

                # Calcul du Delta basé sur les moyennes
                # (On passe 0, 0 pour les matchs car on ne pondère pas par l'expérience en équipe pour l'instant)
                _, _, delta = engine.compute_new_ratings(
                    team_win_avg, team_lose_avg, 0, 0
                )

                # Mise à jour des 2 GAGNANTS (Colonne 2v2)
                for wid in [match["winner_id"], match["winner2_id"]]:
                    curr = p_map[wid]
                    self.supabase.table("profiles").update(
                        {
                            "elo_2v2": curr.get("elo_2v2", 1000) + delta,
                            "matches_2v2": curr.get("matches_2v2", 0) + 1,
                        }
                    ).eq("id", wid).execute()

                # Mise à jour des 2 PERDANTS (Colonne 2v2)
                for lid in [match["loser_id"], match["loser2_id"]]:
                    curr = p_map[lid]
                    self.supabase.table("profiles").update(
                        {
                            "elo_2v2": curr.get("elo_2v2", 1000) - delta,
                            "matches_2v2": curr.get("matches_2v2", 0) + 1,
                        }
                    ).eq("id", lid).execute()

            # =========================================================
            # VALIDATION FINALE (COMMUN AUX DEUX MODES)
            # =========================================================
            self.supabase.table("matches").update(
                {"status": "validated", "elo_gain": delta}
            ).eq("id", match_id).execute()

            return True, "Match validé et classements mis à jour !"

        except Exception as e:
            return False, f"Erreur lors de la validation : {str(e)}"

    def update_user_privacy(self, user_id, hide_lb, hide_prof):
        """Met à jour les préférences de confidentialité"""
        try:
            self.supabase.table("profiles").update(
                {"is_hidden_leaderboard": hide_lb, "is_hidden_profile": hide_prof}
            ).eq("id", user_id).execute()
            return True, "Préférences mises à jour !"
        except Exception as e:
            return False, str(e)

    # =========================================================
    # MODULE GRAND TOURNOI
    # =========================================================

    def create_grand_tournament(self, name, format_type):
        """Crée un nouveau tournoi (Statut: Draft)"""
        try:
            res = self.supabase.table("grand_tournaments").insert({
                "name": name,
                "format": format_type,
                "status": "draft"
            }).execute()
            return True, res.data[0]
        except Exception as e:
            return False, f"Erreur de création : {e}"

    def get_grand_tournaments(self):
        """Récupère tous les tournois triés par date de création"""
        return self.supabase.table("grand_tournaments").select("*").order("created_at", desc=True).execute()

    def get_tournament_participants(self, tournament_id):
        """Récupère les inscrits actuels d'un tournoi avec leur pseudo"""
        return (
            self.supabase.table("gt_participants")
            .select("*, profiles(username)")
            .eq("tournament_id", tournament_id)
            .execute()
        )

    def save_tournament_groups(self, tournament_id, groups_data):
        """Met à jour les poules (écrase les anciens inscrits et sauvegarde les nouveaux)"""
        try:
            # 1. On supprime proprement les anciens participants de ce tournoi
            self.supabase.table("gt_participants").delete().eq("tournament_id", tournament_id).execute()
            
            # 2. On insère la nouvelle configuration
            if groups_data:
                for row in groups_data:
                    row['tournament_id'] = tournament_id
                self.supabase.table("gt_participants").insert(groups_data).execute()
                
            return True, "✅ Poules sauvegardées avec succès !"
        except Exception as e:
            return False, f"Erreur lors de la sauvegarde : {e}"

    def update_tournament_status(self, tournament_id, new_status):
        """Passe le tournoi de brouillon à 'groups' ou 'bracket'"""
        try:
            self.supabase.table("grand_tournaments").update({"status": new_status}).eq("id", tournament_id).execute()
            return True
        except:
            return False

    def generate_group_matches(self, tournament_id):
        """Génère tous les matchs de poule (Round-Robin)"""
        # 1. On récupère les participants
        parts = self.get_tournament_participants(tournament_id).data
        
        # 2. On les regroupe par poule
        groups = {}
        for p in parts:
            g = p['group_name']
            if g not in groups:
                groups[g] = []
            groups[g].append(p['user_id'])
            
        # 3. On crée les affrontements possibles (Combinaisons)
        import itertools
        matches_to_insert = []
        for g, users in groups.items():
            pairs = list(itertools.combinations(users, 2))
            for pair in pairs:
                matches_to_insert.append({
                    "tournament_id": tournament_id,
                    "phase": "group",
                    "group_name": g,
                    "player1_id": pair[0],
                    "player2_id": pair[1],
                    "status": "pending"
                })
                
        # 4. On insère tout d'un coup dans la base
        if matches_to_insert:
            self.supabase.table("gt_matches").insert(matches_to_insert).execute()
            
        # 5. On passe le tournoi au statut "groups"
        self.update_tournament_status(tournament_id, "groups")
        return True

    def get_gt_matches(self, tournament_id, phase="group"):
        """Récupère les matchs d'un tournoi selon la phase"""
        return (
            self.supabase.table("gt_matches")
            .select("*")
            .eq("tournament_id", tournament_id)
            .eq("phase", phase)
            .execute()
        )

    def update_gt_match_score(self, match_id, score1, score2, p1_id, p2_id):
        """Met à jour le score d'un match de tournoi et désigne le vainqueur."""
        try:
            print(f"\n--- 🔎 TENTATIVE DE SAISIE DE SCORE ---")
            print(f"Match ID ciblé : {match_id}")
            print(f"Joueur 1 ({p1_id}) vs Joueur 2 ({p2_id})")
            print(f"Scores à envoyer : {score1} à {score2}")
            
            winner_id = p1_id if score1 > score2 else p2_id
            loser_id = p2_id if score1 > score2 else p1_id
            
            data = {
                "score1": score1,
                "score2": score2,
                "winner_id": winner_id,
                "loser_id": loser_id,
                "status": "completed"
            }
            print(f"Données préparées : {data}")
            
            # On exécute la requête
            res = self.supabase.table("gt_matches").update(data).eq("id", match_id).execute()
            
            # On affiche EXACTEMENT ce que Supabase répond
            print(f"✅ RÉPONSE SUPABASE : {res}")
            print("---------------------------------------\n")
            
            return True
            
        except Exception as e:
            print(f"\n❌ ERREUR CATCHÉE : {str(e)}\n")
            return False
    
    def generate_bracket_matches(self, tournament_id, matchups):
        """
        Crée le premier tour de l'arbre final (Winner Bracket) à partir du tirage au sort manuel.
        matchups est une liste de tuples : [(joueur1_id, joueur2_id), ...]
        """
        matches_to_insert = []
        
        for i, pair in enumerate(matchups):
            # On crée un identifiant unique pour l'arbre. Ex: WB_R1_M1 (Winner Bracket, Round 1, Match 1)
            bracket_id = f"WB_R1_M{i+1}" 
            
            matches_to_insert.append({
                "tournament_id": tournament_id,
                "phase": "bracket",
                "bracket_match_id": bracket_id,
                "player1_id": pair[0],
                "player2_id": pair[1],
                "status": "pending"
            })

        # --- AJOUT DE LA PETITE FINALE (Si Single Elimination) ---
        t_data = self.supabase.table("grand_tournaments").select("format").eq("id", tournament_id).execute().data
        if t_data and "single" in t_data[0].get("format", ""):
            import math
            nb_matches_r1 = len(selections)
            total_rounds_wb = int(math.log2(nb_matches_r1)) + 1
            matches_to_insert.append({
                "tournament_id": tournament_id,
                "bracket_match_id": f"WB_R{total_rounds_wb}_M2", # M2 = Le 2ème match du dernier tour (Petite Finale)
                "status": "pending",
                "phase": "bracket"
            })

        # --- Fin de l'ajout ---
        
        if matches_to_insert:
            self.supabase.table("gt_matches").insert(matches_to_insert).execute()
            
        if matches_to_insert:
            self.supabase.table("gt_matches").insert(matches_to_insert).execute()
            
        # On passe le tournoi en phase finale !
        self.update_tournament_status(tournament_id, "bracket")
        return True

    def update_bracket_match_score(self, match_id, score1, score2, p1_id, p2_id, tournament_id, bracket_id, total_r1_matches, format_type):
        """Met à jour un match d'arbre et propulse le gagnant (et le perdant si LB ou Petite Finale activés)"""
        import math
        
        winner_id = p1_id if score1 > score2 else (p2_id if score2 > score1 else None)
        loser_id = p2_id if score1 > score2 else (p1_id if score2 > score1 else None)
        status = "completed" if winner_id else "pending"

        self.supabase.table("gt_matches").update({
            "score1": score1, "score2": score2, "winner_id": winner_id, "loser_id": loser_id, "status": status
        }).eq("id", match_id).execute()

        if winner_id:
            parts = bracket_id.split('_')
            bracket_type = parts[0]
            r_num = int(parts[1].replace('R', ''))
            m_num = int(parts[2].replace('M', ''))

            total_rounds_wb = int(math.log2(total_r1_matches)) + 1

            def push_player_to_next_match(player_id, next_b_id, is_p1):
                existing = self.supabase.table("gt_matches").select("*").eq("tournament_id", tournament_id).eq("bracket_match_id", next_b_id).execute().data
                if existing:
                    update_data = {"player1_id": player_id} if is_p1 else {"player2_id": player_id}
                    self.supabase.table("gt_matches").update(update_data).eq("id", existing[0]["id"]).execute()
                else:
                    insert_data = {
                        "tournament_id": tournament_id, "phase": "bracket", "bracket_match_id": next_b_id,
                        "player1_id": player_id if is_p1 else None, "player2_id": player_id if not is_p1 else None,
                        "status": "pending"
                    }
                    self.supabase.table("gt_matches").insert(insert_data).execute()

            # --- A. WINNER BRACKET ---
            if bracket_type == "WB":
                # Gagnant
                if r_num < total_rounds_wb:
                    next_r = r_num + 1
                    next_m = math.ceil(m_num / 2)
                    push_player_to_next_match(winner_id, f"WB_R{next_r}_M{next_m}", is_p1=(m_num % 2 != 0))
                    
                    # 🥉 NOUVEAU : LA PETITE FINALE (Seulement en Single Elimination)
                    if "single" in format_type and r_num == total_rounds_wb - 1:
                        # Le perdant va en Petite Finale (Match 2 du dernier tour)
                        push_player_to_next_match(loser_id, f"WB_R{total_rounds_wb}_M2", is_p1=(m_num == 1))

                elif "double" in format_type and r_num == total_rounds_wb:
                    # Le grand vainqueur du WB file en Grande Finale
                    push_player_to_next_match(winner_id, f"WB_R{total_rounds_wb + 1}_M1", is_p1=True)
                elif "double" in format_type and r_num == total_rounds_wb + 1:
                    # ⚠️ LE BRACKET RESET
                    # Si le Joueur 2 (qui vient du Loser Bracket) gagne la Grande Finale, on rejoue un match !
                    if winner_id == p2_id:
                        push_player_to_next_match(p1_id, f"WB_R{total_rounds_wb + 2}_M1", is_p1=True)
                        push_player_to_next_match(p2_id, f"WB_R{total_rounds_wb + 2}_M1", is_p1=False)

                # Perdant (Repêchages pour un format 16 qualifiés)
                if "double" in format_type and total_r1_matches == 8:
                    if r_num == 1:
                        # Tour 1 : Les 2 perdants d'un même quart de tableau se rencontrent (Normal)
                        push_player_to_next_match(loser_id, f"LB_R1_M{math.ceil(m_num / 2)}", is_p1=(m_num % 2 != 0))
                    elif r_num == 2:
                        # ⚠️ LE CROISEMENT (ANTI-REMATCH) ⚠️
                        # On inverse l'ordre d'arrivée : 1 va en 4, 2 va en 3, 3 va en 2, 4 va en 1.
                        lb_m = 5 - m_num 
                        push_player_to_next_match(loser_id, f"LB_R2_M{lb_m}", is_p1=False)
                    elif r_num == 3: 
                        # Tour 3 : Pas besoin de croiser, le brassage a déjà été fait au tour d'avant
                        push_player_to_next_match(loser_id, f"LB_R4_M{m_num}", is_p1=False)
                    elif r_num == 4: 
                        # Perdant de la Finale WB -> LB Tour 6
                        push_player_to_next_match(loser_id, f"LB_R6_M1", is_p1=False)

            # --- B. LOSER BRACKET ---
            elif bracket_type == "LB" and "double" in format_type:
                if total_r1_matches == 8:
                    if r_num == 1:
                        push_player_to_next_match(winner_id, f"LB_R2_M{m_num}", is_p1=True)
                    elif r_num == 2:
                        push_player_to_next_match(winner_id, f"LB_R3_M{math.ceil(m_num / 2)}", is_p1=(m_num % 2 != 0))
                    elif r_num == 3:
                        push_player_to_next_match(winner_id, f"LB_R4_M{m_num}", is_p1=True)
                    elif r_num == 4:
                        push_player_to_next_match(winner_id, f"LB_R5_M{math.ceil(m_num / 2)}", is_p1=(m_num % 2 != 0))
                    elif r_num == 5:
                        push_player_to_next_match(winner_id, f"LB_R6_M1", is_p1=True)
                    elif r_num == 6:
                        # Vainqueur de la finale du Loser -> Retour en Grande Finale contre l'invaincu !
                        push_player_to_next_match(winner_id, f"WB_R5_M1", is_p1=False)

        return True

    def create_ghost_player(self, username):
            """Crée un profil fantôme pour les archives sans compte de connexion."""
            import uuid
            # On génère un faux identifiant unique pour ce joueur
            ghost_id = str(uuid.uuid4())
            
            try:
                # On tente d'insérer le fantôme directement dans les profils
                data = {
                    "id": ghost_id,
                    "username": username,
                    "is_admin": False,
                    "is_ghost": True
                }
                self.supabase.table("profiles").insert(data).execute()
                return True, f"Le joueur fantôme '{username}' a été créé avec succès !"
                
            except Exception as e:
                error_str = str(e)
                # On anticipe le blocage de sécurité classique de Supabase
                if "foreign key constraint" in error_str.lower() or "23503" in error_str:
                    return False, "Supabase a bloqué la création (Sécurité auth.users). Donnez-moi ce message d'erreur et je vous fournirai le code SQL pour autoriser les fantômes !"
                return False, f"Erreur inattendue : {error_str}"
    
    def get_all_profiles(self):
        """Récupère absolument tous les profils enregistrés."""
        # <-- NOUVEAU : On demande à récupérer la colonne is_ghost
        return self.supabase.table("profiles").select("id, username, is_ghost").execute()

    def merge_ghost_to_real(self, ghost_id, real_id):
        """Transfère tout l'historique d'un fantôme vers un vrai joueur, puis supprime le fantôme."""
        try:
            # 1. Mise à jour de la présence dans les tournois (Participants)
            self.supabase.table("gt_participants").update({"user_id": real_id}).eq("user_id", ghost_id).execute()

            # 2. Mise à jour des matchs de tournoi (J1, J2, Vainqueur, Perdant)
            self.supabase.table("gt_matches").update({"player1_id": real_id}).eq("player1_id", ghost_id).execute()
            self.supabase.table("gt_matches").update({"player2_id": real_id}).eq("player2_id", ghost_id).execute()
            self.supabase.table("gt_matches").update({"winner_id": real_id}).eq("winner_id", ghost_id).execute()
            self.supabase.table("gt_matches").update({"loser_id": real_id}).eq("loser_id", ghost_id).execute()

            # 3. Nettoyage : Suppression définitive du profil fantôme
            self.supabase.table("profiles").delete().eq("id", ghost_id).execute()

            return True, "Fusion réussie ! Le joueur a récupéré tout son historique."
        except Exception as e:
            return False, f"Erreur lors de la fusion : {str(e)}"

    def create_weekly_tournament(self, name, description, max_players, event_date):
        """Crée un nouveau tournoi hebdomadaire (Weekly Fun)."""
        try:
            # On convertit la date au format texte pour Supabase (YYYY-MM-DD)
            date_str = event_date.strftime("%Y-%m-%d")
            
            # On insère les données dans la nouvelle table
            data = {
                "name": name,
                "description": description,
                "max_players": max_players,
                "event_date": date_str,
                "status": "open" # Ouvert aux inscriptions par défaut
            }
            
            res = self.supabase.table("weekly_tournaments").insert(data).execute()
            
            if res.data:
                return True, "Tournoi Weekly Fun créé avec succès !"
            return False, "Erreur lors de la création."
        except Exception as e:
            return False, f"Erreur technique : {e}"

    def get_current_weekly_tournament(self):
        """Récupère le tournoi Weekly Fun actuellement ouvert (le plus récent)."""
        try:
            res = (
                self.supabase.table("weekly_tournaments")
                .select("*")
                .eq("status", "open")
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )
            if res.data:
                return res.data[0]
            return None
        except Exception as e:
            return None

    def get_weekly_participants(self, tournament_id):
        """Récupère la liste des inscrits pour un tournoi, triée par ordre d'arrivée."""
        try:
            res = (
                self.supabase.table("weekly_participants")
                .select("*, profiles(username)")
                .eq("tournament_id", tournament_id)
                .eq("status", "registered")
                .order("created_at", desc=False) # Ordre chronologique vital pour la liste d'attente !
                .execute()
            )
            return res.data if res.data else []
        except Exception as e:
            return []

    def register_weekly(self, tournament_id, user_id):
        """Inscrit un joueur au tournoi."""
        try:
            # On vérifie s'il n'est pas déjà inscrit pour éviter les doublons
            existing = self.supabase.table("weekly_participants").select("*").eq("tournament_id", tournament_id).eq("user_id", user_id).execute()
            if existing.data:
                # S'il était désinscrit avant, on supprime la vieille trace pour lui donner un nouveau "created_at"
                self.supabase.table("weekly_participants").delete().eq("tournament_id", tournament_id).eq("user_id", user_id).execute()
                
            data = {"tournament_id": tournament_id, "user_id": user_id, "status": "registered"}
            self.supabase.table("weekly_participants").insert(data).execute()
            return True, "Inscription réussie !"
        except Exception as e:
            return False, f"Erreur : {e}"

    def unregister_weekly(self, tournament_id, user_id):
        """Désinscrit un joueur du tournoi en supprimant sa ligne."""
        try:
            self.supabase.table("weekly_participants").delete().eq("tournament_id", tournament_id).eq("user_id", user_id).execute()
            return True, "Désinscription réussie."
        except Exception as e:
            return False, f"Erreur : {e}"

    def close_weekly_tournament(self, tournament_id, rankings):
        """
        Clôture le tournoi hebdomadaire et enregistre le classement final.
        'rankings' est un dictionnaire de type {user_id: rang_final}
        """
        try:
            # 1. On met à jour le rang de chaque participant
            for u_id, rank in rankings.items():
                self.supabase.table("weekly_participants").update({"final_rank": rank}).eq("tournament_id", tournament_id).eq("user_id", u_id).execute()
            
            # 2. On change le statut du tournoi pour l'archiver
            self.supabase.table("weekly_tournaments").update({"status": "closed"}).eq("id", tournament_id).execute()
            
            return True, "Tournoi clôturé avec succès ! Les badges sont distribués."
        except Exception as e:
            return False, f"Erreur lors de la clôture : {e}"

    def admin_remove_participant(self, tournament_id, user_id):
        """L'admin supprime un participant du tournoi."""
        try:
            self.supabase.table("weekly_participants").delete().eq("tournament_id", tournament_id).eq("user_id", user_id).execute()
            return True, "Joueur retiré."
        except Exception as e:
            return False, f"Erreur : {e}"
    
    def get_user_gt_stats(self, user_id):
        """Récupère le palmarès d'un joueur pour les Grands Tournois (Panthéon)."""
        try:
            # On suppose que ta table s'appelle gt_participants et qu'elle a une colonne final_rank
            # Adapte le nom de la table des tournois (tournaments ou gt_tournaments) si besoin
            res = (
                self.supabase.table("gt_participants")
                .select("final_rank, grand_tournaments(name)(name)")
                .eq("user_id", user_id)
                .not_.is_("final_rank", "null")
                .execute()
            )
            return res.data if res.data else []
        except Exception as e:
            return []

    def get_user_weekly_stats(self, user_id):
        """Récupère le palmarès complet d'un joueur pour les tournois Weekly Fun."""
        try:
            res = (
                self.supabase.table("weekly_participants")
                .select("final_rank, weekly_tournaments(name, event_date)")
                .eq("user_id", user_id)
                .not_.is_("final_rank", "null")
                .execute()
            )
            return res.data if res.data else []
        except Exception as e:
            return []

    def calculate_and_save_final_rankings(self, tournament_id, t_format):
        """Calcule automatiquement le classement final (Top X) d'un Grand Tournoi et l'enregistre."""
        try:
            # 1. On récupère tous les matchs terminés de ce tournoi
            res_matches = (
                self.supabase.table("gt_matches")
                .select("*")
                .eq("tournament_id", tournament_id)
                .eq("status", "completed")
                .execute()
            )
            matches = res_matches.data if res_matches.data else []

            # 2. On récupère les participants actuels
            res_parts = self.supabase.table("gt_participants").select("*").eq("tournament_id", tournament_id).execute()
            participants = res_parts.data if res_parts.data else []
            if not participants:
                return False, "Aucun participant trouvé."

            # Dictionnaire pour stocker le rang final de chacun: {user_id: rank}
            final_ranks = {}
            
            # --- PHASE DE POULES (Traitement commun) ---
            # On identifie d'abord les éliminés en phase de poules
            group_matches = [m for m in matches if m["phase"] == "group"]
            group_letters = set([m["group_name"] for m in group_matches if m["group_name"]])
            
            for g in group_letters:
                g_parts = [p for p in participants if p["group_name"] == g]
                g_m = [m for m in group_matches if m["group_name"] == g]
                
                # Recalcul rapide du classement de la poule
                standings = {p["user_id"]: {"V": 0, "Diff": 0} for p in g_parts}
                for m in g_m:
                    w_id, l_id = m["winner_id"], m["loser_id"]
                    if w_id and w_id in standings:
                        standings[w_id]["V"] += 1
                        standings[w_id]["Diff"] += (m["score1"] - m["score2"] if m["player1_id"] == w_id else m["score2"] - m["score1"])
                    if l_id and l_id in standings:
                        standings[l_id]["Diff"] += (m["score1"] - m["score2"] if m["player1_id"] == l_id else m["score2"] - m["score1"])
                
                sorted_g = sorted(standings.keys(), key=lambda uid: (standings[uid]["V"], standings[uid]["Diff"]), reverse=True)
                
                # Seuls les 2 premiers passent (normalement). Les autres sont classés.
                if len(sorted_g) >= 3:
                    final_ranks[sorted_g[2]] = 33 # 3ème de poule
                if len(sorted_g) >= 4:
                    final_ranks[sorted_g[3]] = 49 # 4ème de poule
                # S'il y a un 5e ou 6e, tu pourrais ajouter 65, etc.

            # --- PHASE D'ARBRE (Bracket) ---
            bracket_matches = [m for m in matches if m["phase"] == "bracket"]
            
            is_double = "double" in t_format
            
            # --- LOGIQUE SIMPLE ÉLIMINATION ---
            # --- LOGIQUE SIMPLE ÉLIMINATION ---
            if not is_double:
                wb_matches = [m for m in matches if m.get("bracket_match_id") and m["bracket_match_id"].startswith("WB_")]
                if not wb_matches: return False, "Erreur structurelle de l'arbre WB."
                
                max_r_str = max([m["bracket_match_id"].split("_")[1] for m in wb_matches])
                max_r = int(max_r_str[1:]) # Numéro du round final
                
                # NOUVEAU : On trie les matchs pour lire la Finale EN PREMIER
                wb_matches = sorted(wb_matches, key=lambda x: int(x["bracket_match_id"].split("_")[1][1:]), reverse=True)
                
                for m in wb_matches:
                    parts = m["bracket_match_id"].split("_")
                    current_r = int(parts[1][1:])
                    m_num = int(parts[2][1:])
                    
                    w_id, l_id = m["winner_id"], m["loser_id"]
                    
                    if not l_id: continue # Gestion BYE ou match non fini

                    if current_r == max_r:
                        if m_num == 1:
                            # C'est la GRANDE FINALE (M1)
                            if w_id and w_id not in final_ranks: final_ranks[w_id] = 1 # Or
                            if l_id and l_id not in final_ranks: final_ranks[l_id] = 2 # Argent
                        elif m_num == 2:
                            # C'est la PETITE FINALE (M2)
                            if w_id and w_id not in final_ranks: final_ranks[w_id] = 3 # Bronze
                            if l_id and l_id not in final_ranks: final_ranks[l_id] = 4 # Chocolat
                            
                    else:
                        # PROTECTION : On n'écrase pas une place déjà donnée par une finale !
                        if l_id and l_id not in final_ranks:
                            if current_r == max_r - 1:
                                final_ranks[l_id] = 3 # Ex-aequo s'il n'y a pas eu de Petite Finale
                            elif current_r == max_r - 2:
                                final_ranks[l_id] = 5
                            elif current_r == max_r - 3:
                                final_ranks[l_id] = 9
                            elif current_r == max_r - 4:
                                final_ranks[l_id] = 17

            else:
                # --- DOUBLE ÉLIMINATION ---
                # La Grande Finale (Grand Final) décide du 1er et 2e
                gf_match = next((m for m in bracket_matches if m["bracket_match_id"] == "GF"), None)
                gf_reset = next((m for m in bracket_matches if m["bracket_match_id"] == "GF_RESET"), None)
                
                # Le gagnant final
                if gf_reset and gf_reset["winner_id"]:
                    final_ranks[gf_reset["winner_id"]] = 1
                    final_ranks[gf_reset["loser_id"]] = 2
                elif gf_match and gf_match["winner_id"]:
                    # Si le WB gagne le premier match GF, pas de reset
                    if not gf_reset:
                        final_ranks[gf_match["winner_id"]] = 1
                        final_ranks[gf_match["loser_id"]] = 2
                
                # Finale du Loser Bracket (LB_Final) = 3ème
                lb_matches = [m for m in bracket_matches if m["bracket_match_id"] and m["bracket_match_id"].startswith("LB_")]
                if lb_matches:
                    max_lb_r = max([int(m["bracket_match_id"].split("_")[1][1:]) for m in lb_matches])
                    
                    for m in lb_matches:
                        r_num = int(m["bracket_match_id"].split("_")[1][1:])
                        l_id = m["loser_id"]
                        
                        if not l_id or l_id in final_ranks: continue # Déjà classé (1er ou 2e)
                        
                        if r_num == max_lb_r: final_ranks[l_id] = 3 # Perdant Finale LB = 3ème
                        elif r_num == max_lb_r - 1: final_ranks[l_id] = 4 # Perdant Demie LB = 4ème
                        elif r_num == max_lb_r - 2: final_ranks[l_id] = 5 # Top 5
                        elif r_num == max_lb_r - 3: final_ranks[l_id] = 7 # Top 7
                        elif r_num == max_lb_r - 4: final_ranks[l_id] = 9 # Top 9
                        elif r_num == max_lb_r - 5: final_ranks[l_id] = 13 # Top 13
                        elif r_num == max_lb_r - 6: final_ranks[l_id] = 17 # Top 17
                        elif r_num == max_lb_r - 7: final_ranks[l_id] = 25 # Top 25
                        # Et ainsi de suite selon la taille du tournoi...

            # 3. Enregistrement en base de données
            for uid, rank in final_ranks.items():
                self.supabase.table("gt_participants").update({"final_rank": rank}).eq("tournament_id", tournament_id).eq("user_id", uid).execute()

            # 4. On passe le tournoi en "completed"
            self.supabase.table("grand_tournaments").update({"status": "completed"}).eq("id", tournament_id).execute()

            return True, "Tournoi clôturé et classements générés avec succès !"
            
        except Exception as e:
            return False, f"Erreur lors du calcul des classements : {e}"

    # ==========================================
    # 🧠 GESTION DES ENTRAÎNEMENTS (COURS)
    # ==========================================
    def create_training(self, name, description, max_players, event_date):
        """Crée un nouvel entraînement et archive l'ancien."""
        try:
            # On archive l'ancien s'il y en a un
            self.supabase.table("trainings").update({"status": "completed"}).eq("status", "active").execute()
            
            # On crée le nouveau
            data = {
                "name": name,
                "description": description,
                "max_players": max_players,
                "event_date": event_date.isoformat(),
                "status": "active"
            }
            res = self.supabase.table("trainings").insert(data).execute()
            return True, "L'entraînement a été publié avec succès !"
        except Exception as e:
            return False, f"Erreur lors de la création de l'entraînement : {e}"

    def get_current_training(self):
        """Récupère l'entraînement actuellement actif."""
        try:
            res = self.supabase.table("trainings").select("*").eq("status", "active").order("created_at", desc=True).limit(1).execute()
            return res.data[0] if res.data else None
        except Exception as e:
            return None

    def get_training_participants(self, training_id):
        """Récupère la liste des inscrits pour un entraînement, triée par ordre d'inscription."""
        try:
            res = (
                self.supabase.table("training_participants")
                .select("*, profiles!inner(username)")
                .eq("training_id", training_id)
                .order("registered_at", desc=False)
                .execute()
            )
            return res.data if res.data else []
        except Exception as e:
            return []

    def register_training(self, training_id, user_id):
        """Inscrit un joueur à l'entraînement."""
        try:
            self.supabase.table("training_participants").insert({
                "training_id": training_id,
                "user_id": user_id
            }).execute()
            return True
        except Exception as e:
            return False

    def unregister_training(self, training_id, user_id):
        """Désinscrit un joueur de l'entraînement."""
        try:
            self.supabase.table("training_participants").delete().eq("training_id", training_id).eq("user_id", user_id).execute()
            return True
        except Exception as e:
            return False

    def admin_remove_training_participant(self, training_id, user_id):
        """Permet à l'admin de virer un joueur de l'entraînement."""
        try:
            self.supabase.table("training_participants").delete().eq("training_id", training_id).eq("user_id", user_id).execute()
            return True
        except Exception as e:
            return False

    def close_training(self, training_id):
        """Clôture l'entraînement sans rien distribuer (pas de palmarès)."""
        try:
            self.supabase.table("trainings").update({"status": "completed"}).eq("id", training_id).execute()
            return True, "Entraînement clôturé et archivé avec succès !"
        except Exception as e:
            return False, f"Erreur lors de la clôture : {e}"

    def check_and_create_tie_breaks(self, tournament_id, group_name):
        """
        Vérifie s'il y a une égalité critique dans une poule.
        Si oui, génère la mini-poule de barrage (Round 1, Round 2, etc.).
        """
        try:
            # 1. On récupère tous les matchs de cette poule spécifique
            res = self.supabase.table("gt_matches").select("*").eq("tournament_id", tournament_id).eq("group_name", group_name).execute()
            matches = res.data if res.data else []
            
            if not matches: return False, "Aucun match."
            
            # 2. Quel est le round actuel ? (0 = régulier, 1 = barrage #1, 2 = barrage #2...)
            current_round = max([m.get("tie_break_round", 0) for m in matches])
            current_matches = [m for m in matches if m.get("tie_break_round", 0) == current_round]
            
            # Si le round actuel n'est pas fini, on ne déclenche pas l'arbitre
            if any(m["status"] != "completed" for m in current_matches):
                return False, "Matchs en cours."
                
            # 3. Calcul du classement (uniquement sur le round actuel)
            players_in_round = set()
            for m in current_matches:
                if m["player1_id"]: players_in_round.add(m["player1_id"])
                if m["player2_id"]: players_in_round.add(m["player2_id"])
                
            standings = {uid: {"V": 0, "Diff": 0} for uid in players_in_round}
            for m in current_matches:
                p1, p2 = m["player1_id"], m["player2_id"]
                s1, s2 = m["score1"], m["score2"]
                if p1 and p2:
                    if s1 > s2: standings[p1]["V"] += 1
                    elif s2 > s1: standings[p2]["V"] += 1
                    standings[p1]["Diff"] += (s1 - s2)
                    standings[p2]["Diff"] += (s2 - s1)
                    
            # 4. Tri des joueurs selon leurs scores
            sorted_uids = sorted(standings.keys(), key=lambda x: (standings[x]["V"], standings[x]["Diff"]), reverse=True)
            
            # On regroupe ceux qui ont EXACTEMENT le même score (V et Diff)
            score_groups = {}
            for uid in sorted_uids:
                score = (standings[uid]["V"], standings[uid]["Diff"])
                if score not in score_groups: score_groups[score] = []
                score_groups[score].append(uid)
                
            # 5. Détection des égalités critiques (Top 1 et Top 2)
            players_to_tie_break = []
            current_rank = 1
            
            for score, uids in score_groups.items():
                nb_tied = len(uids)
                if nb_tied > 1:
                    # Si l'égalité touche la 1ère ou la 2ème place, BARRAGE !
                    if current_rank <= 2:
                        players_to_tie_break.extend(uids)
                current_rank += nb_tied
                
            # S'il n'y a pas d'égalité critique, la poule est validée !
            if not players_to_tie_break:
                return True, "Poule validée ! Aucun barrage nécessaire."
                
            # 6. Création de la mini-poule de barrage (Round + 1)
            next_round = current_round + 1
            import itertools
            new_matches = []
            
            # Chaque joueur à égalité va affronter les autres
            for p1, p2 in itertools.combinations(players_to_tie_break, 2):
                new_matches.append({
                    "tournament_id": tournament_id,
                    "phase": "group",
                    "group_name": group_name,
                    "player1_id": p1,
                    "player2_id": p2,
                    "status": "pending",
                    "score1": 0,
                    "score2": 0,
                    "tie_break_round": next_round
                })
                
            if new_matches:
                self.supabase.table("gt_matches").insert(new_matches).execute()
                return True, f"🚨 Égalité critique détectée ! Matchs de Barrage #{next_round} générés."
                
        except Exception as e:
            return False, f"Erreur de l'arbitre : {e}"

    def get_past_weekly_tournaments(self):
        """Récupère la liste de tous les Weekly Funs terminés (archivés)."""
        try:
            # On cherche tous les tournois avec le statut "completed", triés du plus récent au plus ancien
            res = self.supabase.table("weekly_tournaments").select("*").eq("status", "closed").order("event_date", desc=True).execute()
            return res.data if res.data else []
        except Exception as e:
            return []