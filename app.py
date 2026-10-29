from datetime import datetime

import altair as alt
import extra_streamlit_components as stx
import pandas as pd
import streamlit as st

from badges_config import BADGES_B64  # <-- Ajout de cette ligne
from base_function_temp.draw_luxury_table import draw_luxury_table
from base_function_temp.draw_rank_badge import draw_rank_badge
from base_function_temp.get_badges_html import get_badges_html
from base_function_temp.get_rank_info import get_rank_info
from base_function_temp.render_xp_bar import render_xp_bar
from DB_manager import DBManager
from elo_engine import EloEngine
from frontend.styles.maj_260122 import st_maj260122
from frontend.styles.style import set_style
from frontend.styles.style_2 import set_style_2
from ranks_config import RANK_TIERS

# --- CONFIGURATION DU CODE SECRET ---
SECRET_INVITE_CODE = st.secrets["INVITE_CODE"]

# ==========================================
# 🎨 CHIRURGIE ESTHÉTIQUE DE L'APPLICATION
# ==========================================

# 1. Configuration de la page (Doit être en tout premier)
# (Pense à supprimer tes anciens appels st.set_page_config s'ils existent déjà).
st.set_page_config(page_title="Snook'R Club", page_icon="🎱", layout="wide")

st.markdown(set_style, unsafe_allow_html=True)

# 2. Initialisation du manager et du CookieManager
db = DBManager()
cookie_manager = stx.CookieManager()

# Initialisation du drapeau de déconnexion ---
if "logout_clicked" not in st.session_state:
    st.session_state.logout_clicked = False

# --- STYLE CSS ---
st.markdown(
    set_style_2,
    unsafe_allow_html=True,
)

# 3. GESTION DE LA SESSION
# SÉCURITÉ : On initialise la clé si elle est absente
if "user_data" not in st.session_state:
    st.session_state.user_data = None

# --- RESTAURATION DE LA SESSION SUPABASE ---
# On récupère les tokens cryptés
access_token = cookie_manager.get("bb_access_token")
refresh_token = cookie_manager.get("bb_refresh_token")

# 1. On s'assure que la connexion base de données sait QUI on est à chaque clic
if access_token and refresh_token and not st.session_state.logout_clicked:
    try:
        db.supabase.auth.set_session(access_token, refresh_token)
    except Exception:
        pass  # Le token est peut-être expiré

# 2. On récupère les données du profil SEULEMENT si elles ne sont pas déjà en mémoire
if st.session_state.user_data is None and not st.session_state.logout_clicked:
    try:
        session = db.supabase.auth.get_session()
        if session and session.user:
            user_profile = (
                db.supabase.table("profiles")
                .select("*")
                .eq("id", session.user.id)
                .single()
                .execute()
            )
            if user_profile.data:
                st.session_state.user_data = user_profile.data
    except Exception:
        pass
