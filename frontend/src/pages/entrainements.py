import pandas as pd
import streamlit as st


def afficher(db, user):
    st.header("🧠 Sessions d'Entraînement et Cours")
    
    is_guest = st.session_state.get("guest_mode", False)
    is_admin = not is_guest and user.get("is_admin", False)

    # ==========================================
    # 🛠️ VUE ADMIN : CRÉATION & GESTION
    # ==========================================
    if is_admin:
        with st.expander("🛠️ Zone Admin : Planifier un nouvel entraînement"):
            st.info("Planifier une nouvelle session placera automatiquement la précédente dans les archives.")
            
            with st.form("form_create_training"):
                t_name = st.text_input("Thème de la session", placeholder="Ex: Masterclass sur les effets, Entraînement Défense...")
                t_desc = st.text_area("Description", placeholder="Ex: On travaillera les replacements de base...")
                
                col1, col2 = st.columns(2)
                with col1:
                    t_max_players = st.number_input("Nombre de places maximum", min_value=2, max_value=32, value=8, step=1)
                with col2:
                    import datetime
                    t_date = st.date_input("Date de la session", value=datetime.date.today())
                
                submitted_training = st.form_submit_button("Publier l'entraînement 🚀")
                
                if submitted_training:
                    if not t_name:
                        st.error("⚠️ Le thème de la session est obligatoire.")
                    else:
                        success, msg = db.create_training(t_name, t_desc, t_max_players, t_date)
                        if success:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
                            
        st.divider()

    # ==========================================
    # 📺 VUE SPECTATEUR / JOUEUR : LA SESSION EN COURS
    # ==========================================
    current_training = db.get_current_training()
    
    if not current_training:
        st.info("🛌 Aucune session d'entraînement n'est planifiée pour le moment.")
    else:
        # Formatage propre
        formatted_date = pd.to_datetime(current_training['event_date']).strftime('%d/%m/%Y')
        description_text = current_training.get('description', '')
        if not description_text:
            description_text = "Cours libre, programme défini sur place."

        # Bannière bleue nuit / Or
        training_html = (
            "<div style='background: linear-gradient(145deg, #0f172a, #1e293b); "
            "padding: 25px; border-radius: 12px; border: 1px solid #C69C25; "
            "border-left: 8px solid #C69C25; box-shadow: 0 4px 15px "
            "rgba(0,0,0,0.4); margin-bottom: 25px;'>"
            '<h2 style=\'margin-top: 0; margin-bottom: 15px; color: #C69C25; '
            'font-family: "Playfair Display", serif; font-size: 28px; '
            'font-weight: bold; letter-spacing: 0.5px;\'>'
            f"🧠 {current_training['name']}"
            "</h2>"
            "<div style='display: flex; flex-wrap: wrap; gap: 15px; "
            "margin-bottom: 20px;'>"
            "<div style='background-color: rgba(198,156,37,0.1); "
            "padding: 8px 15px; border-radius: 8px; color: #e0e0e0; "
            "font-weight: 500; font-size: 15px; "
            "border: 1px solid rgba(198,156,37,0.2);'>"
            "📅 Date : "
            f"<span style='color: #ffffff; font-weight: bold;'>{formatted_date}</span>"
            "</div>"
            "<div style='background-color: rgba(198,156,37,0.1); "
            "padding: 8px 15px; border-radius: 8px; color: #e0e0e0; "
            "font-weight: 500; font-size: 15px; "
            "border: 1px solid rgba(198,156,37,0.2);'>"
            "🎟️ Places : "
            f"<span style='color: #ffffff; font-weight: bold;'>{current_training['max_players']} max</span>"
            "</div>"
            "</div>"
            "<div style='color: #cccccc; font-size: 16px; line-height: 1.5; "
            "border-top: 1px dashed rgba(198,156,37,0.3); padding-top: 15px;'>"
            f"<i>{description_text}</i>"
            "</div>"
            "</div>"
        )

        st.markdown(training_html, unsafe_allow_html=True)
        
        # --- 👥 SYSTÈME D'INSCRIPTION ---
        st.subheader("👥 Élèves Inscrits")
        
        participants = db.get_training_participants(current_training['id'])
        max_p = current_training['max_players']

        # --- MODÉRATION ADMIN ---
        if is_admin:
            with st.expander("🛠️ Modération de la liste"):
                col_add, col_rem = st.columns(2)
                
                with col_add:
                    st.write("**Ajouter un joueur**")
                    all_p_res = db.get_leaderboard()
                    if all_p_res.data:
                        player_names = [p['username'] for p in all_p_res.data]
                        target_name = st.selectbox("Sélectionner un joueur", player_names, key="admin_add_t_select")
                        if st.button("Ajouter manuellement", key="btn_admin_add_training"):
                            target_id = next(p['id'] for p in all_p_res.data if p['username'] == target_name)
                            success = db.register_training(current_training['id'], target_id)
                            if success:
                                st.success(f"Ajout de {target_name} réussi !")
                                st.rerun()
                            else:
                                st.error("Erreur lors de l'ajout.")
                
                with col_rem:
                    st.write("**Retirer un joueur**")
                    if not participants:
                        st.write("Aucun joueur à retirer.")
                    else:
                        current_p_names = [p.get('profiles', {}).get('username', 'Inconnu') for p in participants]
                        rem_name = st.selectbox("Joueur à retirer", current_p_names, key="admin_rem_t_select")
                        if st.button("Retirer de la session", type="secondary"):
                            rem_id = next(p['user_id'] for p in participants if p.get('profiles', {}).get('username') == rem_name)
                            db.admin_remove_training_participant(current_training['id'], rem_id)
                            st.warning(f"{rem_name} a été retiré de la liste.")
                            st.rerun()

        # Liste Principale et File d'attente
        main_list = participants[:max_p]
        wait_list = participants[max_p:]
        
        is_registered = False
        if not is_guest:
            is_registered = any(p['user_id'] == user['id'] for p in participants)
        
        col_btn, _ = st.columns([1, 2])
        with col_btn:
            if is_guest:
                st.info("🔒 Connectez-vous pour participer.")
            else:
                if is_registered:
                    if st.button("❌ Se désinscrire de la session", type="secondary", use_container_width=True):
                        db.unregister_training(current_training['id'], user['id'])
                        st.rerun()
                else:
                    btn_text = "✅ S'inscrire au cours" if len(participants) < max_p else "⏳ Rejoindre la file d'attente"
                    if st.button(btn_text, type="primary", use_container_width=True):
                        db.register_training(current_training['id'], user['id'])
                        st.rerun()

        st.write("")
        
        # Affichage des listes
        col_main, col_wait = st.columns(2)
        with col_main:
            st.markdown(f"#### 📋 Liste Principale ({len(main_list)}/{max_p})")
            if not main_list:
                st.write("Aucun inscrit pour le moment.")
            else:
                for i, p in enumerate(main_list):
                    username = p.get('profiles', {}).get('username', 'Inconnu')
                    if not is_guest and p['user_id'] == user['id']:
                        st.markdown(f"**{i+1}. {username} (Vous)**")
                    else:
                        st.markdown(f"{i+1}. {username}")
                        
        with col_wait:
            st.markdown(f"#### ⏳ Liste d'Attente ({len(wait_list)})")
            if not wait_list:
                st.caption("Personne en attente.")
            else:
                for i, p in enumerate(wait_list):
                    username = p.get('profiles', {}).get('username', 'Inconnu')
                    if not is_guest and p['user_id'] == user['id']:
                        st.markdown(f"**{max_p + i + 1}. {username} (Vous)**")
                    else:
                        st.caption(f"{max_p + i + 1}. {username}")

        # ==========================================
        # 👑 PANNEAU DE CONTRÔLE ADMIN
        # ==========================================
        if is_admin:
            st.divider()
            st.subheader("👑 Administration de la session")
            
            with st.expander("🔒 Clôturer la session d'entraînement", expanded=False):
                st.info("L'entraînement est terminé ? Vous pouvez l'archiver pour faire place au suivant. (Cette action n'a pas d'impact sur le classement des joueurs).")
                if st.button("Archiver l'entraînement", type="primary"):
                    success, msg = db.close_training(current_training['id'])
                    if success:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)