import pandas as pd
import streamlit as st

from base_function_temp.draw_luxury_table import draw_luxury_table


def afficher(db, user):

    st.header("🍻 Les Soirées Weekly Fun")
    
    is_guest = st.session_state.get("guest_mode", False)
    is_admin = not is_guest and user.get("is_admin", False)
    all_users = {p["id"]: p["username"] for p in db.get_all_profiles().data}

    # ==========================================
    # 🛠️ VUE ADMIN : CRÉATION DU TOURNOI
    # ==========================================
    if is_admin:
        with st.expander("🛠️ Créer un nouveau Weekly Fun"):
            st.info("Créer un nouveau tournoi clôturera l'ancien.")
            with st.form("form_create_weekly"):
                w_name = st.text_input("Nom de l'événement", placeholder="Ex: Le Défi du Mercredi...")
                w_desc = st.text_area("Règles spéciales", placeholder="Ex: Casse obligatoire par la bande...")
                
                c1, c2, c3 = st.columns(3)
                with c1:
                    w_type = st.selectbox("Mode de jeu", ["🎯 Par Coup (Scoreboard Infini)", "🌳 Arbre Classique (Max 16)"])
                with c2:
                    w_max_players = st.number_input("Places max", min_value=4, max_value=64, value=16, step=1)
                with c3:
                    import datetime
                    w_date = st.date_input("Date", value=datetime.date.today())
                
                if st.form_submit_button("Publier l'événement 🚀"):
                    if not w_name:
                        st.error("⚠️ Le nom est obligatoire.")
                    else:
                        db_type = "par_coup" if "Par Coup" in w_type else "bracket"
                        success, msg = db.create_weekly_tournament(w_name, w_desc, w_max_players, w_date, tournament_type=db_type)
                        if success:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
        st.divider()

    # ==========================================
    # 📺 VUE PRINCIPALE : LE TOURNOI ACTUEL
    # ==========================================
    current_weekly = db.get_current_weekly_tournament()
    
    if not current_weekly:
        st.info("🛌 Aucun tournoi Weekly Fun n'est prévu pour le moment.")
    else:
        t_type = current_weekly.get("tournament_type", "legacy")
        t_status = current_weekly.get("status", "open")
        formatted_date = pd.to_datetime(current_weekly['event_date']).strftime('%d/%m/%Y')
        mode_label = "🎯 MODE PAR COUP" if t_type == "par_coup" else "🌳 MODE ARBRE (16 Joueurs)"
        
        # BANNIÈRE COMMUNE
        st.markdown(
            f"""
            <div style='background: linear-gradient(145deg, #0f172a, #1e293b); padding: 25px; border-radius: 12px; border: 1px solid #C69C25; border-left: 8px solid #C69C25; box-shadow: 0 4px 15px rgba(0,0,0,0.4); margin-bottom: 25px;'>
                <div style='display: flex; justify-content: space-between;'>
                    <div style='color: #C69C25; font-size: 0.85em; font-weight: bold; letter-spacing: 2px;'>{mode_label}</div>
                    <div style='color: {"#2ecc71" if t_status == "open" else "#e74c3c"}; font-size: 0.85em; font-weight: bold;'>
                        {"🟢 INSCRIPTIONS OUVERTES" if t_status == "open" else "🔥 TOURNOI EN DIRECT"}
                    </div>
                </div>
                <h2 style='margin-top: 10px; margin-bottom: 15px; color: white; font-family: "Playfair Display", serif; font-size: 28px; font-weight: bold;'>
                    {current_weekly['name']}
                </h2>
                <div style='color: #cccccc; font-size: 16px; border-top: 1px dashed rgba(198,156,37,0.3); padding-top: 15px;'>
                    <i>{current_weekly.get('description', 'Aucune règle spéciale.')}</i>
                </div>
            </div>
            """, unsafe_allow_html=True
        )

        participants = db.get_weekly_participants(current_weekly['id'])
        max_p = current_weekly['max_players']
        is_registered = not is_guest and any(p['user_id'] == user['id'] for p in participants)

        # ---------------------------------------------------------
        # PHASE 1 : INSCRIPTIONS OUVERTES
        # ---------------------------------------------------------
        if t_status == "open":
            st.subheader("👥 Inscriptions en cours")
            
            if is_admin:
                with st.expander("🛠️ Modération de la liste des inscrits"):
                    col_add, col_rem = st.columns(2)
                    with col_add:
                        st.write("**Ajouter un joueur (Forcer)**")
                        all_p_res = db.get_leaderboard().data
                        if all_p_res:
                            p_names = [p['username'] for p in all_p_res if p['id'] not in [x['user_id'] for x in participants]]
                            t_add = st.selectbox("Sélectionner un joueur", ["-- Choisir --"] + p_names, key="admin_add_open")
                            if st.button("Ajouter manuellement") and t_add != "-- Choisir --":
                                target_id = next(p['id'] for p in all_p_res if p['username'] == t_add)
                                db.register_weekly(current_weekly['id'], target_id)
                                st.rerun()
                    with col_rem:
                        st.write("**Retirer un joueur**")
                        if participants:
                            c_names = [p.get('profiles', {}).get('username', 'Inconnu') for p in participants]
                            t_rem = st.selectbox("Joueur à expulser", ["-- Choisir --"] + c_names, key="admin_rem_open")
                            if st.button("Expulser du tournoi", type="secondary") and t_rem != "-- Choisir --":
                                rem_id = next(p['user_id'] for p in participants if p.get('profiles', {}).get('username') == t_rem)
                                db.admin_remove_participant(current_weekly['id'], rem_id)
                                st.rerun()

            col_btn, _ = st.columns([1, 2])
            with col_btn:
                if is_guest:
                    st.info("🔒 Connectez-vous pour vous inscrire.")
                elif is_registered:
                    if st.button("❌ Se désinscrire", type="secondary", use_container_width=True):
                        db.unregister_weekly(current_weekly['id'], user['id'])
                        st.rerun()
                else:
                    btn_text = "✅ S'inscrire" if len(participants) < max_p else "⏳ Rejoindre la file d'attente"
                    if st.button(btn_text, type="primary", use_container_width=True):
                        db.register_weekly(current_weekly['id'], user['id'])
                        st.rerun()

            col_main, col_wait = st.columns(2)
            with col_main:
                st.markdown(f"#### 📋 Liste Principale ({min(len(participants), max_p)}/{max_p})")
                for i, p in enumerate(participants[:max_p]):
                    uname = p.get('profiles', {}).get('username', 'Inconnu')
                    st.write(f"**{i+1}. {uname} (Vous)**" if (not is_guest and p['user_id'] == user['id']) else f"{i+1}. {uname}")
            with col_wait:
                st.markdown(f"#### ⏳ File d'attente ({max(0, len(participants) - max_p)})")
                for i, p in enumerate(participants[max_p:]):
                    uname = p.get('profiles', {}).get('username', 'Inconnu')
                    st.caption(f"{max_p + i + 1}. {uname}")

            if is_admin:
                st.divider()
                st.markdown("### 🏁 Démarrer l'événement")
                if st.button("🔴 CLÔTURER LES INSCRIPTIONS ET LANCER LE TOURNOI", type="primary", use_container_width=True):
                    db.start_weekly_tournament(current_weekly['id'], t_type)
                    st.rerun()

        # ---------------------------------------------------------
        # PHASE 2 : LE TOURNOI EN DIRECT
        # ---------------------------------------------------------
        elif t_status == "in_progress":
            
            # --- MODE : PAR COUP ---
            if t_type == "par_coup":
                current_shot = current_weekly.get("current_shot", 1)
                st.markdown("### 📊 Scoreboard en direct")
                
                scores_data = db.get_weekly_scores(current_weekly['id'])
                
                player_totals = {p["user_id"]: 0 for p in participants}
                for s in scores_data:
                    if s["user_id"] in player_totals and not s["is_absent"] and s["score"] >= 0:
                        player_totals[s["user_id"]] += s["score"]

                sorted_participants = sorted(participants, key=lambda p: player_totals.get(p["user_id"], 0), reverse=True)

                player_names = {}
                player_ranks = {}
                current_rank = 1
                for i, p in enumerate(sorted_participants):
                    uid = p["user_id"]
                    uname = p.get("profiles", {}).get("username", "Inconnu")
                    if i > 0 and player_totals[uid] == player_totals[sorted_participants[i-1]["user_id"]]:
                        rank = current_rank
                    else:
                        rank = i + 1
                        current_rank = rank
                    player_ranks[uid] = rank
                    player_names[uid] = uname if p.get("is_active", True) else f"{uname} (Parti)"

                shots_matrix = {}
                for s in scores_data:
                    uid = s["user_id"]
                    shot_num = s["shot_number"]
                    if shot_num not in shots_matrix:
                        shots_matrix[shot_num] = {}
                    shots_matrix[shot_num][uid] = "-" if s["is_absent"] or s["score"] < 0 else s["score"]

                if not sorted_participants or current_shot < 1:
                    st.info("Aucun score enregistré pour l'instant.")
                else:
                    html_table = "<div style='overflow-x: auto;'><table style='width: 100%; border-collapse: collapse; margin-bottom: 25px; background: rgba(255,255,255, 0.03); border-radius: 8px; overflow: hidden; border: 1px solid rgba(198, 156, 37, 0.3); font-family: Montserrat, sans-serif;'>"
                    html_table += "<thead style='background-color: rgba(198, 156, 37, 0.1); border-bottom: 2px solid #C69C25;'><tr>"
                    html_table += "<th style='padding: 12px; text-align: left; color: #C69C25; font-size: 0.85em; text-transform: uppercase;'>Coup</th>"
                    for p in sorted_participants:
                        uid = p["user_id"]; rank = player_ranks[uid]
                        th_bg, th_color = "transparent", "#C69C25"
                        if rank == 1: th_bg, th_color = "rgba(198, 156, 37, 0.15)", "#FFD700"
                        elif rank == 2: th_bg, th_color = "rgba(224, 255, 255, 0.08)", "#E0FFFF"
                        elif rank == 3: th_bg, th_color = "rgba(205, 127, 50, 0.08)", "#CD7F32"
                        html_table += f"<th style='padding: 12px; text-align: center; background-color: {th_bg}; color: {th_color}; font-size: 0.9em; font-weight: 600;'>{player_names[uid]}<br><span style='font-size: 0.75em; opacity: 0.7;'>(#{rank})</span></th>"
                    html_table += "</tr></thead><tbody>"

                    for s_num in range(1, current_shot):
                        html_table += f"<tr style='border-bottom: 1px solid rgba(198, 156, 37, 0.15);'><td style='padding: 12px; font-weight: bold; color: #C69C25;'>Coup {s_num}</td>"
                        for p in sorted_participants:
                            uid = p["user_id"]; val = shots_matrix.get(s_num, {}).get(uid, "-")
                            rank = player_ranks[uid]; td_bg = "transparent"
                            if rank == 1: td_bg = "rgba(198, 156, 37, 0.05)"
                            elif rank == 2: td_bg = "rgba(224, 255, 255, 0.03)"
                            elif rank == 3: td_bg = "rgba(205, 127, 50, 0.03)"
                            html_table += f"<td style='padding: 12px; text-align: center; background-color: {td_bg}; opacity: 0.9;'>{val}</td>"
                        html_table += "</tr>"

                    html_table += "<tr style='background-color: rgba(198, 156, 37, 0.08); border-top: 2px solid #C69C25; font-weight: bold;'><td style='padding: 12px; color: #C69C25;'>TOTAL 🏆</td>"
                    for p in sorted_participants:
                        uid = p["user_id"]; tot = player_totals[uid]
                        rank = player_ranks[uid]; td_bg = "transparent"
                        if rank == 1: td_bg = "rgba(198, 156, 37, 0.1)"
                        elif rank == 2: td_bg = "rgba(224, 255, 255, 0.05)"
                        elif rank == 3: td_bg = "rgba(205, 127, 50, 0.05)"
                        html_table += f"<td style='padding: 12px; text-align: center; background-color: {td_bg}; color: white; font-size: 1.1em;'>{tot}</td>"
                    html_table += "</tr></tbody></table></div>"
                    st.markdown(html_table, unsafe_allow_html=True)

                if is_admin:
                    st.divider()
                    st.markdown(f"### ⚙️ Panneau d'Arbitrage - Coup N°{current_shot}")
                    with st.expander("🛠️ Gérer les joueurs (Retards / Abandons)"):
                        ca, cb = st.columns(2)
                        with ca:
                            all_p_res = db.get_leaderboard().data
                            p_names = [p['username'] for p in all_p_res if p['id'] not in [x['user_id'] for x in participants]]
                            t_add = st.selectbox("Ajouter un joueur", ["-- Choisir --"] + p_names, key="add_t")
                            if st.button("Ajouter à la partie") and t_add != "-- Choisir --":
                                target_id = next(p['id'] for p in all_p_res if p['username'] == t_add)
                                db.register_weekly(current_weekly['id'], target_id); st.rerun()
                        with cb:
                            active_names = [p.get('profiles', {}).get('username') for p in participants if p.get('is_active', True)]
                            t_rem = st.selectbox("Signaler un départ", ["-- Choisir --"] + active_names, key="rem_t")
                            if st.button("Retirer de la table") and t_rem != "-- Choisir --":
                                rem_id = next(p['user_id'] for p in participants if p.get('profiles', {}).get('username') == t_rem)
                                db.admin_remove_participant(current_weekly['id'], rem_id); st.rerun()

                    active_players = [p for p in sorted_participants if p.get("is_active", True)]
                    if active_players:
                        with st.form("score_input_form_unified"):
                            st.write(f"Saisissez les points de chaque joueur pour le **Coup N°{current_shot}** (Non saisi : -1) :")
                            cols = st.columns(4)
                            score_inputs = {}
                            for idx, p in enumerate(active_players):
                                uname = p.get('profiles', {}).get('username', 'Inconnu')
                                uid = p["user_id"]
                                ex_score = next((s["score"] for s in scores_data if s["user_id"] == uid and s["shot_number"] == current_shot and not s["is_absent"]), -1)
                                with cols[idx % 4]:
                                    score_inputs[uid] = st.number_input(uname, min_value=-1, max_value=100, value=ex_score, step=1, key=f"s_{uid}_{current_shot}")
                            
                            if st.form_submit_button("💾 Enregistrer les scores (Rester sur ce coup)", type="secondary", use_container_width=True):
                                db.save_weekly_shot_scores(current_weekly['id'], current_shot, score_inputs)
                                st.success("Modifications enregistrées en direct !"); st.rerun()

                    st.write("")
                    col_b1, col_b2 = st.columns(2)
                    with col_b1:
                        if st.button("⏭️ Valider et Passer au Coup Suivant", type="primary", use_container_width=True):
                            auto_inputs = {p["user_id"]: st.session_state.get(f"s_{p['user_id']}_{current_shot}", -1) for p in active_players}
                            db.save_weekly_shot_scores(current_weekly['id'], current_shot, auto_inputs)
                            db.next_weekly_shot(current_weekly['id'], current_shot)
                            st.rerun()
                    with col_b2:
                        if st.button("🚨 Terminer le tournoi et Archiver", type="secondary", use_container_width=True):
                            # auto_close_par_coup doit mettre le statut à "closed"
                            success, msg = db.auto_close_par_coup(current_weekly['id'])
                            if success: st.success(msg); st.balloons(); st.rerun()
                            else: st.error(msg)

            # --- MODE : ARBRE CLASSIQUE ---
            elif t_type == "bracket":
                st.markdown("### 🌳 L'Arbre en direct")
                matches = db.get_weekly_bracket_matches(current_weekly['id'])
                
                if not matches:
                    st.error("Arbre non généré.")
                else:
                    import math
                    nb_matches_r1 = 8
                    total_rounds_wb = 4
                    tier_dict = {m["bracket_match_id"]: m for m in matches}
                    
                    def render_weekly_css_bracket(prefix, title):
                        def get_match_card_weekly(r_num, m_num, is_gf=False):
                            b_id = f"{prefix}_R{r_num}_M{m_num}"
                            m = tier_dict.get(b_id)
                            
                            bg_color = "rgba(15, 23, 42, 0.9)"
                            border_color = "#C69C25" if is_gf else "rgba(198, 156, 37, 0.4)"
                            
                            c_html = f"<div style='background: {bg_color}; border: 1px solid {border_color}; border-radius: 8px; padding: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); margin: 5px 0;'>"
                            c_html += f"<div style='font-size: 10px; color: rgba(198, 156, 37, 0.7); text-align: center; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 1px;'>Match {m_num}</div>"
                            
                            if m:
                                p1_raw = m.get("player1_id")
                                p2_raw = m.get("player2_id")
                                
                                if p1_raw:
                                    p1 = all_users.get(p1_raw, "Fantôme / BYE")
                                else:
                                    p1 = "Fantôme / BYE" if (m["status"] == "completed" or r_num == 1) else "En attente..."
                                    
                                if p2_raw:
                                    p2 = all_users.get(p2_raw, "Fantôme / BYE")
                                else:
                                    p2 = "Fantôme / BYE" if (m["status"] == "completed" or r_num == 1) else "En attente..."
                                
                                s1 = int(m.get("score1") or 0)
                                s2 = int(m.get("score2") or 0)
                                
                                is_done = (m["status"] == "completed")
                                
                                # Gestion des styles de texte selon le vainqueur
                                if is_done:
                                    w1 = "bold; color: white;" if s1 > s2 else "normal; color: #888;"
                                    w2 = "bold; color: white;" if s2 > s1 else "normal; color: #888;"
                                    c1_score = "#C69C25" if s1 > s2 else "#888"
                                    c2_score = "#C69C25" if s2 > s1 else "#888"
                                    disp_s1 = str(s1)
                                    disp_s2 = str(s2)
                                else:
                                    w1 = w2 = "normal; color: white;"
                                    c1_score = c2_score = "#888"
                                    # Si pas encore joué, on ne met pas de score par défaut à 0 si c'est vide
                                    disp_s1 = str(s1) if s1 > 0 else ""
                                    disp_s2 = str(s2) if s2 > 0 else ""
                                
                                c_html += f"<div style='display: flex; justify-content: space-between; font-weight: {w1}; margin-bottom: 5px;'><span style='overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 140px;'>{p1}</span><span style='color: {c1_score}; font-weight: bold;'>{disp_s1}</span></div>"
                                c_html += f"<div style='display: flex; justify-content: space-between; font-weight: {w2};'><span style='overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 140px;'>{p2}</span><span style='color: {c2_score}; font-weight: bold;'>{disp_s2}</span></div>"
                            else:
                                lbl = "Fantôme / BYE" if r_num == 1 else "En attente..."
                                c_html += f"<div style='display: flex; justify-content: space-between; color: #888; margin-bottom: 5px;'><span>{lbl}</span><span></span></div><div style='display: flex; justify-content: space-between; color: #888;'><span>{lbl}</span><span></span></div>"
                            
                            c_html += "</div>"
                            return c_html

                        html = f"<h5 style='color: white; margin-top: 10px;'>{title}</h5>"
                        html += "<div style='display: flex; flex-direction: row; justify-content: flex-start; width: 100%; overflow-x: auto; padding-bottom: 20px; min-height: 400px;'>"
                        for r_num in range(1, total_rounds_wb + 1):
                            html += "<div style='display: flex; flex-direction: column; justify-content: space-around; flex: 0 0 200px; margin-right: 30px;'>"
                            col_title = "👑 Finale" if r_num == total_rounds_wb else f"Tour {r_num}"
                            html += f"<div style='text-align: center; color: #ccc; font-weight: bold; margin-bottom: 10px; flex: 0 0 auto;'>{col_title}</div>"
                            
                            html += "<div style='display: flex; flex-direction: column; justify-content: space-around; flex: 1 1 auto;'>"
                            expected_count = max(1, nb_matches_r1 // (2**(r_num-1)))
                            for m_num in range(1, expected_count + 1):
                                html += get_match_card_weekly(r_num, m_num)
                            html += "</div></div>"
                        html += "</div>"
                        return html

                    st.markdown(render_weekly_css_bracket("WB", "🏆 L'Arbre du Tournoi"), unsafe_allow_html=True)

                    if is_admin:
                        st.divider()
                    
                        # ==========================================
                        # ⏩ OUTIL : VALIDER LES FANTÔMES (BYE)
                        # ==========================================
                        st.markdown("### ⏩ Valider les Fantômes (BYE)")
                        st.info("Une fois que vous avez terminé d'inverser les positions, cliquez ici pour faire avancer automatiquement les vrais joueurs qui jouent contre des Fantômes.")
                        if st.button("Valider les Fantômes", type="primary", use_container_width=True):
                            # CORRECTION ICI : On utilise current_weekly au lieu de selected_t
                            success, msg = db.process_byes(current_weekly["id"])
                            if success:
                                st.success(msg)
                                st.rerun()
                            else:
                                st.error(msg)
                                
                        st.divider()

                        
                        # ==========================================
                        # 🔄 OUTIL : ÉCHANGER DEUX JOUEURS (SWAP)
                        # ==========================================
                        st.markdown("### 🔄 Permuter deux positions (Tour 1)")
                        st.info("Sélectionnez deux emplacements du Tour 1 pour inverser les joueurs. Pratique pour rééquilibrer l'arbre ou déplacer un 'Fantôme / BYE'.")
                        st.warning("⚠️ À utiliser de préférence *avant* de saisir les scores. Si vous déplacez un joueur, pensez à corriger manuellement les scores du Tour 1 si nécessaire.")
                        
                        # 1. On utilise le dictionnaire tier_dict pour ignorer les anciens matchs cachés !
                        r1_matches = [m for k, m in tier_dict.items() if k.startswith("WB_R1_")]
                        r1_matches.sort(key=lambda x: int(x["bracket_match_id"].split("_M")[1]))

                        # 2. Créer le dictionnaire des "Slots" (Emplacements)
                        slots = []
                        for m in r1_matches:
                            m_num = m["bracket_match_id"].split("_M")[1]
                            p1_name = all_users.get(m.get("player1_id"), "Fantôme / Vide") if m.get("player1_id") else "Fantôme / Vide"
                            p2_name = all_users.get(m.get("player2_id"), "Fantôme / Vide") if m.get("player2_id") else "Fantôme / Vide"

                            slots.append({
                                "label": f"Match {m_num} - Joueur 1 ({p1_name})",
                                "match_id": m["id"],
                                "field": "player1_id",
                                "val": m.get("player1_id")
                            })
                            slots.append({
                                "label": f"Match {m_num} - Joueur 2 ({p2_name})",
                                "match_id": m["id"],
                                "field": "player2_id",
                                "val": m.get("player2_id")
                            })

                        slot_labels = [s["label"] for s in slots]

                        # 3. L'interface avec les deux menus déroulants
                        col_s1, col_s2 = st.columns(2)
                        with col_s1:
                            choice1 = st.selectbox("Position A", slot_labels, key="swap_1")
                        with col_s2:
                            choice2 = st.selectbox("Position B", slot_labels, key="swap_2")

                        if st.button("🔄 Inverser ces deux positions", type="secondary", use_container_width=True):
                            if choice1 != choice2:
                                slot1 = next(s for s in slots if s["label"] == choice1)
                                slot2 = next(s for s in slots if s["label"] == choice2)

                                # 4. LA VRAIE TABLE : weekly_matches !
                                db.supabase.table("weekly_matches").update(
                                    {slot1["field"]: slot2["val"]}
                                ).eq("id", slot1["match_id"]).execute()

                                db.supabase.table("weekly_matches").update(
                                    {slot2["field"]: slot1["val"]}
                                ).eq("id", slot2["match_id"]).execute()

                                st.success("🔄 Les positions ont été échangées avec succès !")
                                st.rerun()
                            else:
                                st.error("Veuillez sélectionner deux positions différentes.")
                                
                        st.divider()
                        st.markdown("### ✏️ Saisie des scores de l'Arbre")
                        
                        def draw_weekly_interactive_match(col, m, r_num, m_num):
                            with col.container(border=True):
                                st.markdown(f"<div style='text-align:center; font-size:10px; opacity:0.5;'>Match {m_num}</div>", unsafe_allow_html=True)
                                if m:
                                    p1_raw = m.get("player1_id")
                                    p2_raw = m.get("player2_id")
                                    
                                    # 🔴 AFFICHAGE INTELLIGENT (ADMIN)
                                    if p1_raw:
                                        p1_name = all_users.get(p1_raw, "Fantôme / BYE")
                                    else:
                                        p1_name = "Fantôme / BYE" if (m["status"] == "completed" or r_num == 1) else "En attente..."
                                        
                                    if p2_raw:
                                        p2_name = all_users.get(p2_raw, "Fantôme / BYE")
                                    else:
                                        p2_name = "Fantôme / BYE" if (m["status"] == "completed" or r_num == 1) else "En attente..."
                                        
                                    is_done = m["status"] == "completed"
                                    
                                    st.write(f"**{p1_name}**")
                                    st.write(f"**{p2_name}**")
                                    
                                    if p1_raw and p2_raw:
                                        sc1, sc2 = st.columns(2)
                                        
                                        val_s1 = int(m.get("score1") or 0)
                                        val_s2 = int(m.get("score2") or 0)
                                        
                                        s1 = sc1.number_input("S1", min_value=0, max_value=20, value=val_s1, key=f"w_s1_{m['id']}", label_visibility="collapsed")
                                        s2 = sc2.number_input("S2", min_value=0, max_value=20, value=val_s2, key=f"w_s2_{m['id']}", label_visibility="collapsed")
                                        
                                        btn_lbl = "MAJ" if is_done else "Valider"
                                        if st.button(btn_lbl, key=f"w_btn_{m['id']}", use_container_width=True):
                                            if s1 == s2:
                                                st.error("Pas d'égalité possible.")
                                            else:
                                                db.update_weekly_bracket_score(m["id"], s1, s2, p1_raw, p2_raw, current_weekly['id'], m["bracket_match_id"])
                                                st.rerun()
                                    else:
                                        if m["status"] == "completed":
                                            st.caption("Qualifié d'office (BYE)")
                                        else:
                                            st.caption("En attente des résultats...")

                        for r_num in range(1, total_rounds_wb + 1):
                            st.markdown(f"##### Tour {r_num}")
                            expected_count = max(1, nb_matches_r1 // (2**(r_num-1)))
                            cols_s = st.columns(min(4, expected_count) if expected_count > 0 else 1)
                            for m_num in range(1, expected_count + 1):
                                col = cols_s[(m_num - 1) % len(cols_s)]
                                m = tier_dict.get(f"WB_R{r_num}_M{m_num}")
                                draw_weekly_interactive_match(col, m, r_num, m_num)

                        st.divider()
                        if st.button("🚨 TERMINER LE TOURNOI ET ARCHIVER", type="primary", use_container_width=True):
                            success, msg = db.close_weekly_bracket(current_weekly['id'])
                            if success:
                                st.success(msg)
                                st.balloons()
                                st.rerun()
                            else:
                                st.error(msg)

    # ==========================================
    # 🗄️ SECTION ARCHIVES
    # ==========================================
    st.divider()
    st.header("🗄️ Les Archives du Fun")
    
    past_weeklys = db.get_past_weekly_tournaments()
    
    if not past_weeklys:
        st.info("Aucune archive pour le moment.")
    else:
        weekly_options = {}
        for pt in past_weeklys:
            date_str = pd.to_datetime(pt['event_date']).strftime('%d/%m/%Y')
            m_tag = "🎯" if pt.get("tournament_type") == "par_coup" else "🌳"
            weekly_options[f"{date_str} {m_tag} {pt['name']}"] = pt
            
        selected_weekly_name = st.selectbox("Sélectionnez un ancien tournoi :", list(weekly_options.keys()))
        selected_weekly = weekly_options[selected_weekly_name]
        st.markdown(f"**Règles :** *{selected_weekly.get('description', 'Classique')}*")
        
        if selected_weekly.get("tournament_type") == "par_coup":
            scores_data = db.get_weekly_scores(selected_weekly['id'])
            p_parts = db.get_weekly_participants(selected_weekly['id'])
            if scores_data:
                max_shot = max(s["shot_number"] for s in scores_data)
                board = {p["user_id"]: {"Joueur": p.get('profiles', {}).get('username', 'Inconnu'), "Total": 0} for p in p_parts}
                for s in range(1, max_shot + 1):
                    for uid in board: board[uid][f"Coup {s}"] = "-"
                for s in scores_data:
                    if s["user_id"] in board and not s["is_absent"] and s["score"] >= 0:
                        board[s["user_id"]][f"Coup {s['shot_number']}"] = s["score"]
                        board[s["user_id"]]["Total"] += s["score"]
                        
                sorted_board = sorted(list(board.values()), key=lambda x: x["Total"], reverse=True)
                current_rank = 1
                for i, row in enumerate(sorted_board):
                    if i > 0 and row["Total"] == sorted_board[i-1]["Total"]: row["Rang"] = current_rank
                    else: current_rank = i + 1; row["Rang"] = current_rank
                
                df_cols = ["Rang", "Joueur", "Total"] + [f"Coup {s}" for s in range(1, max_shot + 1)]
                st.markdown(draw_luxury_table(sorted_board, columns=df_cols), unsafe_allow_html=True)
        else:
            # --- 1. AFFICHAGE DE L'ARBRE PAPILLON DANS LES ARCHIVES ---
            matches = db.get_weekly_bracket_matches(selected_weekly['id'])
            if matches:
                import math
                nb_matches_r1 = 8
                total_rounds_wb = 4
                tier_dict = {m["bracket_match_id"]: m for m in matches}
                
                def render_weekly_css_bracket_archive(title):
                    def get_match_card_weekly_archive(r_num, m_num):
                        b_id = f"WB_R{r_num}_M{m_num}"
                        m = tier_dict.get(b_id)
                        
                        bg_color = "rgba(15, 23, 42, 0.9)"
                        border_color = "#C69C25" if r_num == total_rounds_wb else "rgba(198, 156, 37, 0.4)"
                        
                        c_html = f"<div style='background: {bg_color}; border: 1px solid {border_color}; border-radius: 8px; padding: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); margin: 5px 0;'>"
                        c_html += f"<div style='font-size: 10px; color: rgba(198, 156, 37, 0.7); text-align: center; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 1px;'>Match {m_num}</div>"
                        
                        if m:
                            p1_raw = m.get("player1_id")
                            p2_raw = m.get("player2_id")
                            
                            p1 = all_users.get(p1_raw, "Fantôme / BYE") if p1_raw else "Fantôme / BYE"
                            p2 = all_users.get(p2_raw, "Fantôme / BYE") if p2_raw else "Fantôme / BYE"
                            
                            s1 = int(m.get("score1") or 0)
                            s2 = int(m.get("score2") or 0)
                            
                            # Dans les archives, on assume que le match est terminé
                            w1 = "bold; color: white;" if s1 > s2 else "normal; color: #888;"
                            w2 = "bold; color: white;" if s2 > s1 else "normal; color: #888;"
                            c1_score = "#C69C25" if s1 > s2 else "#888"
                            c2_score = "#C69C25" if s2 > s1 else "#888"
                            
                            disp_s1 = str(s1)
                            disp_s2 = str(s2)
                            
                            if p1 == "Fantôme / BYE" and p2 == "Fantôme / BYE": 
                                disp_s1 = disp_s2 = ""
                            
                            c_html += f"<div style='display: flex; justify-content: space-between; font-weight: {w1}; margin-bottom: 5px;'><span style='overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 140px;'>{p1}</span><span style='color: {c1_score}; font-weight: bold;'>{disp_s1}</span></div>"
                            c_html += f"<div style='display: flex; justify-content: space-between; font-weight: {w2};'><span style='overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 140px;'>{p2}</span><span style='color: {c2_score}; font-weight: bold;'>{disp_s2}</span></div>"
                        else:
                            lbl = "Fantôme / BYE"
                            c_html += f"<div style='display: flex; justify-content: space-between; color: #888; margin-bottom: 5px;'><span>{lbl}</span><span></span></div><div style='display: flex; justify-content: space-between; color: #888;'><span>{lbl}</span><span></span></div>"
                        
                        c_html += "</div>"
                        return c_html

                    html = f"<h5 style='color: white; margin-top: 10px;'>{title}</h5>"
                    html += "<div style='display: flex; justify-content: flex-start; width: 100%; overflow-x: auto; padding-bottom: 20px; min-height: 400px;'>"
                    
                    # --- A. PARTIE GAUCHE ---
                    html += "<div style='display: flex; flex-direction: row;'>"
                    for r_num in range(1, total_rounds_wb):
                        html += "<div style='display: flex; flex-direction: column; justify-content: space-around; flex: 0 0 200px; margin-right: 30px;'>"
                        html += f"<div style='text-align: center; color: #ccc; font-weight: bold; margin-bottom: 10px; flex: 0 0 auto;'>Tour {r_num}</div>"
                        html += "<div style='display: flex; flex-direction: column; justify-content: space-around; flex: 1 1 auto;'>"
                        expected_count = max(1, nb_matches_r1 // (2**(r_num-1)))
                        half_count = expected_count // 2
                        for m_num in range(1, half_count + 1):
                            html += get_match_card_weekly_archive(r_num, m_num)
                        html += "</div></div>"
                    html += "</div>"
                    
                    # --- B. CENTRE (GRANDE FINALE) ---
                    html += "<div style='display: flex; flex-direction: column; justify-content: center; flex: 0 0 220px; margin: 0 10px; gap: 40px;'>"
                    html += "<div>"
                    html += "<div style='text-align: center; color: gold; font-weight: bold; margin-bottom: 10px; flex: 0 0 auto;'>👑 Finale</div>"
                    html += get_match_card_weekly_archive(total_rounds_wb, 1)
                    html += "</div>"
                    html += "</div>"
                    
                    # --- C. PARTIE DROITE (INVERSÉE) ---
                    html += "<div style='display: flex; flex-direction: row-reverse;'>"
                    for r_num in range(1, total_rounds_wb):
                        html += "<div style='display: flex; flex-direction: column; justify-content: space-around; flex: 0 0 200px; margin-left: 30px;'>"
                        html += f"<div style='text-align: center; color: #ccc; font-weight: bold; margin-bottom: 10px; flex: 0 0 auto;'>Tour {r_num}</div>"
                        html += "<div style='display: flex; flex-direction: column; justify-content: space-around; flex: 1 1 auto;'>"
                        expected_count = max(1, nb_matches_r1 // (2**(r_num-1)))
                        half_count = expected_count // 2
                        for m_num in range(half_count + 1, expected_count + 1):
                            html += get_match_card_weekly_archive(r_num, m_num)
                        html += "</div></div>"
                    html += "</div>"
                    
                    html += "</div>"
                    return html

                with st.expander("👀 Voir l'Arbre du Tournoi", expanded=True):
                    st.markdown(render_weekly_css_bracket_archive("🏆 Arbre Final"), unsafe_allow_html=True)
            
            # --- 2. AFFICHAGE DU CLASSEMENT FINAL EN DESSOUS ---
            st.markdown("#### 📊 Classement Final")
            p_parts = db.get_weekly_participants(selected_weekly['id'])
            if p_parts:
                real_parts = [p for p in p_parts if p.get('final_rank') is not None]
                if not real_parts:
                    archive_data = [{"Rang": "-", "Joueur": p.get('profiles', {}).get('username', 'Inconnu')} for p in p_parts]
                else:
                    p_parts_sorted = sorted(real_parts, key=lambda x: x.get('final_rank', 999))
                    archive_data = []
                    for p in p_parts_sorted:
                        r_val = p.get('final_rank')
                        r_str = f"{r_val}er" if r_val == 1 else f"{r_val}ème"
                        archive_data.append({
                            "Rang": r_str, 
                            "Joueur": p.get('profiles', {}).get('username', 'Inconnu')
                        })
                st.markdown(draw_luxury_table(archive_data), unsafe_allow_html=True)