# --- ÉCRAN DE CONNEXION / INSCRIPTION ---
if st.session_state.user_data is None:
    # Le nouveau titre "Luxe" pour la page de connexion
    st.markdown("""
    <div style="display: flex; align-items: center; gap: 15px; margin-bottom: 30px; margin-top: 10px;">
        <div style="font-size: 3.5em; text-shadow: 2px 2px 5px rgba(0,0,0,0.5);">🎱</div>
        <div style="line-height: 1.1;">
            <div style="font-family: 'Playfair Display', serif; font-size: 3.5em; font-weight: 700; color: #C69C25; text-shadow: 2px 2px 4px rgba(0,0,0,0.4);">Snook'R</div>
            <div style="font-family: 'Playfair Display', serif; font-size: 1.8em; font-style: italic; color: #8BA1B5;">BlackBall Club</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["Connexion", "Créer un compte"])

    with tab1:
        with st.form("login_form"):
            email = st.text_input("Email")
            pwd = st.text_input("Mot de passe", type="password", autocomplete="current-password")

            # 1. On capture le clic dans une variable 'submitted'
            submitted = st.form_submit_button("Se connecter")

            if submitted:
                auth_success = False  # On initialise le succès à Faux

                try:
                    auth_res = db.log_in(email, pwd)

                    # SÉCURITÉ : On stocke les tokens (clés cryptées) et non l'ID brut
                    if auth_res.session:
                        cookie_manager.set(
                            "bb_access_token",
                            auth_res.session.access_token,
                            key="set_access",
                        )
                        cookie_manager.set(
                            "bb_refresh_token",
                            auth_res.session.refresh_token,
                            key="set_refresh",
                        )

                    # On récupère le profil
                    user_id = auth_res.user.id
                    user_profile = (
                        db.supabase.table("profiles")
                        .select("*")
                        .eq("id", user_id)
                        .single()
                        .execute()
                    )
                    st.session_state.user_data = user_profile.data

                    # Si on arrive ici sans erreur, on valide le succès
                    auth_success = True

                except:
                    st.error("Identifiants incorrects ou erreur technique.")

                # 2. Le redémarrage se fait EN DEHORS du try/except
                if auth_success:
                    st.session_state.logout_clicked = False
                    st.success("Connexion réussie !")
                    st.rerun()

        # BOUTON VISITEUR ---
        st.write("---")
        if st.button("👁️ Entrer sans compte (Mode Visiteur)"):
            # On crée un "faux" profil directement dans la mémoire
            st.session_state.user_data = {
                "id": "guest",
                "username": "Visiteur",
                "role": "guest"
            }
            st.session_state.guest_mode = True
            st.rerun()

        st.write("---")

        # --- MOT DE PASSE OUBLIÉ (MÉTHODE PAR CODE) ---
        with st.expander("Mot de passe oublié ?"):
            st.info("Entrez votre email. Vous recevrez un code à 8 caractères pour changer votre mot de passe.")

            # Étape 1 : Saisie de l'email
            reset_email = st.text_input("Votre adresse email", key="reset_email_input")

            if st.button("Envoyer le code", type="secondary"):
                if not reset_email:
                    st.warning("Veuillez entrer une adresse email.")
                else:
                    success, msg = db.send_password_reset(reset_email)
                    if success:
                        st.session_state.reset_in_progress = True
                        st.session_state.reset_email_target = reset_email
                        st.success("📧 Email envoyé ! Vérifiez vos spams et revenez ici pour entrer le code.")
                        st.rerun()
                    else:
                        st.error(msg)

            # Étape 2 : Saisie du code et du nouveau mot de passe
            if st.session_state.get("reset_in_progress"):
                st.divider()
                st.markdown(f"Veuillez entrer le code reçu sur **{st.session_state.reset_email_target}**")

                # Modification ici : max_chars passe à 8
                reset_code = st.text_input("Code à 8 caractères reçu par e-mail", max_chars=8)
                new_pwd = st.text_input("Nouveau mot de passe (6 caractères min.)", type="password", key="new_pwd_reset")
                new_pwd_confirm = st.text_input("Confirmez le nouveau mot de passe", type="password", key="new_pwd_confirm_reset")

                if st.button("Valider et changer le mot de passe", type="primary"):
                    # Modification ici : on vérifie que la longueur est bien de 8
                    if len(reset_code) != 8:
                        st.error("Le code doit faire exactement 8 caractères.")
                    elif len(new_pwd) < 6:
                        st.error("Le mot de passe doit faire au moins 6 caractères.")
                    elif new_pwd != new_pwd_confirm:
                        st.error("Les mots de passe ne correspondent pas.")
                    else:
                        # 1. Vérification du code
                        success_otp, msg_otp = db.verify_reset_code(st.session_state.reset_email_target, reset_code)
                        if success_otp:
                            # 2. Mise à jour du MDP
                            success_pwd, msg_pwd = db.update_password(new_pwd)
                            if success_pwd:
                                st.success("✅ Mot de passe changé avec succès ! Vous pouvez maintenant vous connecter normalement en haut.")
                                st.session_state.reset_in_progress = False
                                st.balloons()
                            else:
                                st.error(msg_pwd)
                        else:
                            st.error("❌ Code incorrect ou expiré.")

    with tab2:
        st.info("⚠️ Un code d'invitation est requis pour s'inscrire.")
        with st.form("signup_form"):
            new_email = st.text_input("Email")
            new_pwd = st.text_input("Mot de passe (6 caractères min.)", type="password")
            new_pseudo = st.text_input(
                "Prénom Nom (obligatoirement sinon le compte sera supprimé)"
            )
            user_invite_code = st.text_input(
                "Code d'invitation secret", type="password"
            )

            if st.form_submit_button("S'inscrire"):
                if user_invite_code != SECRET_INVITE_CODE:
                    st.error("❌ Code d'invitation incorrect.")
                elif not new_email or not new_pwd or not new_pseudo:
                    st.warning("Veuillez remplir tous les champs.")
                else:
                    try:
                        db.sign_up(new_email, new_pwd, new_pseudo)
                        st.success(
                            "✅ Compte créé ! Connectez-vous via l'onglet 'Connexion'."
                        )
                    except Exception as e:
                        st.error(f"Erreur : {e}")
    st.stop()

# --- SI CONNECTÉ : SYNCHRONISATION DES INFOS ---
current_id = st.session_state.user_data["id"]

# On vérifie si c'est le visiteur avant d'interroger la base de données !
if current_id != "guest":
    fresh_user = (
        db.supabase.table("profiles").select("*").eq("id", current_id).single().execute()
    )
    user = fresh_user.data

    # --- LOGIQUE D'INTERCEPTION (EFFET WAOUH CINÉMATIQUE 1V1 ET 2V2) ---
    if user and current_id != "guest":
        # --- 1. INITIALISATION DES DONNÉES ---
        last_seen_1v1 = user.get("last_seen_elo_1v1")
        last_seen_2v2 = user.get("last_seen_elo_2v2")

        updates_init = {}
        if last_seen_1v1 is None:
            last_seen_1v1 = user.get("elo_rating", 1000)
            updates_init["last_seen_elo_1v1"] = last_seen_1v1
        if last_seen_2v2 is None:
            last_seen_2v2 = user.get("elo_2v2", 1000)
            updates_init["last_seen_elo_2v2"] = last_seen_2v2

        if updates_init:
            db.supabase.table("profiles").update(updates_init).eq("id", user["id"]).execute()

        # --- 2. VÉRIFICATION DU 1V1 ---
        if user.get("elo_rating") != last_seen_1v1:
            old_r = get_rank_info(last_seen_1v1, user.get("current_rank_id_1v1"))
            new_r = get_rank_info(user["elo_rating"], user.get("current_rank_id_1v1"))

            is_gain = user["elo_rating"] > last_seen_1v1
            is_promo = new_r["id"] > old_r["id"]
            is_demote = new_r["id"] < old_r["id"]

            if is_promo:
                st.balloons()
                title = "🚀 NOUVEAU GRADE 1V1 !"
                msg = f"Incroyable ! Vous montez en grade Solo : <b>{new_r['name']}</b>"
            elif is_demote:
                title = "📉 Rétrogradation 1v1"
                msg = "Courage ! Un mauvais passage en Solo, mais vous allez remonter."
            elif is_gain:
                st.balloons()
                title = "🎊 Nouveaux résultats 1v1 !"
                msg = "Félicitations ! Vos points Solo ont été mis à jour."
            else:
                title = "📊 Résultats mis à jour (1v1)"
                msg = "Vos derniers matchs Solo ont été enregistrés."

            st.markdown(f"<h2 style='text-align: center; color: #C69C25; font-family: \"Playfair Display\";'>{title}</h2>", unsafe_allow_html=True)
            st.markdown(f"<p style='text-align: center; opacity: 0.8;'>{msg}</p>", unsafe_allow_html=True)

            st.markdown(render_xp_bar(last_seen_1v1, user["elo_rating"], old_r, new_r), unsafe_allow_html=True)

            if st.button("Continuer", use_container_width=True, key="btn_continue_1v1"):
                updates = {
                    "last_seen_elo_1v1": user["elo_rating"],
                    "current_rank_id_1v1": new_r["id"]
                }
                db.supabase.table("profiles").update(updates).eq("id", user["id"]).execute()
                st.rerun()

            st.stop()  # On bloque ici tant que le 1v1 n'est pas validé

        # --- 3. VÉRIFICATION DU 2V2 ---
        # Si le 1v1 est à jour (ou vient d'être validé), on vérifie le 2v2
        elif user.get("elo_2v2") != last_seen_2v2:
            old_r_2v2 = get_rank_info(last_seen_2v2, user.get("current_rank_id_2v2"))
            new_r_2v2 = get_rank_info(user["elo_2v2"], user.get("current_rank_id_2v2"))

            is_gain_2v2 = user["elo_2v2"] > last_seen_2v2
            is_promo_2v2 = new_r_2v2["id"] > old_r_2v2["id"]
            is_demote_2v2 = new_r_2v2["id"] < old_r_2v2["id"]

            if is_promo_2v2:
                st.balloons()
                title = "🚀 NOUVEAU GRADE 2V2 !"
                msg = f"Incroyable ! Vous montez en grade Duo : <b>{new_r_2v2['name']}</b>"
            elif is_demote_2v2:
                title = "📉 Rétrogradation 2v2"
                msg = "Courage ! Un mauvais passage en Duo, mais l'équipe va se reprendre."
            elif is_gain_2v2:
                st.balloons()
                title = "🎊 Nouveaux résultats 2v2 !"
                msg = "Félicitations ! Vos points Duo ont été mis à jour."
            else:
                title = "📊 Résultats mis à jour (2v2)"
                msg = "Vos derniers matchs Duo ont été enregistrés."

            st.markdown(f"<h2 style='text-align: center; color: #4facfe; font-family: \"Playfair Display\";'>{title}</h2>", unsafe_allow_html=True)
            st.markdown(f"<p style='text-align: center; opacity: 0.8;'>{msg}</p>", unsafe_allow_html=True)

            # On utilise exactement la même fonction d'affichage !
            st.markdown(render_xp_bar(last_seen_2v2, user["elo_2v2"], old_r_2v2, new_r_2v2), unsafe_allow_html=True)

            if st.button("Continuer vers le club", use_container_width=True, key="btn_continue_2v2"):
                updates_2v2 = {
                    "last_seen_elo_2v2": user["elo_2v2"],
                    "current_rank_id_2v2": new_r_2v2["id"]
                }
                db.supabase.table("profiles").update(updates_2v2).eq("id", user["id"]).execute()
                st.rerun()

            st.stop()  # On bloque ici tant que le 2v2 n'est pas validé
    st.session_state.user_data = user
else:
    user = st.session_state.user_data

# --- CALCUL DES RANGS (1v1 et 2v2) ---

# 1. Calcul du Rang SOLO
lb_1v1 = db.get_leaderboard(mode="1v1").data
try:
    rank_1v1 = next(i for i, p in enumerate(lb_1v1) if p["id"] == user["id"]) + 1
except StopIteration:
    rank_1v1 = "-"

# 2. Calcul du Rang DUO
lb_2v2 = db.get_leaderboard(mode="2v2").data
try:
    # On cherche le rang dans la liste triée par Elo 2v2
    rank_2v2 = next(i for i, p in enumerate(lb_2v2) if p["id"] == user["id"]) + 1
except StopIteration:
    rank_2v2 = "-"

# --- BARRE LATÉRALE ---
# 1. Affichage du Logo Panda
# (Assure-toi que l'image s'appelle 'logo.jpg' et est dans le même dossier)
try:
    # On ajoute un peu d'espace avant et après le logo pour que ça respire
    st.sidebar.write("")
    st.sidebar.image("panda_logo.png", use_container_width=True)
    st.sidebar.write("")
except Exception:
    # Sécurité : Si l'image n'est pas trouvée,
    # on remet l'ancien texte au lieu de faire planter l'appli
    st.sidebar.markdown("<div class='sidebar-logo-text'>🎱 Snook'R</div>", unsafe_allow_html=True)
    st.sidebar.markdown("<div style='text-align: center; color: #888; margin-top: -15px; margin-bottom: 20px; font-style: italic;'>Blackball Club</div>", unsafe_allow_html=True)

st.sidebar.write(f"Joueur : **{user['username']}**")

st.sidebar.divider()

# Affichage "Tableau de bord" avec des colonnes
col_solo, col_duo = st.sidebar.columns(2)

with col_solo:
    st.markdown("### 👤 Solo")
    st.write(f"Rang : **#{rank_1v1}**")
    # On utilise st.metric pour un look plus "statistique"
    st.metric("Elo", user.get("elo_rating", 1000))

with col_duo:
    st.markdown("### 👥 Duo")
    st.write(f"Rang : **#{rank_2v2}**")
    # Gestion du cas où l'Elo 2v2 est null ou vide
    elo_duo = user.get("elo_2v2") if user.get("elo_2v2") else 1000
    st.metric("Elo", elo_duo)

st.sidebar.divider()

# --- MENU NAVIGATION ---
menu_options = [
    "🏆 Classement",
    "👤 Profils Joueurs",
    "🎯 Déclarer un match",
    "🆚 Comparateur de joueurs",
    "📑 Mes validations",
    "🧠 Entraînements",
    "🍻 Weekly Fun",
    "🏟️ Grand Tournoi",
    "📢 Nouveautés",
    "📜 Règlement",
    "⚙️ Paramètres",
]

if user.get("is_admin"):
    menu_options.append("🔧 Panel Admin")

# On utilise label_visibility="collapsed" pour un look plus épuré
page = st.sidebar.radio(
    "Menu Navigation",
    menu_options,
    label_visibility="collapsed"
)

st.sidebar.write("")  # Un petit espace pour respirer avant la suite

# BOUTON DÉCONNEXION ROBUSTE
if st.sidebar.button("Déconnexion"):
    # 1. On supprime les tokens (ceux-là existent forcément si on est connecté)
    cookie_manager.delete("bb_access_token", key="del_access")
    cookie_manager.delete("bb_refresh_token", key="del_refresh")

    # 2. On essaie de supprimer l'ancien cookie ID (nettoyage)
    # On met un try/except pour éviter le crash si le cookie n'existe déjà plus
    try:
        cookie_manager.delete("bb_user_id", key="del_user")
    except KeyError:
        pass  # Le cookie n'existe pas ? Pas grave, on passe à la suite.

    # 3. Déconnexion Supabase et nettoyage session
    db.supabase.auth.sign_out()
    st.session_state.user_data = None

    # 4. Drapeau anti-reconnexion
    st.session_state.logout_clicked = True

    st.rerun()

# --- LOGIQUE DES PAGES ---

elif page == "🏆 Classement":
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

elif page == "👤 Profils Joueurs":
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

elif page == "🎯 Déclarer un match":
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

elif page == "🆚 Comparateur de joueurs":
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

elif page == "📑 Mes validations":
    st.header("📑 Matchs à confirmer")

    # 🛑 VÉRIFICATION DU MODE VISITEUR 🛑
    is_guest = st.session_state.get("guest_mode", False)

    if is_guest:
        # Message pour le visiteur
        st.warning("🔒 Accès restreint")
        st.write("Vous êtes actuellement en Mode Visiteur. Vous devez créer un compte pour recevoir et valider des matchs.")

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
                            success, msg = db.validate_match_logic(m["id"])
                            if success:
                                st.rerun()
                    with col_ref:
                        if st.button("C'est une erreur ❌", key=f"ref_{m['id']}"):
                            db.reject_match(m["id"])
                            st.rerun()

elif page == "📢 Nouveautés":
    st.header("📢 Nouveautés & Mises à jour")

    # --- MISE A JOUR V2.1 ---
    with st.container(border=True):
        st.subheader("💎 Mise à jour v2.1 : Trophées & Rivalités")
        st.caption("Déployée le 22 Janvier 2026")

        st.markdown(st_maj260122)

elif page == "📜 Règlement":
    st.header("📜 Règlement Officiel")
    st.markdown(
        """
    ### 1. L'Esprit du Jeu 🤝
    Le but de ce classement est de stimuler la compétition dans une ambiance amicale. Le **fair-play** est la règle absolue. Tout comportement anti-sportif, triche ou manque de respect pourra entraîner une exclusion du classement.

    ### 2. Déroulement et Validation des Matchs 📱
    * **Article 2.1 - Déclaration :** Seul le **vainqueur** déclare le match sur l'application immédiatement après la fin de la partie.
    * **Article 2.2 - Validation :** Le perdant doit se connecter et **confirmer sa défaite** dans l'onglet "Mes validations" pour que les points comptent.
    * **Article 2.3 - Délai :** Tout match non validé sous 48h pourra être traité par un administrateur.

    ### 3. Fonctionnement du Classement Elo 📈
    * **Départ :** 1000 points.
    * **Somme nulle :** Les points gagnés par le vainqueur sont retirés au vaincu.
    * **Logique :** Battre un joueur plus fort rapporte beaucoup de points ("Perf"). Perdre contre un plus faible en coûte beaucoup ("Contre-perf").

    ### 4. Paramètres Techniques ⚙️
    * **Facteur K = 40 (Fixe) :** Le classement est volontairement dynamique. Une bonne série vous propulse vite vers le sommet.
    * **Écart type (400) :** Un écart de 400 points signifie 91% de chances de victoire pour le favori.

    ### 5. Intégrité et Interdictions 🚫
    * **Interdit :** Déclarer des faux matchs, perdre volontairement ("Sandbagging"), ou créer plusieurs comptes ("Smurfing").
    * **Déconseillé :** "Farmer" le même adversaire 10 fois de suite. Variez les rencontres !

    ### 6. Gestion des Litiges ⚖️
    En cas d'erreur ou de désaccord, utilisez les boutons de contestation. Les administrateurs trancheront.

    ---
    > *"Ne jouez pas pour protéger vos points, jouez pour progresser !"*
    """
    )

elif page == "🔧 Panel Admin":
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

elif page == "🏟️ Grand Tournoi":
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
                

elif page == "⚙️ Paramètres":
    st.header("⚙️ Paramètres du compte")

    # --- 🏆 NOUVEAU : SECTION MON TITRE ---
    st.subheader("🎖️ Mon Titre")
    
    # On récupère la liste de façon sécurisée (on gère le None)
    unlocked = user.get("unlocked_titles", [])
    if unlocked is None: unlocked = []

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

elif page == "🍻 Weekly Fun":
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
                        rank = i + 1; current_rank = rank
                    player_ranks[uid] = rank
                    player_names[uid] = uname if p.get("is_active", True) else f"{uname} (Parti)"

                shots_matrix = {}
                for s in scores_data:
                    uid = s["user_id"]
                    shot_num = s["shot_number"]
                    if shot_num not in shots_matrix: shots_matrix[shot_num] = {}
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

elif page == "🧠 Entraînements":
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
        st.markdown(
            f"""
<div style='background: linear-gradient(145deg, #0f172a, #1e293b); padding: 25px; border-radius: 12px; border: 1px solid #C69C25; border-left: 8px solid #C69C25; box-shadow: 0 4px 15px rgba(0,0,0,0.4); margin-bottom: 25px;'>
    <h2 style='margin-top: 0; margin-bottom: 15px; color: #C69C25; font-family: "Playfair Display", serif; font-size: 28px; font-weight: bold; letter-spacing: 0.5px;'>
        🧠 {current_training['name']}
    </h2>
    <div style='display: flex; flex-wrap: wrap; gap: 15px; margin-bottom: 20px;'>
        <div style='background-color: rgba(198,156,37,0.1); padding: 8px 15px; border-radius: 8px; color: #e0e0e0; font-weight: 500; font-size: 15px; border: 1px solid rgba(198,156,37,0.2);'>
            📅 Date : <span style='color: #ffffff; font-weight: bold;'>{formatted_date}</span>
        </div>
        <div style='background-color: rgba(198,156,37,0.1); padding: 8px 15px; border-radius: 8px; color: #e0e0e0; font-weight: 500; font-size: 15px; border: 1px solid rgba(198,156,37,0.2);'>
            🎟️ Places : <span style='color: #ffffff; font-weight: bold;'>{current_training['max_players']} max</span>
        </div>
    </div>
    <div style='color: #cccccc; font-size: 16px; line-height: 1.5; border-top: 1px dashed rgba(198,156,37,0.3); padding-top: 15px;'>
        <i>{description_text}</i>
    </div>
</div>
            """, 
            unsafe_allow_html=True
        )
        
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