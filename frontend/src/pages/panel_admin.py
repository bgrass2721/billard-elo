from datetime import datetime

import pandas as pd
import streamlit as st

from elo_engine import EloEngine
from ranks_config import RANK_TIERS


def afficher(db):

    st.header("🔧 Outils d'administration")

    # --- 1. GESTION DES MATCHS ---
    # On récupère les matchs avec les jointures (winner, loser, winner2, loser2)
    all_matches = db.get_all_matches().data

    status_filter = st.multiselect(
        "Statuts :",
        [
            "pending",  # En attente
            "validated",  # Validé
            "rejected",  # Refusé
            "disputed",  # Litige
            "revoked",  # Révoqué (annulé après validation)
            "rejected_confirmed",  # Refus archivé
        ],
        default=["disputed", "pending"],
    )

    if all_matches:
        for m in all_matches:
            if m["status"] in status_filter:
                # A. Récupération des infos de base
                mode = m.get("mode", "1v1")
                icon = "👥" if mode == "2v2" else "👤"
                dt_utc = pd.to_datetime(m["created_at"])
                dt_paris = (
                    dt_utc.tz_convert("Europe/Paris")
                    if dt_utc.tzinfo
                    else dt_utc.tz_localize("UTC").tz_convert("Europe/Paris")
                )
                date_str = dt_paris.strftime("%d/%m à %Hh%M")

                # B. Récupération sécurisée des pseudos (Gestion des None)
                # Note : m.get("winner") peut être None si la jointure a échoué, d'où le (Or {})
                w1 = (m.get("winner") or {}).get("username", "Inconnu")
                l1 = (m.get("loser") or {}).get("username", "Inconnu")

                # C. Construction du titre selon le mode
                if mode == "2v2":
                    w2 = (m.get("winner2") or {}).get("username", "?")
                    l2 = (m.get("loser2") or {}).get("username", "?")
                    versus_str = f"{w1} & {w2} vs {l1} & {l2}"
                else:
                    versus_str = f"{w1} vs {l1}"

                # D. Titre final de l'expander
                match_label = (
                    f"{icon} {mode} | {m['status'].upper()} | {date_str} | {versus_str}"
                )

                # E. Affichage et Actions
                with st.expander(match_label):
                    c1, c2 = st.columns(2)

                    # --- Actions pour "En attente" ---
                    if m["status"] == "pending":
                        if c1.button("Forcer Validation ✅", key=f"adm_val_{m['id']}"):
                            db.validate_match_logic(m["id"])
                            st.rerun()
                        if c2.button("Supprimer 🗑️", key=f"adm_del_{m['id']}"):
                            db.reject_match(m["id"])
                            st.rerun()

                    # --- Actions pour "Litige" ---
                    elif m["status"] == "disputed":
                        if c1.button("Forcer Validation ✅", key=f"f_v_{m['id']}"):
                            db.validate_match_logic(m["id"])
                            st.rerun()
                        if c2.button("Confirmer Rejet ❌", key=f"f_r_{m['id']}"):
                            db.reject_match(m["id"])
                            st.rerun()

                    # --- Actions pour "Validé" ---
                    elif m["status"] == "validated":
                        st.info(f"Gain enregistré : {m.get('elo_gain')} points")
                        if st.button(
                            "Révoquer le match (Annuler les points) ⚠️",
                            key=f"rev_{m['id']}",
                        ):
                            db.revoke_match(m["id"])
                            st.rerun()

    st.divider()

    # --- 2. SAUVEGARDE DE SÉCURITÉ ---
    st.subheader("💾 Sauvegarde de sécurité")
    if st.button("Préparer les fichiers de sauvegarde"):
        # On télécharge les tables brutes
        profiles = db.supabase.table("profiles").select("*").execute().data
        df_prof = pd.DataFrame(profiles)
        matches = db.supabase.table("matches").select("*").execute().data
        df_match = pd.DataFrame(matches)

        c1, c2 = st.columns(2)
        c1.download_button(
            "📥 Backup Joueurs",
            df_prof.to_csv(index=False).encode("utf-8"),
            "backup_profiles.csv",
            "text/csv",
        )
        c2.download_button(
            "📥 Backup Matchs",
            df_match.to_csv(index=False).encode("utf-8"),
            "backup_matches.csv",
            "text/csv",
        )

    st.divider()

    st.divider()

    # --- 3. SYNCHRONISATION DE LA SAISON EN COURS ---
    st.subheader("🔄 Réparation de la Saison")
    st.info(
        "Recalcule tous les scores de la **saison en cours**. "
        "Le système récupère l'Elo de fin de saison dernière, applique le soft-reset, "
        "puis rejoue tous les matchs actuels dans l'ordre."
    )

    if st.button("🔧 Réparer la saison en cours", type="primary"):
        status_text = st.empty()
        status_text.text("⏳ Démarrage du recalcul...")
        progress_bar = st.progress(0)

        # A. Récupération des archives pour trouver l'Elo de départ de CETTE saison
        archives = db.supabase.table("season_archives").select("*").order("created_at", desc=True).execute().data

        latest_archive_1v1 = {}
        latest_archive_2v2 = {}

        if archives:
            for arc in archives:
                pid = arc["player_id"]
                mode = arc.get("mode", "1v1")
                # Comme on a trié par date décroissante, la première ligne trouvée est la plus récente
                if mode == "1v1" and pid not in latest_archive_1v1:
                    latest_archive_1v1[pid] = arc["final_elo"]
                elif mode == "2v2" and pid not in latest_archive_2v2:
                    latest_archive_2v2[pid] = arc["final_elo"]

        # Fonction miroir du soft-reset (1000 + 40% au-delà de 1000)
        def get_start_elo(last_final_elo):
            if last_final_elo > 1000:
                return 1000 + (last_final_elo - 1000) * 0.4
            return 1000

        # B. Initialisation des compteurs avec les Elos de départ
        players = db.get_leaderboard().data

        temp_elo_1v1 = {}
        matches_1v1 = {}
        temp_elo_2v2 = {}
        matches_2v2 = {}

        for p in players:
            pid = p["id"]
            # Initialisation 1v1
            base_1v1 = latest_archive_1v1.get(pid, 1000)
            temp_elo_1v1[pid] = get_start_elo(base_1v1)
            matches_1v1[pid] = 0  # On remet le compteur de matchs de la saison à 0

            # Initialisation 2v2
            base_2v2 = latest_archive_2v2.get(pid, 1000)
            temp_elo_2v2[pid] = get_start_elo(base_2v2)
            matches_2v2[pid] = 0

        # C. Récupération Chronologique UNIQUEMENT de la saison en cours (status = validated)
        matches = (
            db.supabase.table("matches")
            .select("*")
            .eq("status", "validated")
            .order("created_at", desc=False)
            .execute()
            .data
        )

        engine = EloEngine()
        total_matches = len(matches)
        corrected_matches = 0

        # D. Replay de l'histoire de la saison
        for i, m in enumerate(matches):
            mode = m.get("mode", "1v1")
            gain = 0
            loss = 0

            # --- Logique 1v1 ---
            if mode == "1v1":
                w_id, l_id = m["winner_id"], m["loser_id"]
                if w_id in temp_elo_1v1 and l_id in temp_elo_1v1:
                    new_w, new_l, gain, loss = engine.compute_new_ratings(
                        temp_elo_1v1[w_id], temp_elo_1v1[l_id],
                        matches_1v1[w_id], matches_1v1[l_id]
                    )
                    temp_elo_1v1[w_id] = new_w
                    temp_elo_1v1[l_id] = new_l
                    matches_1v1[w_id] += 1
                    matches_1v1[l_id] += 1

            # --- Logique 2v2 ---
            elif mode == "2v2":
                ids = [m["winner_id"], m["winner2_id"], m["loser_id"], m["loser2_id"]]
                if all(pid in temp_elo_2v2 for pid in ids if pid):
                    w_avg = (temp_elo_2v2[m["winner_id"]] + temp_elo_2v2[m["winner2_id"]]) / 2
                    l_avg = (temp_elo_2v2[m["loser_id"]] + temp_elo_2v2[m["loser2_id"]]) / 2

                    _, _, gain, loss = engine.compute_new_ratings(w_avg, l_avg, 0, 0)

                    for pid in [m["winner_id"], m["winner2_id"]]:
                        temp_elo_2v2[pid] += gain
                        matches_2v2[pid] += 1
                    for pid in [m["loser_id"], m["loser2_id"]]:
                        temp_elo_2v2[pid] -= loss
                        matches_2v2[pid] += 1

            # Correction de l'historique dans la BDD (si le K-factor avait déraillé)
            stored_gain = m.get("elo_gain", 0)
            if abs(stored_gain - gain) > 0.01:
                db.supabase.table("matches").update({
                    "elo_gain": gain,
                    "elo_loss": loss
                }).eq("id", m["id"]).execute()
                corrected_matches += 1

        status_text.text("💾 Sauvegarde des scores finaux...")

        # E. Mise à jour finale des profils
        all_ids = set(temp_elo_1v1.keys()) | set(temp_elo_2v2.keys())

        for p_id in all_ids:
            updates = {}
            if p_id in temp_elo_1v1:
                # 🔴 CORRECTION : On force le format Entier (Integer)
                updates["elo_rating"] = int(round(temp_elo_1v1[p_id]))
                updates["matches_played"] = matches_1v1[p_id]
            if p_id in temp_elo_2v2:
                # 🔴 CORRECTION : On force le format Entier (Integer)
                updates["elo_2v2"] = int(round(temp_elo_2v2[p_id]))
                updates["matches_2v2"] = matches_2v2[p_id]

            if updates:
                db.supabase.table("profiles").update(updates).eq("id", p_id).execute()

        progress_bar.empty()
        status_text.empty()
        st.success(
            f"✅ Réparation terminée ! La saison en cours a été recalculée depuis le soft-reset. ({corrected_matches} matchs ajustés)."
        )
        st.balloons()

    st.divider()
    st.subheader("📅 Clôture de Saison")
    st.info("Cette action va archiver les scores, donner les titres au Top 3 et reset les Elos de tout le monde.")

    with st.expander("🚀 Lancer la fin de saison"):
        # --- SÉLECTEURS DE DATE POUR LE NOM DE SAISON ---
        col_c1, col_c2 = st.columns(2)

        mois_fr = [
            "Janvier", "Février", "Mars", "Avril", "Mai", "Juin", 
            "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"
        ]

        # On récupère la date actuelle pour pré-remplir les sélecteurs
        now = datetime.now()

        with col_c1:
            sel_month = st.selectbox("Mois de la saison", mois_fr, index=now.month - 1)
        with col_c2:
            # On propose de 2025 à 2030, adaptable si besoin
            sel_year = st.selectbox("Année", list(range(2025, 2031)), index=list(range(2025, 2031)).index(now.year))

        # On construit automatiquement le nom (ex: "Avril 2026")
        s_name = f"{sel_month} {sel_year}"

        st.write(f"Saison à clôturer : **{s_name}**")

        s_mode = st.radio("Mode à clôturer", ["Solo (1v1)", "Duo (2v2)", "Les deux"], horizontal=True)

        st.warning("⚠️ Attention : Cette action est irréversible.")

        if st.button("Confirmer la clôture et Reset les Elos", type="primary"):
            modes_to_process = []
            if s_mode == "Solo (1v1)": 
                modes_to_process = ["1v1"]
            elif s_mode == "Duo (2v2)": 
                modes_to_process = ["2v2"]
            else:
                modes_to_process = ["1v1", "2v2"]

            success_count = 0
            for m in modes_to_process:
                # On utilise le s_name construit proprement
                success, msg = db.close_season_logic(s_name, mode=m)
                if success:
                    success_count += 1
                    st.success(f"✅ {m} : {msg}")
                else:
                    st.error(f"❌ {m} : {msg}")

            if success_count > 0:
                st.balloons()
                st.rerun()

    # --- OUTIL TEMPORAIRE : PURGE DES ÉMOJIS & TITRES MARS 2026 ---
    st.divider()
    with st.expander("🛠️ Nettoyer les émojis et réparer les titres (Mars 2026)"):
        st.info("Ce bouton purge les émojis de la base de données et distribue les titres propres (sans emoji).")
        if st.button("Purger et Distribuer", type="primary"):
            try:
                # 1. PURGE GLOBALE : On retire les émojis de tous les profils existants
                all_profs = db.supabase.table("profiles").select("id, unlocked_titles, equipped_title").execute().data
                for prof in all_profs:
                    has_changed = False
                    clean_titles = []
                    if prof.get("unlocked_titles"):
                        for t in prof["unlocked_titles"]:
                            clean_t = t.replace("🏆 ", "").replace("🥈 ", "").replace("🥉 ", "").replace("🥇 ", "")
                            clean_titles.append(clean_t)
                            if clean_t != t:
                                has_changed = True

                    eq_title = prof.get("equipped_title")
                    if eq_title:
                        eq_title = eq_title.replace("🏆 ", "").replace("🥈 ", "").replace("🥉 ", "").replace("🥇 ", "")

                    if has_changed or eq_title != prof.get("equipped_title"):
                        db.supabase.table("profiles").update({"unlocked_titles": clean_titles, "equipped_title": eq_title}).eq("id", prof["id"]).execute()

                # 2. DISTRIBUTION PROPRE
                count_updates = 0
                for m_db, m_lbl in [("1v1", "Solo"), ("2v2", "Duo")]:
                    arch_data = db.supabase.table("season_archives").select("*").eq("season_name", "Mars 2026").eq("mode", m_db).order("final_rank", desc=False).execute().data

                    for p in arch_data:
                        p_id = p["player_id"]
                        f_rank = p["final_rank"]
                        f_elo = p["final_elo"]
                        f_matches = p.get("matches_played", 0)

                        prof = db.supabase.table("profiles").select("unlocked_titles").eq("id", p_id).single().execute().data
                        if not prof:
                            continue
                        titles = prof.get("unlocked_titles", [])
                        if titles is None:
                            titles = []

                        clean_titles = [t for t in titles if not ("Mars 2026" in t and (m_lbl in t or "Solo" not in t and "Duo" not in t))]
                        needs_update = False

                        if f_matches > 1:
                            r_name = "Novice"
                            for tier in reversed(RANK_TIERS):
                                if f_elo >= tier["threshold"]:
                                    r_name = tier["name"]
                                    break
                            r_title = f"{r_name} {m_lbl} Mars 2026"
                            if r_title not in clean_titles:
                                clean_titles.append(r_title)
                                needs_update = True

                        if f_rank == 1:
                            c_title = f"Champion {m_lbl} de Mars 2026"
                            if c_title not in clean_titles:
                                clean_titles.append(c_title)
                                needs_update = True
                        elif f_rank == 2:
                            d_title = f"Dauphin {m_lbl} de Mars 2026"
                            if d_title not in clean_titles:
                                clean_titles.append(d_title)
                                needs_update = True
                        elif f_rank == 3:
                            p_title = f"3ème {m_lbl} de Mars 2026"
                            if p_title not in clean_titles:
                                clean_titles.append(p_title)
                                needs_update = True

                        if needs_update or len(clean_titles) != len(titles):
                            db.supabase.table("profiles").update({"unlocked_titles": clean_titles}).eq("id", p_id).execute()
                            count_updates += 1

                st.success(f"✅ Émojis supprimés et Titres propres distribués à {count_updates} joueurs !")
                st.balloons()
            except Exception as e:
                st.error(f"Erreur : {e}")
