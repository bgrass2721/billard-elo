import streamlit as st
from DB_manager import DBManager
import pandas as pd

# 1. Configuration de la page
st.set_page_config(page_title="Billard Elo School", page_icon="🎱", layout="centered")

# 2. Initialisation du manager
db = DBManager()

# --- STYLE CSS ---
st.markdown(
    """
    <style>
    .main { background-color: #0e1117; }
    stButton>button { width: 100%; border-radius: 5px;
     height: 3em; background-color: #2ecc71; color: white; }
    .stDataFrame { background-color: #1f2937; border-radius: 10px; }
    </style>
    """,
    unsafe_allow_html=True,
)

# 3. GESTION DE LA SESSION (Vérification et persistance)
if "user_data" not in st.session_state:
    session = db.supabase.auth.get_session()
    if session:
        user_id = session.user.id
        user_profile = (
            db.supabase.table("profiles")
            .select("*")
            .eq("id", user_id)
            .single()
            .execute()
        )
        st.session_state.user_data = user_profile.data
    else:
        st.session_state.user_data = None

# --- ÉCRAN DE CONNEXION / INSCRIPTION ---
if st.session_state.user_data is None:
    st.title("🎱 Billard Elo Ranking")
    tab1, tab2 = st.tabs(["Connexion", "Créer un compte"])

    with tab1:
        with st.form("login_form"):
            email = st.text_input("Email")
            pwd = st.text_input("Mot de passe", type="password")
            if st.form_submit_button("Se connecter"):
                try:
                    auth_res = db.log_in(email, pwd)
                    user_profile = (
                        db.supabase.table("profiles")
                        .select("*")
                        .eq("id", auth_res.user.id)
                        .single()
                        .execute()
                    )
                    st.session_state.user_data = user_profile.data
                    st.success("Connexion réussie !")
                    st.rerun()
                except Exception:
                    st.error("Identifiants incorrects.")

    with tab2:
        st.info("Utilisez votre email pour vous inscrire.")
        with st.form("signup_form"):
            new_email = st.text_input("Email")
            new_pwd = st.text_input("Mot de passe (6 caractères min.)", type="password")
            new_pseudo = st.text_input("Pseudo choisi")
            if st.form_submit_button("S'inscrire"):
                try:
                    db.sign_up(new_email, new_pwd, new_pseudo)
                    st.success("Compte créé ! Connectez-vous.")
                except Exception as e:
                    st.error(f"Erreur : {e}")
    st.stop()

# --- SI CONNECTÉ : MISE À JOUR DES INFOS EN DIRECT ---
# On recharge systématiquement le profil depuis Supabase
# pour synchroniser l'Elo sidebar et leaderboard
current_id = st.session_state.user_data["id"]
fresh_user = (
    db.supabase.table("profiles").select("*").eq("id", current_id).single().execute()
)
user = fresh_user.data
st.session_state.user_data = user

# Barre latérale
st.sidebar.title("🎱 Billard Club")
st.sidebar.write(f"Joueur : **{user['username']}**")
st.sidebar.write(f"Rang : **{user['elo_rating']} pts**")

# Construction du menu
menu_options = ["🏆 Classement", "🎯 Déclarer un match", "📑 Mes validations"]
if user.get("is_admin"):
    menu_options.append("🔧 Panel Admin")

page = st.sidebar.radio("Navigation", menu_options)

if st.sidebar.button("Déconnexion"):
    st.session_state.user_data = None
    db.supabase.auth.sign_out()
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
    st.write("Déclarez votre victoire. Votre adversaire devra confirmer.")

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
            c1, c2 = st.columns([3, 1])
            c1.error(f"Victoire contre {adv} refusée")
            if c2.button("Contester ⚖️", key=f"disp_{w['id']}"):
                db.dispute_match(w["id"])
                st.rerun()
        elif status == "disputed":
            st.warning(f"⚖️ Litige en cours contre {adv}")
        else:
            st.write(f"Match contre {adv} : {status.upper()}")

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
        ["pending", "validated", "rejected", "disputed", "revoked"],
        default=["disputed", "pending"],
    )

    if not all_matches:
        st.info("Aucun match enregistré.")
    else:
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
                    else:
                        st.write(
                            f"Gagnant: {m['winner']['username']} | Perdant: {m['loser']['username']}"
                        )
                        if m["status"] == "validated":
                            st.warning(
                                "Ce match a été validé. Les points ont été transférés."
                            )
                            if st.button("Révoquer le match ⚠️", key=f"rev_{m['id']}"):
                                success, msg = db.revoke_match(m["id"])
                                if success:
                                    st.success(msg)
                                    st.rerun()
                                else:
                                    st.error(msg)
