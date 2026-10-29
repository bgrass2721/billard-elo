from ranks_config import RANK_TIERS


def render_xp_bar(old_elo, new_elo, old_rank_info, new_rank_info):
    """Génère la carte d'XP avec le buffer de survie et remplissage dynamique post-transition."""
    is_promo = new_rank_info["id"] > old_rank_info["id"]
    is_demote = new_rank_info["id"] < old_rank_info["id"]
    is_same = not (is_promo or is_demote)

    # Fonction utilitaire pour calculer le % d'une barre
    def get_pct(val, min_v, max_v):
        if max_v <= min_v:
            return 100
        return max(0, min(100, ((val - min_v) / (max_v - min_v)) * 100))

    # === 1. PARAMÈTRES NOUVEAU RANG ===
    new_base_min = new_rank_info["threshold"]
    new_next = next((t for t in RANK_TIERS if t["id"] == new_rank_info["id"] + 1), None)

    new_display_min = (new_base_min - 25) if new_base_min >= 25 else 0
    new_display_max = new_next["threshold"] if new_next else "MAX"
    new_calc_max = (
        new_display_min + 100 if new_display_max == "MAX" else new_display_max
    )

    is_in_danger = new_elo < new_base_min

    # === 2. PARAMÈTRES ANCIEN RANG ===
    old_base_min = old_rank_info["threshold"]
    old_next = next((t for t in RANK_TIERS if t["id"] == old_rank_info["id"] + 1), None)

    old_display_min = (old_base_min - 25) if old_base_min >= 25 else 0
    old_display_max = old_next["threshold"] if old_next else "MAX"
    old_calc_max = (
        old_display_min + 100 if old_display_max == "MAX" else old_display_max
    )

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
        status_text = new_rank_info["name"]
        status_color = "white"
        border_color = "rgba(198,156,37,0.3)"
        bar_color = new_rank_info["bg_gradient"]
        bar_shadow = new_rank_info["color"]
        anim_pulse = ""

    # === 5. ANIMATIONS CSS CINÉMATIQUES ===
    if is_promo:
        anim_css = (
            f"@keyframes fillOld {{from {{width: {old_start_pct}%;}} "
            f"to {{width: {old_end_pct}%;}}}} @keyframes fillNew "
            f"{{from {{width: {new_start_pct}%;}} to {{width: {new_end_pct}%;}}}} "
            f".bar-phase1 {{animation: fillOld 1.5s ease-in forwards;}} "
            f".bar-phase2 {{width: {new_start_pct}%; "
            f"animation: fillNew 1.5s 1.7s ease-out forwards;}}"
        )
        flash_anim = "flashPromo"
    elif is_demote:
        anim_css = (
            f"@keyframes drainOld {{from {{width: {old_start_pct}%;}} "
            f"to {{width: {old_end_pct}%;}}}} @keyframes "
            f"drainNew {{from {{width: {new_start_pct}%;}} to {{width: {new_end_pct}%;}}}} "
            f".bar-phase1 {{animation: drainOld 1.5s ease-in forwards;}} "
            f".bar-phase2 {{width: {new_start_pct}%; animation: "
            f"drainNew 1.5s 1.7s ease-out forwards;}}"
        )
        flash_anim = "flashDemote"
    else:
        anim_css = (
            f"@keyframes moveBar {{from {{width: {old_start_pct}%;}} "
            f"to {{width: {new_end_pct}%;}}}} "
            f".bar-single {{animation: moveBar 2s ease-out forwards;}} @keyframes "
            f"dangerPulse {{ 0% {{opacity: 1;}} 50% {{opacity: 0.6;}} 100% {{opacity: 1;}} }}"
        )
        flash_anim = "none"

    # === 6. HTML MINIFIÉ ===
    css = f"""
    {anim_css}
    @keyframes fadeOut {{
        0%, 88% {{ opacity: 1; transform: scale(1); }}
        100% {{ opacity: 0; transform: scale(1.3); visibility: hidden; }}
    }}
    @keyframes fadeIn {{
        0%, 88% {{ opacity: 0; transform: scale(0.5); }}
        100% {{ opacity: 1; transform: scale(1); }}
    }}
    @keyframes flashPromo {{
        0%, 45% {{
            border-color: rgba(198,156,37,0.3);
            box-shadow: 0 0 0px transparent;
        }}
        50% {{ border-color: white; box-shadow: 0 0 50px white; }}
        100% {{
            border-color: {new_rank_info["color"]};
            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
        }}
    }}
    @keyframes flashDemote {{
        0%, 45% {{
            border-color: rgba(198,156,37,0.3);
            box-shadow: 0 0 0px transparent;
        }}
        50% {{ border-color: #ff4b2b; box-shadow: 0 0 50px #ff4b2b; }}
        100% {{
            border-color: {new_rank_info["color"]};
            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
        }}
    }}
    .xp-card {{
        width: 100%;
        max-width: 600px;
        margin: 0 auto;
        font-family: 'Montserrat', sans-serif;
        background: #0f172a;
        padding: 40px 30px;
        border-radius: 20px;
        border: 2px solid {border_color};
        text-align: center;
        color: white;
        overflow: hidden;
    }}
    .card-anim-cinematic {{ animation: {flash_anim} 3.5s forwards; }}
    .swap-out {{ animation: fadeOut 1.7s forwards; }}
    .swap-in {{ opacity: 0; animation: fadeIn 1.7s forwards; }}
    .huge-icon img, .huge-icon svg {{
        width: 130px !important;
        height: 130px !important;
        object-fit: contain;
    }}
    .prog-container {{
        width: 100%;
        height: 18px;
        background: #1e293b;
        border-radius: 9px;
        overflow: hidden;
        border: 1px solid #334155;
        position: relative;
        {anim_pulse}
    }}
    .bar-base {{ height: 100%; }}
    """

    html = f"""
    <style>
    {css}
    </style>
    <div class="xp-card {
        "card-anim-cinematic" if not is_same else ""
    }">
    """

    if is_same:
        status_html = f"""
            <div style="display:flex; flex-direction:column; align-items:center;
                        gap:20px; margin-bottom:35px;">
                <div class="huge-icon">{new_rank_info["icon"]}</div>
                <span style="font-weight:900; color:{status_color};
                            font-size:1.8em; text-transform:uppercase;
                            letter-spacing:1px;">{status_text}</span>
            </div>
            <div class="prog-container">
                <div class="bar-base bar-single"
                    style="background:{bar_color};
                            box-shadow:0 0 15px {bar_shadow};"></div>
            </div>
            <div style="display:flex; justify-content:space-between;
                        margin-top:12px; font-size:0.9em;
                        color:#8BA1B5; font-weight:bold;">
                <span>{new_display_min} ELO
                    {"(SURVIE)" if is_in_danger else ""}</span>
                <span>{new_display_max}
                    {" ELO" if new_display_max != "MAX" else ""}</span>
            </div>
        """
    else:
        old_status_color = "#e74c3c" if is_demote else "white"
        new_status_color = "#f1c40f" if is_promo else "#e74c3c"
        transition_text = (
            "⬆️ PROMOTION !" if is_promo else "⬇️ RÉTROGRADATION..."
        )

        old_max_suffix = " ELO" if old_display_max != "MAX" else ""
        new_max_suffix = " ELO" if new_display_max != "MAX" else ""
        danger_suffix = "(SURVIE)" if is_in_danger else ""

        status_html = f"""
            <div style="display:grid; grid-template-columns:1fr;">
                <div style="grid-row:1; grid-column:1; z-index:2;"
                    class="swap-out">
                    <div style="display:flex; flex-direction:column;
                                align-items:center; gap:20px;
                                margin-bottom:35px;">
                        <div class="huge-icon">{old_rank_info["icon"]}</div>
                        <span style="font-weight:900; color:{old_status_color};
                                    font-size:1.8em; text-transform:uppercase;
                                    letter-spacing:1px;">
                            {old_rank_info["name"]}
                        </span>
                    </div>
                    <div class="prog-container">
                        <div class="bar-base bar-phase1"
                            style="background:{old_rank_info["bg_gradient"]};
                                    box-shadow:0 0 15px {old_rank_info["color"]};">
                        </div>
                    </div>
                    <div style="display:flex; justify-content:space-between;
                                margin-top:12px; font-size:0.9em;
                                color:#8BA1B5; font-weight:bold;">
                        <span>{old_display_min} ELO</span>
                        <span>{old_display_max}{old_max_suffix}</span>
                    </div>
                </div>

                <div style="grid-row:1; grid-column:1; z-index:3;"
                    class="swap-in">
                    <div style="display:flex; flex-direction:column;
                                align-items:center; gap:20px;
                                margin-bottom:35px;">
                        <div class="huge-icon">{new_rank_info["icon"]}</div>
                        <span style="font-weight:900; color:{new_status_color};
                                    font-size:1.8em; text-transform:uppercase;
                                    letter-spacing:1px;">
                            {transition_text}
                        </span>
                    </div>
                    <div class="prog-container">
                        <div class="bar-base bar-phase2"
                            style="background:{new_rank_info["bg_gradient"]};
                                    box-shadow:0 0 15px {new_rank_info["color"]};">
                        </div>
                    </div>
                    <div style="display:flex; justify-content:space-between;
                                margin-top:12px; font-size:0.9em;
                                color:#8BA1B5; font-weight:bold;">
                        <span>{new_display_min} ELO {danger_suffix}</span>
                        <span>{new_display_max}{new_max_suffix}</span>
                    </div>
                </div>
            </div>
        """

    html += status_html

    html += f"""
        <div style="margin-top:40px; position:relative; z-index:5;">
            <div style="font-family:'Playfair Display',serif;
                        font-size:3.2em; font-weight:bold;">
                {int(new_elo)}
                <span style="font-size:0.3em; color:#C69C25;">ELO</span>
            </div>
            <div style="color:{color_pts}; font-weight:900;
                        font-size:1.6em; margin-top:5px;">
                {diff:+} PTS
            </div>
        </div>
    </div>
    """
    return html.replace("\n", "")
