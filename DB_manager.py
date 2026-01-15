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
        """Annule un match validé et rétablit les anciens scores Elo"""
        try:
            # 1. Récupérer les données du match validé
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

            # 2. Récupérer les profils actuels
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

            delta = match["elo_gain"]

            # 3. Inverser les scores et décrémenter le compteur de matchs
            # On rend les points au perdant et on les retire au gagnant
            self.supabase.table("profiles").update(
                {
                    "elo_rating": winner["elo_rating"] - delta,
                    "matches_played": max(0, winner["matches_played"] - 1),
                }
            ).eq("id", winner["id"]).execute()

            self.supabase.table("profiles").update(
                {
                    "elo_rating": loser["elo_rating"] + delta,
                    "matches_played": max(0, loser["matches_played"] - 1),
                }
            ).eq("id", loser["id"]).execute()

            # 4. Marquer le match comme révoqué
            self.supabase.table("matches").update({"status": "revoked"}).eq(
                "id", match_id
            ).execute()

            return True, "Match révoqué avec succès. Les scores ont été rétablis."
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
        """Récupère l'historique complet des matchs pour l'administrateur"""
        return (
            self.supabase.table("matches")
            .select(
                "*, winner:profiles!winner_id(username), loser:profiles!loser_id(username)"
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
        # Le !winner_id(username) est crucial pour récupérer le pseudo du gagnant
        return (
            self.supabase.table("matches")
            .select("*, profiles!winner_id(username)")
            .eq("loser_id", user_id)
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
