from textwrap import dedent

import pandas as pd

from badges_config import BADGES_B64


def get_badges_html(player, matches_history):
    """
    Génère les badges avec progression visible et infobulles compatibles mobile.
    Version compactée sans retours à la ligne pour éviter les bugs d'affichage.
    """

    # --- 1. CALCUL DES STATS ---
    # 🔴 CORRECTION ICI : On utilise la longueur de l'historique complet
    # pour ne pas être affecté par le reset de saison !
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
        "platinum": "#00e5ff",  # Un cyan brillant fait très "Platine/Diamant"
        "magma": "#ff4500",
        "electric": "#ffd700",
        "blood": "#ff0000",
        "locked": "#444444"
    }

    def process_tier_badge(current_val, tiers, base_image_url, label):
        # 🛡️ LE BULLDOZER : Retire guillemets, retours à la ligne et espaces !
        clean_url = base_image_url.replace('"', '').replace("'", "").replace('\n', '')
        clean_url = clean_url.replace('\r', '').replace(' ', '')

        achieved_tier = None
        next_tier = None
        for tier in tiers:
            if current_val >= tier["req"]:
                achieved_tier = tier
            else:
                next_tier = tier
                break

        progress_text = (
            f"<span style='color: #4db8ff; font-weight:bold;'>📊 Actuel : {current_val}</span>"
        )

        if achieved_tier:
            style = achieved_tier["style"]
            name = achieved_tier["name"]
            color = TIER_COLORS.get(style, "#ffffff")
            if next_tier:
                tooltip_text = (
                    f"✅ {name}<br>{progress_text}<br><span style='font-size:0.9em; "
                    f"opacity:0.8;'>🎯 "
                    f"Prochain : {next_tier['name']} ({next_tier['req']} {label})</span>"
                )
            else:
                tooltip_text = (
                    f"🏆 NIVEAU MAX<br>{name}<br>{progress_text}<br><span style='font-size:0.9em; "
                    f"opacity:0.8;'>Vous êtes une légende !</span>"
                )
            css_class = ""
        else:
            first_tier = tiers[0]
            style = "locked"
            name = first_tier["name"]
            color = TIER_COLORS["locked"]
            tooltip_text = (
                f"🔒 BLOQUÉ<br>{progress_text}<br><span style='font-size:0.9em; "
                f"opacity:0.8;'>🎯 Objectif : {first_tier['req']} {label}</span>"
            )
            css_class = "locked"

        # 🔴 NOUVEAU DESIGN : Pas de cadre, juste lueur & image plus grosse
        badge_html = dedent(f'''
            <div
                class="badge-item {css_class}"
                style="
                    position: relative;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    margin: 10px;
                    width: 80px;
                "
            >
                <div
                    style="
                        width: 70px;
                        height: 70px;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        position: relative;
                    "
                >
                    <img
                        src="{clean_url}"
                        style="
                            width: 70px;
                            height: 70px;
                            object-fit: contain;
                            filter: drop-shadow(0 0 8px {color});
                        "
                    />
                </div>

                <div
                    style="
                        font-size: 0.85em;
                        font-weight: bold;
                        margin-top: 8px;
                        color: {color if style != 'locked' else '#888'};
                        text-transform: uppercase;
                        text-shadow: 1px 1px 2px rgba(0,0,0,0.8);
                        text-align: center;
                    "
                >
                    {name}
                </div>
                <span class="tooltip-content">{tooltip_text}</span>
            </div>
        ''')
        html_parts.append(badge_html)

    def add_special(cond, style, image_url, name, desc, current_stat=""):
        # 🛡️ LE BULLDOZER
        clean_url = image_url.replace('"', '').replace("'", "").replace('\n', '')
        clean_url = clean_url.replace('\r', '').replace(' ', '')

        css_class = "" if cond else "locked"
        color = TIER_COLORS.get(style, "#ffffff") if cond else TIER_COLORS["locked"]

        stat_line = ""
        if current_stat:
            stat_line = f"<br><span style='color: #ff9f43; font-weight:bold;'>{current_stat}</span>"
        if cond:
            tooltip_text = (
                f"✅ {name}{stat_line}<br><span style='font-size:0.9em; opacity:0.8;'>{desc}</span>"
            )
        else:
            tooltip_text = (
                f"🔒 BLOQUÉ{stat_line}<br>"
                f"<span style='font-size:0.9em; opacity:0.8;'>Objectif : {desc}</span>"
            )

        # 🔴 PAREIL ICI : Pas d'hexagone, lueur intense & image grosse
        badge_html = dedent(f'''
            <div
                class="badge-item {css_class}"
                style="
                    position: relative;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    margin: 10px;
                    width: 80px;
                "
            >
                <div
                    style="
                        width: 70px;
                        height: 70px;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        position: relative;
                    "
                >
                    <img
                        src="{clean_url}"
                        style="
                            width: 70px;
                            height: 70px;
                            object-fit: contain;
                            filter: drop-shadow(0 0 8px {color});
                        "
                    />
                </div>

                <div
                    style="
                        font-size: 0.85em;
                        font-weight: bold;
                        margin-top: 8px;
                        color: {color if cond else '#888'};
                        text-transform: uppercase;
                        text-shadow: 1px 1px 2px rgba(0,0,0,0.8);
                        text-align: center;
                    "
                >
                    {name}
                </div>
                <span class="tooltip-content">{tooltip_text}</span>
            </div>
        ''')
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

    container_style = (
        "display: flex; flex-wrap: wrap; justify-content: center; gap: 4px; "
        "background: rgba(20, 20, 30, 0.4); padding: 15px; border-radius: 16px; "
        "border: 1px solid rgba(255,255,255,0.05); box-shadow: 0 4px 20px rgba(0,0,0,0.3);"
    )
    return f'<div style="{container_style}">{"".join(html_parts)}</div>'

    def add_special(cond, shape, style, icon, name, desc, current_stat=""):
        css = "" if cond else "locked"
        stat_line = (
            f"<br><span style='color: #ff9f43; font-weight:bold;'>{current_stat}</span>"
            if current_stat
            else ""
        )
        if cond:
            tooltip_text = (
                f"✅ {name}{stat_line}<br><span style='font-size:0.9em; opacity:0.8;'>{desc}</span>"
            )
        else:
            tooltip_text = (
                f"🔒 BLOQUÉ{stat_line}<br><span "
                f"style='font-size:0.9em; opacity:0.8;'>Objectif : {desc}</span>"
            )

        badge_html = (
            f'<div class="badge-item {css}">'
            f'<div class="badge-icon-box {shape} {style}">{icon}</div>'
            f'<div class="badge-name">{name}</div>'
            f'<span class="tooltip-content">{tooltip_text}</span></div>'
        )
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

    container_style = (
        "display: flex; flex-wrap: wrap; justify-content: center; gap: 4px; "
        "background: rgba(20, 20, 30, 0.4); padding: 15px; border-radius: 16px; "
        "border: 1px solid rgba(255,255,255,0.05); box-shadow: 0 4px 20px rgba(0,0,0,0.3);"
    )
    return f'<div style="{container_style}">{"".join(html_parts)}</div>'
