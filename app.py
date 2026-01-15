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
st.sidebar.title("🎱 BlackBall")
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

# MENU NAVIGATION
menu_options = [
    "🏆 Classement",
    "👤 Profils Joueurs",
    "🎯 Déclarer un match",
    "🆚 Historique des Parties",
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

elif page == "🏆 Classement":
    st.header("🏆 Classement Général")

    # 1. Le Sélecteur de Mode
    ranking_mode = st.radio("Mode :", ["Solo (1v1)", "Duo (2v2)"], horizontal=True)
    mode_db = "1v1" if ranking_mode == "Solo (1v1)" else "2v2"

    # 2. Récupération des données triées
    res = db.get_leaderboard(mode=mode_db)

    if not res.data:
        st.info("Aucun joueur n'est encore inscrit.")
    else:
        # 3. Préparation des colonnes selon le mode
        if mode_db == "1v1":
            target_elo = "elo_rating"
            target_matches = "matches_played"
        else:
            target_elo = "elo_2v2"
            target_matches = "matches_2v2"

        df = pd.DataFrame(res.data)

        # --- LE FILTRE MAGIQUE ICI ---
        # On ne garde que les lignes où la colonne target_matches est supérieure à 0
        df = df[df[target_matches] > 0]

        # Si après le filtre le tableau est vide (ex: personne n'a fait de 2v2)
        if df.empty:
            st.info("Aucun joueur classé (0 match joué) pour le moment dans ce mode.")
        else:
            # 4. Création du tableau propre
            display_df = df[["username", target_elo, target_matches]].copy()

            # On renomme les colonnes
            display_df.columns = ["Joueur", "Points Elo", "Matchs"]

            # IMPORTANT : On reset l'index pour que le classement reparte de 1, 2, 3...
            # Sinon, si le 1er et le 2ème ont 0 match, le tableau commencerait à "3".
            display_df.reset_index(drop=True, inplace=True)
            display_df.index = display_df.index + 1

            # 5. Affichage
            st.dataframe(
                display_df,
                use_container_width=True,
                column_config={
                    "Points Elo": st.column_config.NumberColumn(format="%d ⭐️"),
                    "Matchs": st.column_config.NumberColumn(format="%d 🎮"),
                },
            )

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
    try:
        default_index = options.index(user["username"])
    except ValueError:
        default_index = 0

    selected_username = st.selectbox(
        "Voir le profil de :", options, index=default_index
    )
    target_user = players_map[selected_username]

    st.header(f"👤 Profil de {target_user['username']}")

    # --- 1. SÉLECTEUR DE MODE (1v1 / 2v2) ---
    view_mode = st.radio(
        "Voir les statistiques :", ["Solo (1v1)", "Duo (2v2)"], horizontal=True
    )
    target_mode_db = "1v1" if view_mode == "Solo (1v1)" else "2v2"

    # --- 2. RÉCUPÉRATION DES MATCHS DU MODE CHOISI ---
    all_validated_matches = (
        db.supabase.table("matches")
        .select("*")
        .eq("status", "validated")
        .eq("mode", target_mode_db)
        .order("created_at", desc=False)
        .execute()
        .data
    )

    # --- 3. RECONSTRUCTION DE LA COURBE & STATS ---

    # Init des compteurs
    match_counter = 0
    win_counter = 0
    loss_counter = 0

    # Courbe du joueur ciblé
    target_elo_curve = [{"Numéro": 0, "Date": "Début", "Elo": 1000}]

    for m in all_validated_matches:
        # Est-ce que le joueur cible est impliqué ?
        is_involved = (
            m["winner_id"] == target_user["id"]
            or m["loser_id"] == target_user["id"]
            or m.get("winner2_id") == target_user["id"]
            or m.get("loser2_id") == target_user["id"]
        )

        if is_involved:
            match_counter += 1
            # Formatage Date et Heure
            # Astuce: Ajouter .tz_convert('Europe/Paris') si besoin
            date_display = pd.to_datetime(m["created_at"]).strftime("%d/%m %Hh%M")

            # Est-ce une victoire ?
            is_win = (
                m["winner_id"] == target_user["id"]
                or m.get("winner2_id") == target_user["id"]
            )

            # Mise à jour des compteurs
            if is_win:
                win_counter += 1
            else:
                loss_counter += 1

            # Combien de points ?
            delta = m.get("elo_gain", 0)
            if delta is None:
                delta = 0

            # Mise à jour du score courant pour la courbe
            last_score = target_elo_curve[-1]["Elo"]
            new_score = last_score + delta if is_win else last_score - delta

            target_elo_curve.append(
                {
                    "Numéro": match_counter,
                    "Date": date_display,
                    "Elo": new_score,
                    "Résultat": "Victoire" if is_win else "Défaite",
                }
            )

    # --- 4. AFFICHAGE DE LA COURBE ET DES STATS ---
    st.subheader(f"📈 Évolution {view_mode}")

    if len(target_elo_curve) > 1:
        # A. Le Graphique
        df_curve = pd.DataFrame(target_elo_curve)
        chart = (
            alt.Chart(df_curve)
            .mark_line(point=True, color="#3498db")
            .encode(
                x=alt.X("Numéro", title="Progression (Matchs joués)"),
                y=alt.Y("Elo", scale=alt.Scale(zero=False), title="Score Elo"),
                tooltip=["Date", "Elo", "Résultat"],
            )
            .properties(height=350)
            .interactive()
        )
        st.altair_chart(chart, use_container_width=True)

        # B. Les Statistiques (C'est ICI que ça change)
        current_elo = target_elo_curve[-1]["Elo"]
        diff_total = current_elo - 1000

        # Calcul du taux de victoire
        win_rate = (win_counter / match_counter * 100) if match_counter > 0 else 0

        # Affichage sur 4 colonnes
        k1, k2, k3, k4 = st.columns(4)
        k1.metric(f"Elo {view_mode}", current_elo, delta=diff_total)
        k2.metric("Matchs Joués", match_counter)
        k3.metric("Victoires", win_counter, f"{win_rate:.0f}%")
        k4.metric("Défaites", loss_counter)

    else:
        st.info(
            f"{target_user['username']} n'a pas encore de match classé en {view_mode}."
        )

    st.divider()

    # --- 5. HISTORIQUE RÉCENT ---
    st.subheader(f"🗓️ Derniers Matchs ({view_mode})")

    # On filtre pour ne garder que les matchs du joueur (déjà fait dans la boucle mais on refait propre pour l'affichage inversé)
    my_matches = []
    for m in all_validated_matches:
        if (
            m["winner_id"] == target_user["id"]
            or m["loser_id"] == target_user["id"]
            or m.get("winner2_id") == target_user["id"]
            or m.get("loser2_id") == target_user["id"]
        ):
            my_matches.append(m)

    # On prend les 10 derniers
    recent_matches = my_matches[::-1][:10]
    id_name = {p["id"]: p["username"] for p in all_players}

    if not recent_matches:
        st.write("Aucun historique dans ce mode.")
    else:
        history_data = []
        for m in recent_matches:
            is_win = (
                m["winner_id"] == target_user["id"]
                or m.get("winner2_id") == target_user["id"]
            )

            res_str = "✅ VICTOIRE" if is_win else "❌ DÉFAITE"
            # Affichage de l'heure ici aussi
            date_str = pd.to_datetime(m["created_at"]).strftime("%d/%m à %Hh%M")
            points = m.get("elo_gain", 0)
            sign = "+" if is_win else "-"

            if target_mode_db == "1v1":
                opp_id = m["loser_id"] if is_win else m["winner_id"]
                details = f"vs {id_name.get(opp_id, 'Inconnu')}"
            else:
                if m["winner_id"] == target_user["id"]:
                    my_mate = m.get("winner2_id")
                elif m.get("winner2_id") == target_user["id"]:
                    my_mate = m["winner_id"]
                elif m["loser_id"] == target_user["id"]:
                    my_mate = m.get("loser2_id")
                else:
                    my_mate = m["loser_id"]

                mate_name = id_name.get(my_mate, "?")

                if is_win:
                    opp_ids = [m["loser_id"], m.get("loser2_id")]
                else:
                    opp_ids = [m["winner_id"], m.get("winner2_id")]

                opp_names = [id_name.get(oid, "?") for oid in opp_ids if oid]
                details = f"Avec {mate_name} vs {' & '.join(opp_names)}"

            history_data.append(
                {
                    "Date": date_str,
                    "Résultat": res_str,
                    "Détails": details,
                    "Points": f"{sign}{points}",
                }
            )

        st.dataframe(
            pd.DataFrame(history_data), use_container_width=True, hide_index=True
        )

elif page == "🎯 Déclarer un match":
    st.header("🎯 Déclarer un résultat")

    # 1. Choix du mode de jeu
    mode_input = st.radio("Type de match", ["👤 1 vs 1", "👥 2 vs 2"], horizontal=True)

    # Récupération de la liste des joueurs (sauf moi-même)
    players_res = db.get_leaderboard()
    # On gère le cas où la liste est vide ou None
    all_players = players_res.data if players_res.data else []
    adv_map = {p["username"]: p["id"] for p in all_players if p["id"] != user["id"]}

    if not adv_map:
        st.warning("Il n'y a pas assez de joueurs inscrits pour déclarer un match.")
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

elif page == "🆚 Historique des Parties":
    st.header("🆚 Historique des Parties")

    # 1. Menu de sélection des joueurs
    players_res = db.get_leaderboard()
    if not players_res.data:
        st.warning("Aucun joueur trouvé.")
        st.stop()

    adversaires = [p for p in players_res.data if p["id"] != user["id"]]
    id_name = {p["id"]: p["username"] for p in players_res.data}

    if not adversaires:
        st.warning("Pas assez de joueurs.")
    else:
        # A. Choix du JOUEUR CIBLE
        adv_map = {p["username"]: p["id"] for p in adversaires}
        selected_opponent_name = st.selectbox(
            "Voir mon historique avec :", list(adv_map.keys())
        )
        opponent_id = adv_map[selected_opponent_name]

        # B. Choix du MODE (FILTRE STRICT)
        # C'est ce bouton qui empêche le mélange des points
        hist_mode = st.radio("Mode :", ["Solo (1v1)", "Duo (2v2)"], horizontal=True)
        target_db_mode = "1v1" if hist_mode == "Solo (1v1)" else "2v2"

        # 2. Récupération des matchs (Filtrés dès la requête SQL)
        all_matches = (
            db.supabase.table("matches")
            .select("*")
            .eq("status", "validated")
            .eq("mode", target_db_mode)  # <--- ON NE CHARGE QUE LE BON MODE
            .order("created_at", desc=True)
            .execute()
            .data
        )

        # 3. Analyse des interactions
        history_data = []

        # Stats : On distingue "Adversaire" et "Partenaire" (seulement possible en 2v2)
        stats_vs = {"played": 0, "win": 0, "loss": 0, "elo_diff": 0}
        stats_coop = {"played": 0, "win": 0, "loss": 0, "elo_diff": 0}

        for m in all_matches:
            # Suis-je dans le match ?
            i_am_winner = (
                m["winner_id"] == user["id"] or m.get("winner2_id") == user["id"]
            )
            i_am_loser = m["loser_id"] == user["id"] or m.get("loser2_id") == user["id"]

            if not (i_am_winner or i_am_loser):
                continue

            # Est-ce que L'AUTRE est dans le match ?
            opp_is_winner = (
                m["winner_id"] == opponent_id or m.get("winner2_id") == opponent_id
            )
            opp_is_loser = (
                m["loser_id"] == opponent_id or m.get("loser2_id") == opponent_id
            )

            if not (opp_is_winner or opp_is_loser):
                continue

            # --- ANALYSE ---
            is_victory = i_am_winner
            points = m.get("elo_gain", 0)
            if points is None:
                points = 0

            # Cas 1 : Nous étions PARTENAIRES (Même coté) - Impossible en 1v1
            if (i_am_winner and opp_is_winner) or (i_am_loser and opp_is_loser):
                relation_type = "🤝 Partenaire"
                stats_coop["played"] += 1
                if is_victory:
                    stats_coop["win"] += 1
                    stats_coop["elo_diff"] += points
                else:
                    stats_coop["loss"] += 1
                    stats_coop["elo_diff"] -= points

            # Cas 2 : Nous étions ADVERSAIRES (Cotés opposés)
            else:
                relation_type = "⚔️ Adversaire"
                stats_vs["played"] += 1
                if is_victory:
                    stats_vs["win"] += 1
                    stats_vs["elo_diff"] += points
                else:
                    stats_vs["loss"] += 1
                    stats_vs["elo_diff"] -= points

            # Préparation ligne tableau
            date_str = pd.to_datetime(m["created_at"]).strftime("%d/%m à %Hh%M")
            res_icon = "✅ VICTOIRE" if is_victory else "❌ DÉFAITE"

            # Info contextuelle
            if target_db_mode == "1v1":
                info_sup = "Duel classique"
            else:
                # En 2v2, on précise avec qui on jouait
                # Trouver mon partenaire à MOI
                if m["winner_id"] == user["id"]:
                    my_mate_id = m.get("winner2_id")
                elif m.get("winner2_id") == user["id"]:
                    my_mate_id = m["winner_id"]
                elif m["loser_id"] == user["id"]:
                    my_mate_id = m.get("loser2_id")
                else:
                    my_mate_id = m["loser_id"]

                mate_name = id_name.get(my_mate_id, "?")
                info_sup = f"Moi & {mate_name}"

            history_data.append(
                {
                    "Date": date_str,
                    "Relation": relation_type,
                    "Résultat": res_icon,
                    "Détail": info_sup,
                    "Points": f"{points:+}" if is_victory else f"{-points:+}",
                }
            )

        # 4. AFFICHAGE

        # A. Statistiques Face-à-Face (Toujours pertinent)
        st.subheader(f"⚔️ Face-à-Face ({hist_mode})")
        if stats_vs["played"] == 0:
            st.info(f"Aucun match l'un contre l'autre en {hist_mode}.")
        else:
            wr_vs = (stats_vs["win"] / stats_vs["played"]) * 100
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Matchs", stats_vs["played"])
            c2.metric("Victoires", stats_vs["win"], f"{wr_vs:.0f}%")
            c3.metric("Défaites", stats_vs["loss"])
            c4.metric(
                f"Bilan Elo {target_db_mode}",
                f"{stats_vs['elo_diff']:+}",
                help="Total des points échangés",
            )

        st.divider()

        # B. Statistiques Coop (Affiché systématiquement en mode 2v2)
        if target_db_mode == "2v2":
            st.subheader(f"🤝 En Équipe avec {selected_opponent_name}")

            if stats_coop["played"] == 0:
                st.info(
                    f"Vous n'avez jamais joué en équipe avec {selected_opponent_name}."
                )
            else:
                wr_coop = (stats_coop["win"] / stats_coop["played"]) * 100
                k1, k2, k3, k4 = st.columns(4)
                k1.metric("Duos joués", stats_coop["played"])
                k2.metric("Victoires", stats_coop["win"], f"{wr_coop:.0f}%")
                k3.metric("Défaites", stats_coop["loss"])
                k4.metric(
                    "Gain Elo (2v2)",
                    f"{stats_coop['elo_diff']:+}",
                    help="Points gagnés ensemble",
                )

            st.divider()

        # 5. Tableau
        st.subheader("Historique détaillé")
        if not history_data:
            st.write("Rien à afficher avec ces filtres.")
        else:
            st.dataframe(
                pd.DataFrame(history_data), use_container_width=True, hide_index=True
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
