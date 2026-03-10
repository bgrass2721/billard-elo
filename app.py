import streamlit as st
from DB_manager import DBManager
import pandas as pd
import extra_streamlit_components as stx
from elo_engine import EloEngine
import altair as alt
from datetime import datetime
import pytz

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
    Génère les badges avec progression visible et infobulles compatibles mobile.
    Version compactée sans retours à la ligne pour éviter les bugs d'affichage.
    """

    # --- 1. CALCUL DES STATS ---
    total_matches = player.get("matches_played", 0) + player.get("matches_2v2", 0)
    wins = 0
    current_streak = 0
    unique_opponents = set()
    matches_by_day = {}
    partners_counter = {}

    has_giant_kill = False
    streak_active = True

    sorted_matches = sorted(
        matches_history, key=lambda x: str(x["created_at"]), reverse=True
    )

    for m in sorted_matches:
        # Conversion UTC -> Paris
        dt_utc = pd.to_datetime(m["created_at"])
        dt_paris = (
            dt_utc.tz_convert("Europe/Paris")
            if dt_utc.tzinfo
            else dt_utc.tz_localize("UTC").tz_convert("Europe/Paris")
        )
        day = dt_paris.strftime("%Y-%m-%d")
        if day not in matches_by_day:
            matches_by_day[day] = 0
        matches_by_day[day] += 1

        is_2v2 = m.get("mode") == "2v2"
        is_win = m["winner_id"] == player["id"] or m.get("winner2_id") == player["id"]

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

    max_daily_matches = max(matches_by_day.values()) if matches_by_day else 0
    nb_unique = len(unique_opponents)
    max_duo_matches = max(partners_counter.values()) if partners_counter else 0
    has_marathon = max_daily_matches >= 10

    # --- 2. GÉNÉRATEUR DE HTML ---
    html_parts = []

    def process_tier_badge(current_val, tiers, shape, base_icon, label):
        achieved_tier = None
        next_tier = None
        for tier in tiers:
            if current_val >= tier["req"]:
                achieved_tier = tier
            else:
                next_tier = tier
                break

        progress_text = f"<span style='color: #4db8ff; font-weight:bold;'>📊 Actuel : {current_val}</span>"

        if achieved_tier:
            style = achieved_tier["style"]
            name = achieved_tier["name"]
            if next_tier:
                tooltip_text = f"✅ {name}<br>{progress_text}<br><span style='font-size:0.9em; opacity:0.8;'>🎯 Prochain : {next_tier['name']} ({next_tier['req']} {label})</span>"
            else:
                tooltip_text = f"🏆 NIVEAU MAX<br>{name}<br>{progress_text}<br><span style='font-size:0.9em; opacity:0.8;'>Vous êtes une légende !</span>"
            css_class = ""
            icon = base_icon
        else:
            first_tier = tiers[0]
            style = first_tier["style"]
            name = first_tier["name"]
            tooltip_text = f"🔒 BLOQUÉ<br>{progress_text}<br><span style='font-size:0.9em; opacity:0.8;'>🎯 Objectif : {first_tier['req']} {label}</span>"
            css_class = "locked"
            icon = base_icon

        badge_html = f'<div class="badge-item {css_class}"><div class="badge-icon-box {shape} {style}">{icon}</div><div class="badge-name">{name}</div><span class="tooltip-content">{tooltip_text}</span></div>'
        html_parts.append(badge_html)

    def add_special(cond, shape, style, icon, name, desc, current_stat=""):
        css = "" if cond else "locked"
        stat_line = (
            f"<br><span style='color: #ff9f43; font-weight:bold;'>{current_stat}</span>"
            if current_stat
            else ""
        )
        if cond:
            tooltip_text = f"✅ {name}{stat_line}<br><span style='font-size:0.9em; opacity:0.8;'>{desc}</span>"
        else:
            tooltip_text = f"🔒 BLOQUÉ{stat_line}<br><span style='font-size:0.9em; opacity:0.8;'>Objectif : {desc}</span>"

        badge_html = f'<div class="badge-item {css}"><div class="badge-icon-box {shape} {style}">{icon}</div><div class="badge-name">{name}</div><span class="tooltip-content">{tooltip_text}</span></div>'
        html_parts.append(badge_html)

    # --- 3. DÉFINITION DES PALIERS ---
    tiers_fidelity = [
        {"req": 10, "style": "bronze", "name": "Rookie"},
        {"req": 50, "style": "silver", "name": "Confirmé"},
        {"req": 100, "style": "gold", "name": "Pilier"},
        {"req": 200, "style": "platinum", "name": "Légende"},
    ]
    process_tier_badge(total_matches, tiers_fidelity, "shield", "⚔️", "matchs")

    tiers_victory = [
        {"req": 10, "style": "bronze", "name": "Gâchette"},
        {"req": 25, "style": "silver", "name": "Conquérant"},
        {"req": 50, "style": "gold", "name": "Champion"},
        {"req": 100, "style": "platinum", "name": "Invincible"},
    ]
    process_tier_badge(wins, tiers_victory, "star", "🏆", "victoires")

    tiers_duo = [
        {"req": 10, "style": "bronze", "name": "Binôme"},
        {"req": 30, "style": "silver", "name": "Frères d'armes"},
        {"req": 60, "style": "gold", "name": "Fusion"},
        {"req": 120, "style": "platinum", "name": "Symbiose"},
    ]
    process_tier_badge(max_duo_matches, tiers_duo, "circle", "🤝", "matchs ensemble")

    tiers_social = [
        {"req": 5, "style": "bronze", "name": "Explorateur"},
        {"req": 10, "style": "silver", "name": "Voyageur"},
        {"req": 20, "style": "gold", "name": "Monde"},
        {"req": 40, "style": "platinum", "name": "Universel"},
    ]
    process_tier_badge(nb_unique, tiers_social, "circle", "🌍", "adversaires")

    add_special(
        current_streak >= 5,
        "hexagon",
        "magma",
        "🔥",
        "On Fire",
        "Série de 5 victoires",
        f"Série : {current_streak}",
    )
    add_special(
        has_marathon,
        "hexagon",
        "electric",
        "⚡",
        "Marathon",
        "10 matchs en 1 jour",
        f"Record jour : {max_daily_matches}",
    )
    add_special(
        has_giant_kill,
        "hexagon",
        "blood",
        "🩸",
        "Tueur",
        "Battre un +200 Elo",
        "Accompli !" if has_giant_kill else "Pas encore...",
    )

    container_style = "display: flex; flex-wrap: wrap; justify-content: center; gap: 4px; background: rgba(20, 20, 30, 0.4); padding: 15px; border-radius: 16px; border: 1px solid rgba(255,255,255,0.05); box-shadow: 0 4px 20px rgba(0,0,0,0.3);"
    return f'<div style="{container_style}">{"".join(html_parts)}</div>'


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
    /* --- INFOBULLE (TOOLTIP) - MOBILE COMPATIBLE --- */
    .tooltip-content {
        visibility: hidden;
        width: 150px; /* Un peu plus large pour le texte de progression */
        background-color: rgba(0, 0, 0, 0.95);
        color: #fff;
        text-align: center;
        border-radius: 8px;
        padding: 8px;
        position: absolute;
        z-index: 100;
        top: 105%; left: 50%;
        transform: translateX(-50%);
        font-size: 11px; font-weight: normal; line-height: 1.4;
        border: 1px solid rgba(255,255,255,0.2);
        box-shadow: 0 4px 10px rgba(0,0,0,0.5);
        opacity: 0; transition: opacity 0.3s;
        pointer-events: none;
    }

    /* Flèche du haut */
    .tooltip-content::after {
        content: ""; position: absolute; bottom: 100%; left: 50%; margin-left: -5px;
        border-width: 5px; border-style: solid;
        border-color: transparent transparent rgba(0,0,0,0.95) transparent;
    }

    /* L'ACTIVATION MOBILE (Le secret est ici) */
    /* :active et :focus permettent l'affichage au clic sur téléphone */
    .badge-item:hover .tooltip-content,
    .badge-item:active .tooltip-content,
    .badge-item:focus .tooltip-content {
        visibility: visible;
        opacity: 1;
    }
    </style>
    """,
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
        pass # Le token est peut-être expiré

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
    "🏟️ Grand Tournoi",
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
            dt_utc = pd.to_datetime(m["created_at"])
            dt_paris = (
                dt_utc.tz_convert("Europe/Paris")
                if dt_utc.tzinfo
                else dt_utc.tz_localize("UTC").tz_convert("Europe/Paris")
            )
            date_display = dt_paris.strftime("%d/%m %Hh%M")

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
            dt_utc = pd.to_datetime(m["created_at"])
            dt_paris = (
                dt_utc.tz_convert("Europe/Paris")
                if dt_utc.tzinfo
                else dt_utc.tz_localize("UTC").tz_convert("Europe/Paris")
            )
            date_str = dt_paris.strftime("%d/%m à %Hh%M")
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
                f"<h2 style='text-align: center; color: #4CAF50;'>{vs_stats['p1_wins']}</h2>",
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

            elo_color = "#4CAF50" if cumulative_score_elo >= 0 else "#FF5252"
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

