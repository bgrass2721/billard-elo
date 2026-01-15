import streamlit as st
from DB_manager import DBManager
import pandas as pd
import extra_streamlit_components as stx
from elo_engine import EloEngine
import altair as alt

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

# Initialisation du drapeau de déconnexion ---
if "logout_clicked" not in st.session_state:
    st.session_state.logout_clicked = False

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

# 3. GESTION DE LA SESSION
# SÉCURITÉ : On initialise la clé si elle est absente
if "user_data" not in st.session_state:
    st.session_state.user_data = None

# Tentative de reconnexion automatique via Cookies SÉCURISÉS
if st.session_state.user_data is None and not st.session_state.logout_clicked:
    # 1. On récupère les tokens cryptés
    access_token = cookie_manager.get("bb_access_token")
    refresh_token = cookie_manager.get("bb_refresh_token")

    if access_token and refresh_token:
        try:
            # 2. On restaure la session Supabase avec ces tokens
            # Cela vérifie automatiquement si le token est valide et non falsifié
            session = db.supabase.auth.set_session(access_token, refresh_token)

            # 3. Si la session est valide, on récupère l'utilisateur
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
            # Si le token est expiré ou invalide (tentative de hack), on ne fait rien
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
                # Cela empêche le message rouge d'apparaître en même temps que le vert
                if auth_success:
                    st.session_state.logout_clicked = False
                    st.success("Connexion réussie !")
                    st.rerun()

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

# MENU NAVIGATION
menu_options = [
    "🏆 Classement",
    "👤 Profils Joueurs",
    "🎯 Déclarer un match",
    "🆚 Historique des Duels",
    "📑 Mes validations",
    "📜 Règlement",
]
if user.get("is_admin"):
    menu_options.append("🔧 Panel Admin")

page = st.sidebar.radio("Navigation", menu_options)

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

if page == "🏆 Classement":
    st.header("🏆 Tableau des Leaders")
    res = db.get_leaderboard()
    if res.data:
        df = pd.DataFrame(res.data)

        # --- FILTRE AJOUTÉ ---
        # On ne garde que les lignes où 'matches_played' est supérieur à 0
        df = df[df["matches_played"] > 0]
        # ---------------------

        df = df[["username", "elo_rating", "matches_played"]]
        df.columns = ["Joueur", "Points Elo", "Matchs"]
        st.dataframe(df, use_container_width=True, hide_index=True)

