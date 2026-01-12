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

    def get_leaderboard(self):
        """Récupère le classement trié par Elo descendante"""
        return (
            self.supabase.table("profiles")
            .select("*")
            .order("elo_rating", desc=True)
            .execute()
        )

    def declare_match(self, winner_id, loser_id, created_by_id):
        """Crée un match en attente"""
        data = {
            "winner_id": winner_id,
            "loser_id": loser_id,
            "created_by": created_by_id,
            "status": "pending",
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

    def validate_match_logic(self, match_id):
        try:
            # 1. Récupération sécurisée des données du match
            match_res = (
                self.supabase.table("matches")
                .select("*")
                .eq("id", match_id)
                .single()
                .execute()
            )
            match = match_res.data

            # 2. Récupération des profils avec leurs statistiques à jour
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

            # 3. Calcul via ton moteur EloEngine
            from elo_engine import EloEngine

            engine = EloEngine()

            new_w_elo, new_l_elo, delta = engine.compute_new_ratings(
                winner["elo_rating"],
                loser["elo_rating"],
                winner["matches_played"],
                loser["matches_played"],
            )

            # 4. Enregistrement des changements
            # On met à jour le gagnant
            self.supabase.table("profiles").update(
                {
                    "elo_rating": new_w_elo,
                    "matches_played": winner["matches_played"] + 1,
                }
            ).eq("id", winner["id"]).execute()

            # On met à jour le perdant
            self.supabase.table("profiles").update(
                {"elo_rating": new_l_elo, "matches_played": loser["matches_played"] + 1}
            ).eq("id", loser["id"]).execute()

            # On valide définitivement le match
            self.supabase.table("matches").update(
                {"status": "validated", "elo_gain": delta}
            ).eq("id", match_id).execute()

            return True, "Match validé et classements mis à jour !"

        except Exception as e:
            return False, f"Erreur lors de la validation : {str(e)}"
