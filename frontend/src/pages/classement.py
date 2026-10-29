import pandas as pd
import streamlit as st

from base_function_temp.draw_luxury_table import draw_luxury_table
from base_function_temp.get_rank_info import get_rank_info


def afficher(db, user):

    st.header("🏆 Classement Général")

    # Création des deux sous-onglets
    tab_current, tab_archives = st.tabs(["🔥 Saison en cours", "🏛️ Archives des Saisons"])

    with tab_current:
        # 1. Le Sélecteur de Mode
        ranking_mode = st.radio("Mode :", ["Solo (1v1)", "Duo (2v2)"], horizontal=True, key="rank_current")
        mode_db = "1v1" if ranking_mode == "Solo (1v1)" else "2v2"

        # 2. Récupération des données triées
        res = db.get_leaderboard(mode=mode_db)

        if not res.data:
            st.info("Aucun joueur n'est encore inscrit.")
        else:
            # 3. Préparation des données
            if mode_db == "1v1":
                target_elo = "elo_rating"
                target_matches = "matches_played"
                target_rank_col = "current_rank_id_1v1"
            else:
                target_elo = "elo_2v2"
                target_matches = "matches_2v2"
                target_rank_col = "current_rank_id_2v2"

            df = pd.DataFrame(res.data)
            df = df[df[target_matches] > 0]  # Uniquement les actifs

            if df.empty:
                st.info("Aucun joueur classé pour le moment dans ce mode.")
            else:
                # --- ANONYMISATION ---
                def anonymize(row):
                    if row.get("is_hidden_leaderboard", False) and row["id"] != user["id"]:
                        return "🕵️ Joueur Masqué"
                    return row["username"]

                df["username"] = df.apply(anonymize, axis=1)

                # 4. Création de la liste pour le tableau VIP
                list_data = []

                # On trie le dataframe par Elo
                df = df.sort_values(by=target_elo, ascending=False).reset_index(drop=True)

                for index, row in df.iterrows():
                    joueur_elo = row[target_elo]
                    joueur_rank_id = row.get(target_rank_col)  # NOUVEAU : On récupère l'ID

                    # On passe les deux infos pour que le bouclier fonctionne !
                    rank_info = get_rank_info(joueur_elo, joueur_rank_id)
                    icone_html = rank_info["icon"]

                    list_data.append({
                        "Rang": index + 1,
                        "Joueur": f"<div style='display: flex; align-items: center; gap: 10px;'>{icone_html} <span>{row['username']}</span></div>",
                        "Points Elo": f"<b>{int(joueur_elo)}</b> <span style='color: #ffd700;'>⭐️</span>",
                        "Matchs": f"{int(row[target_matches])} 🎮"
                    })

                st.markdown(draw_luxury_table(list_data), unsafe_allow_html=True)

    with tab_archives:
        st.markdown("#### 📜 Explorer le passé")
        res_archives = db.supabase.table("season_archives").select("season_name").execute()

        if not res_archives.data:
            st.info("Aucune saison n'a encore été archivée. Clôturez une saison depuis le Panel Admin !")
        else:
            # Récupérer les noms uniques de saisons
            archived_names = sorted(list(set([s['season_name'] for s in res_archives.data])), reverse=True)

            c1, c2 = st.columns(2)
            selected_season = c1.selectbox("Sélectionner la saison :", archived_names)
            arch_mode = c2.radio("Mode :", ["Solo (1v1)", "Duo (2v2)"], horizontal=True, key="rank_archive")
            arch_mode_db = "1v1" if arch_mode == "Solo (1v1)" else "2v2"

            # 🔴 CORRECTION : On utilise la colonne "final_rank" ou "final_elo" (colonnes d'archives)
            try:
                # On essaie de trier par la colonne "final_elo" nativement
                archive_data = db.supabase.table("season_archives").select("*").eq("season_name", selected_season).eq("mode", arch_mode_db).order("final_elo", desc=True).execute().data
            except Exception:
                # SÉCURITÉ : Si "final_elo" n'existe pas, on récupère tout en vrac et on triera en Python pour éviter le crash !
                archive_data = db.supabase.table("season_archives").select("*").eq("season_name", selected_season).eq("mode", arch_mode_db).execute().data

            if not archive_data:
                st.info(f"Aucun classement trouvé pour **{selected_season}** en **{arch_mode}**.")
            else:
                list_arch = []

                # 1. On filtre d'abord pour garder uniquement ceux qui ont un match ou plus
                active_archive_data = []
                for row in archive_data:
                    nb_matchs = row.get("matches_played", row.get("final_matches", 0))
                    if int(nb_matchs) > 0:
                        active_archive_data.append(row)

                if not active_archive_data:
                    st.info(f"Aucun joueur actif trouvé pour **{selected_season}** en **{arch_mode}**.")
                else:
                    # 2. On trie les joueurs actifs par Elo décroissant pour être sûr de l'ordre
                    active_archive_data = sorted(
                        active_archive_data,
                        key=lambda x: float(x.get("final_elo", x.get("elo", x.get("elo_rating", 1000)))),
                        reverse=True
                    )

                    # 3. On construit la liste avec des rangs propres et continus (1, 2, 3...)
                    for index, row in enumerate(active_archive_data):
                        score_elo = row.get("final_elo", row.get("elo", row.get("elo_rating", 1000)))
                        nb_matchs = row.get("matches_played", row.get("final_matches", 0))

                        rank_info = get_rank_info(score_elo)

                        list_arch.append({
                            "Rang": index + 1,  # <--- Attribue un numéro propre qui se suit (1, 2, 3...)
                            "Joueur": f"<div style='display: flex; align-items: center; gap: 10px;'>{rank_info['icon']} <span>{row.get('username', 'Inconnu')}</span></div>",
                            "Points Elo": f"<b>{int(score_elo)}</b> <span style='color: #a0aec0;'>pts</span>",
                            "Matchs Joués": f"{int(nb_matchs)} 🎮"
                        })

                    st.markdown(draw_luxury_table(list_arch, title=f"Classement Final - {selected_season}"), unsafe_allow_html=True)
