import streamlit as st
from DB_manager import DBManager
import pandas as pd
import extra_streamlit_components as stx
from elo_engine import EloEngine
import altair as alt
from datetime import datetime
import pytz
from ranks_config import RANK_TIERS
import textwrap
from badges_config import BADGES_B64  # <-- Ajout de cette ligne

# --- CONFIGURATION DU CODE SECRET ---
SECRET_INVITE_CODE = st.secrets["INVITE_CODE"]

# ==========================================
# 🎨 CHIRURGIE ESTHÉTIQUE DE L'APPLICATION
# ==========================================
import streamlit as st
import pandas as pd

# 1. Configuration de la page (Doit être en tout premier)
# (Pense à supprimer tes anciens appels st.set_page_config s'ils existent déjà).
st.set_page_config(page_title="Snook'R Club", page_icon="🎱", layout="wide")

st.markdown("""
<style>
    /* Importation des polices Google : Montserrat (texte) et Playfair Display (titres) */
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600&family=Playfair+Display:wght@700&display=swap');
    
    /* On force la police de texte propre partout */
    html, body, [class*="css"] {
        font-family: 'Montserrat', sans-serif !important;
    }
    
    /* On donne la police "Héraldique/Classe" à tous les grands titres de l'app */
    h1, h2, h3 {
        font-family: 'Playfair Display', serif !important;
    }

    /* Le style spécifique pour le gros logo en haut à gauche */
    .sidebar-logo-text {
        font-family: 'Playfair Display', serif;
        color: #C69C25; /* Couleur Or */
        font-size: 2.8em;
        text-align: center;
        margin-top: 0px;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
    }

    /* 1. Style des options de navigation dans la barre latérale */
    div[data-testid="stSidebarNav"] {
        padding-top: 2rem;
    }

    /* Rendre les boutons radio invisibles mais styliser les labels */
    div[data-testid="stSidebar"] .stRadio > div {
        background-color: transparent;
        padding: 0;
    }

    div[data-testid="stSidebar"] .stRadio label {
        background-color: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(198, 156, 37, 0.1);
        border-radius: 8px;
        padding: 10px 15px !important;
        margin-bottom: 8px;
        transition: all 0.3s ease;
        color: #F8F9FA !important;
        width: 100%;
    }

    /* Effet au survol */
    div[data-testid="stSidebar"] .stRadio label:hover {
        background-color: rgba(198, 156, 37, 0.1);
        border-color: #C69C25;
        transform: translateX(5px);
    }

    /* Style de l'option sélectionnée */
    div[data-testid="stSidebar"] .stRadio div[data-checked="true"] label {
        background: linear-gradient(90deg, rgba(198, 156, 37, 0.2) 0%, rgba(198, 156, 37, 0) 100%) !important;
        border-left: 5px solid #C69C25 !important;
        border-color: #C69C25;
        color: #C69C25 !important;
        font-weight: 600 !important;
    }

    /* Masquer le petit cercle radio original */
    div[data-testid="stSidebar"] .stRadio div[role="radiogroup"] [data-testid="stWidgetLabel"] + div {
        display: none;
    }
    
    /* 2. Style spécial pour le bouton déconnexion */
    .stSidebar [data-testid="stButton"] button {
        background-color: transparent;
        border: 1px solid #ff4b4b;
        color: #ff4b4b;
        transition: all 0.3s;
    }
    .stSidebar [data-testid="stButton"] button:hover {
        background-color: #ff4b4b;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

def render_xp_bar(old_elo, new_elo, old_rank_info, new_rank_info):
    """Génère la carte d'XP avec le buffer de survie et remplissage dynamique post-transition."""
    is_promo = new_rank_info["id"] > old_rank_info["id"]
    is_demote = new_rank_info["id"] < old_rank_info["id"]
    is_same = not (is_promo or is_demote)

    # Fonction utilitaire pour calculer le % d'une barre
    def get_pct(val, min_v, max_v):
        if max_v <= min_v: return 100
        return max(0, min(100, ((val - min_v) / (max_v - min_v)) * 100))

    # === 1. PARAMÈTRES NOUVEAU RANG ===
    new_base_min = new_rank_info["threshold"]
    new_next = next((t for t in RANK_TIERS if t["id"] == new_rank_info["id"] + 1), None)

    new_display_min = (new_base_min - 25) if new_base_min >= 25 else 0
    new_display_max = new_next["threshold"] if new_next else "MAX"
    new_calc_max = new_display_min + 100 if new_display_max == "MAX" else new_display_max

    is_in_danger = new_elo < new_base_min

    # === 2. PARAMÈTRES ANCIEN RANG ===
    old_base_min = old_rank_info["threshold"]
    old_next = next((t for t in RANK_TIERS if t["id"] == old_rank_info["id"] + 1), None)
    
    old_display_min = (old_base_min - 25) if old_base_min >= 25 else 0
    old_display_max = old_next["threshold"] if old_next else "MAX"
    old_calc_max = old_display_min + 100 if old_display_max == "MAX" else old_display_max

    # === 3. CALCUL DES POURCENTAGES (Correction Téléportation) ===
    if is_promo:
        trans_elo = new_base_min
        old_start_pct = get_pct(old_elo, old_display_min, old_calc_max)
        old_end_pct = get_pct(trans_elo, old_display_min, old_calc_max)
        # 🔴 CORRECTION : La nouvelle barre part de 0% pour montrer le remplissage du buffer
        new_start_pct = 0 
        new_end_pct = get_pct(new_elo, new_display_min, new_calc_max)
    elif is_demote:
        trans_elo = old_base_min - 25
        old_start_pct = get_pct(old_elo, old_display_min, old_calc_max)
        old_end_pct = get_pct(trans_elo, old_display_min, old_calc_max)
        # 🔴 CORRECTION : La nouvelle barre part de 100% et se vide
        new_start_pct = 100 
        new_end_pct = get_pct(new_elo, new_display_min, new_calc_max)
    else:
        old_start_pct = get_pct(old_elo, new_display_min, new_calc_max)
        new_end_pct = get_pct(new_elo, new_display_min, new_calc_max)

    diff = int(new_elo - old_elo)
    color_pts = "#2ecc71" if diff > 0 else "#e74c3c"

    # === 4. STYLES (Zone de Danger) ===
    if is_same and is_in_danger:
        status_text = "⚠️ ZONE DE DANGER"
        status_color = "#ff4b2b"
        border_color = "#ff4b2b"
        bar_color = "linear-gradient(90deg, #ff4b2b, #ff416c)"
        bar_shadow = "#ff4b2b"
        anim_pulse = "animation: dangerPulse 2s infinite;"
    else:
        status_text = new_rank_info['name']
        status_color = "white"
        border_color = "rgba(198,156,37,0.3)"
        bar_color = new_rank_info['bg_gradient']
        bar_shadow = new_rank_info['color']
        anim_pulse = ""

    # === 5. ANIMATIONS CSS CINÉMATIQUES ===
    if is_promo:
        anim_css = f"@keyframes fillOld {{from {{width: {old_start_pct}%;}} to {{width: {old_end_pct}%;}}}} @keyframes fillNew {{from {{width: {new_start_pct}%;}} to {{width: {new_end_pct}%;}}}} .bar-phase1 {{animation: fillOld 1.5s ease-in forwards;}} .bar-phase2 {{width: {new_start_pct}%; animation: fillNew 1.5s 1.7s ease-out forwards;}}"
        flash_anim = "flashPromo"
    elif is_demote:
        anim_css = f"@keyframes drainOld {{from {{width: {old_start_pct}%;}} to {{width: {old_end_pct}%;}}}} @keyframes drainNew {{from {{width: {new_start_pct}%;}} to {{width: {new_end_pct}%;}}}} .bar-phase1 {{animation: drainOld 1.5s ease-in forwards;}} .bar-phase2 {{width: {new_start_pct}%; animation: drainNew 1.5s 1.7s ease-out forwards;}}"
        flash_anim = "flashDemote"
    else:
        anim_css = f"@keyframes moveBar {{from {{width: {old_start_pct}%;}} to {{width: {new_end_pct}%;}}}} .bar-single {{animation: moveBar 2s ease-out forwards;}} @keyframes dangerPulse {{ 0% {{opacity: 1;}} 50% {{opacity: 0.6;}} 100% {{opacity: 1;}} }}"
        flash_anim = "none"

    # === 6. HTML MINIFIÉ ===
    html = f"""<style>{anim_css}
    @keyframes fadeOut {{ 0%, 88% {{opacity:1; transform:scale(1);}} 100% {{opacity:0; transform:scale(1.3); visibility:hidden;}} }}
    @keyframes fadeIn {{ 0%, 88% {{opacity:0; transform:scale(0.5);}} 100% {{opacity:1; transform:scale(1);}} }}
    @keyframes flashPromo {{ 0%, 45% {{border-color: rgba(198,156,37,0.3); box-shadow: 0 0 0px transparent;}} 50% {{border-color: white; box-shadow: 0 0 50px white;}} 100% {{border-color: {new_rank_info['color']}; box-shadow: 0 10px 30px rgba(0,0,0,0.5);}} }}
    @keyframes flashDemote {{ 0%, 45% {{border-color: rgba(198,156,37,0.3); box-shadow: 0 0 0px transparent;}} 50% {{border-color: #ff4b2b; box-shadow: 0 0 50px #ff4b2b;}} 100% {{border-color: {new_rank_info['color']}; box-shadow: 0 10px 30px rgba(0,0,0,0.5);}} }}
    .xp-card {{width:100%; max-width:600px; margin:0 auto; font-family:'Montserrat',sans-serif; background:#0f172a; padding:40px 30px; border-radius:20px; border:2px solid {border_color}; text-align:center; color:white; overflow:hidden;}}
    .card-anim-cinematic {{animation: {flash_anim} 3.5s forwards;}}
    .swap-out {{animation: fadeOut 1.7s forwards;}}
    .swap-in {{opacity:0; animation: fadeIn 1.7s forwards;}}
    .huge-icon img, .huge-icon svg {{width:130px !important; height:130px !important; object-fit:contain;}}
    .prog-container {{width:100%; height:18px; background:#1e293b; border-radius:9px; overflow:hidden; border:1px solid #334155; position:relative; {anim_pulse}}}
    .bar-base {{height:100%;}}
    </style>
    <div class="xp-card {'card-anim-cinematic' if not is_same else ''}">
    """

    if is_same:
        html += f"""
        <div style="display:flex; flex-direction:column; align-items:center; gap:20px; margin-bottom:35px;">
            <div class="huge-icon">{new_rank_info['icon']}</div>
            <span style="font-weight:900; color:{status_color}; font-size:1.8em; text-transform:uppercase; letter-spacing:1px;">{status_text}</span>
        </div>
        <div class="prog-container"><div class="bar-base bar-single" style="background:{bar_color}; box-shadow:0 0 15px {bar_shadow};"></div></div>
        <div style="display:flex; justify-content:space-between; margin-top:12px; font-size:0.9em; color:#8BA1B5; font-weight:bold;">
            <span>{new_display_min} ELO {'(SURVIE)' if is_in_danger else ''}</span>
            <span>{new_display_max}{' ELO' if new_display_max != 'MAX' else ''}</span>
        </div>
        """
    else:
        html += f"""
        <div style="display: grid; grid-template-columns: 1fr;">
            <div style="grid-row: 1; grid-column: 1; z-index: 2;" class="swap-out">
                <div style="display:flex; flex-direction:column; align-items:center; gap:20px; margin-bottom:35px;">
                    <div class="huge-icon">{old_rank_info['icon']}</div>
                    <span style="font-weight:900; color:{'#e74c3c' if is_demote else 'white'}; font-size:1.8em; text-transform:uppercase; letter-spacing:1px;">{old_rank_info['name']}</span>
                </div>
                <div class="prog-container"><div class="bar-base bar-phase1" style="background:{old_rank_info['bg_gradient']}; box-shadow:0 0 15px {old_rank_info['color']};"></div></div>
                <div style="display:flex; justify-content:space-between; margin-top:12px; font-size:0.9em; color:#8BA1B5; font-weight:bold;">
                    <span>{old_display_min} ELO</span>
                    <span>{old_display_max}{' ELO' if old_display_max != 'MAX' else ''}</span>
                </div>
            </div>
            
            <div style="grid-row: 1; grid-column: 1; z-index: 3;" class="swap-in">
                <div style="display:flex; flex-direction:column; align-items:center; gap:20px; margin-bottom:35px;">
                    <div class="huge-icon">{new_rank_info['icon']}</div>
                    <span style="font-weight:900; color:{'#f1c40f' if is_promo else '#e74c3c'}; font-size:1.8em; text-transform:uppercase; letter-spacing:1px;">{'⬆️ PROMOTION !' if is_promo else '⬇️ RÉTROGRADATION...'}</span>
                </div>
                <div class="prog-container"><div class="bar-base bar-phase2" style="background:{new_rank_info['bg_gradient']}; box-shadow:0 0 15px {new_rank_info['color']};"></div></div>
                <div style="display:flex; justify-content:space-between; margin-top:12px; font-size:0.9em; color:#8BA1B5; font-weight:bold;">
                    <span>{new_display_min} ELO {'(SURVIE)' if is_in_danger else ''}</span>
                    <span>{new_display_max}{' ELO' if new_display_max != 'MAX' else ''}</span>
                </div>
            </div>
        </div>
        """

    html += f"""
        <div style="margin-top:40px; position:relative; z-index:5;">
            <div style="font-family:'Playfair Display',serif; font-size:3.2em; font-weight:bold;">{int(new_elo)} <span style="font-size:0.3em; color:#C69C25;">ELO</span></div>
            <div style="color:{color_pts}; font-weight:900; font-size:1.6em; margin-top:5px;">{diff:+} PTS</div>
        </div>
    </div>
    """
    return html.replace('\n', '')
    
def draw_luxury_table(data_list, title=None, columns=None, is_ranking=True):
    """Génère un tableau HTML au design 'Snook'R Héraldique' avec option podium"""
    if not data_list: return ""
    
    html = ""
    if title:
        html += f"<h4 style=\"font-family: 'Playfair Display', serif; color: #C69C25; margin-bottom: 15px; margin-top: 20px;\">{title}</h4>"
        
    html += "<table style='width: 100%; border-collapse: collapse; margin-bottom: 25px; background: rgba(255,255,255, 0.03); border-radius: 8px; overflow: hidden; border: 1px solid rgba(198, 156, 37, 0.3);'>"
    
    # En-tête
    if not columns:
        columns = list(data_list[0].keys())
        
    html += "<thead style='background-color: rgba(198, 156, 37, 0.1); border-bottom: 2px solid #C69C25;'><tr>"
    for col in columns:
        # On aligne les textes longs à gauche, les chiffres au centre
        align = "left" if col in ["Joueur", "Nom", "Détails du Match"] else "center"
        html += f"<th style='padding: 12px; text-align: {align}; color: #C69C25; font-size: 0.85em; text-transform: uppercase; letter-spacing: 1px;'>{col}</th>"
    html += "</tr></thead><tbody>"
    
    # Lignes
    for i, row in enumerate(data_list, 1):
        bg_row = "transparent"
        rank_color = "inherit"
        rank_icon = str(row.get("Rang", row.get("Numéro", i)))
        
        # GESTION DU PODIUM (Uniquement si is_ranking est True)
        if is_ranking:
            # On tente de récupérer la vraie valeur du rang si elle existe
            try:
                actual_rank = int(row.get("Rang", i))
            except:
                actual_rank = i
                
            if actual_rank == 1:
                bg_row = "rgba(198, 156, 37, 0.08)" # Or subtil
                rank_color = "#FFD700" 
                rank_icon = "🥇"
            elif actual_rank == 2:
                bg_row = "rgba(224, 255, 255, 0.04)" # Argent très léger
                rank_color = "#E0FFFF"
                rank_icon = "🥈"
            elif actual_rank == 3:
                bg_row = "rgba(205, 127, 50, 0.04)" # Bronze très léger
                rank_color = "#CD7F32"
                rank_icon = "🥉"
            else:
                rank_icon = str(actual_rank)
                
        html += f"<tr style='background-color: {bg_row}; border-bottom: 1px solid rgba(198, 156, 37, 0.15);'>"
        for col in columns:
            val = row.get(col, "")
            align = "left" if col in ["Joueur", "Nom", "Détails du Match"] else "center"
            
            if is_ranking and col in ["Rang", "Numéro"]:
                html += f"<td style='padding: 12px; text-align: {align}; font-weight: bold; color: {rank_color}; font-size: 1.2em;'>{rank_icon}</td>"
            elif col in ["Joueur", "Nom"]:
                html += f"<td style='padding: 12px; text-align: {align}; font-weight: 600;'>{val}</td>"
            else:
                html += f"<td style='padding: 12px; text-align: {align}; opacity: 0.9;'>{val}</td>"
        html += "</tr>"
        
    html += "</tbody></table>"
    return html


def get_rank_info(current_elo, current_rank_id=None):
    # (Ton code ici...)
    strict_rank = None
    for tier in reversed(RANK_TIERS):
        if current_elo >= tier["threshold"]:
            strict_rank = tier
            break
            
    if current_rank_id is None:
        return strict_rank

    if strict_rank["id"] < current_rank_id:
        current_tier = next(t for t in RANK_TIERS if t["id"] == current_rank_id)
        if current_elo >= (current_tier["threshold"] - 25):
            return current_tier 
        else:
            return strict_rank 
    else:
        return strict_rank 

def draw_rank_badge(elo):
    rank = get_rank_info(elo) # Cette fonction utilise RANK_TIERS
    
    # On récupère l'icône (qui est déjà une balise <img> complète en Base64)
    icon_html = rank['icon']
    
    # On l'intègre dans un design plus grand pour le profil
    html = f"""
    <div style="
        background: {rank['bg_gradient']};
        border: 2px solid {rank['color']};
        border-radius: 15px;
        padding: 20px;
        text-align: center;
        box-shadow: {rank.get('glow', '0 0 10px rgba(0,0,0,0.5)')};
        color: white;
    ">
        <div style="transform: scale(2); margin-bottom: 15px;">{icon_html}</div>
        <div style="font-family: 'Playfair Display', serif; font-size: 1.5em; font-weight: bold;">
            {rank['name'].upper()}
        </div>
        <div style="font-size: 1em; opacity: 0.9;">{int(elo)} Elo</div>
    </div>
    """
    return html

def get_badges_html(player, matches_history):
    """
    Génère les badges avec progression visible et infobulles compatibles mobile.
    Version compactée sans retours à la ligne pour éviter les bugs d'affichage.
    """

    # --- 1. CALCUL DES STATS ---
    # 🔴 CORRECTION ICI : On utilise la longueur de l'historique complet pour ne pas être affecté par le reset de saison !
    total_matches = len(matches_history)
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

    # --- Dictionnaire des couleurs magiques ---
    # Tu peux ajuster ces codes couleurs hexadécimaux selon tes goûts
    TIER_COLORS = {
        "bronze": "#cd7f32",
        "silver": "#c0c0c0",
        "gold": "#ffd700",
        "platinum": "#00e5ff", # Un cyan brillant fait très "Platine/Diamant"
        "magma": "#ff4500",
        "electric": "#ffd700",
        "blood": "#ff0000",
        "locked": "#444444"
    }

    def process_tier_badge(current_val, tiers, base_image_url, label):
        # 🛡️ LE BULLDOZER : Retire guillemets, retours à la ligne et espaces !
        clean_url = base_image_url.replace('"', '').replace("'", "").replace('\n', '').replace('\r', '').replace(' ', '')
        
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
            color = TIER_COLORS.get(style, "#ffffff")
            if next_tier:
                tooltip_text = f"✅ {name}<br>{progress_text}<br><span style='font-size:0.9em; opacity:0.8;'>🎯 Prochain : {next_tier['name']} ({next_tier['req']} {label})</span>"
            else:
                tooltip_text = f"🏆 NIVEAU MAX<br>{name}<br>{progress_text}<br><span style='font-size:0.9em; opacity:0.8;'>Vous êtes une légende !</span>"
            css_class = ""
        else:
            first_tier = tiers[0]
            style = "locked"
            name = first_tier["name"]
            color = TIER_COLORS["locked"]
            tooltip_text = f"🔒 BLOQUÉ<br>{progress_text}<br><span style='font-size:0.9em; opacity:0.8;'>🎯 Objectif : {first_tier['req']} {label}</span>"
            css_class = "locked"

        # 🔴 NOUVEAU DESIGN : Pas de cadre, juste lueur & image plus grosse
        badge_html = f'''<div class="badge-item {css_class}" style="position: relative; display: flex; flex-direction: column; align-items: center; margin: 10px; width: 80px;">
<div style="width: 70px; height: 70px; display: flex; justify-content: center; align-items: center; position: relative;">
<img src="{clean_url}" style="width: 70px; height: 70px; object-fit: contain; filter: drop-shadow(0 0 8px {color});" />
</div>
<div style="font-size: 0.85em; font-weight: bold; margin-top: 8px; color: {color if style != 'locked' else '#888'}; text-transform: uppercase; text-shadow: 1px 1px 2px rgba(0,0,0,0.8); text-align: center;">{name}</div>
<span class="tooltip-content">{tooltip_text}</span>
</div>'''
        html_parts.append(badge_html)
    
    def add_special(cond, style, image_url, name, desc, current_stat=""):
        # 🛡️ LE BULLDOZER
        clean_url = image_url.replace('"', '').replace("'", "").replace('\n', '').replace('\r', '').replace(' ', '')
        
        css_class = "" if cond else "locked"
        color = TIER_COLORS.get(style, "#ffffff") if cond else TIER_COLORS["locked"]
        
        stat_line = f"<br><span style='color: #ff9f43; font-weight:bold;'>{current_stat}</span>" if current_stat else ""
        if cond:
            tooltip_text = f"✅ {name}{stat_line}<br><span style='font-size:0.9em; opacity:0.8;'>{desc}</span>"
        else:
            tooltip_text = f"🔒 BLOQUÉ{stat_line}<br><span style='font-size:0.9em; opacity:0.8;'>Objectif : {desc}</span>"

        # 🔴 PAREIL ICI : Pas d'hexagone, lueur intense & image grosse
        badge_html = f'''<div class="badge-item {css_class}" style="position: relative; display: flex; flex-direction: column; align-items: center; margin: 10px; width: 80px;">
<div style="width: 70px; height: 70px; display: flex; justify-content: center; align-items: center; position: relative;">
<img src="{clean_url}" style="width: 70px; height: 70px; object-fit: contain; filter: drop-shadow(0 0 8px {color});" />
</div>
<div style="font-size: 0.85em; font-weight: bold; margin-top: 8px; color: {color if cond else '#888'}; text-transform: uppercase; text-shadow: 1px 1px 2px rgba(0,0,0,0.8); text-align: center;">{name}</div>
<span class="tooltip-content">{tooltip_text}</span>
</div>'''
        html_parts.append(badge_html)

    # --- 3. DÉFINITION DES PALIERS ---
    
    # 1. Palier Fidélité (Matchs)
    tiers_fidelity = [
        {"req": 10, "style": "bronze", "name": "Rookie"},
        {"req": 50, "style": "silver", "name": "Confirmé"},
        {"req": 100, "style": "gold", "name": "Pilier"},
        {"req": 200, "style": "platinum", "name": "Légende"},
    ]
    process_tier_badge(total_matches, tiers_fidelity, BADGES_B64["fidelite"], "matchs")

    # 2. Palier Victoire
    tiers_victory = [
        {"req": 10, "style": "bronze", "name": "Gâchette"},
        {"req": 25, "style": "silver", "name": "Conquérant"},
        {"req": 50, "style": "gold", "name": "Champion"},
        {"req": 100, "style": "platinum", "name": "Invincible"},
    ]
    process_tier_badge(wins, tiers_victory, BADGES_B64["victoire"], "victoires")

    # 3. Palier Duo
    tiers_duo = [
        {"req": 10, "style": "bronze", "name": "Binôme"},
        {"req": 30, "style": "silver", "name": "Frères d'armes"},
        {"req": 60, "style": "gold", "name": "Fusion"},
        {"req": 120, "style": "platinum", "name": "Symbiose"},
    ]
    process_tier_badge(max_duo_matches, tiers_duo, BADGES_B64["duo"], "matchs ensemble")

    # 4. Palier Social
    tiers_social = [
        {"req": 5, "style": "bronze", "name": "Explorateur"},
        {"req": 10, "style": "silver", "name": "Voyageur"},
        {"req": 20, "style": "gold", "name": "Monde"},
        {"req": 40, "style": "platinum", "name": "Universel"},
    ]
    process_tier_badge(nb_unique, tiers_social, BADGES_B64["social"], "adversaires")

    # 5. Badges Spéciaux
    add_special(
        current_streak >= 5,
        "magma",
        BADGES_B64["on_fire"],
        "On Fire",
        "Série de 5 victoires",
        f"Série : {current_streak}",
    )
    add_special(
        has_marathon,
        "electric",
        BADGES_B64["marathon"],
        "Marathon",
        "10 matchs en 1 jour",
        f"Record jour : {max_daily_matches}",
    )
    add_special(
        has_giant_kill,
        "blood",
        BADGES_B64["tueur"],
        "Tueur",
        "Battre un +200 Elo",
        "Accompli !" if has_giant_kill else "Pas encore...",
    )

    container_style = "display: flex; flex-wrap: wrap; justify-content: center; gap: 4px; background: rgba(20, 20, 30, 0.4); padding: 15px; border-radius: 16px; border: 1px solid rgba(255,255,255,0.05); box-shadow: 0 4px 20px rgba(0,0,0,0.3);"
    return f'<div style="{container_style}">{"".join(html_parts)}</div>'
    
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
                if auth_success:
                    st.session_state.logout_clicked = False
                    st.success("Connexion réussie !")
                    st.rerun()
                    
        # --- NOUVEAU : BOUTON VISITEUR ---
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
        
        # --- NOUVEAU : MOT DE PASSE OUBLIÉ ---
        with st.expander("Mot de passe oublié ?"):
            st.info("Entrez votre email. Nous vous enverrons un lien pour vous connecter et changer votre mot de passe.")
            reset_email = st.text_input("Votre adresse email", key="reset_email_input")
            
            if st.button("Envoyer le lien de récupération", type="secondary"):
                if not reset_email:
                    st.warning("Veuillez entrer une adresse email.")
                else:
                    success, msg = db.send_password_reset(reset_email)
                    if success:
                        st.success("📧 Email envoyé ! Vérifiez vos spams. Cliquez sur le lien dans l'email pour revenir ici.")
                    else:
                        st.error(msg)

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
                title, msg = "🚀 NOUVEAU GRADE 1V1 !", f"Incroyable ! Vous montez en grade Solo : <b>{new_r['name']}</b>"
            elif is_demote:
                title, msg = "📉 Rétrogradation 1v1", "Courage ! Un mauvais passage en Solo, mais vous allez remonter."
            elif is_gain:
                st.balloons()
                title, msg = "🎊 Nouveaux résultats 1v1 !", "Félicitations ! Vos points Solo ont été mis à jour."
            else:
                title, msg = "📊 Résultats mis à jour (1v1)", "Vos derniers matchs Solo ont été enregistrés."

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
                
            st.stop() # On bloque ici tant que le 1v1 n'est pas validé

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
                title, msg = "🚀 NOUVEAU GRADE 2V2 !", f"Incroyable ! Vous montez en grade Duo : <b>{new_r_2v2['name']}</b>"
            elif is_demote_2v2:
                title, msg = "📉 Rétrogradation 2v2", "Courage ! Un mauvais passage en Duo, mais l'équipe va se reprendre."
            elif is_gain_2v2:
                st.balloons()
                title, msg = "🎊 Nouveaux résultats 2v2 !", "Félicitations ! Vos points Duo ont été mis à jour."
            else:
                title, msg = "📊 Résultats mis à jour (2v2)", "Vos derniers matchs Duo ont été enregistrés."

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
                
            st.stop() # On bloque ici tant que le 2v2 n'est pas validé
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
# 1. Affichage du Logo Panda (Assure-toi que l'image s'appelle 'logo.jpg' et est dans le même dossier)
try:
    # On ajoute un peu d'espace avant et après le logo pour que ça respire
    st.sidebar.write("") 
    st.sidebar.image("panda_logo.png", use_container_width=True)
    st.sidebar.write("")
except Exception:
    # Sécurité : Si l'image n'est pas trouvée, on remet l'ancien texte au lieu de faire planter l'appli
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

st.sidebar.write("") # Un petit espace pour respirer avant la suite

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
            else:
                target_elo = "elo_2v2"
                target_matches = "matches_2v2"

            df = pd.DataFrame(res.data)
            df = df[df[target_matches] > 0] # Uniquement les actifs

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
                    rank_info = get_rank_info(joueur_elo)
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
                
                # Boucle sécurisée qui s'adapte au nom exact de tes colonnes d'archives
                for index, row in enumerate(archive_data):
                    # Cherche la valeur Elo sous différents noms possibles
                    score_elo = row.get("final_elo", row.get("elo", row.get("elo_rating", 1000)))
                    
                    # Cherche le nombre de matchs
                    nb_matchs = row.get("matches_played", row.get("final_matches", 0))
                    
                    # Cherche le rang final
                    final_rank = row.get("final_rank", index + 1)
                    
                    rank_info = get_rank_info(score_elo)
                    
                    list_arch.append({
                        "Rang": final_rank,
                        "Joueur": f"<div style='display: flex; align-items: center; gap: 10px;'>{rank_info['icon']} <span>{row.get('username', 'Inconnu')}</span></div>",
                        "Points Elo": f"<b>{int(score_elo)}</b> <span style='color: #a0aec0;'>pts</span>",
                        "Matchs Joués": f"{int(nb_matchs)} 🎮"
                    })
                
                # Tri de sécurité en Python au cas où le tri Supabase aurait échoué
                list_arch = sorted(list_arch, key=lambda x: int(x["Rang"]))
                
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
    
    # 1. On affiche d'abord le Badge
    badge_html = draw_rank_badge(target_elo)
    st.markdown(badge_html, unsafe_allow_html=True)
    
    # 2. On affiche le Titre juste en dessous - Version Emblème de Rang
    equipped_title = target_user.get("equipped_title")
    if equipped_title:
        # Initialisations par défaut
        rank_color = "#C69C25" # Or Snook'R par défaut
        title_icon = "" # L'emblème du grade ou podium

        # --- 1. DÉTERMINATION DE L'ICÔNE ET DE LA COULEUR ---

        # Cas spéciaux : Le Podium (prioritaire car "Champion" ne commence pas par un rang)
        if "Champion" in equipped_title:
            rank_color = "#FFD700" # Or éclatant
            title_icon = "🥇" # Médaille d'or
        elif "Dauphin" in equipped_title:
            rank_color = "#E0FFFF" # Argent
            title_icon = "🥈" # Médaille d'argent
        elif "3ème" in equipped_title:
            rank_color = "#CD7F32" # Bronze
            title_icon = "🥉" # Médaille de bronze
        else:
            # Cas normal : Les Grades (on cherche du plus HAUT au plus BAS dans RANK_TIERS)
            found_rank = False
            for tier in reversed(RANK_TIERS):
                if equipped_title.startswith(tier["name"]):
                    rank_color = tier.get("color", "#C69C25")
                    # 🔴 ICI : On récupère l'icône définie dans ranks_config.py
                    title_icon = tier.get("icon", "🔰") # Fallback si pas d'icône définie
                    found_rank = True
                    break
            
            # Si vraiment aucun rang trouvé dans config (peu probable), icône générique
            if not found_rank:
                title_icon = "🔰" # Icône de rang par défaut

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
        if not cfg: return ""
        
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
                rank_text = f"{rank}{'er' if rank==1 else 'ème'}" if rank in [1, 2, 3] else f"Top {rank}"
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
                html_list_w += f"<div style='padding: 10px 0; border-bottom: 1px solid rgba(255,255,255,0.1); display: flex; align-items: center;'>{icon}<span><b>{rank}{'er' if rank==1 else 'ème'}</b> <span style='opacity: 0.6;'>au</span> <i style='color: #C69C25;'>{t_name}</i> <span style='opacity: 0.4; font-size: 0.85em; margin-left: 6px;'>({t_date})</span></span></div>"
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
            if not s_matches and s_name != "🔥 Saison en cours": continue
            
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
        .in_("status", ["validated", "archived"]) # CORRECTION ICI : Historique All-Time !
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
            gain = 0
            loss = 0

            # --- Logique 1v1 ---
            if mode == "1v1":
                w_id, l_id = m["winner_id"], m["loser_id"]
                if w_id in temp_elo_1v1 and l_id in temp_elo_1v1:
                    # ON RÉCUPÈRE LES 4 VALEURS ICI (gain ET loss)
                    new_w, new_l, gain, loss = engine.compute_new_ratings(
                        temp_elo_1v1[w_id], temp_elo_1v1[l_id], 
                        matches_1v1[w_id], matches_1v1[l_id] # On passe le nombre de matchs pour le K-factor
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

                    # ON RÉCUPÈRE LES 4 VALEURS ICI AUSSI
                    _, _, gain, loss = engine.compute_new_ratings(w_avg, l_avg, 0, 0)

                    for pid in [m["winner_id"], m["winner2_id"]]:
                        temp_elo_2v2[pid] += gain
                        matches_2v2[pid] += 1
                    for pid in [m["loser_id"], m["loser2_id"]]:
                        temp_elo_2v2[pid] -= loss
                        matches_2v2[pid] += 1

            # D. Correction de l'historique (elo_gain ET elo_loss)
            stored_gain = m.get("elo_gain", 0)
            # On vérifie si la DB doit être mise à jour
            if abs(stored_gain - gain) > 0.01:
                db.supabase.table("matches").update({
                    "elo_gain": gain, 
                    "elo_loss": loss # On en profite pour remplir la nouvelle colonne loss
                }).eq("id", m["id"]).execute()
                corrected_matches += 1

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
                            if clean_t != t: has_changed = True
                    
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
                        if not prof: continue
                        titles = prof.get("unlocked_titles", [])
                        if titles is None: titles = []
                        
                        clean_titles = [t for t in titles if not ("Mars 2026" in t and (m_lbl in t or "Solo" not in t and "Duo" not in t))]
                        needs_update = False
                        
                        if f_matches > 1:
                            r_name = "Novice"
                            for tier in reversed(RANK_TIERS):
                                if f_elo >= tier["threshold"]:
                                    r_name = tier["name"]
                                    break
                            r_title = f"{r_name} {m_lbl} Mars 2026"
                            if r_title not in clean_titles: clean_titles.append(r_title); needs_update = True
                                
                        if f_rank == 1:
                            c_title = f"Champion {m_lbl} de Mars 2026"
                            if c_title not in clean_titles: clean_titles.append(c_title); needs_update = True
                        elif f_rank == 2:
                            d_title = f"Dauphin {m_lbl} de Mars 2026"
                            if d_title not in clean_titles: clean_titles.append(d_title); needs_update = True
                        elif f_rank == 3:
                            p_title = f"3ème {m_lbl} de Mars 2026"
                            if p_title not in clean_titles: clean_titles.append(p_title); needs_update = True
                            
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
                                            if s1 > s2: reg_standings[p1]["V"] += 1
                                            else: reg_standings[p1]["D"] += 1
                                            reg_standings[p1]["Diff"] += (s1 - s2)
                                        if p2 in reg_standings:
                                            if s2 > s1: reg_standings[p2]["V"] += 1
                                            else: reg_standings[p2]["D"] += 1
                                            reg_standings[p2]["Diff"] += (s2 - s1)
                                            
                                tie_matches_all = [m for m in g_matches if m.get("tie_break_round", 0) > 0]
                                for m in tie_matches_all:
                                    if m["status"] == "completed":
                                        s1, s2 = m["score1"], m["score2"]
                                        p1, p2 = m["player1_id"], m["player2_id"]
                                        if p1 in reg_standings:
                                            if s1 > s2: reg_standings[p1]["Tie_V"] += 1
                                            reg_standings[p1]["Tie_Diff"] += (s1 - s2)
                                        if p2 in reg_standings:
                                            if s2 > s1: reg_standings[p2]["Tie_V"] += 1
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
                                        if m["player1_id"]: tie_players.add(m["player1_id"])
                                        if m["player2_id"]: tie_players.add(m["player2_id"])
                                        
                                    tie_standings = {}
                                    for uid in tie_players:
                                        tie_standings[uid] = {"Nom": all_users_spec.get(uid, "?"), "V": 0, "D": 0, "Diff": 0}
                                        
                                    for m in tie_matches:
                                        if m["status"] == "completed":
                                            s1, s2 = m["score1"], m["score2"]
                                            p1, p2 = m["player1_id"], m["player2_id"]
                                            if p1 in tie_standings:
                                                if s1 > s2: tie_standings[p1]["V"] += 1
                                                else: tie_standings[p1]["D"] += 1
                                                tie_standings[p1]["Diff"] += (s1 - s2)
                                            if p2 in tie_standings:
                                                if s2 > s1: tie_standings[p2]["V"] += 1
                                                else: tie_standings[p2]["D"] += 1
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
                                    if not r_matches: continue
                                    
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
                                            match_html += f"<div style='flex: 0 0 80px; text-align: center; color: #555; font-size: 0.9em; font-style: italic;'>vs ⏳</div>"
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
                            bg_color = "rgba(15, 23, 42, 0.9)" # Bleu nuit profond
                            border_color = "#C69C25" if is_gf else ("#CD7F32" if is_pf else "rgba(198, 156, 37, 0.4)")
                            
                            c_html = f"<div style='background: {bg_color}; border: 1px solid {border_color}; border-radius: 8px; padding: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); margin: 5px 0;'>"
                            c_html += f"<div style='font-size: 10px; color: rgba(198, 156, 37, 0.7); text-align: center; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 1px;'>Match {m_num}</div>"
                            
                            if m:
                                p1 = all_users_spec.get(m.get("player1_id"), "...") if m.get("player1_id") else "..."
                                p2 = all_users_spec.get(m.get("player2_id"), "...") if m.get("player2_id") else "..."
                                s1, s2 = m.get("score1", 0), m.get("score2", 0)
                                
                                if m["status"] == "completed":
                                    podium_1_c = "#C69C25" # Or Snook'R
                                    podium_2_c = "#E0FFFF" # Argent
                                    podium_3_c = "#CD7F32" # Bronze
                                    
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
                                        c1_score = "#C69C25" if s1 > s2 else "#888" # Score gagnant en Or
                                        c2_score = "#C69C25" if s2 > s1 else "#888"
                                else:
                                    w1 = w2 = "normal; color: white;"
                                    c1_score = c2_score = "transparent"
                                    if p1 == "..." and p2 == "...": s1 = s2 = ""
                                    
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
                                
                                if is_final_col: col_title = "👑 Grande Finale"
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
                            
                            # B. CENTRE (Grande Finale + Petite Finale)
                            html += "<div style='display: flex; flex-direction: column; justify-content: center; flex: 0 0 220px; margin: 0 10px; gap: 40px;'>"
                            
                            html += "<div>"
                            html += f"<div style='text-align: center; color: gold; font-weight: bold; margin-bottom: 10px; flex: 0 0 auto;'>👑 Finale</div>"
                            html += get_match_card(total_rounds_wb, 1, is_gf=True)
                            html += "</div>"
                            
                            html += "<div>"
                            html += f"<div style='text-align: center; color: #CD7F32; font-weight: bold; margin-bottom: 10px; flex: 0 0 auto;'>🥉 Petite Finale</div>"
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
                                        if s1 > s2: reg_standings[p1]["V"] += 1
                                        else: reg_standings[p1]["D"] += 1
                                        reg_standings[p1]["Diff"] += (s1 - s2)
                                    if p2 in reg_standings:
                                        if s2 > s1: reg_standings[p2]["V"] += 1
                                        else: reg_standings[p2]["D"] += 1
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
                                    if m["player1_id"]: tie_players.add(m["player1_id"])
                                    if m["player2_id"]: tie_players.add(m["player2_id"])
                                    
                                tie_standings = {}
                                for uid in tie_players:
                                    tie_standings[uid] = {"Nom": all_users.get(uid, "?"), "V": 0, "D": 0, "Diff": 0}
                                    
                                for m in tie_matches:
                                    if m["status"] == "completed":
                                        s1, s2 = m["score1"], m["score2"]
                                        p1, p2 = m["player1_id"], m["player2_id"]
                                        if p1 in tie_standings:
                                            if s1 > s2: tie_standings[p1]["V"] += 1
                                            else: tie_standings[p1]["D"] += 1
                                            tie_standings[p1]["Diff"] += (s1 - s2)
                                        if p2 in tie_standings:
                                            if s2 > s1: tie_standings[p2]["V"] += 1
                                            else: tie_standings[p2]["D"] += 1
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
                                if not r_matches: continue
                                
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
                                            st.error(msg) # S'affiche en rouge pour alerter l'admin qu'il y a des barrages !
                                        else:
                                            st.success(msg) # S'affiche en vert : la poule est saine.
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
                                            if p1 == "..." and p2 == "...": s1 = s2 = ""
                                            
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
    
    # Vérification du statut Admin avec ta vraie colonne
    is_guest = st.session_state.get("guest_mode", False)
    is_admin = not is_guest and user.get("is_admin", False)

    # ==========================================
    # 🛠️ VUE ADMIN : CRÉATION & GESTION
    # ==========================================
    if is_admin:
        with st.expander("🛠️ Zone Admin : Créer un nouveau Weekly Fun"):
            st.info("Créer un nouveau tournoi placera automatiquement le précédent dans les archives.")
            
            with st.form("form_create_weekly"):
                w_name = st.text_input("Nom du tournoi", placeholder="Ex: Tournoi Main Gauche, Le Défi du Mercredi...")
                w_desc = st.text_area("Description / Règles spéciales", placeholder="Ex: Ce soir, la casse est obligatoire par la bande...")
                
                col1, col2 = st.columns(2)
                with col1:
                    w_max_players = st.number_input("Nombre de places maximum", min_value=4, max_value=64, value=16, step=1)
                with col2:
                    import datetime
                    w_date = st.date_input("Date de l'événement", value=datetime.date.today())
                    
                submitted_weekly = st.form_submit_button("Publier le tournoi 🚀")
                
                if submitted_weekly:
                    if not w_name:
                        st.error("⚠️ Le nom du tournoi est obligatoire.")
                    else:
                        success, msg = db.create_weekly_tournament(w_name, w_desc, w_max_players, w_date)
                        if success:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
                            
        st.divider()

    # ==========================================
    # 📺 VUE SPECTATEUR / JOUEUR : LE TOURNOI EN COURS
    # ==========================================
    
    # On récupère le tournoi actif
    current_weekly = db.get_current_weekly_tournament()
    
    if not current_weekly:
        st.info("🛌 Aucun tournoi Weekly Fun n'est prévu pour le moment. L'admin prépare sûrement le prochain !")
    else:
        # Formatage propre de la date et gestion de la description
        formatted_date = pd.to_datetime(current_weekly['event_date']).strftime('%d/%m/%Y')
        description_text = current_weekly.get('description', '')
        if not description_text:
            description_text = "Aucune règle spéciale pour ce tournoi."

        # Affiche la bannière du tournoi avec le design Premium Snook'R
        st.markdown(
            f"""
<div style='background: linear-gradient(145deg, #0f172a, #1e293b); padding: 25px; border-radius: 12px; border: 1px solid #C69C25; border-left: 8px solid #C69C25; box-shadow: 0 4px 15px rgba(0,0,0,0.4); margin-bottom: 25px;'>
    <h2 style='margin-top: 0; margin-bottom: 15px; color: #C69C25; font-family: "Playfair Display", serif; font-size: 28px; font-weight: bold; letter-spacing: 0.5px;'>
        🏆 {current_weekly['name']}
    </h2>
    <div style='display: flex; flex-wrap: wrap; gap: 15px; margin-bottom: 20px;'>
        <div style='background-color: rgba(198,156,37,0.1); padding: 8px 15px; border-radius: 8px; color: #e0e0e0; font-weight: 500; font-size: 15px; border: 1px solid rgba(198,156,37,0.2);'>
            📅 Date : <span style='color: #ffffff; font-weight: bold;'>{formatted_date}</span>
        </div>
        <div style='background-color: rgba(198,156,37,0.1); padding: 8px 15px; border-radius: 8px; color: #e0e0e0; font-weight: 500; font-size: 15px; border: 1px solid rgba(198,156,37,0.2);'>
            🎟️ Places : <span style='color: #ffffff; font-weight: bold;'>{current_weekly['max_players']} max</span>
        </div>
    </div>
    <div style='color: #cccccc; font-size: 16px; line-height: 1.5; border-top: 1px dashed rgba(198,156,37,0.3); padding-top: 15px;'>
        <i>{description_text}</i>
    </div>
</div>
            """, 
            unsafe_allow_html=True
        )
        
        # --- 👥 SYSTÈME D'INSCRIPTION ET LISTE D'ATTENTE ---
        st.subheader("👥 Joueurs Inscrits")
        
        # 1. On récupère tous les joueurs inscrits à ce tournoi
        participants = db.get_weekly_participants(current_weekly['id'])
        max_p = current_weekly['max_players']

        # --- 🛠️ MODÉRATION ADMIN (AJOUTER / SUPPRIMER) ---
        if is_admin:
            with st.expander("🛠️ Modération de la liste"):
                col_add, col_rem = st.columns(2)
                
                with col_add:
                    st.write("**Ajouter un joueur (Forcer)**")
                    # On récupère tous les profils pour le menu déroulant
                    all_p_res = db.get_leaderboard()
                    if all_p_res.data:
                        player_names = [p['username'] for p in all_p_res.data]
                        target_name = st.selectbox("Sélectionner un joueur", player_names, key="admin_add_select")
                        if st.button("Ajouter manuellement"):
                            # On trouve l'ID correspondant au nom
                            target_id = next(p['id'] for p in all_p_res.data if p['username'] == target_name)
                            db.register_weekly(current_weekly['id'], target_id)
                            st.success(f"Ajout de {target_name} réussi !")
                            st.rerun()
                
                with col_rem:
                    st.write("**Retirer un joueur**")
                    if not participants:
                        st.write("Aucun joueur à retirer.")
                    else:
                        # On liste les gens actuellement dans le tournoi
                        current_p_names = [p.get('profiles', {}).get('username', 'Inconnu') for p in participants]
                        rem_name = st.selectbox("Joueur à expulser", current_p_names, key="admin_rem_select")
                        if st.button("Expulser du tournoi", type="secondary"):
                            # On trouve l'ID correspondant
                            rem_id = next(p['user_id'] for p in participants if p.get('profiles', {}).get('username') == rem_name)
                            db.admin_remove_participant(current_weekly['id'], rem_id)
                            st.warning(f"{rem_name} a été retiré.")
                            st.rerun()
        
        # 2. Le script coupe la liste en deux selon la limite de places
        main_list = participants[:max_p]
        wait_list = participants[max_p:]
        
        # 3. Est-ce que le joueur qui regarde la page est dedans ?
        is_registered = False
        if not is_guest:
            is_registered = any(p['user_id'] == user['id'] for p in participants)
        
        # 4. Le bouton d'action magique
        col_btn, _ = st.columns([1, 2])
        with col_btn:
            if is_guest:
                st.info("🔒 Connectez-vous pour vous inscrire.")
            else:
                if is_registered:
                    if st.button("❌ Se désinscrire", type="secondary", use_container_width=True):
                        db.unregister_weekly(current_weekly['id'], user['id'])
                        st.rerun()
                else:
                    # Le texte du bouton s'adapte s'il n'y a plus de place
                    btn_text = "✅ S'inscrire" if len(participants) < max_p else "⏳ Rejoindre la file d'attente"
                    if st.button(btn_text, type="primary", use_container_width=True):
                        db.register_weekly(current_weekly['id'], user['id'])
                        st.rerun()

        st.write("") # Petit espace
        
        # 5. Affichage propre des deux listes
        col_main, col_wait = st.columns(2)
        
        with col_main:
            st.markdown(f"#### 📋 Liste Principale ({len(main_list)}/{max_p})")
            if not main_list:
                st.write("Aucun inscrit pour le moment.")
            else:
                for i, p in enumerate(main_list):
                    # On affiche le joueur en gras si c'est "nous"
                    username = p.get('profiles', {}).get('username', 'Inconnu')
                    if not is_guest and p['user_id'] == user['id']:
                        st.markdown(f"**{i+1}. {username} (Vous)**", help="Vous êtes qualifié d'office !")
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
                        st.markdown(f"**{max_p + i + 1}. {username} (Vous)**", help="Si quelqu'un se désiste, vous montez !")
                    else:
                        st.caption(f"{max_p + i + 1}. {username}")

        # ==========================================
        # 👑 PANNEAU DE CONTRÔLE ADMIN (Tournoi Actif)
        # ==========================================
        if is_admin:
            st.divider()
            st.subheader("👑 Panneau de Clôture (Admin)")
            
            if not participants:
                st.info("Impossible de clôturer un tournoi sans participants.")
            else:
                with st.expander("🏆 Saisir le classement final et clôturer", expanded=False):
                    st.warning("⚠️ Attention : Une fois clôturé, le tournoi sera archivé et les badges seront distribués. Cette action est définitive.")
                    
                    with st.form("form_close_weekly"):
                        st.write("Indiquez la position finale de chaque joueur (1 pour le vainqueur, 2, 3, etc.) :")
                        
                        # Dictionnaire pour stocker les résultats saisis
                        rank_inputs = {}
                        
                        # On crée une ligne par joueur pour saisir son rang
                        for p in participants:
                            u_name = p.get('profiles', {}).get('username', 'Inconnu')
                            u_id = p['user_id']
                            
                            # On met 0 par défaut (il faudra que l'admin change la valeur)
                            rank_inputs[u_id] = st.number_input(f"Rang pour {u_name}", min_value=1, max_value=len(participants), value=1, key=f"rank_{u_id}")
                            
                        submit_close = st.form_submit_button("Clôturer le Tournoi 🔒", type="primary")
                        
                        if submit_close:
                            success, msg = db.close_weekly_tournament(current_weekly['id'], rank_inputs)
                            if success:
                                st.success(msg)
                                st.rerun()
                            else:
                                st.error(msg)
    # ==========================================
    # 🗄️ SECTION ARCHIVES : LES ANCIENS WEEKLY FUNS
    # ==========================================
    st.divider()
    st.header("🗄️ Les Archives du Fun")
    
    past_weeklys = db.get_past_weekly_tournaments()
    
    if not past_weeklys:
        st.info("Aucune archive pour le moment. Le premier Weekly Fun est encore en cours ou n'a pas commencé !")
    else:
        # 1. Création du menu déroulant
        import pandas as pd
        weekly_options = {}
        for pt in past_weeklys:
            date_str = pd.to_datetime(pt['event_date']).strftime('%d/%m/%Y')
            # Format du nom dans le menu : "25/03/2026 - Le roi de la visée"
            weekly_options[f"{date_str} - {pt['name']}"] = pt
            
        selected_weekly_name = st.selectbox("Sélectionnez un ancien tournoi :", list(weekly_options.keys()))
        selected_weekly = weekly_options[selected_weekly_name]
        
        # 2. Affichage des détails du tournoi sélectionné
        st.markdown(f"**Description :** *{selected_weekly.get('description', 'Aucune règle spéciale.')}*")
        
        p_participants = db.get_weekly_participants(selected_weekly['id'])
        
        if not p_participants:
            st.write("Aucun joueur n'avait participé à cette édition.")
        else:
            p_participants_sorted = sorted(p_participants, key=lambda x: x.get('final_rank', 999))
            
            st.markdown("### 🏆 Classement Final")
            
            # Préparation des données pour notre belle fonction
            archive_data = []
            for index, p in enumerate(p_participants_sorted, start=1):
                p_name = p.get('profiles', {}).get('username', 'Inconnu')
                display_rank = p.get('final_rank', index)
                archive_data.append({
                    "Rang": display_rank,
                    "Joueur": p_name
                })
            
            # Affichage majestueux
            st.markdown(draw_luxury_table(archive_data), unsafe_allow_html=True)
            st.write("") # Petit espace pour respirer

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