elif page == "🏟️ Grand Tournoi":
    st.header("🏟️ Espace Grand Tournoi")
    
    # On sépare la vue Admin de la vue Spectateur
    is_admin = user.get("is_admin", False)
    
    if is_admin:
        tab_spectator, tab_admin = st.tabs(["Historique des tournois", "🛠️ Panel Admin Tournoi"])
    else:
        tab_spectator = st.container() # Le joueur normal ne voit que ça
        
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
                                
                                # Calcul classement
                                standings = {}
                                for p in g_parts:
                                    standings[p["user_id"]] = {"Nom": all_users_spec.get(p["user_id"], "?"), "V": 0, "D": 0, "Diff": 0}
                                    
                                for m in g_matches:
                                    if m["status"] == "completed":
                                        s1, s2 = m["score1"], m["score2"]
                                        p1, p2 = m["player1_id"], m["player2_id"]
                                        if p1 in standings:
                                            if s1 > s2: standings[p1]["V"] += 1
                                            else: standings[p1]["D"] += 1
                                            standings[p1]["Diff"] += (s1 - s2)
                                        if p2 in standings:
                                            if s2 > s1: standings[p2]["V"] += 1
                                            else: standings[p2]["D"] += 1
                                            standings[p2]["Diff"] += (s2 - s1)
                                            
                                sorted_standings = sorted(standings.values(), key=lambda x: (x["V"], x["Diff"]), reverse=True)
                                import pandas as pd
                                df_standings = pd.DataFrame(sorted_standings)
                                df_standings.index = df_standings.index + 1
                                st.dataframe(df_standings, use_container_width=True)
                                
                                # Liste des matchs joués/à venir
                                if g_matches:
                                    st.markdown("**Matchs :**")
                                    for m in g_matches:
                                        p1_name = all_users_spec.get(m["player1_id"], "?")
                                        p2_name = all_users_spec.get(m["player2_id"], "?")
                                        if m["status"] == "completed":
                                            # Affichage visuel du gagnant
                                            st.markdown(f"**{p1_name}** `{m['score1']} - {m['score2']}` **{p2_name}** ✅")
                                        else:
                                            st.markdown(f"{p1_name} `vs` {p2_name} ⏳")

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
                        
                        # Fonction interne magique : Génère le code HTML d'un match (Évite de répéter le code)
                        def get_match_card(r_num, m_num, is_gf=False):
                            b_id = f"{prefix}_R{r_num}_M{m_num}"
                            m = tier_dict.get(b_id)
                            
                            bg_color = "rgba(255, 215, 0, 0.05)" if is_gf else "#1E1E28"
                            border_color = "#FFD700" if is_gf else "#444"
                            
                            c_html = f"<div style='background-color: {bg_color}; border: 1px solid {border_color}; border-radius: 8px; padding: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.2); margin: 5px 0;'>"
                            c_html += f"<div style='font-size: 10px; color: #888; text-align: center; margin-bottom: 8px;'>Match {m_num}</div>"
                            
                            if m:
                                p1 = all_users_spec.get(m.get("player1_id"), "...") if m.get("player1_id") else "..."
                                p2 = all_users_spec.get(m.get("player2_id"), "...") if m.get("player2_id") else "..."
                                s1, s2 = m.get("score1", 0), m.get("score2", 0)
                                
                                if m["status"] == "completed":
                                    w1 = "bold; color: white;" if s1 > s2 else "normal; color: #888;"
                                    w2 = "bold; color: white;" if s2 > s1 else "normal; color: #888;"
                                    c1 = "#4CAF50" if s1 > s2 else "#888"
                                    c2 = "#4CAF50" if s2 > s1 else "#888"
                                else:
                                    w1 = w2 = "normal; color: white;"
                                    c1 = c2 = "transparent"
                                    if p1 == "..." and p2 == "...": s1 = s2 = ""
                                    
                                c_html += f"<div style='display: flex; justify-content: space-between; font-weight: {w1}; margin-bottom: 5px;'><span style='overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 140px;'>{p1}</span><span style='color: {c1}; font-weight: bold;'>{s1}</span></div>"
                                c_html += f"<div style='display: flex; justify-content: space-between; font-weight: {w2};'><span style='overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 140px;'>{p2}</span><span style='color: {c2}; font-weight: bold;'>{s2}</span></div>"
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
                                
                                if prefix == "WB" and r_num == total_rounds_wb + 1: col_title = "👑 Grande Finale"
                                elif prefix == "WB" and r_num == total_rounds_wb + 2: col_title = "⚔️ Bracket Reset"
                                else: col_title = f"Tour {r_num}"
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
                            
                            # B. CENTRE (Finale)
                            html += "<div style='display: flex; flex-direction: column; justify-content: space-around; flex: 0 0 220px; margin: 0 10px;'>"
                            html += f"<div style='text-align: center; color: gold; font-weight: bold; margin-bottom: 10px; flex: 0 0 auto;'>👑 Finale</div>"
                            html += "<div style='display: flex; flex-direction: column; justify-content: space-around; flex: 1 1 auto;'>"
                            html += get_match_card(total_rounds_wb, 1, is_gf=True)
                            html += "</div></div>"
                            
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
                            
                            html += "</div>" # Fin du flex-start
                        
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
                
                ghost_profiles = [p for p in all_profiles if p.get("is_ghost") == True]
                real_profiles = [p for p in all_profiles if p.get("is_ghost") != True]
                
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
                            p for p in user_options.keys() 
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
                            
                            standings = {}
                            for p in g_parts:
                                standings[p["user_id"]] = {"Nom": all_users.get(p["user_id"], "?"), "V": 0, "D": 0, "Diff": 0}
                                
                            for m in g_matches:
                                if m["status"] == "completed":
                                    s1, s2 = m["score1"], m["score2"]
                                    p1, p2 = m["player1_id"], m["player2_id"]
                                    
                                    if p1 in standings:
                                        if s1 > s2: standings[p1]["V"] += 1
                                        else: standings[p1]["D"] += 1
                                        standings[p1]["Diff"] += (s1 - s2)
                                        
                                    if p2 in standings:
                                        if s2 > s1: standings[p2]["V"] += 1
                                        else: standings[p2]["D"] += 1
                                        standings[p2]["Diff"] += (s2 - s1)
                            
                            sorted_standings = sorted(standings.values(), key=lambda x: (x["V"], x["Diff"]), reverse=True)
                            
                            st.markdown("**Classement Actuel :**")
                            import pandas as pd
                            df_standings = pd.DataFrame(sorted_standings)
                            df_standings.index = df_standings.index + 1
                            st.dataframe(df_standings, use_container_width=True)
                            
                            st.divider()
                            st.markdown("**Saisie des Matchs :**")
                            
                            for m in g_matches:
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
                                    if s1 > s2: temp_standings[p1]["V"] += 1
                                    temp_standings[p1]["Diff"] += (s1 - s2)
                                if p2 in temp_standings:
                                    if s2 > s1: temp_standings[p2]["V"] += 1
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
                        if val_p1: all_selected_in_draw.add(val_p1)
                        if val_p2: all_selected_in_draw.add(val_p2)

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
                                    bg_color = "#2E7D32" if r_num == 1 else "#1E1E28"
                                    border_color = "#4CAF50" if r_num == 1 else "#444"
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
                                    bg_color = "#2E7D32" if r_num == 1 else "#1E1E28"
                                    border_color = "#4CAF50" if r_num == 1 else "#444"
                                    text_color = "white" if r_num == 1 else "#888"
                                    html_map += f"<div style='background-color: {bg_color}; border: 1px solid {border_color}; border-radius: 6px; padding: 10px 5px; text-align: center; margin: 4px 0;'><strong style='color: {text_color}; font-size: 13px;'>Match {m_num}</strong></div>"
                                html_map += "</div></div>"
                            html_map += "</div>"
                            
                            # 2. CENTRE
                            html_map += "<div style='display: flex; flex-direction: column; justify-content: space-around; flex: 0 0 140px; margin: 0 15px;'>"
                            html_map += f"<div style='text-align: center; color: gold; font-weight: bold; margin-bottom: 10px;'>👑 Finale</div>"
                            html_map += "<div style='display: flex; flex-direction: column; justify-content: space-around; flex: 1 1 auto;'>"
                            html_map += f"<div style='background-color: rgba(255,215,0,0.1); border: 1px solid gold; border-radius: 6px; padding: 15px 5px; text-align: center; margin: 4px 0;'><strong style='color: white; font-size: 14px;'>Match 1</strong></div>"
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
                                    bg_color = "#2E7D32" if r_num == 1 else "#1E1E28"
                                    border_color = "#4CAF50" if r_num == 1 else "#444"
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
                                
                                def get_match_card_admin(r_num, m_num, is_gf=False):
                                    b_id = f"{prefix}_R{r_num}_M{m_num}"
                                    m = tier_dict.get(b_id)
                                    bg_color = "rgba(255, 215, 0, 0.05)" if is_gf else "#1E1E28"
                                    border_color = "#FFD700" if is_gf else "#444"
                                    
                                    c_html = f"<div style='background-color: {bg_color}; border: 1px solid {border_color}; border-radius: 8px; padding: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.2); margin: 5px 0;'>"
                                    c_html += f"<div style='font-size: 10px; color: #888; text-align: center; margin-bottom: 8px;'>Match {m_num}</div>"
                                    
                                    if m:
                                        p1 = all_users.get(m.get("player1_id"), "...") if m.get("player1_id") else "..."
                                        p2 = all_users.get(m.get("player2_id"), "...") if m.get("player2_id") else "..."
                                        s1, s2 = m.get("score1", 0), m.get("score2", 0)
                                        
                                        if m["status"] == "completed":
                                            w1 = "bold; color: white;" if s1 > s2 else "normal; color: #888;"
                                            w2 = "bold; color: white;" if s2 > s1 else "normal; color: #888;"
                                            c1 = "#4CAF50" if s1 > s2 else "transparent"
                                            c2 = "#4CAF50" if s2 > s1 else "transparent"
                                        else:
                                            w1 = w2 = "normal; color: white;"
                                            c1 = c2 = "transparent"
                                            if p1 == "..." and p2 == "...": s1 = s2 = ""
                                            
                                        c_html += f"<div style='display: flex; justify-content: space-between; font-weight: {w1}; margin-bottom: 5px;'><span style='overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 120px;'>{p1}</span><span style='color: {c1}; font-weight: bold;'>{s1}</span></div>"
                                        c_html += f"<div style='display: flex; justify-content: space-between; font-weight: {w2};'><span style='overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 120px;'>{p2}</span><span style='color: {c2}; font-weight: bold;'>{s2}</span></div>"
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
                                        if prefix == "WB" and r_num == total_rounds_wb + 1: col_title = "👑 Finale"
                                        elif prefix == "WB" and r_num == total_rounds_wb + 2: col_title = "⚔️ Reset"
                                        else: col_title = f"Tour {r_num}"
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
                                    html += f"<div style='text-align: center; color: gold; font-weight: bold; margin-bottom: 10px; flex: 0 0 auto;'>👑 Finale</div>"
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
                                titre_tour = "👑 Finale" if is_finale else f"Tour {r_num}"
                                
                                st.markdown(f"##### {titre_tour}")
                                
                                expected_count = max(1, nb_matches_r1 // (2**(r_num-1)))
                                
                                # On crée des rangées de 3 colonnes max pour que ça reste toujours large et lisible
                                cols_per_row = min(3, expected_count) if expected_count > 1 else 1
                                cols = st.columns(cols_per_row)
                                
                                for m_num in range(1, expected_count + 1):
                                    col = cols[(m_num - 1) % cols_per_row]
                                    m = tier_dict_wb.get(f"WB_R{r_num}_M{m_num}")
                                    draw_interactive_match(col, m, r_num, m_num, is_gf=is_finale)
                                
                                st.write("") # Petit espace entre chaque tour

                    st.divider()
                    st.info("Une fois la Grande Finale jouée et validée, vous pourrez clôturer l'événement.")
                    if st.button("🏆 Clôturer le Tournoi (Archiver)", type="primary"):
                        db.update_tournament_status(selected_t["id"], "completed")
                        st.success("Tournoi terminé et archivé !")
                        st.balloons()
                        st.rerun()

                elif selected_t["status"] == "completed":
                    st.success("🏁 Ce tournoi est terminé et archivé.")
                

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
