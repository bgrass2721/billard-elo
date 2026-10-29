import altair as alt
import pandas as pd
import streamlit as st

from base_function_temp.draw_luxury_table import draw_luxury_table


def afficher(db, user):

    st.header("⚔️ Comparateur")

    # 1. RÉCUPÉRATION DES JOUEURS
    players_res = db.get_leaderboard()
    if not players_res.data:
        st.warning("Aucun joueur trouvé.")
        st.stop()

    all_players = players_res.data
    players_map = {p["username"]: p for p in all_players}
    id_to_name = {p["id"]: p["username"] for p in all_players}

    player_names = list(players_map.keys())

    # 2. SÉLECTEURS (Joueur A vs Joueur B)
    c1, c2, c3 = st.columns([1.5, 0.5, 1.5])

    # 🛑 GESTION DU MODE VISITEUR 🛑
    is_guest = st.session_state.get("guest_mode", False)

    with c1:
        try:
            if is_guest and len(player_names) > 0:
                # Si visiteur, on prend le premier de la liste (le N°1 du leaderboard)
                default_ix_1 = 0
            else:
                default_ix_1 = player_names.index(user["username"])
        except ValueError:
            default_ix_1 = 0
        p1_name = st.selectbox("Joueur 1 (Gauche)", player_names, index=default_ix_1)

    with c2:
        st.markdown(
            "<h2 style='text-align: center; padding-top: 20px;'>VS</h2>",
            unsafe_allow_html=True,
        )

    with c3:
        if is_guest and len(player_names) > 1:
            # Si visiteur, on prend le N°2 du leaderboard (l'index 1)
            default_ix_2 = 1
        else:
            default_ix_2 = 1 if len(player_names) > 1 else 0

        if player_names[default_ix_2] == p1_name and len(player_names) > 1:
            # Sécurité si jamais le N°2 est le même nom que le N°1 (peu probable mais prudent)
            # Ou si un vrai utilisateur est lui-même à l'index par défaut
            # On cherche le premier joueur différent de Joueur 1
            for i in range(len(player_names)):
                if player_names[i] != p1_name:
                    default_ix_2 = i
                    break

        p2_name = st.selectbox("Joueur 2 (Droite)", player_names, index=default_ix_2)

    if p1_name == p2_name:
        st.warning("Veuillez sélectionner deux joueurs différents.")
        st.stop()

    player_1 = players_map[p1_name]
    player_2 = players_map[p2_name]
    id_1 = player_1["id"]
    id_2 = player_2["id"]

    # 3. SÉLECTEUR DE MODE
    st.write("")
    hist_mode = st.radio(
        "Mode de comparaison :", ["Solo (1v1)", "Duo (2v2)"], horizontal=True
    )
    target_db_mode = "1v1" if hist_mode == "Solo (1v1)" else "2v2"

    # 4. RÉCUPÉRATION DES MATCHS
    raw_matches = (
        db.supabase.table("matches")
        .select("*")
        .in_("status", ["validated", "archived"])  # CORRECTION ICI : Historique All-Time !
        .eq("mode", target_db_mode)
        .order("created_at", desc=False)
        .execute()
        .data
    )

    # 5. ANALYSE
    duel_matches = []
    vs_stats = {
        "p1_wins": 0,
        "p2_wins": 0,
        "total": 0,
        "streak_p1": 0,
        "current_streak_winner": None,
    }
    coop_stats = {"wins": 0, "losses": 0, "total": 0}

    graph_data = [
        {
            "Match": 0,
            "Score Cumulé (Victoires)": 0,
            "Score Cumulé (Elo)": 0,
            "Date": "Début",
        }
    ]
    cumulative_score_wins = 0
    cumulative_score_elo = 0

    for m in raw_matches:
        # --- CORRECTION HEURE : Conversion UTC -> Paris ---
        dt_utc = pd.to_datetime(m["created_at"])
        # On localise en UTC puis on convertit en Europe/Paris pour gérer le décalage (+1h/+2h)
        dt_paris = (
            dt_utc.tz_convert("Europe/Paris")
            if dt_utc.tzinfo
            else dt_utc.tz_localize("UTC").tz_convert("Europe/Paris")
        )

        date_label = dt_paris.strftime("%d/%m")
        date_tableau = dt_paris.strftime("%d/%m %Hh%M")

        # P1 et P2 sont-ils présents ?
        p1_is_present = (
            m["winner_id"] == id_1
            or m["loser_id"] == id_1
            or m.get("winner2_id") == id_1
            or m.get("loser2_id") == id_1
        )
        p2_is_present = (
            m["winner_id"] == id_2
            or m["loser_id"] == id_2
            or m.get("winner2_id") == id_2
            or m.get("loser2_id") == id_2
        )

        if p1_is_present and p2_is_present:
            p1_is_winner = m["winner_id"] == id_1 or m.get("winner2_id") == id_1
            p2_is_winner = m["winner_id"] == id_2 or m.get("winner2_id") == id_2

            is_coop = (p1_is_winner and p2_is_winner) or (
                not p1_is_winner and not p2_is_winner
            )
            elo_gain = m.get("elo_gain", 0)

            if is_coop:
                coop_stats["total"] += 1
                if p1_is_winner:
                    coop_stats["wins"] += 1
                else:
                    coop_stats["losses"] += 1
            else:
                vs_stats["total"] += 1
                if p1_is_winner:
                    vs_stats["p1_wins"] += 1
                    cumulative_score_wins += 1
                    cumulative_score_elo += elo_gain
                    if vs_stats["current_streak_winner"] == "p1":
                        vs_stats["streak_p1"] += 1
                    else:
                        vs_stats["streak_p1"] = 1
                        vs_stats["current_streak_winner"] = "p1"
                else:
                    vs_stats["p2_wins"] += 1
                    cumulative_score_wins -= 1
                    cumulative_score_elo -= elo_gain
                    if vs_stats["current_streak_winner"] == "p2":
                        vs_stats["streak_p1"] += 1
                    else:
                        vs_stats["streak_p1"] = 1
                        vs_stats["current_streak_winner"] = "p2"

                # Graphique avec date corrigée
                graph_data.append(
                    {
                        "Match": vs_stats["total"],
                        "Score Cumulé (Victoires)": cumulative_score_wins,
                        "Score Cumulé (Elo)": cumulative_score_elo,
                        "Date": date_label,
                    }
                )

            # --- CONSTRUCTION LIGNE TABLEAU ---
            w1 = id_to_name.get(m["winner_id"], "?")
            w2 = id_to_name.get(m["winner2_id"])
            l1 = id_to_name.get(m["loser_id"], "?")
            l2 = id_to_name.get(m["loser2_id"])

            team_win = f"{w1} & {w2}" if w2 else w1
            team_lose = f"{l1} & {l2}" if l2 else l1
            match_str = f"{team_win}  ⚡  {team_lose}"
            points_display = f"{elo_gain:+}" if p1_is_winner else f"{-elo_gain:+}"

            duel_matches.append(
                {
                    "Date": date_tableau,  # Heure corrigée ici
                    "Type": "Partenaires" if is_coop else "Rivaux",
                    "Détails du Match": match_str,
                    "Résultat (P1)": "🏆 Victoire" if p1_is_winner else "💀 Défaite",
                    "Elo": points_display,
                }
            )

    # 6. AFFICHAGE DUEL (RIVAUX)
    st.divider()
    st.subheader(f"🥊 {p1_name} VS {p2_name}")

    if vs_stats["total"] == 0:
        st.info("Aucun affrontement direct (l'un contre l'autre).")
    else:
        col_left, col_mid, col_right = st.columns([2, 3, 2])
        with col_left:
            st.markdown(
                f"<h2 style='text-align: center; color: #C69C25;'>{vs_stats['p1_wins']}</h2>",
                unsafe_allow_html=True,
            )
            st.markdown(
                f"<div style='text-align: center;'><b>{p1_name}</b></div>",
                unsafe_allow_html=True,
            )

        with col_mid:
            p1_win_rate = vs_stats["p1_wins"] / vs_stats["total"]
            title_text = "⚔️ Duel Équilibré"
            title_color = "#ccc"

            if vs_stats["total"] >= 3:
                if p1_win_rate >= 0.70:
                    title_text = f"🩸 BÊTE NOIRE DE {p2_name.upper()}"
                    title_color = "#ff4b4b"
                elif p1_win_rate >= 0.55:
                    title_text = f"💪 {p1_name.upper()} DOMINE"
                    title_color = "#fca311"
                elif p1_win_rate <= 0.30:
                    title_text = f"🥊 SAC DE FRAPPE DE {p2_name.upper()}"
                    title_color = "#ff4b4b"
                elif p1_win_rate <= 0.45:
                    title_text = f"🛡️ {p2_name.upper()} A L'AVANTAGE"
                    title_color = "#fca311"
                else:
                    title_text = "⚖️ RIVAUX ÉTERNELS"
                    title_color = "#3498db"

                if vs_stats["streak_p1"] >= 3:
                    leader = (
                        p1_name
                        if vs_stats["current_streak_winner"] == "p1"
                        else p2_name
                    )
                    title_text = (
                        f"🔥 {leader.upper()} EN FEU ({vs_stats['streak_p1']} vict.)"
                    )
                    title_color = "#e25822"

            st.markdown(
                f"<div style='text-align: center; font-size: 18px; font-weight: bold; color: {title_color}; margin-top: 10px;'>{title_text}</div>",
                unsafe_allow_html=True,
            )
            st.progress(p1_win_rate)
            st.caption(f"Taux de victoire de {p1_name} : {p1_win_rate*100:.0f}%")

            elo_color = "#C69C25" if cumulative_score_elo >= 0 else "#FF5252"
            st.markdown(
                f"<div style='text-align: center; margin-top: 15px; padding: 10px; border-radius: 10px; background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1);'><div style='font-size: 0.8em; opacity: 0.7; text-transform: uppercase;'>Bilan Elo Net ({p1_name})</div><div style='font-size: 1.5em; font-weight: bold; color: {elo_color};'>{cumulative_score_elo:+} pts</div></div>",
                unsafe_allow_html=True,
            )

        with col_right:
            st.markdown(
                f"<h2 style='text-align: center; color: #FF5252;'>{vs_stats['p2_wins']}</h2>",
                unsafe_allow_html=True,
            )
            st.markdown(
                f"<div style='text-align: center;'><b>{p2_name}</b></div>",
                unsafe_allow_html=True,
            )

        st.write("")
        st.markdown("##### 📈 Historique de la domination")
        tab_elo, tab_wins = st.tabs(
            ["📉 Écart Elo (Points)", "📊 Écart Victoires (Net)"]
        )
        df_graph = pd.DataFrame(graph_data)

        with tab_elo:
            chart_elo = (
                alt.Chart(df_graph)
                .mark_line(point=True)
                .encode(
                    x=alt.X("Match", axis=alt.Axis(tickMinStep=1)),
                    y=alt.Y("Score Cumulé (Elo)", title=f"Avantage Points ({p1_name})"),
                    tooltip=["Date", "Score Cumulé (Elo)"],
                    color=alt.value("#9b59b6"),
                )
                .properties(height=300)
            )
            rule = (
                alt.Chart(pd.DataFrame({"y": [0]}))
                .mark_rule(color="white", opacity=0.3)
                .encode(y="y")
            )
            st.altair_chart(chart_elo + rule, use_container_width=True)

        with tab_wins:
            chart_wins = (
                alt.Chart(df_graph)
                .mark_line(point=True)
                .encode(
                    x=alt.X("Match", axis=alt.Axis(tickMinStep=1)),
                    y=alt.Y(
                        "Score Cumulé (Victoires)",
                        title=f"Avantage Victoires ({p1_name})",
                    ),
                    tooltip=["Date", "Score Cumulé (Victoires)"],
                    color=alt.value("#3498db"),
                )
                .properties(height=300)
            )
            st.altair_chart(chart_wins + rule, use_container_width=True)

    # 7. AFFICHAGE COOP (PARTENAIRES - 2v2)
    if target_db_mode == "2v2":
        st.divider()
        st.subheader(f"🧬 Synergie : {p1_name} & {p2_name}")
        if coop_stats["total"] == 0:
            st.write("Ils n'ont jamais joué ensemble dans la même équipe.")
        else:
            wr_coop = coop_stats["wins"] / coop_stats["total"]
            coop_title, emoji_coop = "🤝 Binôme Standard", "😐"
            if coop_stats["total"] >= 5:
                if wr_coop >= 0.75:
                    coop_title, emoji_coop = "🦍 LES GORILLES (Invincibles)", "🔥"
                elif wr_coop >= 0.55:
                    coop_title, emoji_coop = "⚔️ FRÈRES D'ARMES", "💪"
                elif wr_coop <= 0.35:
                    coop_title, emoji_coop = "💔 LES TOXIQUES (Incompatibles)", "💀"
                else:
                    coop_title, emoji_coop = "⚖️ PILE OU FACE", "🪙"

            k1, k2, k3 = st.columns(3)
            k1.metric("Matchs Ensemble", coop_stats["total"])
            k2.metric("Victoires", coop_stats["wins"], f"{wr_coop*100:.0f}%")
            k3.metric("Statut", emoji_coop, coop_title)

    # 8. TABLEAU GLOBAL
    st.divider()
    with st.expander("📜 Voir l'historique complet des rencontres", expanded=True):
        if not duel_matches:
            st.write("Aucun match trouvé.")
        else:
            # On inverse la liste pour avoir les plus récents en premier, et on affiche !
            # On désactive le mode classement (is_ranking=False) pour ne pas avoir de médaille d'or
            st.markdown(draw_luxury_table(duel_matches[::-1], is_ranking=False), unsafe_allow_html=True)
