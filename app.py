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


def get_badges_html(player, matches_history):
    """
    Génère les badges avec infobulles descriptives (ex: 'Confirmé : 50 matchs joués').
    """

    # --- 1. CALCUL DES STATS ---
    total_matches = player.get("matches_played", 0) + player.get("matches_2v2", 0)

    wins = 0
    current_streak = 0
    unique_opponents = set()
    matches_by_day = {}

    # Pour le calcul Duo spécifique
    partners_counter = {}

    has_giant_kill = False
    streak_active = True

    sorted_matches = sorted(
        matches_history, key=lambda x: str(x["created_at"]), reverse=True
    )

    for m in sorted_matches:
        day = str(m["created_at"]).split("T")[0]
        if day not in matches_by_day:
            matches_by_day[day] = 0
        matches_by_day[day] += 1

        is_2v2 = m.get("mode") == "2v2"

        # Identification du résultat
        is_win = m["winner_id"] == player["id"] or m.get("winner2_id") == player["id"]

        # --- LOGIQUE DUO (Partenaire unique) ---
        if is_2v2:
            partner_id = None
            if m["winner_id"] == player["id"]:
                partner_id = m.get("winner2_id")
            elif m.get("winner2_id") == player["id"]:
                partner_id = m["winner_id"]
            elif m["loser_id"] == player["id"]:
                partner_id = m.get("loser2_id")
            elif m.get("loser2_id") == player["id"]:
                partner_id = m["loser_id"]

            if partner_id:
                partners_counter[partner_id] = partners_counter.get(partner_id, 0) + 1

        # --- LOGIQUE VICTOIRE / GLOBE TROTTER ---
        if is_win:
            wins += 1
            if streak_active:
                current_streak += 1
            if m.get("elo_gain", 0) >= 30:
                has_giant_kill = True

            opp_ids = [m["loser_id"], m.get("loser2_id")] if is_2v2 else [m["loser_id"]]
            for oid in opp_ids:
                if oid:
                    unique_opponents.add(oid)
        else:
            streak_active = False
            opp_ids = (
                [m["winner_id"], m.get("winner2_id")] if is_2v2 else [m["winner_id"]]
            )
            for oid in opp_ids:
                if oid:
                    unique_opponents.add(oid)

    has_marathon = any(count >= 10 for count in matches_by_day.values())
    nb_unique = len(unique_opponents)

    max_duo_matches = max(partners_counter.values()) if partners_counter else 0

    # --- 2. FONCTION DE GESTION DES PALIERS ---
    html_parts = []

    def process_tier_badge(current_val, tiers, shape, base_icon, label):
        """
        Gère l'affichage progressif avec infobulle personnalisée.
        """
        achieved_tier = None
        next_tier = None

        # On cherche le rang actuel
        for tier in tiers:
            if current_val >= tier["req"]:
                achieved_tier = tier
            else:
                next_tier = tier
                break

        if achieved_tier:
            style = achieved_tier["style"]
            name = achieved_tier["name"]

            # --- MODIFICATION ICI ---
            # On construit la description de ce qu'est le badge actuel
            current_desc = f"{achieved_tier['req']} {label}"

            if next_tier:
                # Format : "Confirmé : 50 matchs joués. Prochain : Pilier (100 matchs joués)"
                tooltip = f"✅ {name} : {current_desc}. Prochain : {next_tier['name']} ({next_tier['req']} {label})"
            else:
                tooltip = f"🏆 NIVEAU MAX : {name} ({current_desc})"

            css_class = ""
            icon = base_icon

        else:
            # Aucun badge
            first_tier = tiers[0]
            style = first_tier["style"]
            name = first_tier["name"]
            tooltip = f"🔒 BLOQUÉ : Il faut {first_tier['req']} {label} pour débloquer"
            css_class = "locked"
            icon = base_icon

        html_parts.append(
            f"""<div class="badge-item {css_class}" title="{tooltip}"><div class="badge-icon-box {shape} {style}">{icon}</div><div class="badge-name">{name}</div></div>"""
        )

    # --- 3. DÉFINITION DES FAMILLES ---

    # A. FIDÉLITÉ (Shields)
    tiers_fidelity = [
        {"req": 10, "style": "bronze", "name": "Rookie"},
        {"req": 50, "style": "silver", "name": "Confirmé"},
        {"req": 100, "style": "gold", "name": "Pilier"},
        {"req": 200, "style": "platinum", "name": "Légende"},
    ]
    process_tier_badge(total_matches, tiers_fidelity, "shield", "⚔️", "matchs joués")

    # B. VICTOIRES (Stars)
    tiers_victory = [
        {"req": 10, "style": "bronze", "name": "Gâchette"},
        {"req": 25, "style": "silver", "name": "Conquérant"},
        {"req": 50, "style": "gold", "name": "Champion"},
        {"req": 100, "style": "platinum", "name": "Invincible"},
    ]
    process_tier_badge(wins, tiers_victory, "star", "🏆", "victoires")

    # C. DUO (Circles)
    tiers_duo = [
        {"req": 10, "style": "bronze", "name": "Binôme"},
        {"req": 30, "style": "silver", "name": "Frères d'armes"},
        {"req": 60, "style": "gold", "name": "Fusion"},
        {"req": 120, "style": "platinum", "name": "Symbiose"},
    ]
    process_tier_badge(
        max_duo_matches, tiers_duo, "circle", "🤝", "matchs avec le même partenaire"
    )

    # D. SOCIAL (Circles)
    tiers_social = [
        {"req": 5, "style": "bronze", "name": "Explorateur"},
        {"req": 10, "style": "silver", "name": "Voyageur"},
        {"req": 20, "style": "gold", "name": "Monde"},
        {"req": 40, "style": "platinum", "name": "Universel"},
    ]
    process_tier_badge(nb_unique, tiers_social, "circle", "🌍", "adversaires uniques")

    # --- 4. BADGES SPÉCIAUX ---

    def add_special(cond, shape, style, icon, name, desc):
        css = "" if cond else "locked"
        tooltip = f"✅ {desc}" if cond else f"🔒 BLOQUÉ : {desc}"
        html_parts.append(
            f"""<div class="badge-item {css}" title="{tooltip}"><div class="badge-icon-box {shape} {style}">{icon}</div><div class="badge-name">{name}</div></div>"""
        )

    # On Fire (Série de 5)
    add_special(
        current_streak >= 5,
        "hexagon",
        "magma",
        "🔥",
        "On Fire",
        "Série active de 5 victoires",
    )

    # Marathon (10 matchs/jour)
    add_special(
        has_marathon,
        "hexagon",
        "electric",
        "⚡",
        "Marathon",
        "Jouer 10 matchs en 1 jour",
    )

    # Giant Slayer (+200 Elo)
    add_special(
        has_giant_kill, "hexagon", "blood", "🩸", "Tueur", "Battre un joueur +200 Elo"
    )

    # --- 5. RENDU ---
    return f"""<div style="display: flex; flex-wrap: wrap; justify-content: center; gap: 4px; background: rgba(20, 20, 30, 0.4); padding: 15px; border-radius: 16px; border: 1px solid rgba(255,255,255,0.05); box-shadow: 0 4px 20px rgba(0,0,0,0.3);">{''.join(html_parts)}</div>"""


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
    /* --- 1. CONTENEUR GLOBAL --- */
    .badge-item {
        display: flex; flex-direction: column; align-items: center;
        width: 85px; margin: 12px;
        position: relative;
        cursor: help;
    }

    /* Texte sous le badge */
    .badge-name {
        font-size: 11px; font-weight: 800; text-align: center; color: #ccc; margin-top: 8px;
        text-transform: uppercase; letter-spacing: 0.5px; text-shadow: 1px 1px 2px black;
    }

    /* --- 2. LE BADGE (Lumière et Ombres) --- */
    .badge-icon-box {
        position: relative;
        width: 60px; height: 60px;
        display: flex; align-items: center; justify-content: center;
        font-size: 24px;
        color: white;
        background: transparent; /* Fond transparent pour laisser passer la lueur */
        z-index: 1;
        
        /* LUEUR DE CONTOUR (Rim Light) + OMBRE PORTÉE */
        /* Maintenant que le parent n'est plus coupé, ceci s'affiche parfaitement sur fond noir */
        filter: 
            drop-shadow(0 0 3px rgba(255, 255, 255, 0.6)) 
            drop-shadow(0 5px 10px rgba(0,0,0,0.8));
    }

    /* --- 3. DÉFINITION DES FORMES (Via Variables CSS) --- */
    /* On stocke la forme dans --shape sans couper le parent */
    .shield { --shape: polygon(50% 0, 100% 15%, 100% 75%, 50% 100%, 0 75%, 0 15%); }
    /* Ta forme étoile "Dodue" conservée */
    .star { --shape: polygon(50% 0%, 63% 38%, 100% 38%, 69% 59%, 82% 100%, 50% 75%, 18% 100%, 31% 59%, 0% 38%, 37% 38%); }
    .hexagon { --shape: polygon(25% 0%, 75% 0%, 100% 50%, 75% 100%, 25% 100%, 0% 50%); }

    /* Le cercle est un cas spécial géré par border-radius */
    .circle { --shape: none; border-radius: 50%; }


    /* --- 4. COUCHES INTÉRIEURES (Ce sont elles qu'on découpe) --- */

    /* COUCHE DU FOND : LA BORDURE NOIRE (Niveau -2) */
    .badge-icon-box::before {
        content: ""; position: absolute;
        inset: 0;
        background: #111;
        z-index: -2;
        
        /* On applique la découpe ICI seulement */
        clip-path: var(--shape);
        border-radius: inherit; /* Pour le cercle */
    }

    /* COUCHE DU MILIEU : LA COULEUR/MATIÈRE (Niveau -1) */
    .badge-icon-box::after {
        content: ""; position: absolute;
        inset: 3px; /* Épaisseur standard */
        z-index: -1;
        
        /* On applique la découpe ICI aussi */
        clip-path: var(--shape);
        border-radius: inherit;
        
        /* Ombre interne */
        box-shadow: inset 0 2px 5px rgba(255,255,255,0.4), inset 0 -4px 8px rgba(0,0,0,0.4);
    }


    /* --- 5. COULEURS (Inchangé) --- */
    .bronze::after { background: linear-gradient(135deg, #e7a566, #8b4513); }
    .silver::after { background: linear-gradient(135deg, #ffffff, #999); }
    .silver { color: #222; text-shadow: none; }
    .gold::after { background: linear-gradient(135deg, #fff5c3, #ffbf00, #c78400); }
    .platinum::after { background: linear-gradient(135deg, #ffffff, #dbeafe, #60a5fa); }
    .platinum { color: #0f172a; text-shadow: none; }

    .magma::after    { background: linear-gradient(135deg, #ffdd00, #ff4800, #910a0a); }
    .blood::after    { background: linear-gradient(135deg, #ff5555, #aa0000, #300000); }
    .electric::after { background: linear-gradient(135deg, #ffffa1, #ffc800, #ff7b00); }
    .electric { color: #222; text-shadow: none; }
    .ice::after      { background: linear-gradient(135deg, #e0f7fa, #00bcd4, #006064); }
    .ice { color: #003c3f; text-shadow: none; }

    /* --- 6. ÉTAT VERROUILLÉ --- */
    .locked {
        filter: grayscale(100%) opacity(0.5);
        transform: scale(0.95);
        transition: all 0.3s;
    }
    .locked .badge-icon-box::before { background: #333; }
    .locked .badge-icon-box::after { background: #555; box-shadow: none; }
    .locked:hover {
        filter: grayscale(0%) opacity(1);
        transform: scale(1.1);
        z-index: 10;
    }

    /* --- 7. TES CORRECTIFS SPÉCIFIQUES --- */

    /* Épaisseur bordure étoile (Tu avais mis 7px) */
    .badge-icon-box.star::after {
        inset: 7px; 
    }
    /* Taille police étoile (Tu avais mis 14px) */
    .badge-icon-box.star {
        font-size: 14px;
        padding-top: 2px;
    }
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
    "🆚 Comparateur de joueurs",
    "📑 Mes validations",
    "📢 Nouveautés",
    "📜 Règlement",
    "⚙️ Paramètres",
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

        # --- LE FILTRE MAGIQUE ---
        # On ne garde que les joueurs actifs (> 0 match)
        df = df[df[target_matches] > 0]

        if df.empty:
            st.info("Aucun joueur classé (0 match joué) pour le moment dans ce mode.")
        else:
            # --- MASQUAGE DES NOMS (PRIVACY) ---
            # On remplace le pseudo par "Joueur Masqué" si l'option est activée
            # et que ce n'est pas moi-même qui regarde.
            def anonymize(row):
                # on utilise .get() pour éviter le crash si la colonne n'existe pas encore
                if row.get("is_hidden_leaderboard", False) and row["id"] != user["id"]:
                    return "🕵️ Joueur Masqué"
                return row["username"]

            df["username"] = df.apply(anonymize, axis=1)
            # -----------------------------------

            # 4. Création du tableau propre
            display_df = df[["username", target_elo, target_matches]].copy()

            # On renomme les colonnes
            display_df.columns = ["Joueur", "Points Elo", "Matchs"]

            # Reset de l'index pour avoir un classement 1, 2, 3...
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

    # --- SÉCURITÉ : BLOCAGE SI PROFIL PRIVÉ ---
    if target_user.get("is_hidden_profile", False) and target_user["id"] != user["id"]:
        st.warning(f"🔒 Le profil de {target_user['username']} est privé.")
        st.info("L'utilisateur a choisi de masquer ses statistiques et son historique.")
        st.stop()
    # ------------------------------------------

    st.header(f"👤 Profil de {target_user['username']}")

    # --- 1. BADGES (NOUVEAU) ---
    # On doit récupérer TOUS les matchs validés (peu importe le mode) pour ce joueur
    # pour calculer ses badges correctement (Marathon, Globe-Trotter...)
    raw_matches = (
        db.supabase.table("matches")
        .select("*")
        .eq("status", "validated")
        .execute()
        .data
    )

    user_full_history = [
        m
        for m in raw_matches
        if m["winner_id"] == target_user["id"]
        or m["loser_id"] == target_user["id"]
        or m.get("winner2_id") == target_user["id"]
        or m.get("loser2_id") == target_user["id"]
    ]

    # Affiche le HTML en l'interprétant graphiquement
    st.markdown(get_badges_html(target_user, user_full_history), unsafe_allow_html=True)
    # ---------------------------

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

        # B. Les Statistiques
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

    # On filtre pour ne garder que les matchs du joueur
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

elif page == "🆚 Comparateur de joueurs":
    st.header("⚔️ Comparateur")

    # 1. RÉCUPÉRATION DES JOUEURS
    players_res = db.get_leaderboard()
    if not players_res.data:
        st.warning("Aucun joueur trouvé.")
        st.stop()

    all_players = players_res.data
    players_map = {p["username"]: p for p in all_players}
    # CRUCIAL : On crée un dictionnaire ID -> Nom pour l'affichage 2v2
    id_to_name = {p["id"]: p["username"] for p in all_players}

    player_names = list(players_map.keys())

    # 2. SÉLECTEURS (Joueur A vs Joueur B)
    c1, c2, c3 = st.columns([1.5, 0.5, 1.5])

    with c1:
        try:
            default_ix_1 = player_names.index(user["username"])
        except:
            default_ix_1 = 0
        p1_name = st.selectbox("Joueur 1 (Gauche)", player_names, index=default_ix_1)

    with c2:
        st.markdown(
            "<h2 style='text-align: center; padding-top: 20px;'>VS</h2>",
            unsafe_allow_html=True,
        )

    with c3:
        default_ix_2 = 1 if len(player_names) > 1 else 0
        if player_names[default_ix_2] == p1_name and len(player_names) > 1:
            default_ix_2 = 0
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
        .eq("status", "validated")
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

    # On initialise le graph avec le point 0
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

            # --- CALCUL STATS ---
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
                    # P1 gagne : il prend +1 victoire et +X points Elo
                    cumulative_score_wins += 1
                    cumulative_score_elo += elo_gain

                    if vs_stats["current_streak_winner"] == "p1":
                        vs_stats["streak_p1"] += 1
                    else:
                        vs_stats["streak_p1"] = 1
                        vs_stats["current_streak_winner"] = "p1"
                else:
                    vs_stats["p2_wins"] += 1
                    # P1 perd : il prend -1 victoire et -X points Elo
                    cumulative_score_wins -= 1
                    cumulative_score_elo -= elo_gain

                    if vs_stats["current_streak_winner"] == "p2":
                        vs_stats["streak_p1"] += 1
                    else:
                        vs_stats["streak_p1"] = 1
                        vs_stats["current_streak_winner"] = "p2"

                # Graphique (Uniquement pour Duel)
                date_label = pd.to_datetime(m["created_at"]).strftime("%d/%m")
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
                    "Date": pd.to_datetime(m["created_at"]).strftime("%d/%m %Hh%M"),
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
        # SCOREBOARD
        col_left, col_mid, col_right = st.columns([2, 3, 2])

        with col_left:
            st.markdown(
                f"<h2 style='text-align: center; color: #4CAF50;'>{vs_stats['p1_wins']}</h2>",
                unsafe_allow_html=True,
            )
            st.markdown(
                f"<div style='text-align: center;'><b>{p1_name}</b></div>",
                unsafe_allow_html=True,
            )

        with col_mid:
            # Titres
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

        with col_right:
            st.markdown(
                f"<h2 style='text-align: center; color: #FF5252;'>{vs_stats['p2_wins']}</h2>",
                unsafe_allow_html=True,
            )
            st.markdown(
                f"<div style='text-align: center;'><b>{p2_name}</b></div>",
                unsafe_allow_html=True,
            )

        # --- GRAPHIQUES (ONGLETS) ---
        st.write("")
        st.markdown("##### 📈 Historique de la domination")

        tab_elo, tab_wins = st.tabs(
            ["📉 Écart Elo (Points)", "📊 Écart Victoires (Net)"]
        )

        df_graph = pd.DataFrame(graph_data)

        # Graphique 1 : Écart ELO
        with tab_elo:
            chart_elo = (
                alt.Chart(df_graph)
                .mark_line(point=True)
                .encode(  # Point=True + Line (sans step) = Droites
                    x=alt.X("Match", axis=alt.Axis(tickMinStep=1)),
                    y=alt.Y("Score Cumulé (Elo)", title=f"Avantage Points ({p1_name})"),
                    tooltip=["Date", "Score Cumulé (Elo)"],
                    color=alt.value("#9b59b6"),  # Violet pour l'Elo
                )
                .properties(height=300)
            )

            rule = (
                alt.Chart(pd.DataFrame({"y": [0]}))
                .mark_rule(color="white", opacity=0.3)
                .encode(y="y")
            )
            st.altair_chart(chart_elo + rule, use_container_width=True)
            st.caption(
                "Ce graphique montre le cumul des points Elo gagnés/perdus l'un contre l'autre."
            )

        # Graphique 2 : Écart VICTOIRES
        with tab_wins:
            chart_wins = (
                alt.Chart(df_graph)
                .mark_line(point=True)
                .encode(  # Lignes droites
                    x=alt.X("Match", axis=alt.Axis(tickMinStep=1)),
                    y=alt.Y(
                        "Score Cumulé (Victoires)",
                        title=f"Avantage Victoires ({p1_name})",
                    ),
                    tooltip=["Date", "Score Cumulé (Victoires)"],
                    color=alt.value("#3498db"),  # Bleu pour les victoires
                )
                .properties(height=300)
            )

            st.altair_chart(chart_wins + rule, use_container_width=True)
            st.caption(
                "Ce graphique montre la différence de victoires (Forme du moment)."
            )

    # 7. AFFICHAGE COOP (PARTENAIRES - 2v2)
    if target_db_mode == "2v2":
        st.divider()
        st.subheader(f"🧬 Synergie : {p1_name} & {p2_name}")

        if coop_stats["total"] == 0:
            st.write("Ils n'ont jamais joué ensemble dans la même équipe.")
        else:
            wr_coop = coop_stats["wins"] / coop_stats["total"]

            # Titres Coop
            coop_title = "🤝 Binôme Standard"
            emoji_coop = "😐"

            if coop_stats["total"] >= 5:
                if wr_coop >= 0.75:
                    coop_title = "🦍 LES GORILLES (Invincibles)"
                    emoji_coop = "🔥"
                elif wr_coop >= 0.55:
                    coop_title = "⚔️ FRÈRES D'ARMES"
                    emoji_coop = "💪"
                elif wr_coop <= 0.35:
                    coop_title = "💔 LES TOXIQUES (Incompatibles)"
                    emoji_coop = "💀"
                else:
                    coop_title = "⚖️ PILE OU FACE"
                    emoji_coop = "🪙"

            k1, k2, k3 = st.columns(3)
            k1.metric("Matchs Ensemble", coop_stats["total"])
            k2.metric("Victoires", coop_stats["wins"], f"{wr_coop*100:.0f}%")
            k3.metric("Statut", emoji_coop, coop_title)

    # 8. TABLEAU GLOBAL (Commun aux deux analyses)
    st.divider()
    with st.expander("📜 Voir l'historique complet des rencontres", expanded=True):
        if not duel_matches:
            st.write("Aucun match trouvé.")
        else:
            # On affiche du plus récent au plus ancien
            st.dataframe(
                pd.DataFrame(duel_matches[::-1]),
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Détails du Match": st.column_config.TextColumn(width="large"),
                    "Résultat (P1)": st.column_config.TextColumn(width="small"),
                },
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

elif page == "📢 Nouveautés":
    st.header("📢 Nouveautés & Mises à jour")

    # --- MISE A JOUR V2.1 ---
    with st.container(border=True):
        st.subheader("💎 Mise à jour v2.1 : Trophées & Rivalités")
        st.caption("Déployée le 22 Janvier 2026")

        st.markdown(
            """
            L'application s'enrichit de deux fonctionnalités majeures pour pimenter la compétition !

            ### 🏅 1. Arrivée des Badges & Trophées
            Vos exploits sont désormais immortalisés ! Un système de succès inédit fait son apparition sur votre profil :
            * **Collectionnez-les tous :** Des badges au design 3D (Or, Argent, Bronze) qui récompensent votre fidélité, vos victoires et votre style de jeu.
            * **Objectif PLATINE 💎 :** Serez-vous assez assidu pour atteindre ce rang ultime (ex: 200 matchs ou 100 victoires) ?
            * **Progression Interactive :** Cliquez sur un badge verrouillé (grisé) pour découvrir l'objectif précis à atteindre.
            * **Spécial Duo :** Des trophées exclusifs pour récompenser la fidélité de votre binôme.

            ### ⚔️ 2. Le Comparateur de Joueurs
            Fini les débats, place aux chiffres. L'onglet **"Historique"** devient un puissant outil d'analyse :
            * **Duel au Sommet :** Comparez n'importe quel joueur A contre n'importe quel joueur B.
            * **Graphiques Avancés :** Analysez la domination via deux courbes : l'écart de Victoires (Forme) et l'écart de Points Elo (Niveau).
            * **Titres & Statuts :** L'appli détermine automatiquement si vous êtes la "Bête Noire" de votre adversaire ou son "Sac de Frappe".
            * **Analyse Synergie (2v2) :** Découvrez si votre duo est classé comme "Gorilles" (Invincibles) ou "Toxiques" (Incompatibles).

            ---
            *La chasse aux trophées est ouverte !* 🏆
            """
        )

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
                date_str = pd.to_datetime(m["created_at"]).strftime("%d/%m à %Hh%M")

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

    # --- 3. SYNCHRONISATION TOTALE (CORRIGÉE) ---
    st.subheader("🔄 Synchronisation Totale")
    st.info(
        "Recalcule tous les scores depuis le début et met à jour l'historique des gains. "
        "Utile pour corriger les écarts entre le profil et le classement."
    )

    if st.button("Lancer la réparation (Reset & Replay) ⚠️"):
        status_text = st.empty()
        status_text.text("⏳ Démarrage du recalcul...")
        progress_bar = st.progress(0)

        # A. Récupération Chronologique
        matches = (
            db.supabase.table("matches")
            .select("*")
            .eq("status", "validated")
            .order("created_at", desc=False)
            .execute()
            .data
        )

        # B. Initialisation des compteurs virtuels
        players = db.get_leaderboard().data

        # On sépare 1v1 et 2v2
        temp_elo_1v1 = {p["id"]: 1000 for p in players}
        matches_1v1 = {p["id"]: 0 for p in players}

        temp_elo_2v2 = {p["id"]: 1000 for p in players}
        matches_2v2 = {p["id"]: 0 for p in players}

        engine = EloEngine()
        total_matches = len(matches)
        corrected_matches = 0

        # C. Replay de l'histoire
        for i, m in enumerate(matches):
            mode = m.get("mode", "1v1")
            delta = 0

            # --- Logique 1v1 ---
            if mode == "1v1":
                w_id, l_id = m["winner_id"], m["loser_id"]
                if w_id in temp_elo_1v1 and l_id in temp_elo_1v1:
                    new_w, new_l, delta = engine.compute_new_ratings(
                        temp_elo_1v1[w_id], temp_elo_1v1[l_id], 0, 0
                    )
                    temp_elo_1v1[w_id] = new_w
                    temp_elo_1v1[l_id] = new_l
                    matches_1v1[w_id] += 1
                    matches_1v1[l_id] += 1

            # --- Logique 2v2 ---
            elif mode == "2v2":
                ids = [m["winner_id"], m["winner2_id"], m["loser_id"], m["loser2_id"]]
                # On vérifie que les 4 joueurs existent
                if all(pid in temp_elo_2v2 for pid in ids if pid):
                    w_avg = (
                        temp_elo_2v2[m["winner_id"]] + temp_elo_2v2[m["winner2_id"]]
                    ) / 2
                    l_avg = (
                        temp_elo_2v2[m["loser_id"]] + temp_elo_2v2[m["loser2_id"]]
                    ) / 2

                    _, _, delta = engine.compute_new_ratings(w_avg, l_avg, 0, 0)

                    for pid in [m["winner_id"], m["winner2_id"]]:
                        temp_elo_2v2[pid] += delta
                        matches_2v2[pid] += 1
                    for pid in [m["loser_id"], m["loser2_id"]]:
                        temp_elo_2v2[pid] -= delta
                        matches_2v2[pid] += 1

            # D. Correction de l'historique (elo_gain)
            stored_gain = m.get("elo_gain", 0)
            # Si le gain calculé diffère du gain stocké de plus de 0.01
            if abs(stored_gain - delta) > 0.01:
                db.supabase.table("matches").update({"elo_gain": delta}).eq(
                    "id", m["id"]
                ).execute()
                corrected_matches += 1

            if total_matches > 0:
                progress_bar.progress((i + 1) / total_matches)

        status_text.text("💾 Sauvegarde des scores finaux...")

        # E. Mise à jour finale des profils
        all_ids = set(temp_elo_1v1.keys()) | set(temp_elo_2v2.keys())

        for p_id in all_ids:
            updates = {}
            if p_id in temp_elo_1v1:
                updates["elo_rating"] = temp_elo_1v1[p_id]
                updates["matches_played"] = matches_1v1[p_id]
            if p_id in temp_elo_2v2:
                updates["elo_2v2"] = temp_elo_2v2[p_id]
                updates["matches_2v2"] = matches_2v2[p_id]

            if updates:
                db.supabase.table("profiles").update(updates).eq("id", p_id).execute()

        progress_bar.empty()
        st.success(
            f"✅ Synchronisation terminée ! {corrected_matches} matchs historiques corrigés."
        )
        st.balloons()

elif page == "⚙️ Paramètres":
    st.header("⚙️ Paramètres de confidentialité")

    with st.form("privacy_form"):
        st.write("Gérez la visibilité de votre compte :")

        # On récupère les valeurs actuelles (ou False par défaut)
        current_hide_lb = user.get("is_hidden_leaderboard", False)
        current_hide_prof = user.get("is_hidden_profile", False)

        # Les interrupteurs
        new_hide_lb = st.toggle(
            "Masquer mon nom dans le classement",
            value=current_hide_lb,
            help="Votre nom sera remplacé par 'Joueur Masqué'.",
        )
        new_hide_prof = st.toggle(
            "Rendre mon profil privé",
            value=current_hide_prof,
            help="Les autres joueurs ne pourront pas voir vos détails et graphiques.",
        )

        if st.form_submit_button("Enregistrer les modifications"):
            success, msg = db.update_user_privacy(
                user["id"], new_hide_lb, new_hide_prof
            )
            if success:
                st.success("✅ " + msg)
                # On met à jour la session pour que l'effet soit immédiat
                user["is_hidden_leaderboard"] = new_hide_lb
                user["is_hidden_profile"] = new_hide_prof
                st.rerun()
            else:
                st.error("❌ " + msg)
