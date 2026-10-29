import streamlit as st


def afficher(db, user):

    st.header("⚙️ Paramètres du compte")

    # --- 🏆 NOUVEAU : SECTION MON TITRE ---
    st.subheader("🎖️ Mon Titre")
    
    # On récupère la liste de façon sécurisée (on gère le None)
    unlocked = user.get("unlocked_titles", [])
    if unlocked is None:
        unlocked = []

    if not unlocked:
        st.info("Vous n'avez pas encore de titre débloqué. Participez aux tournois pour en gagner !")
    else:
        # On prépare les options du menu déroulant
        options_titres = ["< Aucun titre >"] + list(unlocked)
        
        # On cherche quel titre est actuellement équipé
        current_t = user.get("equipped_title")
        try:
            default_idx = options_titres.index(current_t) if current_t in options_titres else 0
        except:
            default_idx = 0
            
        chosen_title = st.selectbox("Sélectionnez le titre à afficher sous votre pseudo :", options_titres, index=default_idx)
        
        if st.button("Équiper ce titre"):
            new_val = None if chosen_title == "< Aucun titre >" else chosen_title
            
            # Mise à jour dans Supabase
            try:
                db.supabase.table("profiles").update({"equipped_title": new_val}).eq("id", user["id"]).execute()
                # Mise à jour immédiate de la session pour l'affichage
                st.session_state.user_data["equipped_title"] = new_val
                st.success(f"Titre mis à jour : {chosen_title}")
                st.rerun()
            except Exception as e:
                st.error(f"Erreur lors de la mise à jour : {e}")

    st.divider()

    # --- 🔒 SECTION CONFIDENTIALITÉ (Ton code actuel) ---
    with st.form("privacy_form"):
        st.write("Gérez la visibilité de votre compte :")
        current_hide_lb = user.get("is_hidden_leaderboard", False)
        current_hide_prof = user.get("is_hidden_profile", False)

        new_hide_lb = st.toggle("Masquer mon nom dans le classement", value=current_hide_lb)
        new_hide_prof = st.toggle("Rendre mon profil privé", value=current_hide_prof)

        if st.form_submit_button("Enregistrer les modifications"):
            success, msg = db.update_user_privacy(user["id"], new_hide_lb, new_hide_prof)
            if success:
                st.success("✅ " + msg)
                st.session_state.user_data["is_hidden_leaderboard"] = new_hide_lb
                st.session_state.user_data["is_hidden_profile"] = new_hide_prof
                st.rerun()
