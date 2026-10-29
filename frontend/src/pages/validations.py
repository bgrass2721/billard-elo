import streamlit as st


def afficher(db, user):

    st.header("📑 Matchs à confirmer")

    # 🛑 VÉRIFICATION DU MODE VISITEUR 🛑
    is_guest = st.session_state.get("guest_mode", False)

    if is_guest:
        # Message pour le visiteur
        st.warning("🔒 Accès restreint")
        st.write(
            "Vous êtes actuellement en Mode Visiteur. "
            "Vous devez créer un compte pour recevoir et valider des matchs."
        )

        # Bouton pour quitter le mode visiteur
        if st.button("Se déconnecter et créer un compte", key="btn_guest_val"):
            st.session_state.user_data = None
            st.session_state.guest_mode = False
            st.rerun()

    else:
        # ✅ LE CODE NORMAL POUR LES VRAIS JOUEURS ✅
        pending = db.get_pending_matches(user["id"]).data
        if not pending:
            st.write("Aucun match en attente.")
        else:
            for m in pending:
                winner_name = m.get("profiles", {}).get("username", "Un joueur")
                with st.expander(f"Match contre {winner_name}", expanded=True):
                    col_val, col_ref = st.columns(2)
                    with col_val:
                        if st.button("Confirmer la défaite ✅", key=f"val_{m['id']}"):
                            success, _msg = db.validate_match_logic(m["id"])
                            if success:
                                st.rerun()
                    with col_ref:
                        if st.button("C'est une erreur ❌", key=f"ref_{m['id']}"):
                            db.reject_match(m["id"])
                            st.rerun()
