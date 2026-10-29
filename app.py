import extra_streamlit_components as stx
import streamlit as st

from base_function_temp.get_rank_info import get_rank_info
from base_function_temp.render_xp_bar import render_xp_bar
from DB_manager import DBManager
from frontend.src.pages import (
    classement,
    comparateur_joueurs,
    declarer_match,
    entrainements,
    grand_tournoi,
    nouveautes,
    panel_admin,
    parametres,
    profils_joueurs,
    reglement,
    validations,
    weekly_fun,
)
from frontend.styles.style import set_style
from frontend.styles.style_2 import set_style_2

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
if "db" not in st.session_state:
    st.session_state.db = DBManager()

db = st.session_state.db
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
    classement.afficher(db, user)

elif page == "👤 Profils Joueurs":
    profils_joueurs.afficher(db, user)

elif page == "🎯 Déclarer un match":
    declarer_match.afficher(db, user)

elif page == "🆚 Comparateur de joueurs":
    comparateur_joueurs.afficher(db, user)

elif page == "📑 Mes validations":
    validations.afficher(db, user)

elif page == "📢 Nouveautés":
    nouveautes.afficher()

elif page == "📜 Règlement":
    reglement.afficher()

elif page == "🔧 Panel Admin":
    panel_admin.afficher(db)

elif page == "🏟️ Grand Tournoi":
    grand_tournoi.afficher(db, user)

elif page == "⚙️ Paramètres":
    parametres.afficher(db, user)

elif page == "🍻 Weekly Fun":
    weekly_fun.afficher(db, user)

elif page == "🧠 Entraînements":
    entrainements.afficher(db, user)
