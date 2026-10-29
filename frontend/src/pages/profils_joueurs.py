import altair as alt
import pandas as pd
import streamlit as st

from badges_config import BADGES_B64
from base_function_temp.draw_rank_badge import draw_rank_badge
from base_function_temp.get_badges_html import get_badges_html
from base_function_temp.get_rank_info import get_rank_info
from ranks_config import RANK_TIERS


def afficher(db, user):

    # --- 0. SÉLECTION DU JOUEUR ---
    players_res = db.get_leaderboard()
    if not players_res.data:
        st.error("Impossible de récupérer les joueurs.")
        st.stop()

    all_players = players_res.data
    players_map = {p["username"]: p for p in all_players}

    # Menu déroulant
    options = list(players_map.keys())

    # 🛑 GESTION DU MODE VISITEUR 🛑
    is_guest = st.session_state.get("guest_mode", False)

    try:
        if is_guest and len(all_players) > 0:
            # Si c'est un visiteur, on sélectionne le N°1 du classement
            default_username = all_players[0]["username"]
            default_index = options.index(default_username)
        else:
            # Sinon, on sélectionne le joueur connecté
            default_index = options.index(user["username"])
    except ValueError:
        default_index = 0

    selected_username = st.selectbox(
        "Voir le profil de :", options, index=default_index
    )
    target_user = players_map[selected_username]

    # --- SÉCURITÉ : BLOCAGE SI PROFIL PRIVÉ ---
    if target_user.get("is_hidden_profile", False) and (is_guest or target_user["id"] != user["id"]):
        st.warning(f"🔒 Le profil de {target_user['username']} est privé.")
        st.info("L'utilisateur a choisi de masquer ses statistiques et son historique.")
        st.stop()
    # ------------------------------------------

    st.header(f"👤 Profil de {target_user['username']}")

    # --- 💎 AFFICHAGE DU RANG ET DU TITRE ---
    target_elo = target_user.get("elo_rating", 1000)
    target_rank_id = target_user.get("current_rank_id_1v1")

    # 1. On affiche d'abord le Badge
    badge_html = draw_rank_badge(target_elo, target_rank_id)
    st.markdown(badge_html, unsafe_allow_html=True)

    # 2. On affiche le Titre juste en dessous - Version Emblème de Rang
    equipped_title = target_user.get("equipped_title")
    if equipped_title:
        # Initialisations par défaut
        rank_color = "#C69C25"  # Or Snook'R par défaut
        title_icon = ""  # L'emblème du grade ou podium

        # --- 1. DÉTERMINATION DE L'ICÔNE ET DE LA COULEUR ---

        # Cas spéciaux : Le Podium (prioritaire car "Champion" ne commence pas par un rang)
        if "Champion" in equipped_title:
            rank_color = "#FFD700"  # Or éclatant
            title_icon = "🥇"  # Médaille d'or
        elif "Dauphin" in equipped_title:
            rank_color = "#E0FFFF"  # Argent
            title_icon = "🥈"  # Médaille d'argent
        elif "3ème" in equipped_title:
            rank_color = "#CD7F32"  # Bronze
            title_icon = "🥉"  # Médaille de bronze
        else:
            # Cas normal : Les Grades (on cherche du plus HAUT au plus BAS dans RANK_TIERS)
            found_rank = False
            for tier in reversed(RANK_TIERS):
                if equipped_title.startswith(tier["name"]):
                    rank_color = tier.get("color", "#C69C25")
                    # 🔴 ICI : On récupère l'icône définie dans ranks_config.py
                    title_icon = tier.get("icon", "🔰")  # Fallback si pas d'icône définie
                    found_rank = True
                    break

            # Si vraiment aucun rang trouvé dans config (peu probable), icône générique
            if not found_rank:
                title_icon = "🔰"  # Icône de rang par défaut

        # --- 2. AFFICHAGE DU BADGE STYLÉ AVEC EMBLÈME ---
        st.markdown(f"""
            <div style='
                display: flex;
                justify-content: center;
                align-items: center;
                gap: 12px;
                background: linear-gradient(135deg, {rank_color} 0%, color-mix(in srgb, {rank_color} 50%, black) 100%);
                border: 2px solid rgba(255,255,255,0.2);
                border-radius: 50px;
                padding: 10px 25px;
                color: white;
                font-weight: bold;
                font-family: "Playfair Display", serif;
                font-size: 1.25em;
                font-style: italic;
                box-shadow: 0 4px 15px rgba(0, 0, 0, 0.4), 0 0 15px color-mix(in srgb, {rank_color} 70%, white);
                text-shadow: 1px 1px 3px rgba(0,0,0,0.7);
                margin: 20px auto;
                width: fit-content;
                letter-spacing: 0.5px;
            '>
                <span style="font-size: 1.5em; display: flex; align-items: center;">{title_icon}</span>
                <span>{equipped_title}</span>
            </div>
        """, unsafe_allow_html=True)
    else:
        st.write("<br>", unsafe_allow_html=True)

    st.divider()

    # ==========================================
    # 🏆 VITRINES DE PALMARÈS (PODIUM UNIQUEMENT)
    # ==========================================

    # --- 1. PRÉPARATION & NETTOYAGE DES IMAGES ---
    def clean_b64(key):
        raw = BADGES_B64.get(key, "")
        return raw.replace('"', '').replace("'", "").replace('\n', '').replace('\r', '').replace(' ', '')

    img_or = clean_b64("medaille_or")
    img_argent = clean_b64("medaille_argent")
    img_bronze = clean_b64("medaille_bronze")

    # --- 2. CONFIGURATION DES STYLES (OR, ARGENT, BRONZE) ---
    RARETY_STYLES = {
        1: {"color": "#FFD700", "label": "Or", "img": img_or, "emoji": "🥇"},
        2: {"color": "#C0C0C0", "label": "Argent", "img": img_argent, "emoji": "🥈"},
        3: {"color": "#CD7F32", "label": "Bronze", "img": img_bronze, "emoji": "🥉"}
    }

    def render_trophy_card(rank_key, count):
        """Génère le HTML d'une carte de trophée avec style dynamique"""
        cfg = RARETY_STYLES.get(rank_key)
        if not cfg:
            return ""

        color = cfg["color"]
        card_css = f"border: 2px solid {color}; border-radius: 12px; padding: 15px; text-align: center; background: color-mix(in srgb, {color} 7%, transparent); min-width: 125px; box-shadow: 0 4px 15px rgba(0,0,0,0.3); display: flex; flex-direction: column; align-items: center;"
        number_css = f"font-family: 'Playfair Display', serif; font-size: 2.5em; font-weight: bold; color: {color}; margin-top: 5px; text-shadow: 1px 1px 2px rgba(0,0,0,0.5);"
        label_css = "font-size: 0.85em; text-transform: uppercase; letter-spacing: 1.5px; opacity: 0.8; margin-top: 8px; color: white;"

        if cfg["img"]:
            icon_html = f'<img src="{cfg["img"]}" style="width: 55px; height: 55px; object-fit: contain; filter: drop-shadow(0 0 8px {color});" />'
        else:
            icon_html = f'<div style="font-size: 2.5em;">{cfg["emoji"]}</div>'

        return f"<div style='{card_css}'>{icon_html}<div style='{label_css}'>{cfg['label']}</div><div style='{number_css}'>{count}</div></div>"

    def get_list_icon(rank):
        """Génère l'icône pour les listes détaillées (Podium ou Médaille militaire)"""
        cfg = RARETY_STYLES.get(rank)
        if cfg:
            if cfg["img"]:
                return f'<img src="{cfg["img"]}" style="width: 25px; height: 25px; object-fit: contain; filter: drop-shadow(0 0 5px {cfg["color"]}); margin-right: 15px;" />'
            return f'<span style="font-size: 1.4em; margin-right: 15px;">{cfg["emoji"]}</span>'
        return "<span style='font-size: 1.4em; margin-right: 15px;'>🎖️</span>"

    # --- VITRINE 1 : LE PANTHÉON (GRANDS TOURNOIS) ---
    st.subheader("🏆 Le Panthéon")
    gt_stats = db.get_user_gt_stats(target_user["id"])

    if not gt_stats:
        st.caption("Aucune participation en Grand Tournoi pour le moment.")
    else:
        gt_counts = {r: sum(1 for s in gt_stats if s.get('final_rank') == r) for r in [1, 2, 3]}

        html_gt = "<div style='display: flex; flex-wrap: wrap; gap: 15px; margin-bottom: 20px;'>"
        for r in [1, 2, 3]:
            if gt_counts[r] > 0:
                html_gt += render_trophy_card(r, gt_counts[r])
        html_gt += "</div>"
        st.markdown(html_gt, unsafe_allow_html=True)

        with st.expander("📜 Palmarès détaillé (Grands Tournois)"):
            html_list = "<div style='padding-top: 5px;'>"
            for s in sorted(gt_stats, key=lambda x: x.get('final_rank', 999)):
                rank = s.get('final_rank')
                t_name = s.get('grand_tournaments', {}).get('name', 'Tournoi Inconnu')
                icon = get_list_icon(rank)
                rank_text = f"{rank}{'er' if rank == 1 else 'ème'}" if rank in [1, 2, 3] else f"Top {rank}"
                html_list += f"<div style='padding: 10px 0; border-bottom: 1px solid rgba(255,255,255,0.1); display: flex; align-items: center;'>{icon}<span><b>{rank_text}</b> <span style='opacity: 0.6;'>au</span> <i style='color: #C69C25;'>{t_name}</i></span></div>"
            st.markdown(html_list + "</div>", unsafe_allow_html=True)

    # --- VITRINE 2 : SUCCÈS DE CARRIÈRE ---
    st.divider()
    st.subheader("🏅 Succès de Carrière")
    raw_matches = db.supabase.table("matches").select("*").in_("status", ["validated", "archived"]).execute().data
    user_full_history = [m for m in raw_matches if target_user["id"] in [m["winner_id"], m["loser_id"], m.get("winner2_id"), m.get("loser2_id")]]
    st.markdown(get_badges_html(target_user, user_full_history), unsafe_allow_html=True)

    # --- VITRINE 3 : LE MUR DU FUN (WEEKLY FUN) ---
    st.divider()
    st.subheader("🎉 Le Mur du Fun")
    weekly_stats = db.get_user_weekly_stats(target_user["id"])

    if not weekly_stats:
        st.caption("Aucune participation aux soirées Weekly Fun pour le moment.")
    else:
        # On ne compte QUE le podium
        w_counts = {r: sum(1 for s in weekly_stats if s['final_rank'] == r) for r in [1, 2, 3]}

        html_w = "<div style='display: flex; flex-wrap: wrap; gap: 15px; margin-bottom: 20px;'>"
        for r in [1, 2, 3]:
            if w_counts[r] > 0:
                html_w += render_trophy_card(r, w_counts[r])
        html_w += "</div>"
        st.markdown(html_w, unsafe_allow_html=True)

        with st.expander("📜 Palmarès détaillé (Weekly Fun)"):
            html_list_w = "<div style='padding-top: 5px;'>"
            for s in sorted(weekly_stats, key=lambda x: x['weekly_tournaments']['event_date'] if x.get('weekly_tournaments') else '', reverse=True):
                rank = s['final_rank']
                icon = get_list_icon(rank)
                t_name = s.get('weekly_tournaments', {}).get('name', 'Tournoi Inconnu')
                t_date = pd.to_datetime(s.get('weekly_tournaments', {}).get('event_date')).strftime('%d/%m/%y') if s.get('weekly_tournaments') else "??/??/??"
                html_list_w += f"<div style='padding: 10px 0; border-bottom: 1px solid rgba(255,255,255,0.1); display: flex; align-items: center;'>{icon}<span><b>{rank}{'er' if rank == 1 else 'ème'}</b> <span style='opacity: 0.6;'>au</span> <i style='color: #C69C25;'>{t_name}</i> <span style='opacity: 0.4; font-size: 0.85em; margin-left: 6px;'>({t_date})</span></span></div>"
            st.markdown(html_list_w + "</div>", unsafe_allow_html=True)

    st.divider()

    # ==========================================
    # 📊 CENTRE DE STATISTIQUES AVANCÉES
    # ==========================================
    st.divider()
    st.subheader("📊 Centre de Statistiques")

    # --- 1. SÉLECTEUR DE MODE ---
    view_mode = st.radio("Mode de jeu :", ["Solo (1v1)", "Duo (2v2)"], horizontal=True, key="stats_mode_select")
    target_mode_db = "1v1" if view_mode == "Solo (1v1)" else "2v2"

    # --- 2. RÉCUPÉRATION DE TOUS LES MATCHS DU JOUEUR ---
    raw_matches = db.supabase.table("matches").select("*").in_("status", ["validated", "archived"]).eq("mode", target_mode_db).order("created_at", desc=False).execute().data
    user_matches = [m for m in raw_matches if target_user["id"] in [m["winner_id"], m["loser_id"], m.get("winner2_id"), m.get("loser2_id")]]

    all_users_map = {p["id"]: p["username"] for p in db.get_all_profiles().data}

    if not user_matches:
        st.info(f"{target_user['username']} n'a joué aucun match classé en {view_mode}.")
    else:
        # --- 3. MOTEUR DE CALCUL STATISTIQUE (Par Saison & All-Time) ---
        user_seasons = {}

        # A. Initialisation des saisons
        user_seasons["🔥 Saison en cours"] = {'matches': [], 'end_elo': target_user.get("elo_rating" if target_mode_db == "1v1" else "elo_2v2", 1000)}
        arch_data = db.supabase.table("season_archives").select("*").eq("player_id", target_user["id"]).eq("mode", target_mode_db).execute().data
        for arc in arch_data:
            user_seasons[arc["season_name"]] = {'matches': [], 'end_elo': arc["final_elo"]}

        # B. Distribution des matchs dans les saisons
        for m in user_matches:
            s_name = m.get("season_name") if m.get("status") == "archived" else "🔥 Saison en cours"
            if s_name not in user_seasons:
                user_seasons[s_name] = {'matches': [], 'end_elo': 1000}
            user_seasons[s_name]['matches'].append(m)

        # C. Variables Globales (All-Time)
        all_time_peak = 1000
        global_wins = 0
        global_max_streak = 0
        global_current_streak = 0
        global_opponents = {}
        global_dates = {}

        season_curves = {}
        season_stats = {}

        # D. Calculs des courbes, pics et adversaires PAR SAISON
        for s_name, s_data in user_seasons.items():
            s_matches = s_data['matches']
            if not s_matches and s_name != "🔥 Saison en cours":
                continue

            # Calcul du gain net pour trouver l'Elo de départ exact
            net_gain = 0
            for m in s_matches:
                is_win = target_user["id"] in [m["winner_id"], m.get("winner2_id")]
                delta = m.get("elo_loss", m.get("elo_gain", 0)) if not is_win else m.get("elo_gain", 0)
                net_gain += delta if is_win else -delta

            start_elo = s_data['end_elo'] - net_gain
            current_s_elo = start_elo
            s_peak = start_elo
            s_wins = 0
            s_opponents = {}
            s_dates = {}
            s_max_streak = 0
            s_current_streak = 0

            curve = [{"Numéro": 0, "Date": "Début", "Elo": start_elo, "Gain": 0, "Résultat": "-"}]

            for i, m in enumerate(s_matches):
                is_win = target_user["id"] in [m["winner_id"], m.get("winner2_id")]
                delta = m.get("elo_loss", m.get("elo_gain", 0)) if not is_win else m.get("elo_gain", 0)

                # Traqueurs Globaux & Saison (Séries)
                if is_win:
                    global_wins += 1
                    s_wins += 1
                    global_current_streak += 1
                    s_current_streak += 1
                    global_max_streak = max(global_max_streak, global_current_streak)
                    s_max_streak = max(s_max_streak, s_current_streak)
                else:
                    global_current_streak = 0
                    s_current_streak = 0

                # Traqueur adversaires (Saison & Global)
                opp_ids = [m["loser_id"], m.get("loser2_id")] if is_win else [m["winner_id"], m.get("winner2_id")]
                for oid in [oid for oid in opp_ids if oid]:
                    s_opponents[oid] = s_opponents.get(oid, 0) + 1
                    global_opponents[oid] = global_opponents.get(oid, 0) + 1

                current_s_elo += delta if is_win else -delta
                s_peak = max(s_peak, current_s_elo)
                all_time_peak = max(all_time_peak, current_s_elo)

                dt_utc = pd.to_datetime(m["created_at"])
                dt_paris = dt_utc.tz_convert("Europe/Paris") if dt_utc.tzinfo else dt_utc.tz_localize("UTC").tz_convert("Europe/Paris")

                # Traqueur Dates (Marathon)
                day_str = dt_paris.strftime("%Y-%m-%d")
                s_dates[day_str] = s_dates.get(day_str, 0) + 1
                global_dates[day_str] = global_dates.get(day_str, 0) + 1

                curve.append({
                    "Numéro": i + 1,
                    "Date": dt_paris.strftime("%d/%m %Hh%M"),
                    "Elo": current_s_elo,
                    "Gain": delta if is_win else -delta,
                    "Résultat": "Victoire" if is_win else "Défaite"
                })

            # Formatage des stats de la saison
            s_most_played = "Aucun"
            if s_opponents:
                top_oid, top_c = max(s_opponents.items(), key=lambda x: x[1])
                s_most_played = f"{all_users_map.get(top_oid, 'Inconnu')} ({top_c} matchs)"

            s_max_day = max(s_dates.values()) if s_dates else 0

            season_curves[s_name] = curve
            season_stats[s_name] = {
                "peak": s_peak,
                "wins": s_wins,
                "losses": len(s_matches) - s_wins,
                "total": len(s_matches),
                "start_elo": start_elo,
                "end_elo": s_data['end_elo'],
                "most_played": s_most_played,
                "max_day": s_max_day,
                "longest_streak": s_max_streak
            }

        # Formatage des stats globales
        g_most_played = "Aucun"
        if global_opponents:
            g_top_oid, g_top_c = max(global_opponents.items(), key=lambda x: x[1])
            g_most_played = f"{all_users_map.get(g_top_oid, 'Inconnu')} ({g_top_c} matchs)"

        g_max_day = max(global_dates.values()) if global_dates else 0

        # --- 4. AFFICHAGE DES STATS ALL-TIME ---
        st.markdown("#### 🌍 Carrière (All-Time)")
        global_matches = len(user_matches)
        global_wr = (global_wins / global_matches * 100) if global_matches > 0 else 0
        peak_rank_info = get_rank_info(all_time_peak)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Matchs Joués", global_matches)
        c2.metric("Taux de Victoire", f"{global_wr:.1f}%", f"{global_wins} V - {global_matches - global_wins} D", delta_color="off")
        c3.metric("Record Elo (Peak)", int(all_time_peak), peak_rank_info["name"])
        c4.metric("Meilleure Série", f"{global_max_streak} victoires", "🔥 On Fire" if global_max_streak >= 5 else None)

        c5, c6 = st.columns(2)
        with c5.container(border=True):
            st.markdown("<div style='font-size: 0.9em; opacity: 0.7;'>⚔️ Rival Principal (Le plus affronté)</div>", unsafe_allow_html=True)
            st.markdown(f"<div style='font-size: 1.2em; font-weight: bold; color: #f39c12;'>{g_most_played}</div>", unsafe_allow_html=True)
        with c6.container(border=True):
            st.markdown("<div style='font-size: 0.9em; opacity: 0.7;'>⚡ Marathon (Max matchs en 1 jour)</div>", unsafe_allow_html=True)
            st.markdown(f"<div style='font-size: 1.2em; font-weight: bold; color: #3498db;'>{g_max_day} matchs joués</div>", unsafe_allow_html=True)

        st.write("")

        # --- 5. AFFICHAGE DES STATS PAR SAISON ---
        st.markdown("#### 📅 Analyse par Saison")
        available_seasons = [s for s in ["🔥 Saison en cours"] + sorted(list(user_seasons.keys()), reverse=True) if s in season_stats]
        # On dédoublonne la "saison en cours"
        available_seasons = list(dict.fromkeys(available_seasons))

        if available_seasons:
            chosen_season = st.selectbox("Sélectionnez une saison à analyser :", available_seasons, label_visibility="collapsed")
            stats = season_stats[chosen_season]

            s_wr = (stats['wins'] / stats['total'] * 100) if stats['total'] > 0 else 0
            delta_net = stats['end_elo'] - stats['start_elo']

            st.markdown(f"**Bilan : {chosen_season}**")
            k1, k2, k3, k4 = st.columns(4)
            # 🔴 CORRECTION DU TEXTE DE VARIATION : Elo Final d'abord, la variation en dessous
            k1.metric("Elo Final", int(stats['end_elo']), f"{int(delta_net):+} pts (Variation)")
            k2.metric("Meilleur Elo", int(stats['peak']), get_rank_info(stats['peak'])["name"])
            k3.metric("Matchs de Saison", stats['total'])
            k4.metric("Victoires", stats['wins'], f"{s_wr:.0f}%", delta_color="off")

            # Affichage des 3 stats funs de la saison
            if stats['total'] > 0:
                s1, s2, s3 = st.columns(3)
                with s1.container(border=True):
                    st.markdown("<div style='font-size: 0.85em; opacity: 0.7;'>⚔️ Rival de la saison</div>", unsafe_allow_html=True)
                    st.markdown(f"<div style='font-size: 1.1em; font-weight: bold; color: #f39c12;'>{stats['most_played']}</div>", unsafe_allow_html=True)
                with s2.container(border=True):
                    st.markdown("<div style='font-size: 0.85em; opacity: 0.7;'>🔥 Série d'invincibilité</div>", unsafe_allow_html=True)
                    st.markdown(f"<div style='font-size: 1.1em; font-weight: bold; color: #e74c3c;'>{stats['longest_streak']} victoires</div>", unsafe_allow_html=True)
                with s3.container(border=True):
                    st.markdown("<div style='font-size: 0.85em; opacity: 0.7;'>⚡ Marathon</div>", unsafe_allow_html=True)
                    st.markdown(f"<div style='font-size: 1.1em; font-weight: bold; color: #3498db;'>{stats['max_day']} matchs en 1j</div>", unsafe_allow_html=True)

            df_season = pd.DataFrame(season_curves[chosen_season])
            chart_s = (
                alt.Chart(df_season)
                .mark_line(point=True, color="#e74c3c" if delta_net < 0 else "#2ecc71")
                .encode(
                    x=alt.X("Numéro", title="Matchs joués", axis=alt.Axis(tickMinStep=1)),
                    y=alt.Y("Elo", scale=alt.Scale(zero=False), title="Score Elo"),
                    tooltip=["Date", "Elo", "Résultat", "Gain"],
                ).properties(height=300).interactive()
            )
            st.altair_chart(chart_s, use_container_width=True)

        # --- 6. HISTORIQUE DES DERNIERS MATCHS ---
        with st.expander("📜 Historique des 15 derniers matchs", expanded=False):
            recent_matches = user_matches[::-1][:15]
            history_data = []

            for m in recent_matches:
                is_win = (m["winner_id"] == target_user["id"] or m.get("winner2_id") == target_user["id"])
                res_str = "✅ VICTOIRE" if is_win else "❌ DÉFAITE"

                dt_utc = pd.to_datetime(m["created_at"])
                dt_paris = dt_utc.tz_convert("Europe/Paris") if dt_utc.tzinfo else dt_utc.tz_localize("UTC").tz_convert("Europe/Paris")
                date_str = dt_paris.strftime("%d/%m à %Hh%M")

                points = m.get("elo_gain", 0) if is_win else m.get("elo_loss", m.get("elo_gain", 0))
                sign = "+" if is_win else "-"

                if target_mode_db == "1v1":
                    opp_id = m["loser_id"] if is_win else m["winner_id"]
                    details = f"vs {all_users_map.get(opp_id, 'Inconnu')}"
                else:
                    my_mate = m.get("winner2_id") if m["winner_id"] == target_user["id"] else \
                              m["winner_id"] if m.get("winner2_id") == target_user["id"] else \
                              m.get("loser2_id") if m["loser_id"] == target_user["id"] else m["loser_id"]
                    mate_name = all_users_map.get(my_mate, "?")
                    opp_ids = [m["loser_id"], m.get("loser2_id")] if is_win else [m["winner_id"], m.get("winner2_id")]
                    opp_names = [all_users_map.get(oid, "?") for oid in opp_ids if oid]
                    details = f"Avec {mate_name} vs {' & '.join(opp_names)}"

                history_data.append({
                    "Date": date_str,
                    "Résultat": res_str,
                    "Détails": details,
                    "Points": f"{sign}{points}",
                    "Saison": m.get("season_name", "En cours") if m["status"] == "archived" else "En cours"
                })

            st.dataframe(pd.DataFrame(history_data), use_container_width=True, hide_index=True)
