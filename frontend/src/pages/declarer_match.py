import streamlit as st


def afficher(db, user):

    st.header("🎯 Déclarer un résultat")

    # 🛑 VÉRIFICATION DU MODE VISITEUR 🛑
    is_guest = st.session_state.get("guest_mode", False)

    if is_guest:
        # Message pour le visiteur
        st.warning("🔒 Accès restreint")
        st.write("Vous êtes actuellement en Mode Visiteur. Vous devez créer un compte pour pouvoir déclarer vos matchs et participer au classement officiel.")

        # Un petit bouton pour les inviter à se déconnecter du mode visiteur
        if st.button("Se déconnecter et créer un compte"):
            st.session_state.user_data = None
            st.session_state.guest_mode = False
            st.rerun()

    else:
        # ✅ LE CODE NORMAL POUR LES VRAIS JOUEURS ✅

        # 1. Choix du mode de jeu
        mode_input = st.radio("Type de match", ["👤 1 vs 1", "👥 2 vs 2"], horizontal=True)

        # 2. NOUVEAU : Le bouton magique (Toggle) pour débloquer tous les joueurs
        show_all_players = st.toggle("🔍 Afficher également les joueurs inactifs (Nouveaux et Anciens)")

        # Récupération de la liste des joueurs
        players_res = db.get_leaderboard()
        all_players = players_res.data if players_res.data else []

        adv_map = {}

        for p in all_players:
            if p["id"] == user["id"]:
                continue  # On s'ignore soi-même

            # On vérifie l'activité selon le mode
            if mode_input == "👤 1 vs 1":
                is_active = p.get("matches_played", 0) > 0
            else:
                is_active = p.get("matches_2v2", 0) > 0

            # On ajoute le joueur au dictionnaire s'il est actif, OU si le bouton est coché
            if is_active or show_all_players:
                # Petit plus visuel : On ajoute le mot "(Inactif)" si le joueur n'a pas encore joué
                label = p["username"] if is_active else f"{p['username']} (Inactif)"
                adv_map[label] = p["id"]

        # Tri de la liste par ordre alphabétique pour s'y retrouver facilement
        adv_map = dict(sorted(adv_map.items()))

        if not adv_map:
            st.warning("Il n'y a pas encore de joueurs actifs. Cochez le bouton ci-dessus pour afficher tout le monde !")
        else:
            with st.form("match_form"):
                # --- INTERFACE 1 vs 1 ---
                if mode_input == "👤 1 vs 1":
                    adv_nom = st.selectbox(
                        "J'ai gagné contre :",
                        list(adv_map.keys()),
                        index=None,
                        placeholder="Choisir un adversaire...",
                    )
                    # On met les autres à None pour éviter les erreurs de variables
                    partner_nom = None
                    adv2_nom = None

                # --- INTERFACE 2 vs 2 ---
                else:
                    c1, c2 = st.columns(2)
                    # Mon coéquipier
                    partner_nom = c1.selectbox(
                        "Mon coéquipier :",
                        list(adv_map.keys()),
                        index=None,
                        placeholder="Qui était avec toi ?",
                    )

                    # Les adversaires
                    adv_nom = c2.selectbox(
                        "Adversaire 1 :",
                        list(adv_map.keys()),
                        index=None,
                        placeholder="Adversaire 1",
                    )
                    adv2_nom = c2.selectbox(
                        "Adversaire 2 :",
                        list(adv_map.keys()),
                        index=None,
                        placeholder="Adversaire 2",
                    )

                submitted = st.form_submit_button("Envoyer pour validation")

                if submitted:
                    # ==========================================
                    # LOGIQUE DE VALIDATION ET ENVOI
                    # ==========================================

                    # CAS 1 : MODE 1 vs 1
                    if mode_input == "👤 1 vs 1":
                        # Sécurité : Champ vide
                        if adv_nom is None:
                            st.error("⚠️ Vous devez sélectionner un adversaire !")
                            st.stop()

                        # Sécurité : Anti-Spam (Vérifier si match déjà en attente)
                        opponent_id = adv_map[adv_nom]
                        existing = (
                            db.supabase.table("matches")
                            .select("*")
                            .eq("winner_id", user["id"])
                            .eq("loser_id", opponent_id)
                            .eq("status", "pending")
                            .execute()
                        )

                        if existing.data:
                            st.warning(
                                "Un match contre ce joueur est déjà en attente de validation."
                            )
                            st.stop()

                        # Envoi 1v1
                        db.declare_match(user["id"], opponent_id, user["id"], mode="1v1")

                    # CAS 2 : MODE 2 vs 2
                    else:
                        # Sécurité : Champs vides
                        if not (partner_nom and adv_nom and adv2_nom):
                            st.error("⚠️ Veuillez remplir les 3 autres joueurs !")
                            st.stop()

                        # Sécurité : Doublons (ex: Paul partenaire ET adversaire)
                        # On utilise un 'set' pour compter les joueurs uniques
                        selected_players = {partner_nom, adv_nom, adv2_nom}
                        if len(selected_players) < 3:
                            st.error("⚠️ Un joueur ne peut pas être sélectionné deux fois.")
                            st.stop()

                        # Envoi 2v2
                        db.declare_match(
                            winner_id=user["id"],
                            loser_id=adv_map[adv_nom],
                            created_by_id=user["id"],
                            winner2_id=adv_map[partner_nom],
                            loser2_id=adv_map[adv2_nom],
                            mode="2v2",
                        )

                    st.success("Match envoyé avec succès ! 🚀")
                    st.balloons()

        # --- SECTION BAS DE PAGE : HISTORIQUE DES DÉCLARATIONS ---
        st.divider()
        st.subheader("Mes déclarations récentes")

        # On récupère mes victoires récentes pour voir les statuts
        my_wins = (
            db.supabase.table("matches")
            .select("*, profiles!loser_id(username)")  # On récupère le nom du perdant 1
            .eq("created_by", user["id"])  # On filtre sur ceux que J'AI créés
            .order("created_at", desc=True)
            .limit(5)
            .execute()
            .data
        )

        if not my_wins:
            st.info("Aucune déclaration récente.")
        else:
            for w in my_wins:
                status = w["status"]
                # Petit trick pour récupérer le nom : en 2v2 c'est parfois plus complexe,
                # mais on affiche au moins le perdant principal pour se repérer.
                adv = w.get("profiles", {}).get("username", "Inconnu")
                mode_display = " (2v2)" if w.get("mode") == "2v2" else ""

                with st.container(border=True):
                    c1, c2 = st.columns([3, 1])
                    c1.write(f"**VS {adv}** {mode_display}")

                    if status == "pending":
                        c2.info("⏳ En attente")
                    elif status == "validated":
                        c2.success("✅ Validé")

                    elif status == "rejected":
                        c2.error("❌ Refusé")
                        st.write("Votre adversaire a refusé ce match.")
                        col_btn1, col_btn2 = st.columns(2)
                        if col_btn1.button(
                            "Accepter le rejet (Supprimer)", key=f"acc_{w['id']}"
                        ):
                            db.accept_rejection(w["id"])
                            st.rerun()
                        if col_btn2.button("Contester (Litige)", key=f"disp_{w['id']}"):
                            db.dispute_match(w["id"])
                            st.rerun()

                    elif status == "disputed":
                        c2.warning("⚖️ Litige")
                        st.caption("Un administrateur va trancher.")

                    elif status == "rejected_confirmed":
                        c2.write("🗑️ Supprimé")