elif page == "👤 Profils Joueurs":
    # --- 0. SÉLECTION DU JOUEUR À ANALYSER ---
    # On récupère la liste de tous les joueurs
    players_res = db.get_leaderboard()
    if not players_res.data:
        st.error("Impossible de récupérer les joueurs.")
        st.stop()

    all_players = players_res.data
    # On crée un dictionnaire {Pseudo: ID} pour retrouver l'ID facilement
    players_map = {p["username"]: p for p in all_players}

    # Le menu déroulant (Par défaut sur MOI)
    options = list(players_map.keys())
    # On cherche l'index de mon pseudo pour le mettre par défaut
    try:
        default_index = options.index(user["username"])
    except ValueError:
        default_index = 0

    selected_username = st.selectbox(
        "Voir le profil de :", options, index=default_index
    )

    # C'est lui qu'on va regarder (target_user)
    target_user = players_map[selected_username]

    st.header(f"👤 Profil de {target_user['username']}")

    # --- 1. RÉCUPÉRATION DES DONNÉES ---
    all_validated_matches = (
        db.supabase.table("matches")
        .select("*")
        .eq("status", "validated")
        .order("created_at", desc=False)
        .execute()
        .data
    )

    # --- 2. RECONSTRUCTION DE LA COURBE ELO ---
    elo_history = {u["id"]: 1000 for u in all_players}

    # On prépare la courbe pour le joueur CIBLÉ (target_user)
    target_elo_curve = [{"Numéro": 0, "Date": "Début", "Elo": 1000, "Adversaire": "-"}]

    engine = EloEngine()
    match_counter = 0

    for m in all_validated_matches:
        w_id = m["winner_id"]
        l_id = m["loser_id"]

        w_elo = elo_history.get(w_id, 1000)
        l_elo = elo_history.get(l_id, 1000)

        # Calcul
        new_w, new_l, _ = engine.compute_new_ratings(w_elo, l_elo, 0, 0)

        # Mise à jour globale
        elo_history[w_id] = new_w
        elo_history[l_id] = new_l

        # Si le match concerne le joueur CIBLÉ, on l'ajoute à sa courbe
        if w_id == target_user["id"] or l_id == target_user["id"]:
            match_counter += 1
            date_display = pd.to_datetime(m["created_at"]).strftime("%d/%m")

            is_win = w_id == target_user["id"]
            # Son score après ce match
            current_elo = new_w if is_win else new_l

            target_elo_curve.append(
                {
                    "Numéro": match_counter,
                    "Date": date_display,
                    "Elo": current_elo,
                    "Résultat": "Victoire" if is_win else "Défaite",
                }
            )

    # --- 3. AFFICHAGE DE LA COURBE (ALTAIR) ---
    st.subheader("📈 Évolution du classement")

    if len(target_elo_curve) > 0:
        df_curve = pd.DataFrame(target_elo_curve)

        chart = (
            alt.Chart(df_curve)
            .mark_line(point=True, color="#3498db")
            .encode(
                x=alt.X("Numéro", title="Progression (Match après match)"),
                y=alt.Y("Elo", scale=alt.Scale(zero=False), title="Score Elo"),
                tooltip=["Date", "Elo", "Résultat"],
            )
            .properties(height=400)
            .interactive()
        )

        st.altair_chart(chart, use_container_width=True)

        # Indicateur (Stat du joueur ciblé)
        current_elo = target_elo_curve[-1]["Elo"]
        start_elo = 1000
        diff = current_elo - start_elo

        # On affiche le delta en couleur normale (pas vert/rouge relatif à MOI, mais absolu)
        st.metric(f"Elo Actuel de {target_user['username']}", current_elo, delta=diff)

    else:
        st.info(f"{target_user['username']} n'a pas encore joué de match validé.")

    st.divider()

    # --- 4. LISTE DES DERNIERS MATCHS DU CIBLÉ ---
    st.subheader(f"🗓️ Derniers Matchs de {target_user['username']}")

    # On filtre les matchs du joueur CIBLÉ
    target_matches = [
        m
        for m in all_validated_matches
        if m["winner_id"] == target_user["id"] or m["loser_id"] == target_user["id"]
    ]
    target_matches.reverse()  # Du plus récent au plus vieux

    if not target_matches:
        st.write("Aucun match trouvé.")
    else:
        history_data = []
        # Mapping ID -> Nom pour l'affichage des adversaires
        id_to_name = {p["id"]: p["username"] for p in all_players}

        for m in target_matches[:10]:
            is_win = m["winner_id"] == target_user["id"]

            # L'adversaire est celui qui n'est PAS le joueur ciblé
            opponent_id = m["loser_id"] if is_win else m["winner_id"]
            opponent_name = id_to_name.get(opponent_id, "Inconnu")

            result_str = "✅ VICTOIRE" if is_win else "❌ DÉFAITE"
            date_str = pd.to_datetime(m["created_at"]).strftime("%d/%m %H:%M")

            history_data.append(
                {"Date": date_str, "Résultat": result_str, "Adversaire": opponent_name}
            )

        st.dataframe(
            pd.DataFrame(history_data), use_container_width=True, hide_index=True
        )

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

