import streamlit as st
from DB_manager import DBManager
import pandas as pd
import extra_streamlit_components as stx

# --- CONFIGURATION DU CODE SECRET ---
SECRET_INVITE_CODE = st.secrets["INVITE_CODE"]

# 1. Configuration de la page
st.set_page_config(
    page_title="🎱 BlackBall Compétition",
    page_icon="🎱",
    layout="centered",
)

# 2. Initialisation du manager et du CookieManager
db = DBManager()
cookie_manager = stx.CookieManager()

# --- STYLE CSS ---
st.markdown(
    """
    <style>
    .main { background-color: #0e1117; }
    stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #2ecc71; color: white; }
    .stDataFrame { background-color: #1f2937; border-radius: 10px; }
    </style>
    """,
    unsafe_allow_html=True,
)

# 3. GESTION DE LA SESSION (Correction de l'AttributeError)
# SÉCURITÉ : On initialise la clé si elle est absente pour éviter le crash au premier chargement
if "user_data" not in st.session_state:
    st.session_state.user_data = None

# Tentative de reconnexion automatique via Cookies ou Session Supabase
if st.session_state.user_data is None:
    # 1. On vérifie d'abord les cookies (pour le rafraîchissement de page)
    saved_user_id = cookie_manager.get("bb_user_id")

    if saved_user_id:
        try:
            user_profile = (
                db.supabase.table("profiles")
                .select("*")
                .eq("id", saved_user_id)
                .single()
                .execute()
            )
            if user_profile.data:
                st.session_state.user_data = user_profile.data
        except Exception:
            pass

    # 2. Si toujours rien, on tente de récupérer la session active Supabase
    if st.session_state.user_data is None:
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
                st.session_state.user_data = user_profile.data
        except Exception:
            pass

# --- ÉCRAN DE CONNEXION / INSCRIPTION ---
if st.session_state.user_data is None:
    st.title("🎱 BlackBall Compétition")
    tab1, tab2 = st.tabs(["Connexion", "Créer un compte"])

    with tab1:
        with st.form("login_form"):
            email = st.text_input("Email")
            pwd = st.text_input("Mot de passe", type="password")
            if st.form_submit_button("Se connecter"):
                try:
                    auth_res = db.log_in(email, pwd)
                    user_id = auth_res.user.id

                    # Sauvegarde du cookie pour 30 jours
                    cookie_manager.set("bb_user_id", user_id, key="set_cookie_login")

                    user_profile = (
                        db.supabase.table("profiles")
                        .select("*")
                        .eq("id", user_id)
                        .single()
                        .execute()
                    )
                    st.session_state.user_data = user_profile.data
                    st.success("Connexion réussie !")
                    st.rerun()
                except Exception:
                    st.error("Identifiants incorrects ou compte non vérifié.")

    with tab2:
        st.info("⚠️ Un code d'invitation est requis pour s'inscrire.")
        with st.form("signup_form"):
            new_email = st.text_input("Email")
            new_pwd = st.text_input("Mot de passe (6 caractères min.)", type="password")
            new_pseudo = st.text_input("Prénom Nom (le compte sera supprimé dans le cas contraire)")
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
fresh_user = (
    db.supabase.table("profiles").select("*").eq("id", current_id).single().execute()
)
user = fresh_user.data
st.session_state.user_data = user

# --- CALCUL DU RANG ---
leaderboard_data = db.get_leaderboard().data
try:
    user_rank = (
        next(i for i, p in enumerate(leaderboard_data) if p["id"] == user["id"]) + 1
    )
except:
    user_rank = "?"

# --- BARRE LATÉRALE ---
st.sidebar.title("🎱 BlackBall")
st.sidebar.write(f"Joueur : **{user['username']}**")
st.sidebar.write(f"Rang : **#{user_rank}**")
st.sidebar.write(f"Elo : **{user['elo_rating']}**")

# Ajout de l'option "Face-à-Face" dans le menu
menu_options = [
    "🏆 Classement",
    "🎯 Déclarer un match",
    "🆚 Historique des Duels",
    "📑 Mes validations",
]
if user.get("is_admin"):
    menu_options.append("🔧 Panel Admin")

page = st.sidebar.radio("Navigation", menu_options)

if st.sidebar.button("Déconnexion"):
    cookie_manager.delete("bb_user_id", key="delete_logout")
    db.supabase.auth.sign_out()
    st.session_state.user_data = None
    st.rerun()

# --- LOGIQUE DES PAGES ---

if page == "🏆 Classement":
    st.header("🏆 Tableau des Leaders")
    res = db.get_leaderboard()
    if res.data:
        df = pd.DataFrame(res.data)
        df = df[["username", "elo_rating", "matches_played"]]
        df.columns = ["Joueur", "Points Elo", "Matchs"]
        st.dataframe(df, use_container_width=True, hide_index=True)

