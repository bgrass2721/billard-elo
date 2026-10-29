import streamlit as st

from base_function_temp.draw_luxury_table import draw_luxury_table


def afficher(db, user):

    st.header("🏟️ Espace Grand Tournoi")

    # On sépare la vue Admin de la vue Spectateur
    is_admin = user.get("is_admin", False)

    if is_admin:
        tab_spectator, tab_admin = st.tabs(["Historique des tournois", "🛠️ Panel Admin Tournoi"])
    else:
        tab_spectator = st.container()  # Le joueur normal ne voit que ça

    # --- VUE SPECTATEUR (Publique) ---
    with tab_spectator:
        tournaments = db.get_grand_tournaments().data

        if not tournaments:
            st.info("Aucun Grand Tournoi n'a été organisé pour le moment.")
        else:
            # Sélecteur de tournoi pour le public
            t_map_spec = {f"{t['name']}": t for t in tournaments}
            selected_t_spec_name = st.selectbox("Sélectionnez un tournoi à regarder :", list(t_map_spec.keys()), key="spec_select")
            selected_t_spec = t_map_spec[selected_t_spec_name]

            st.divider()

            # Affichage de l'en-tête du tournoi
            status_map = {
                "draft": "🛠️ En préparation",
                "groups": "🟢 Phase de Poules en cours",
                "bracket": "⚔️ Phase Finale en cours",
                "completed": "🏁 Terminé"
            }
            st.markdown(f"### {selected_t_spec['name']}")
            st.caption(f"Statut : {status_map.get(selected_t_spec['status'], 'Inconnu')} | Format : {selected_t_spec['format']}")

            # --- CAS 1 : BROUILLON ---
            if selected_t_spec["status"] == "draft":
                st.info("Les inscriptions et le tirage des poules sont en cours. Revenez plus tard !")

            # --- CAS 2 & 3 : POULES ET ARBRE ---
            if selected_t_spec["status"] in ["groups", "bracket", "completed"]:
                st.markdown("#### 📊 Phase de Poules")
                matches_grp = db.get_gt_matches(selected_t_spec["id"], "group").data
                parts = db.get_tournament_participants(selected_t_spec["id"]).data
                all_users_spec = {p["id"]: p["username"] for p in db.get_leaderboard().data}

                if not parts:
                    st.write("Aucune poule générée.")
                else:
                    group_letters = sorted(list(set([p["group_name"] for p in parts if p["group_name"]])))

                    # Utilisation d'onglets pour une navigation mobile fluide
                    if group_letters:
                        tabs_poules = st.tabs([f"Poule {g}" for g in group_letters])
                        for idx, g in enumerate(group_letters):
                            with tabs_poules[idx]:
                                g_matches = [m for m in matches_grp if m["group_name"] == g]
                                g_parts = [p for p in parts if p["group_name"] == g]

                                # 1. On sépare les rounds
                                max_round = max([m.get("tie_break_round", 0) for m in g_matches]) if g_matches else 0
                                regular_matches = [m for m in g_matches if m.get("tie_break_round", 0) == 0]

                                # ==========================================
                                # 2. CLASSEMENT PHASE RÉGULIÈRE
                                # ==========================================
                                reg_standings = {}
                                for p in g_parts:
                                    reg_standings[p["user_id"]] = {"Nom": all_users_spec.get(p["user_id"], "?"), "V": 0, "D": 0, "Diff": 0, "Tie_V": 0, "Tie_Diff": 0}

                                for m in regular_matches:
                                    if m["status"] == "completed":
                                        s1, s2 = m["score1"], m["score2"]
                                        p1, p2 = m["player1_id"], m["player2_id"]
                                        if p1 in reg_standings:
                                            if s1 > s2:
                                                reg_standings[p1]["V"] += 1
                                            else:
                                                reg_standings[p1]["D"] += 1
                                            reg_standings[p1]["Diff"] += (s1 - s2)
                                        if p2 in reg_standings:
                                            if s2 > s1:
                                                reg_standings[p2]["V"] += 1
                                            else:
                                                reg_standings[p2]["D"] += 1
                                            reg_standings[p2]["Diff"] += (s2 - s1)

                                tie_matches_all = [m for m in g_matches if m.get("tie_break_round", 0) > 0]
                                for m in tie_matches_all:
                                    if m["status"] == "completed":
                                        s1, s2 = m["score1"], m["score2"]
                                        p1, p2 = m["player1_id"], m["player2_id"]
                                        if p1 in reg_standings:
                                            if s1 > s2:
                                                reg_standings[p1]["Tie_V"] += 1
                                            reg_standings[p1]["Tie_Diff"] += (s1 - s2)
                                        if p2 in reg_standings:
                                            if s2 > s1:
                                                reg_standings[p2]["Tie_V"] += 1
                                            reg_standings[p2]["Tie_Diff"] += (s2 - s1)

                                sorted_reg = sorted(reg_standings.values(), key=lambda x: (x["V"], x["Diff"], x["Tie_V"], x["Tie_Diff"]), reverse=True)

                                # --- NOUVEAU DESIGN VIP ---
                                display_reg = [{"Rang": i+1, "Joueur": x["Nom"], "V": x["V"], "D": x["D"], "Diff": x["Diff"]} for i, x in enumerate(sorted_reg)]
                                st.markdown(draw_luxury_table(display_reg, "📊 Classement Phase Régulière"), unsafe_allow_html=True)

                                # ==========================================
                                # 3. CLASSEMENT DÉPARTAGE (Si barrages)
                                # ==========================================
                                if max_round > 0:
                                    tie_matches = [m for m in g_matches if m.get("tie_break_round", 0) == max_round]
                                    tie_players = set()
                                    for m in tie_matches:
                                        if m["player1_id"]:
                                            tie_players.add(m["player1_id"])
                                        if m["player2_id"]:
                                            tie_players.add(m["player2_id"])

                                    tie_standings = {}
                                    for uid in tie_players:
                                        tie_standings[uid] = {"Nom": all_users_spec.get(uid, "?"), "V": 0, "D": 0, "Diff": 0}

                                    for m in tie_matches:
                                        if m["status"] == "completed":
                                            s1, s2 = m["score1"], m["score2"]
                                            p1, p2 = m["player1_id"], m["player2_id"]
                                            if p1 in tie_standings:
                                                if s1 > s2:
                                                    tie_standings[p1]["V"] += 1
                                                else:
                                                    tie_standings[p1]["D"] += 1
                                                tie_standings[p1]["Diff"] += (s1 - s2)
                                            if p2 in tie_standings:
                                                if s2 > s1:
                                                    tie_standings[p2]["V"] += 1
                                                else:
                                                    tie_standings[p2]["D"] += 1
                                                tie_standings[p2]["Diff"] += (s2 - s1)

                                    sorted_tie = sorted(tie_standings.values(), key=lambda x: (x["V"], x["Diff"]), reverse=True)

                                    # --- NOUVEAU DESIGN VIP ---
                                    display_tie = [{"Rang": i+1, "Joueur": x["Nom"], "V": x["V"], "D": x["D"], "Diff": x["Diff"]} for i, x in enumerate(sorted_tie)]
                                    st.markdown(draw_luxury_table(display_tie, f"🔥 Départage (Round {max_round})"), unsafe_allow_html=True)

                                # ==========================================
                                # 4. AFFICHAGE SÉPARÉ DES MATCHS (Panneau Sportif)
                                # ==========================================
                                st.write("")
                                st.markdown("<h4 style=\"font-family: 'Playfair Display', serif; color: #C69C25; border-bottom: 1px solid rgba(198,156,37,0.3); padding-bottom: 10px; margin-bottom: 15px;\">🎱 Matchs de la Poule</h4>", unsafe_allow_html=True)

                                for r in range(max_round + 1):
                                    r_matches = [m for m in g_matches if m.get("tie_break_round", 0) == r]
                                    if not r_matches:
                                        continue

                                    if max_round > 0:
                                        round_title = "Phase Régulière" if r == 0 else f"Barrages #{r}"
                                        st.markdown(f"<div style='color: #C69C25; font-size: 0.85em; text-transform: uppercase; letter-spacing: 1px; margin-top: 15px; margin-bottom: 10px; font-weight: 600;'>{round_title}</div>", unsafe_allow_html=True)

                                    for m in r_matches:
                                        p1_name = all_users_spec.get(m["player1_id"], "?")
                                        p2_name = all_users_spec.get(m["player2_id"], "?")

                                        match_html = "<div style='display: flex; justify-content: space-between; align-items: center; padding: 12px 15px; background: rgba(0,0,0,0.2); border-radius: 6px; margin-bottom: 8px; border-left: 3px solid #C69C25;'>"

                                        if m["status"] == "completed":
                                            match_html += f"<div style='flex: 1; text-align: right; font-weight: 600;'>{p1_name}</div>"
                                            match_html += f"<div style='flex: 0 0 80px; text-align: center; color: #C69C25; font-family: \"Playfair Display\", serif; font-size: 1.3em; font-weight: bold;'>{m['score1']} - {m['score2']}</div>"
                                            match_html += f"<div style='flex: 1; text-align: left; font-weight: 600;'>{p2_name}</div>"
                                        else:
                                            match_html += f"<div style='flex: 1; text-align: right; font-weight: 600; opacity: 0.7;'>{p1_name}</div>"
                                            match_html += "<div style='flex: 0 0 80px; text-align: center; color: #555; font-size: 0.9em; font-style: italic;'>vs ⏳</div>"
                                            match_html += f"<div style='flex: 1; text-align: left; font-weight: 600; opacity: 0.7;'>{p2_name}</div>"

                                        match_html += "</div>"
                                        st.markdown(match_html, unsafe_allow_html=True)

            # --- CAS 3 : ARBRE UNIQUEMENT ---
            if selected_t_spec["status"] in ["bracket", "completed"]:
                st.divider()
                st.markdown("#### 🌳 Phase Finale (Arbre)")

                matches_brk = db.get_gt_matches(selected_t_spec["id"], "bracket").data

                if not matches_brk:
                    st.info("L'arbre est en cours de construction.")
                else:
                    import math
                    nb_matches_r1 = 8 if "32" in selected_t_spec["format"] else 16
                    total_rounds_wb = int(math.log2(nb_matches_r1)) + 1
                    is_double_elim = "double" in selected_t_spec["format"]

                    # LA SOLUTION DÉFINITIVE : Génération d'un arbre HTML/Flexbox
                    def render_css_bracket(prefix, title):
                        tier_matches = [m for m in matches_brk if m["bracket_match_id"].startswith(prefix)]
                        tier_dict = {m["bracket_match_id"]: m for m in tier_matches}

                        # Fonction interne magique : Génère le code HTML d'un match
                        def get_match_card(r_num, m_num, is_gf=False, is_pf=False):
                            b_id = f"{prefix}_R{r_num}_M{m_num}"
                            m = tier_dict.get(b_id)

                            # --- DESIGN SNOOK'R VIP ---
                            bg_color = "rgba(15, 23, 42, 0.9)"  # Bleu nuit profond
                            border_color = "#C69C25" if is_gf else ("#CD7F32" if is_pf else "rgba(198, 156, 37, 0.4)")

                            c_html = f"<div style='background: {bg_color}; border: 1px solid {border_color}; border-radius: 8px; padding: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); margin: 5px 0;'>"
                            c_html += f"<div style='font-size: 10px; color: rgba(198, 156, 37, 0.7); text-align: center; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 1px;'>Match {m_num}</div>"

                            if m:
                                p1 = all_users_spec.get(m.get("player1_id"), "...") if m.get("player1_id") else "..."
                                p2 = all_users_spec.get(m.get("player2_id"), "...") if m.get("player2_id") else "..."
                                s1, s2 = m.get("score1", 0), m.get("score2", 0)

                                if m["status"] == "completed":
                                    podium_1_c = "#C69C25"  # Or Snook'R
                                    podium_2_c = "#E0FFFF"  # Argent
                                    podium_3_c = "#CD7F32"  # Bronze

                                    if is_gf:
                                        w1 = f"bold; color: {podium_1_c};" if s1 > s2 else f"bold; color: {podium_2_c};"
                                        w2 = f"bold; color: {podium_1_c};" if s2 > s1 else f"bold; color: {podium_2_c};"
                                        c1_score = podium_1_c if s1 > s2 else podium_2_c
                                        c2_score = podium_1_c if s2 > s1 else podium_2_c
                                    elif is_pf:
                                        w1 = f"bold; color: {podium_3_c};" if s1 > s2 else "normal; color: #888;"
                                        w2 = f"bold; color: {podium_3_c};" if s2 > s1 else "normal; color: #888;"
                                        c1_score = podium_3_c if s1 > s2 else "#888"
                                        c2_score = podium_3_c if s2 > s1 else "#888"
                                    else:
                                        w1 = "bold; color: white;" if s1 > s2 else "normal; color: #888;"
                                        w2 = "bold; color: white;" if s2 > s1 else "normal; color: #888;"
                                        c1_score = "#C69C25" if s1 > s2 else "#888"  # Score gagnant en Or
                                        c2_score = "#C69C25" if s2 > s1 else "#888"
                                else:
                                    w1 = w2 = "normal; color: white;"
                                    c1_score = c2_score = "transparent"
                                    if p1 == "..." and p2 == "...":
                                        s1 = s2 = ""

                                c_html += f"<div style='display: flex; justify-content: space-between; font-weight: {w1}; margin-bottom: 5px;'><span style='overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 140px;'>{p1}</span><span style='color: {c1_score}; font-weight: bold;'>{s1}</span></div>"
                                c_html += f"<div style='display: flex; justify-content: space-between; font-weight: {w2};'><span style='overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 140px;'>{p2}</span><span style='color: {c2_score}; font-weight: bold;'>{s2}</span></div>"
                            else:
                                c_html += "<div style='display: flex; justify-content: space-between; color: #888; margin-bottom: 5px;'><span>...</span></div>"
                                c_html += "<div style='display: flex; justify-content: space-between; color: #888;'><span>...</span></div>"

                            c_html += "</div>"
                            return c_html

                        html = f"<h5 style='color: white; margin-top: 10px;'>{title}</h5>"

                        # --- 1. DOUBLE ÉLIMINATION ou LOSER BRACKET (Classique de gauche à droite) ---
                        if is_double_elim or prefix == "LB":
                            has_reset = any(m["bracket_match_id"] == f"WB_R{total_rounds_wb + 2}_M1" for m in matches_brk)
                            if prefix == "WB":
                                num_rounds = total_rounds_wb + 2 if (has_reset and is_double_elim) else (total_rounds_wb + 1 if is_double_elim else total_rounds_wb)
                            else:
                                num_rounds = (total_rounds_wb - 1) * 2

                            html += f"<div style='display: flex; flex-direction: row; justify-content: flex-start; width: 100%; overflow-x: auto; padding-bottom: 20px; min-height: {'600px' if prefix == 'WB' else '400px'};'>"
                            for r_num in range(1, num_rounds + 1):
                                html += "<div style='display: flex; flex-direction: column; justify-content: space-around; flex: 0 0 200px; margin-right: 30px;'>"

                                is_final_col = (prefix == "WB" and r_num == total_rounds_wb + 1)

                                if is_final_col:
                                    col_title = "👑 Grande Finale"
                                elif prefix == "WB" and r_num == total_rounds_wb + 2:
                                    col_title = "⚔️ Bracket Reset"
                                else:
                                    col_title = f"Tour {r_num}"
                                html += f"<div style='text-align: center; color: #ccc; font-weight: bold; margin-bottom: 10px; flex: 0 0 auto;'>{col_title}</div>"

                                if prefix == "WB":
                                    virtual_round = min(r_num, total_rounds_wb)
                                    expected_count = max(1, nb_matches_r1 // (2**(virtual_round-1)))
                                else:
                                    virtual_round = math.ceil(r_num / 2)
                                    expected_count = max(1, nb_matches_r1 // (2**virtual_round))

                                html += "<div style='display: flex; flex-direction: column; justify-content: space-around; flex: 1 1 auto;'>"
                                for m_num in range(1, expected_count + 1):
                                    is_gf = (prefix == "WB" and r_num > total_rounds_wb)
                                    html += get_match_card(r_num, m_num, is_gf)

                                html += "</div></div>"
                            html += "</div>"

                        # --- 2. SINGLE ÉLIMINATION (Format Symétrique Papillon) ---
                        else:
                            html += "<div style='display: flex; justify-content: flex-start; width: 100%; overflow-x: auto; padding-bottom: 20px; min-height: 400px;'>"

                            # A. PARTIE GAUCHE
                            html += "<div style='display: flex; flex-direction: row;'>"
                            for r_num in range(1, total_rounds_wb):
                                html += "<div style='display: flex; flex-direction: column; justify-content: space-around; flex: 0 0 200px; margin-right: 30px;'>"
                                html += f"<div style='text-align: center; color: #ccc; font-weight: bold; margin-bottom: 10px; flex: 0 0 auto;'>Tour {r_num}</div>"
                                html += "<div style='display: flex; flex-direction: column; justify-content: space-around; flex: 1 1 auto;'>"
                                expected_count = max(1, nb_matches_r1 // (2**(r_num-1)))
                                half_count = expected_count // 2
                                for m_num in range(1, half_count + 1):
                                    html += get_match_card(r_num, m_num)
                                html += "</div></div>"
                            html += "</div>"

                            # B. CENTRE (Grande Finale + Petite Finale)
                            html += "<div style='display: flex; flex-direction: column; justify-content: center; flex: 0 0 220px; margin: 0 10px; gap: 40px;'>"

                            html += "<div>"
                            html += "<div style='text-align: center; color: gold; font-weight: bold; margin-bottom: 10px; flex: 0 0 auto;'>👑 Finale</div>"
                            html += get_match_card(total_rounds_wb, 1, is_gf=True)
                            html += "</div>"

                            html += "<div>"
                            html += "<div style='text-align: center; color: #CD7F32; font-weight: bold; margin-bottom: 10px; flex: 0 0 auto;'>🥉 Petite Finale</div>"
                            html += get_match_card(total_rounds_wb, 2, is_gf=False, is_pf=True)
                            html += "</div>"

                            html += "</div>"

                            # C. PARTIE DROITE (On inverse l'ordre !)
                            html += "<div style='display: flex; flex-direction: row-reverse;'>"
                            for r_num in range(1, total_rounds_wb):
                                html += "<div style='display: flex; flex-direction: column; justify-content: space-around; flex: 0 0 200px; margin-left: 30px;'>"
                                html += f"<div style='text-align: center; color: #ccc; font-weight: bold; margin-bottom: 10px; flex: 0 0 auto;'>Tour {r_num}</div>"
                                html += "<div style='display: flex; flex-direction: column; justify-content: space-around; flex: 1 1 auto;'>"
                                expected_count = max(1, nb_matches_r1 // (2**(r_num-1)))
                                half_count = expected_count // 2
                                for m_num in range(half_count + 1, expected_count + 1):
                                    html += get_match_card(r_num, m_num)
                                html += "</div></div>"
                            html += "</div>"

                            html += "</div>"

                        return html

                    # Affichage via la fonction markdown HTML
                    st.markdown(render_css_bracket("WB", "🏆 L'Arbre du Tournoi"), unsafe_allow_html=True)

                    if is_double_elim:
                        st.divider()
                        st.markdown(render_css_bracket("LB", "💀 Loser Bracket (Repêchages)"), unsafe_allow_html=True)

    # --- VUE ADMIN (Privée) ---
    if is_admin:
        with tab_admin:
            st.header("⚙️ Administration des Tournois")

            # --- OUTIL : CRÉATION DE FANTÔMES ---
            with st.expander("👻 Créer un Joueur Fantôme (Pour les archives)"):
                st.info("Ces joueurs apparaîtront dans la liste pour pouvoir être ajoutés à un tournoi, mais ils n'auront pas de compte pour se connecter et n'impacteront pas le classement général.")

                c1, c2 = st.columns([3, 1])
                ghost_name = c1.text_input("Prénom et Nom du joueur", placeholder="Ex: Paul Dupont", label_visibility="collapsed")

                if c2.button("Créer le joueur", use_container_width=True):
                    if len(ghost_name) < 3:
                        st.error("Le nom doit contenir au moins 3 caractères.")
                    else:
                        final_name = f"{ghost_name}"
                        success, msg = db.create_ghost_player(final_name)
                        if success:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
            st.divider()

            # --- OUTIL : FUSION FANTÔME -> VRAI JOUEUR ---
            with st.expander("🔄 Remplacer un Fantôme par un Vrai Joueur"):
                st.info("Transférez tout l'historique d'un profil fantôme vers le vrai compte d'un joueur qui vient de s'inscrire, puis supprimez le fantôme.")

                all_profiles = db.get_all_profiles().data
                all_profiles = sorted(all_profiles, key=lambda x: x["username"].lower() if x.get("username") else "")

                ghost_profiles = [p for p in all_profiles if p.get("is_ghost") is True]
                real_profiles = [p for p in all_profiles if p.get("is_ghost") is not True]

                ghost_map = {f"{p['username']} ({p['id'][:4]})": p["id"] for p in ghost_profiles if p.get("username")}
                real_map = {f"{p['username']} ({p['id'][:4]})": p["id"] for p in real_profiles if p.get("username")}

                c1, c2 = st.columns(2)
                ghost_choice = c1.selectbox("1. Le profil Fantôme (à supprimer)", ["-- Sélectionner --"] + list(ghost_map.keys()), key="merge_ghost")
                real_choice = c2.selectbox("2. Le Vrai Compte (qui récupère l'historique)", ["-- Sélectionner --"] + list(real_map.keys()), key="merge_real")

                if st.button("Fusionner et Remplacer", use_container_width=True, type="primary"):
                    if ghost_choice == "-- Sélectionner --" or real_choice == "-- Sélectionner --":
                        st.error("Veuillez sélectionner les deux profils à fusionner.")
                    else:
                        ghost_id = ghost_map[ghost_choice]
                        real_id = real_map[real_choice]

                        success, msg = db.merge_ghost_to_real(ghost_id, real_id)
                        if success:
                            st.success(msg)
                            st.balloons()
                            st.rerun()
                        else:
                            st.error(msg)

            st.subheader("1. Créer un nouveau tournoi")
            with st.form("new_tournament_form"):
                t_name = st.text_input("Nom de l'événement (ex: Grand Open d'Hiver)")
                t_format = st.selectbox("Format", [
                    "32_single",
                    "64_single",
                    "32_double"
                ])

                if st.form_submit_button("Créer le tournoi (Brouillon)"):
                    if not t_name:
                        st.error("Veuillez donner un nom au tournoi.")
                    else:
                        success, data_or_err = db.create_grand_tournament(t_name, t_format)
                        if success:
                            st.success("Tournoi créé avec succès ! Vous pouvez maintenant gérer les inscrits.")
                            st.rerun()
                        else:
                            st.error(data_or_err)

            st.divider()

            # --- 2. GESTION DES TOURNOIS EXISTANTS ---
            st.subheader("2. Gérer un tournoi existant")

            if not tournaments:
                st.write("Aucun tournoi à gérer pour le moment.")
            else:
                t_map = {f"{t['name']} ({t['format']} - {t['status']})": t for t in tournaments}
                selected_t_name = st.selectbox("Sélectionnez le tournoi à administrer :", list(t_map.keys()))
                selected_t = t_map[selected_t_name]

                # ==========================================
                # PHASE : BROUILLON (DRAFT & POULES)
                # ==========================================
                if selected_t["status"] == "draft":
                    st.info("📝 Ce tournoi est en préparation. Constituez vos poules !")

                    all_app_users = db.get_all_profiles().data
                    all_app_users = sorted(all_app_users, key=lambda x: x["username"].lower() if x.get("username") else "")
                    user_options = {p["username"]: p["id"] for p in all_app_users if p.get("username")}

                    existing_parts = db.get_tournament_participants(selected_t["id"]).data
                    current_groups = {}
                    for ep in existing_parts:
                        g = ep.get("group_name")
                        uname = ep.get("profiles", {}).get("username")
                        if g and uname:
                            if g not in current_groups:
                                current_groups[g] = []
                            current_groups[g].append(uname)

                    nb_groups = 8 if "32" in selected_t["format"] else 16
                    group_letters = [chr(65+i) for i in range(nb_groups)]

                    st.write("Sélectionnez les joueurs pour chaque poule (4 conseillés).")

                    for g in group_letters:
                        key = f"draft_{selected_t['id']}_{g}"
                        if key not in st.session_state:
                            st.session_state[key] = [val for val in current_groups.get(g, []) if val in user_options]

                    all_selected_players = set()
                    for g in group_letters:
                        key = f"draft_{selected_t['id']}_{g}"
                        all_selected_players.update(st.session_state[key])

                    cols = st.columns(2)
                    selections = {}

                    for i, g in enumerate(group_letters):
                        col = cols[i % 2]
                        key = f"draft_{selected_t['id']}_{g}"

                        available_players = [
                            p for p in user_options 
                            if p not in all_selected_players or p in st.session_state[key]
                        ]

                        selections[g] = col.multiselect(
                            f"Poule {g}", 
                            options=available_players, 
                            key=key,
                            max_selections=5
                        )

                    if st.button("💾 Sauvegarder les poules"):
                        flat_data = []
                        for g, unames in selections.items():
                            for uname in unames:
                                flat_data.append({
                                    "user_id": user_options[uname],
                                    "group_name": g
                                })

                        success, msg = db.save_tournament_groups(selected_t["id"], flat_data)
                        if success:
                            st.success(msg)
                            for g in group_letters:
                                del st.session_state[f"draft_{selected_t['id']}_{g}"]
                            st.rerun()
                        else:
                            st.error(msg)

                    st.write("")
                    if st.button("🏁 Verrouiller et Lancer la phase de Poules", type="primary"):
                        total_inscrits = len(existing_parts)
                        if total_inscrits < 2:
                            st.error("Il faut au moins 2 joueurs pour lancer un tournoi.")
                        else:
                            db.generate_group_matches(selected_t["id"])
                            st.success("Le tournoi est lancé ! Les matchs de poule sont générés.")
                            st.balloons()
                            st.rerun()

                # ==========================================
                # PHASE : POULES (SAISIE DES SCORES)
                # ==========================================
                elif selected_t["status"] == "groups":
                    st.success("🟢 Phase de poules en cours.")

                    matches = db.get_gt_matches(selected_t["id"], "group").data
                    participants = db.get_tournament_participants(selected_t["id"]).data
                    all_users = {p["id"]: p["username"] for p in db.get_all_profiles().data}

                    group_letters = sorted(list(set([m["group_name"] for m in matches])))

                    for g in group_letters:
                        with st.expander(f"📊 Gestion de la Poule {g}", expanded=True):
                            g_matches = [m for m in matches if m["group_name"] == g]
                            g_parts = [p for p in participants if p["group_name"] == g]

                            # 1. On sépare les matchs réguliers des matchs de barrage
                            max_round = max([m.get("tie_break_round", 0) for m in g_matches]) if g_matches else 0
                            regular_matches = [m for m in g_matches if m.get("tie_break_round", 0) == 0]
                            current_round_matches = [m for m in g_matches if m.get("tie_break_round", 0) == max_round]

                            # ==========================================
                            # 2. CLASSEMENT DE LA PHASE RÉGULIÈRE (Intouchable !)
                            # ==========================================
                            reg_standings = {}
                            for p in g_parts:
                                reg_standings[p["user_id"]] = {"Nom": all_users.get(p["user_id"], "?"), "V": 0, "D": 0, "Diff": 0}

                            for m in regular_matches:
                                if m["status"] == "completed":
                                    s1, s2 = m["score1"], m["score2"]
                                    p1, p2 = m["player1_id"], m["player2_id"]
                                    if p1 in reg_standings:
                                        if s1 > s2:
                                            reg_standings[p1]["V"] += 1
                                        else:
                                            reg_standings[p1]["D"] += 1
                                        reg_standings[p1]["Diff"] += (s1 - s2)
                                    if p2 in reg_standings:
                                        if s2 > s1:
                                            reg_standings[p2]["V"] += 1
                                        else:
                                            reg_standings[p2]["D"] += 1
                                        reg_standings[p2]["Diff"] += (s2 - s1)

                            sorted_reg = sorted(reg_standings.values(), key=lambda x: (x["V"], x["Diff"]), reverse=True)

                            # --- NOUVEAU DESIGN VIP ---
                            display_reg = [{"Rang": i+1, "Joueur": x["Nom"], "V": x["V"], "D": x["D"], "Diff": x["Diff"]} for i, x in enumerate(sorted_reg)]
                            st.markdown(draw_luxury_table(display_reg, "📊 Classement Phase Régulière"), unsafe_allow_html=True)

                            # ==========================================
                            # 3. CLASSEMENT DU DÉPARTAGE EN COURS
                            # ==========================================
                            if max_round > 0:
                                tie_matches = [m for m in g_matches if m.get("tie_break_round", 0) == max_round]

                                tie_players = set()
                                for m in tie_matches:
                                    if m["player1_id"]:
                                        tie_players.add(m["player1_id"])
                                    if m["player2_id"]:
                                        tie_players.add(m["player2_id"])

                                tie_standings = {}
                                for uid in tie_players:
                                    tie_standings[uid] = {"Nom": all_users.get(uid, "?"), "V": 0, "D": 0, "Diff": 0}

                                for m in tie_matches:
                                    if m["status"] == "completed":
                                        s1, s2 = m["score1"], m["score2"]
                                        p1, p2 = m["player1_id"], m["player2_id"]
                                        if p1 in tie_standings:
                                            if s1 > s2:
                                                tie_standings[p1]["V"] += 1
                                            else:
                                                tie_standings[p1]["D"] += 1
                                            tie_standings[p1]["Diff"] += (s1 - s2)
                                        if p2 in tie_standings:
                                            if s2 > s1:
                                                tie_standings[p2]["V"] += 1
                                            else:
                                                tie_standings[p2]["D"] += 1
                                            tie_standings[p2]["Diff"] += (s2 - s1)

                                sorted_tie = sorted(tie_standings.values(), key=lambda x: (x["V"], x["Diff"]), reverse=True)

                                # --- NOUVEAU DESIGN VIP ---
                                display_tie = [{"Rang": i+1, "Joueur": x["Nom"], "V": x["V"], "D": x["D"], "Diff": x["Diff"]} for i, x in enumerate(sorted_tie)]
                                st.markdown(draw_luxury_table(display_tie, f"🔥 Classement du Départage (Round {max_round})"), unsafe_allow_html=True)

                            st.divider()
                            st.markdown("<h4 style=\"font-family: 'Playfair Display', serif; color: #C69C25;\">✏️ Saisie des Matchs</h4>", unsafe_allow_html=True)

                            # 3. Affichage visuel séparé par Round (Régulier vs Barrages)
                            for r in range(max_round + 1):
                                r_matches = [m for m in g_matches if m.get("tie_break_round", 0) == r]
                                if not r_matches:
                                    continue

                                if r == 0:
                                    st.markdown("🎯 *Phase Régulière*")
                                else:
                                    st.markdown(f"🔥 **Matchs de Barrage #{r}**")

                                for m in r_matches:
                                    p1_name = all_users.get(m["player1_id"], "?")
                                    p2_name = all_users.get(m["player2_id"], "?")
                                    is_done = m["status"] == "completed"

                                    c1, c2, c3, c4, c5 = st.columns([3, 1, 0.5, 1, 2])
                                    c1.write(f"**{p1_name}** vs **{p2_name}**" + (" ✅" if is_done else ""))

                                    score1 = c2.number_input("S1", min_value=0, max_value=9, value=m["score1"], key=f"s1_{m['id']}", label_visibility="collapsed")
                                    c3.write("-")
                                    score2 = c4.number_input("S2", min_value=0, max_value=9, value=m["score2"], key=f"s2_{m['id']}", label_visibility="collapsed")

                                    btn_label = "Mettre à jour" if is_done else "Valider"
                                    if c5.button(btn_label, key=f"btn_{m['id']}"):
                                        if score1 == score2:
                                            st.error("Il ne peut pas y avoir d'égalité au billard !")
                                        else:
                                            success = db.update_gt_match_score(m["id"], score1, score2, m["player1_id"], m["player2_id"])
                                            if success:
                                                st.rerun()

                            # 4. LE BOUTON MAGIQUE DE L'ARBITRE
                            # Il n'apparaît que si tous les matchs du round actuel sont finis
                            all_done = all(m["status"] == "completed" for m in current_round_matches)
                            if all_done and current_round_matches:
                                st.write("")
                                if st.button(f"🔍 Valider la Poule {g} (Vérifier les égalités)", key=f"check_tie_{g}", type="primary"):
                                    success, msg = db.check_and_create_tie_breaks(selected_t["id"], g)
                                    if success:
                                        if "générés" in msg.lower():
                                            st.error(msg)  # S'affiche en rouge pour alerter l'admin qu'il y a des barrages !
                                        else:
                                            st.success(msg)  # S'affiche en vert : la poule est saine.
                                        st.rerun()
                                    else:
                                        st.warning(msg)

                    # ==========================================
                    # LE TIRAGE AU SORT (TRANSITION VERS L'ARBRE)
                    # ==========================================
                    st.divider()
                    st.subheader("🎲 Tirage au sort de la Phase Finale")
                    st.info("Une fois TOUS les matchs de poule terminés, faites votre tirage au sort physique et saisissez les rencontres ci-dessous. Seuls les 2 premiers de chaque poule sont sélectionnables.")

                    qualified_players = []
                    for g in group_letters:
                        g_matches = [m for m in matches if m["group_name"] == g]
                        g_parts = [p for p in participants if p["group_name"] == g]
                        temp_standings = {p["user_id"]: {"V": 0, "Diff": 0} for p in g_parts}

                        for m in g_matches:
                            if m["status"] == "completed":
                                s1, s2 = m["score1"], m["score2"]
                                p1, p2 = m["player1_id"], m["player2_id"]
                                if p1 in temp_standings:
                                    if s1 > s2:
                                        temp_standings[p1]["V"] += 1
                                    temp_standings[p1]["Diff"] += (s1 - s2)
                                if p2 in temp_standings:
                                    if s2 > s1:
                                        temp_standings[p2]["V"] += 1
                                    temp_standings[p2]["Diff"] += (s2 - s1)

                        sorted_uids = sorted(temp_standings.keys(), key=lambda uid: (temp_standings[uid]["V"], temp_standings[uid]["Diff"]), reverse=True)
                        qualified_players.extend(sorted_uids[:2])

                    nb_matches_r1 = 8 if "32" in selected_t["format"] else 16

                    for i in range(nb_matches_r1):
                        if f"r1_m{i}_p1_{selected_t['id']}" not in st.session_state:
                            st.session_state[f"r1_m{i}_p1_{selected_t['id']}"] = None
                        if f"r1_m{i}_p2_{selected_t['id']}" not in st.session_state:
                            st.session_state[f"r1_m{i}_p2_{selected_t['id']}"] = None

                    all_selected_in_draw = set()
                    for i in range(nb_matches_r1):
                        val_p1 = st.session_state.get(f"r1_m{i}_p1_{selected_t['id']}")
                        val_p2 = st.session_state.get(f"r1_m{i}_p2_{selected_t['id']}")
                        if val_p1:
                            all_selected_in_draw.add(val_p1)
                        if val_p2:
                            all_selected_in_draw.add(val_p2)

                    st.markdown("#### 🗺️ Cartographie de l'arbre")
                    st.info("Utilisez ce plan pour savoir où placer vos joueurs. Les vainqueurs se dirigent vers le centre.")

                    # --- DESSIN DU SQUELETTE DE L'ARBRE ---
                    with st.container(border=True):
                        import math
                        nb_matches_r1 = 8 if "32" in selected_t["format"] else 16
                        total_rounds_wb = int(math.log2(nb_matches_r1)) + 1
                        is_double_elim = "double" in selected_t["format"]

                        html_map = "<div style='display: flex; justify-content: flex-start; width: 100%; overflow-x: auto; padding-bottom: 10px; zoom: 0.85;'>"

                        if is_double_elim:
                            html_map += "<div style='display: flex; flex-direction: row;'>"
                            for r_num in range(1, total_rounds_wb + 1):
                                html_map += "<div style='display: flex; flex-direction: column; justify-content: space-around; flex: 0 0 140px; margin-right: 15px;'>"
                                html_map += f"<div style='text-align: center; color: #ccc; font-weight: bold; margin-bottom: 10px;'>Tour {r_num}</div>"

                                expected_count = max(1, nb_matches_r1 // (2**(r_num-1)))
                                html_map += "<div style='display: flex; flex-direction: column; justify-content: space-around; flex: 1 1 auto;'>"
                                for m_num in range(1, expected_count + 1):
                                    bg_color = "rgba(198, 156, 37, 0.2)" if r_num == 1 else "rgba(15, 23, 42, 0.5)"
                                    border_color = "#C69C25" if r_num == 1 else "#444"
                                    text_color = "white" if r_num == 1 else "#888"
                                    html_map += f"<div style='background-color: {bg_color}; border: 1px solid {border_color}; border-radius: 6px; padding: 15px 5px; text-align: center; margin: 4px 0;'><strong style='color: {text_color}; font-size: 14px;'>Match {m_num}</strong></div>"
                                html_map += "</div></div>"
                            html_map += "</div>"

                        else:
                            # 1. GAUCHE
                            html_map += "<div style='display: flex; flex-direction: row;'>"
                            for r_num in range(1, total_rounds_wb):
                                html_map += "<div style='display: flex; flex-direction: column; justify-content: space-around; flex: 0 0 120px; margin: 0 10px;'>"
                                html_map += f"<div style='text-align: center; color: #ccc; font-weight: bold; margin-bottom: 10px;'>Tour {r_num}</div>"

                                expected_count = max(1, nb_matches_r1 // (2**(r_num-1)))
                                half_count = expected_count // 2

                                html_map += "<div style='display: flex; flex-direction: column; justify-content: space-around; flex: 1 1 auto;'>"
                                for m_num in range(1, half_count + 1):
                                    bg_color = "rgba(198, 156, 37, 0.2)" if r_num == 1 else "rgba(15, 23, 42, 0.5)"
                                    border_color = "#C69C25" if r_num == 1 else "#444"
                                    text_color = "white" if r_num == 1 else "#888"
                                    html_map += f"<div style='background-color: {bg_color}; border: 1px solid {border_color}; border-radius: 6px; padding: 10px 5px; text-align: center; margin: 4px 0;'><strong style='color: {text_color}; font-size: 13px;'>Match {m_num}</strong></div>"
                                html_map += "</div></div>"
                            html_map += "</div>"

                            # 2. CENTRE
                            html_map += "<div style='display: flex; flex-direction: column; justify-content: space-around; flex: 0 0 140px; margin: 0 15px;'>"
                            html_map += "<div style='text-align: center; color: gold; font-weight: bold; margin-bottom: 10px;'>👑 Finale</div>"
                            html_map += "<div style='display: flex; flex-direction: column; justify-content: space-around; flex: 1 1 auto;'>"
                            html_map += "<div style='background-color: rgba(255,215,0,0.1); border: 1px solid gold; border-radius: 6px; padding: 15px 5px; text-align: center; margin: 4px 0;'><strong style='color: white; font-size: 14px;'>Match 1</strong></div>"
                            html_map += "</div></div>"

                            # 3. DROITE
                            html_map += "<div style='display: flex; flex-direction: row-reverse;'>"
                            for r_num in range(1, total_rounds_wb):
                                html_map += "<div style='display: flex; flex-direction: column; justify-content: space-around; flex: 0 0 120px; margin: 0 10px;'>"
                                html_map += f"<div style='text-align: center; color: #ccc; font-weight: bold; margin-bottom: 10px;'>Tour {r_num}</div>"

                                expected_count = max(1, nb_matches_r1 // (2**(r_num-1)))
                                half_count = expected_count // 2

                                html_map += "<div style='display: flex; flex-direction: column; justify-content: space-around; flex: 1 1 auto;'>"
                                for m_num in range(half_count + 1, expected_count + 1):
                                    bg_color = "rgba(198, 156, 37, 0.2)" if r_num == 1 else "rgba(15, 23, 42, 0.5)"
                                    border_color = "#C69C25" if r_num == 1 else "#444"
                                    text_color = "white" if r_num == 1 else "#888"
                                    html_map += f"<div style='background-color: {bg_color}; border: 1px solid {border_color}; border-radius: 6px; padding: 10px 5px; text-align: center; margin: 4px 0;'><strong style='color: {text_color}; font-size: 13px;'>Match {m_num}</strong></div>"
                                html_map += "</div></div>"
                            html_map += "</div>"

                        html_map += "</div>"
                        st.markdown(html_map, unsafe_allow_html=True)
                    st.divider()

                    # 4. Interface du Tirage
                    selections = []
                    cols = st.columns(2)

                    for i in range(nb_matches_r1):
                        col = cols[i % 2]
                        with col.container(border=True):
                            st.markdown(f"**Match {i+1}**")

                            curr_p1 = st.session_state.get(f"r1_m{i}_p1_{selected_t['id']}")
                            avail_p1 = [p for p in qualified_players if p not in all_selected_in_draw or p == curr_p1]

                            p1 = st.selectbox(
                                "Joueur 1", 
                                options=avail_p1, 
                                format_func=lambda x: all_users.get(x, "Sélectionner...") if x else "Sélectionner...", 
                                index=avail_p1.index(curr_p1) if curr_p1 in avail_p1 else None,
                                key=f"r1_m{i}_p1_{selected_t['id']}",
                                placeholder="Sélectionner..."
                            )

                            curr_p2 = st.session_state.get(f"r1_m{i}_p2_{selected_t['id']}")
                            avail_p2 = [p for p in qualified_players if p not in all_selected_in_draw or p == curr_p2]

                            p2 = st.selectbox(
                                "Joueur 2", 
                                options=avail_p2, 
                                format_func=lambda x: all_users.get(x, "Sélectionner...") if x else "Sélectionner...", 
                                index=avail_p2.index(curr_p2) if curr_p2 in avail_p2 else None,
                                key=f"r1_m{i}_p2_{selected_t['id']}",
                                placeholder="Sélectionner..."
                            )
                            selections.append((p1, p2))

                    st.write("")
                    if st.button("⚔️ Valider le Tirage et Lancer l'Arbre", type="primary"):
                        if any(p1 is None or p2 is None for p1, p2 in selections):
                            st.error("⚠️ Veuillez remplir tous les matchs du premier tour avec les qualifiés.")
                        else:
                            flat_list = [p for pair in selections for p in pair]
                            if len(flat_list) != len(set(flat_list)):
                                st.error("⚠️ Erreur : Un joueur a été sélectionné plusieurs fois !")
                            else:
                                db.generate_bracket_matches(selected_t["id"], selections)
                                for i in range(nb_matches_r1):
                                    st.session_state.pop(f"r1_m{i}_p1_{selected_t['id']}", None)
                                    st.session_state.pop(f"r1_m{i}_p2_{selected_t['id']}", None)

                                st.success("Tirage au sort validé ! Transition vers l'arbre final...")
                                st.balloons()
                                st.rerun()

                # ==========================================
                # PHASE : ARBRE FINAL (BRACKET)
                # ==========================================
                elif selected_t["status"] == "bracket":
                    st.success("⚔️ Phase finale en cours !")

                    matches = db.get_gt_matches(selected_t["id"], "bracket").data
                    all_users = {p["id"]: p["username"] for p in db.get_all_profiles().data}

                    if not matches:
                        st.error("Aucun match d'arbre trouvé.")
                    else:
                        import math
                        nb_matches_r1 = 8 if "32" in selected_t["format"] else 16
                        total_rounds_wb = int(math.log2(nb_matches_r1)) + 1
                        is_double_elim = "double" in selected_t["format"]

                        # --- AFFICHAGE VISUEL DE L'ARBRE (PAPILLON) ---
                        with st.expander("👀 Voir l'arbre visuel en direct", expanded=True):
                            def render_css_bracket_admin(prefix, title):
                                tier_matches = [m for m in matches if m["bracket_match_id"].startswith(prefix)]
                                tier_dict = {m["bracket_match_id"]: m for m in tier_matches}

                                def get_match_card_admin(r_num, m_num, is_gf=False, is_pf=False):
                                    b_id = f"{prefix}_R{r_num}_M{m_num}"
                                    m = tier_dict.get(b_id)

                                    # --- DESIGN SNOOK'R VIP ---
                                    bg_color = "rgba(15, 23, 42, 0.9)"
                                    border_color = "#C69C25" if is_gf else ("#CD7F32" if is_pf else "rgba(198, 156, 37, 0.4)")

                                    c_html = f"<div style='background: {bg_color}; border: 1px solid {border_color}; border-radius: 8px; padding: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); margin: 5px 0;'>"
                                    c_html += f"<div style='font-size: 10px; color: rgba(198, 156, 37, 0.7); text-align: center; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 1px;'>Match {m_num}</div>"

                                    if m:
                                        p1 = all_users.get(m.get("player1_id"), "...") if m.get("player1_id") else "..."
                                        p2 = all_users.get(m.get("player2_id"), "...") if m.get("player2_id") else "..."
                                        s1, s2 = m.get("score1", 0), m.get("score2", 0)

                                        if m["status"] == "completed":
                                            podium_1_c = "#C69C25"
                                            podium_2_c = "#E0FFFF"
                                            podium_3_c = "#CD7F32"

                                            if is_gf:
                                                w1 = f"bold; color: {podium_1_c};" if s1 > s2 else f"bold; color: {podium_2_c};"
                                                w2 = f"bold; color: {podium_1_c};" if s2 > s1 else f"bold; color: {podium_2_c};"
                                                c1_score = podium_1_c if s1 > s2 else podium_2_c
                                                c2_score = podium_1_c if s2 > s1 else podium_2_c
                                            elif is_pf:
                                                w1 = f"bold; color: {podium_3_c};" if s1 > s2 else "normal; color: #888;"
                                                w2 = f"bold; color: {podium_3_c};" if s2 > s1 else "normal; color: #888;"
                                                c1_score = podium_3_c if s1 > s2 else "transparent"
                                                c2_score = podium_3_c if s2 > s1 else "transparent"
                                            else:
                                                w1 = "bold; color: white;" if s1 > s2 else "normal; color: #888;"
                                                w2 = "bold; color: white;" if s2 > s1 else "normal; color: #888;"
                                                c1_score = "#C69C25" if s1 > s2 else "transparent"
                                                c2_score = "#C69C25" if s2 > s1 else "transparent"
                                        else:
                                            w1 = w2 = "normal; color: white;"
                                            c1_score = c2_score = "transparent"
                                            if p1 == "..." and p2 == "...":
                                                s1 = s2 = ""

                                        c_html += f"<div style='display: flex; justify-content: space-between; font-weight: {w1}; margin-bottom: 5px;'><span style='overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 120px;'>{p1}</span><span style='color: {c1_score}; font-weight: bold;'>{s1}</span></div>"
                                        c_html += f"<div style='display: flex; justify-content: space-between; font-weight: {w2};'><span style='overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 120px;'>{p2}</span><span style='color: {c2_score}; font-weight: bold;'>{s2}</span></div>"
                                    else:
                                        c_html += "<div style='display: flex; justify-content: space-between; color: #888; margin-bottom: 5px;'><span>...</span></div><div style='display: flex; justify-content: space-between; color: #888;'><span>...</span></div>"

                                    c_html += "</div>"
                                    return c_html

                                html = f"<h5 style='color: white; margin-top: 10px;'>{title}</h5>"

                                if is_double_elim or prefix == "LB":
                                    has_reset = any(m["bracket_match_id"] == f"WB_R{total_rounds_wb + 2}_M1" for m in matches)
                                    if prefix == "WB":
                                        num_rounds = total_rounds_wb + 2 if (has_reset and is_double_elim) else (total_rounds_wb + 1 if is_double_elim else total_rounds_wb)
                                    else:
                                        num_rounds = (total_rounds_wb - 1) * 2

                                    html += f"<div style='display: flex; flex-direction: row; justify-content: flex-start; width: 100%; overflow-x: auto; padding-bottom: 20px; min-height: {'600px' if prefix == 'WB' else '400px'}; zoom: 0.8;'>"
                                    for r_num in range(1, num_rounds + 1):
                                        html += "<div style='display: flex; flex-direction: column; justify-content: space-around; flex: 0 0 180px; margin-right: 20px;'>"
                                        if prefix == "WB" and r_num == total_rounds_wb + 1:
                                            col_title = "👑 Finale"
                                        elif prefix == "WB" and r_num == total_rounds_wb + 2:
                                            col_title = "⚔️ Reset"
                                        else:
                                            col_title = f"Tour {r_num}"
                                        html += f"<div style='text-align: center; color: #ccc; font-weight: bold; margin-bottom: 10px; flex: 0 0 auto;'>{col_title}</div>"

                                        if prefix == "WB":
                                            virtual_round = min(r_num, total_rounds_wb)
                                            expected_count = max(1, nb_matches_r1 // (2**(virtual_round-1)))
                                        else:
                                            virtual_round = math.ceil(r_num / 2)
                                            expected_count = max(1, nb_matches_r1 // (2**virtual_round))

                                        html += "<div style='display: flex; flex-direction: column; justify-content: space-around; flex: 1 1 auto;'>"
                                        for m_num in range(1, expected_count + 1):
                                            is_gf = (prefix == "WB" and r_num > total_rounds_wb)
                                            html += get_match_card_admin(r_num, m_num, is_gf)
                                        html += "</div></div>"
                                    html += "</div>"

                                else:
                                    html += "<div style='display: flex; justify-content: flex-start; width: 100%; overflow-x: auto; padding-bottom: 20px; min-height: 400px; zoom: 0.8;'>"
                                    html += "<div style='display: flex; flex-direction: row;'>"
                                    for r_num in range(1, total_rounds_wb):
                                        html += "<div style='display: flex; flex-direction: column; justify-content: space-around; flex: 0 0 180px; margin-right: 20px;'>"
                                        html += f"<div style='text-align: center; color: #ccc; font-weight: bold; margin-bottom: 10px; flex: 0 0 auto;'>Tour {r_num}</div>"
                                        html += "<div style='display: flex; flex-direction: column; justify-content: space-around; flex: 1 1 auto;'>"
                                        expected_count = max(1, nb_matches_r1 // (2**(r_num-1)))
                                        half_count = expected_count // 2
                                        for m_num in range(1, half_count + 1):
                                            html += get_match_card_admin(r_num, m_num)
                                        html += "</div></div>"
                                    html += "</div>"

                                    html += "<div style='display: flex; flex-direction: column; justify-content: space-around; flex: 0 0 200px; margin: 0 10px;'>"
                                    html += "<div style='text-align: center; color: gold; font-weight: bold; margin-bottom: 10px; flex: 0 0 auto;'>👑 Finale</div>"
                                    html += "<div style='display: flex; flex-direction: column; justify-content: space-around; flex: 1 1 auto;'>"
                                    html += get_match_card_admin(total_rounds_wb, 1, is_gf=True)
                                    html += "</div></div>"

                                    html += "<div style='display: flex; flex-direction: row-reverse;'>"
                                    for r_num in range(1, total_rounds_wb):
                                        html += "<div style='display: flex; flex-direction: column; justify-content: space-around; flex: 0 0 180px; margin-left: 20px;'>"
                                        html += f"<div style='text-align: center; color: #ccc; font-weight: bold; margin-bottom: 10px; flex: 0 0 auto;'>Tour {r_num}</div>"
                                        html += "<div style='display: flex; flex-direction: column; justify-content: space-around; flex: 1 1 auto;'>"
                                        expected_count = max(1, nb_matches_r1 // (2**(r_num-1)))
                                        half_count = expected_count // 2
                                        for m_num in range(half_count + 1, expected_count + 1):
                                            html += get_match_card_admin(r_num, m_num)
                                        html += "</div></div>"
                                    html += "</div>"
                                    html += "</div>"

                                return html

                            st.markdown(render_css_bracket_admin("WB", "🏆 Arbre du Tournoi"), unsafe_allow_html=True)
                            if is_double_elim:
                                st.markdown(render_css_bracket_admin("LB", "💀 Loser Bracket"), unsafe_allow_html=True)

                        st.divider()
                        st.markdown("### ✏️ Saisie des scores")

                        # --- NOUVELLE FONCTION DE SAISIE INTERACTIVE (PAPILLON COMPATIBLE) ---
                        def draw_interactive_match(col, m, r_num, m_num, is_gf=False):
                            bg_color = "background: rgba(255, 215, 0, 0.1);" if is_gf else ""
                            with col.container(border=True):
                                st.markdown(f"<div style='text-align:center; font-size:10px; opacity:0.5; {bg_color}'>Match {m_num}</div>", unsafe_allow_html=True)

                                if m:
                                    p1_name = all_users.get(m.get("player1_id"), "En attente...") if m.get("player1_id") else "En attente..."
                                    p2_name = all_users.get(m.get("player2_id"), "En attente...") if m.get("player2_id") else "En attente..."
                                    is_done = m["status"] == "completed"

                                    st.write(f"**{p1_name}**")
                                    st.write(f"**{p2_name}**")

                                    if p1_name != "En attente..." and p2_name != "En attente...":
                                        sc1, sc2 = st.columns(2)
                                        s1 = sc1.number_input("S1", min_value=0, max_value=9, value=m["score1"], key=f"b_s1_{m['id']}", label_visibility="collapsed")
                                        s2 = sc2.number_input("S2", min_value=0, max_value=9, value=m["score2"], key=f"b_s2_{m['id']}", label_visibility="collapsed")

                                        btn_lbl = "MAJ" if is_done else "Valider"
                                        if st.button(btn_lbl, key=f"b_btn_{m['id']}", use_container_width=True):
                                            if s1 == s2:
                                                st.error("Il faut un vainqueur !")
                                            else:
                                                db.update_bracket_match_score(m["id"], s1, s2, m["player1_id"], m["player2_id"], selected_t["id"], m["bracket_match_id"], nb_matches_r1, selected_t["format"])
                                                st.rerun()
                                else:
                                    st.write("**En attente...**")
                                    st.write("**En attente...**")

                        # --- AFFICHAGE DES ZONES DE SAISIE SELON LE FORMAT ---
                        tier_matches_wb = [m for m in matches if m["bracket_match_id"].startswith("WB")]
                        tier_dict_wb = {m["bracket_match_id"]: m for m in tier_matches_wb}

                        if is_double_elim:
                            # 1. WINNER BRACKET (DE GAUCHE À DROITE)
                            st.markdown("#### 🏆 Winner Bracket")
                            cols_wb = st.columns(total_rounds_wb)
                            for r_idx, col in enumerate(cols_wb):
                                r_num = 1 + r_idx
                                col.markdown(f"<h5 style='text-align:center; color:#ccc;'>Tour {r_num}</h5>", unsafe_allow_html=True)
                                expected_count = max(1, nb_matches_r1 // (2**(r_num-1)))
                                for m_num in range(1, expected_count + 1):
                                    m = tier_dict_wb.get(f"WB_R{r_num}_M{m_num}")
                                    draw_interactive_match(col, m, r_num, m_num)

                            # 2. LOSER BRACKET
                            st.divider()
                            st.markdown("#### 💀 Loser Bracket (Repêchages)")
                            total_rounds_lb = (total_rounds_wb - 1) * 2
                            tier_matches_lb = [m for m in matches if m["bracket_match_id"].startswith("LB")]
                            tier_dict_lb = {m["bracket_match_id"]: m for m in tier_matches_lb}
                            cols_lb = st.columns(total_rounds_lb)
                            for r_idx, col in enumerate(cols_lb):
                                r_num = 1 + r_idx
                                col.markdown(f"<h5 style='text-align:center; color:#ccc;'>Tour {r_num}</h5>", unsafe_allow_html=True)
                                expected_count = max(1, nb_matches_r1 // (2 ** math.ceil(r_num / 2)))
                                for m_num in range(1, expected_count + 1):
                                    m = tier_dict_lb.get(f"LB_R{r_num}_M{m_num}")
                                    draw_interactive_match(col, m, r_num, m_num)

                            # 3. GRANDE FINALE
                            st.divider()
                            has_reset = any(m["bracket_match_id"] == f"WB_R{total_rounds_wb + 2}_M1" for m in matches)
                            end_round = total_rounds_wb + 2 if has_reset else total_rounds_wb + 1
                            title = "👑 Grande Finale & Bracket Reset" if has_reset else "👑 Grande Finale"
                            st.markdown(f"#### {title}")
                            num_cols_gf = end_round - total_rounds_wb
                            cols_gf = st.columns(num_cols_gf)
                            for r_idx, col in enumerate(cols_gf):
                                r_num = total_rounds_wb + 1 + r_idx
                                col.markdown(f"<h5 style='text-align:center; color:#ccc;'>Tour {r_num}</h5>", unsafe_allow_html=True)
                                m = tier_dict_wb.get(f"WB_R{r_num}_M1")
                                draw_interactive_match(col, m, r_num, 1, is_gf=True)

                        else:
                            # SINGLE ELIMINATION (Saisie Verticale Propre)
                            st.markdown("#### ✏️ Saisie des scores de l'Arbre")

                            # On boucle sur chaque tour, de gauche à droite
                            for r_num in range(1, total_rounds_wb + 1):
                                is_finale = (r_num == total_rounds_wb)

                                if not is_finale:
                                    st.markdown(f"##### Tour {r_num}")
                                    expected_count = max(1, nb_matches_r1 // (2**(r_num-1)))

                                    # On crée des rangées de 3 colonnes max pour que ça reste toujours large et lisible
                                    cols_per_row = min(3, expected_count) if expected_count > 1 else 1
                                    cols = st.columns(cols_per_row)

                                    for m_num in range(1, expected_count + 1):
                                        col = cols[(m_num - 1) % cols_per_row]
                                        m = tier_dict_wb.get(f"WB_R{r_num}_M{m_num}")
                                        draw_interactive_match(col, m, r_num, m_num)
                                else:
                                    # LE DERNIER TOUR : Grande Finale et Petite Finale
                                    st.markdown("##### 👑 Finales")
                                    cols_finales = st.columns(2)
                                    
                                    # 1. Grande Finale (M1)
                                    m_gf = tier_dict_wb.get(f"WB_R{r_num}_M1")
                                    draw_interactive_match(cols_finales[0], m_gf, r_num, 1, is_gf=True)
                                    
                                    # 2. Petite Finale (M2)
                                    m_pf = tier_dict_wb.get(f"WB_R{r_num}_M2")
                                    cols_finales[1].markdown("<div style='text-align:center; color:#CD7F32; font-weight:bold; margin-bottom: 5px;'>🥉 Petite Finale</div>", unsafe_allow_html=True)
                                    draw_interactive_match(cols_finales[1], m_pf, r_num, 2, is_gf=False)
                                
                                st.write("") # Petit espace entre chaque tour

                    st.divider()
                    st.info("Une fois les Finales jouées et validées, vous pourrez clôturer l'événement.")
                    st.warning("⚠️ Attention : Cette action va générer automatiquement le classement final (Top 1, Top 2, Top 3, Top 5, Top 9...) pour tous les joueurs en fonction de leur parcours dans l'arbre, puis archivera le tournoi.")
                    
                    if st.button("🏆 Calculer les classements et Archiver", type="primary"):
                        success, msg = db.calculate_and_save_final_rankings(selected_t["id"], selected_t["format"])
                        if success:
                            st.success(msg)
                            st.balloons()
                            st.rerun()
                        else:
                            st.error(msg)

                # J'ai rajouté "archived" ici au cas où pour être sûr que ça s'affiche bien une fois clôturé
                elif selected_t["status"] in ["completed", "archived"]:
                    st.success("🏁 Ce tournoi est terminé et archivé.")           