elif page == "🆚 Historique des Duels":
    st.header("🆚 Historique des Duels")

    # 1. Menu de sélection
    players_res = db.get_leaderboard()
    adversaires = [p for p in players_res.data if p["id"] != user["id"]]

    if not adversaires:
        st.warning("Pas assez de joueurs pour comparer.")
    else:
        adv_map = {p["username"]: p["id"] for p in adversaires}
        selected_opponent_name = st.selectbox(
            "Choisir un adversaire :", list(adv_map.keys())
        )
        opponent_id = adv_map[selected_opponent_name]

        # 2. CALCUL DE L'HISTORIQUE (REPLAY)
        all_matches = (
            db.supabase.table("matches")
            .select("*")
            .eq("status", "validated")
            .order("created_at", desc=False)
            .execute()
            .data
        )

        elo_tracker = {p["id"]: 1000 for p in players_res.data}
        match_deltas = {}

        engine = EloEngine()

        for m in all_matches:
            w_id = m["winner_id"]
            l_id = m["loser_id"]

            w_elo = elo_tracker.get(w_id, 1000)
            l_elo = elo_tracker.get(l_id, 1000)

            _, _, delta = engine.compute_new_ratings(w_elo, l_elo, 0, 0)

            elo_tracker[w_id] += delta
            elo_tracker[l_id] -= delta
            match_deltas[m["id"]] = delta

        # 3. FILTRAGE
        all_matches.reverse()  # On veut les récents en premier pour le tableau

        my_duels = []
        for m in all_matches:
            if (m["winner_id"] == user["id"] and m["loser_id"] == opponent_id) or (
                m["winner_id"] == opponent_id and m["loser_id"] == user["id"]
            ):
                my_duels.append(m)

        if not my_duels:
            st.info(f"Aucun match validé trouvé contre {selected_opponent_name}.")
        else:
            # 4. CALCULS STATISTIQUES
            nb_total = len(my_duels)
            nb_victoires = 0
            total_elo_diff = 0  # <-- La nouvelle variable pour le total

            for m in my_duels:
                points = match_deltas.get(m["id"], 0)
                if m["winner_id"] == user["id"]:
                    nb_victoires += 1
                    total_elo_diff += points  # J'ai gagné, j'ajoute
                else:
                    total_elo_diff -= points  # J'ai perdu, je soustrais

            nb_defaites = nb_total - nb_victoires
            win_rate = (nb_victoires / nb_total) * 100

            # 5. AFFICHAGE DES MÉTRIQUES (4 Colonnes maintenant)
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Matchs", nb_total)
            c2.metric("Victoires", f"{nb_victoires}", delta=f"{win_rate:.0f}%")
            c3.metric("Défaites", f"{nb_defaites}")

            # Affichage du Bilan avec couleur automatique selon le signe
            c4.metric(
                "Bilan Points",
                f"{total_elo_diff:+}",
                help="Total des points gagnés ou perdus contre ce joueur",
            )

            st.divider()
            st.subheader(f"Détail des rencontres")

            display_data = []
            for m in my_duels:
                is_win = m["winner_id"] == user["id"]
                date_str = pd.to_datetime(m["created_at"]).strftime("%d/%m/%Y")
                res_icon = "✅ VICTOIRE" if is_win else "❌ DÉFAITE"

                points = match_deltas.get(m["id"], 0)
                points_str = f"+{points}" if is_win else f"-{points}"

                display_data.append(
                    {
                        "Date": date_str,
                        "Résultat": res_icon,
                        "Points Elo": points_str,
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
                    # --- CAS 1 : LITIGE ---
                    if m["status"] == "disputed":
                        st.error("⚖️ LITIGE DÉCLARÉ")
                        c1, c2 = st.columns(2)
                        if c1.button("Forcer Validation ✅", key=f"f_v_{m['id']}"):
                            db.validate_match_logic(m["id"])
                            st.rerun()
                        if c2.button("Confirmer Rejet ❌", key=f"f_r_{m['id']}"):
                            db.reject_match(m["id"])
                            st.rerun()

                    # --- CAS 2 : EN ATTENTE
                    elif m["status"] == "pending":
                        st.info("⏳ EN ATTENTE DE VALIDATION")
                        st.write("Ce match n'a pas encore été confirmé par le perdant.")

                        c1, c2 = st.columns(2)
                        # L'admin valide à la place du joueur
                        if c1.button("Forcer Validation ✅", key=f"adm_val_{m['id']}"):
                            db.validate_match_logic(m["id"])
                            st.rerun()

                        # L'admin supprime le match (spam/erreur)
                        if c2.button("Supprimer le match 🗑️", key=f"adm_del_{m['id']}"):
                            db.reject_match(m["id"])
                            st.rerun()

                    # --- CAS 3 : VALIDÉ ---
                    elif m["status"] == "validated":
                        st.warning("Match validé. Points transférés.")
                        if st.button("Révoquer le match ⚠️", key=f"rev_{m['id']}"):
                            success, msg = db.revoke_match(m["id"])
                            if success:
                                st.rerun()

    # --- AJOUT BOUTON BACKUP ---
    st.divider()
    st.subheader("💾 Sauvegarde de sécurité")
    if st.button("Préparer les fichiers de sauvegarde"):
        # 1. Récupérer les profils
        profiles = db.supabase.table("profiles").select("*").execute().data
        df_prof = pd.DataFrame(profiles)
        csv_prof = df_prof.to_csv(index=False).encode("utf-8")

        # 2. Récupérer les matchs
        matches = db.supabase.table("matches").select("*").execute().data
        df_match = pd.DataFrame(matches)
        csv_match = df_match.to_csv(index=False).encode("utf-8")

        c1, c2 = st.columns(2)
        c1.download_button(
            "📥 Backup Joueurs", csv_prof, "backup_profiles.csv", "text/csv"
        )
        c2.download_button(
            "📥 Backup Matchs", csv_match, "backup_matches.csv", "text/csv"
        )

    # --- SECTION DE SYNCHRONISATION (NOUVEAU) ---
    st.divider()
    st.subheader("🔄 Synchronisation des Scores")
    st.info("Utile si vous voyez une différence entre le classement et la courbe.")

    if st.button("Recalculer tous les Elo (Reset & Replay) ⚠️"):
        status_text = st.empty()
        status_text.text("⏳ Démarrage du recalcul...")
        progress_bar = st.progress(0)

        # 1. On récupère TOUS les matchs validés (ordre chronologique)
        matches = (
            db.supabase.table("matches")
            .select("*")
            .eq("status", "validated")
            .order("created_at", desc=False)
            .execute()
            .data
        )

        # 2. On récupère tous les joueurs
        players = db.get_leaderboard().data

        # 3. Dictionnaire temporaire pour refaire les calculs
        # On remet tout le monde à 1000 pour commencer
        temp_elo = {p["id"]: 1000 for p in players}
        matches_played = {p["id"]: 0 for p in players}  # Pour compter les matchs

        engine = EloEngine()

        total_matches = len(matches)

        # 4. On rejoue l'histoire match par match
        for i, m in enumerate(matches):
            w_id = m["winner_id"]
            l_id = m["loser_id"]

            # Si un joueur a été supprimé entre temps, on ignore
            if w_id not in temp_elo or l_id not in temp_elo:
                continue

            w_elo = temp_elo[w_id]
            l_elo = temp_elo[l_id]

            new_w, new_l, _ = engine.compute_new_ratings(w_elo, l_elo, 0, 0)

            temp_elo[w_id] = new_w
            temp_elo[l_id] = new_l
            matches_played[w_id] += 1
            matches_played[l_id] += 1

            # Barre de progression
            progress_bar.progress((i + 1) / total_matches)

        status_text.text("💾 Sauvegarde des nouveaux scores dans la base...")

        # 5. On met à jour la base de données (Profils)
        for p_id, final_elo in temp_elo.items():
            db.supabase.table("profiles").update(
                {"elo_rating": final_elo, "matches_played": matches_played[p_id]}
            ).eq("id", p_id).execute()

        progress_bar.empty()
        status_text.success(
            "✅ Tout le monde a été synchronisé avec l'historique exact !"
        )
        st.balloons()