elif page == "🎯 Déclarer un match":
    st.header("🎯 Enregistrer un résultat")
    players_res = db.get_leaderboard()
    adversaires = [p for p in players_res.data if p["id"] != user["id"]]

    if not adversaires:
        st.warning("Aucun autre joueur inscrit.")
    else:
        adv_map = {p["username"]: p["id"] for p in adversaires}
        with st.form("match_form"):
            adv_nom = st.selectbox("Contre qui avez-vous gagné ?", list(adv_map.keys()))
            if st.form_submit_button("Envoyer pour validation"):
                db.declare_match(user["id"], adv_map[adv_nom], user["id"])
                st.success(f"Match envoyé à {adv_nom} !")

    st.divider()
    st.subheader("Mes déclarations récentes")
    my_wins = (
        db.supabase.table("matches")
        .select("*, profiles!loser_id(username)")
        .eq("winner_id", user["id"])
        .order("created_at", desc=True)
        .limit(5)
        .execute()
        .data
    )
    for w in my_wins:
        status = w["status"]
        adv = w.get("profiles", {}).get("username", "Inconnu")
        if status == "rejected":
            st.error(f"Victoire contre {adv} refusée")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("Accepter le rejet ✅", key=f"acc_{w['id']}"):
                    db.accept_rejection(w["id"])
                    st.rerun()
            with c2:
                if st.button("Contester ⚖️", key=f"disp_{w['id']}"):
                    db.dispute_match(w["id"])
                    st.rerun()
        elif status == "disputed":
            st.warning(f"⚖️ Litige en cours contre {adv}")
        elif status == "rejected_confirmed":
            st.info(f"Match contre {adv} : Rejet accepté")
        else:
            st.write(f"Match contre {adv} : {status.upper()}")

# --- NOUVELLE SECTION : FACE-À-FACE ---
elif page == "🆚 Historique des Duels":
    st.header("🆚 Historique des Duels")

    # 1. Récupérer la liste des adversaires possibles
    players_res = db.get_leaderboard()
    adversaires = [p for p in players_res.data if p["id"] != user["id"]]

    if not adversaires:
        st.warning("Pas assez de joueurs pour comparer.")
    else:
        # Créer un dictionnaire pour retrouver l'ID via le nom
        adv_map = {p["username"]: p["id"] for p in adversaires}
        selected_opponent_name = st.selectbox(
            "Choisir un adversaire :", list(adv_map.keys())
        )
        opponent_id = adv_map[selected_opponent_name]

        # 2. Récupérer TOUS les matchs validés où JE suis impliqué
        response = (
            db.supabase.table("matches")
            .select("*, winner:winner_id(username), loser:loser_id(username)")
            .or_(f"winner_id.eq.{user['id']},loser_id.eq.{user['id']}")
            .eq("status", "validated")
            .order("created_at", desc=True)
            .execute()
        )

        all_my_matches = response.data

        if not all_my_matches:
            st.info("Vous n'avez pas encore joué de match validé.")
        else:
            # 3. Filtrer avec Pandas pour ne garder que ceux contre l'adversaire choisi
            df = pd.DataFrame(all_my_matches)

            # On garde les lignes où l'adversaire est soit le vainqueur, soit le perdant
            mask = (df["winner_id"] == opponent_id) | (df["loser_id"] == opponent_id)
            df_duel = df[mask].copy()

            if df_duel.empty:
                st.info(f"Aucun match trouvé contre {selected_opponent_name}.")
            else:
                # 4. Calcul des statistiques
                nb_total = len(df_duel)
                nb_victoires = len(df_duel[df_duel["winner_id"] == user["id"]])
                nb_defaites = len(df_duel[df_duel["loser_id"] == user["id"]])

                win_rate = (nb_victoires / nb_total) * 100

                # 5. Affichage des KPIs
                col1, col2, col3 = st.columns(3)
                col1.metric("Matchs", nb_total)
                col2.metric("Victoires", f"{nb_victoires}", delta=f"{win_rate:.0f}%")
                col3.metric("Défaites", f"{nb_defaites}")

                st.divider()

                # 6. Affichage de l'historique détaillé
                st.subheader(f"Historique contre {selected_opponent_name}")

                display_data = []
                for _, row in df_duel.iterrows():
                    is_win = row["winner_id"] == user["id"]
                    res_icon = "✅ VICTOIRE" if is_win else "❌ DÉFAITE"
                    date_str = pd.to_datetime(row["created_at"]).strftime("%d/%m/%Y")

                    display_data.append(
                        {
                            "Date": date_str,
                            "Résultat": res_icon,
                            "Vainqueur": row["winner"]["username"],
                            "Perdant": row["loser"]["username"],
                        }
                    )

                st.dataframe(
                    pd.DataFrame(display_data),
                    use_container_width=True,
                    hide_index=True,
                )

elif page == "📑 Mes validations":
    st.header("📑 Matchs à confirmer")
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

elif page == "🔧 Panel Admin":
    st.header("🔧 Outils d'administration")
    all_matches = db.get_all_matches().data
    status_filter = st.multiselect(
        "Statuts :",
        [
            "pending",
            "validated",
            "rejected",
            "disputed",
            "revoked",
            "rejected_confirmed",
        ],
        default=["disputed", "pending"],
    )
    if all_matches:
        for m in all_matches:
            if m["status"] in status_filter:
                with st.expander(
                    f"Match {m['status'].upper()} - {m['winner']['username']} vs {m['loser']['username']}"
                ):
                    if m["status"] == "disputed":
                        st.error("⚖️ LITIGE DÉCLARÉ")
                        c1, c2 = st.columns(2)
                        if c1.button("Forcer Validation ✅", key=f"f_v_{m['id']}"):
                            db.validate_match_logic(m["id"])
                            st.rerun()
                        if c2.button("Confirmer Rejet ❌", key=f"f_r_{m['id']}"):
                            db.reject_match(m["id"])
                            st.rerun()
                    elif m["status"] == "validated":
                        st.warning("Match validé. Points transférés.")
                        if st.button("Révoquer le match ⚠️", key=f"rev_{m['id']}"):
                            success, msg = db.revoke_match(m["id"])
                            if success:
                                st.rerun()
