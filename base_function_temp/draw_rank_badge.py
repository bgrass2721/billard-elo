from base_function_temp.get_rank_info import get_rank_info


def draw_rank_badge(elo, current_rank_id=None):
    rank = get_rank_info(
        elo, current_rank_id
    )  # On passe l'ID actuel pour activer le bouclier !

    # On récupère l'icône (qui est déjà une balise <img> complète en Base64)
    icon_html = rank["icon"]

    # On l'intègre dans un design plus grand pour le profil
    html = f"""
    <div style="
        background: {rank["bg_gradient"]};
        border: 2px solid {rank["color"]};
        border-radius: 15px;
        padding: 20px;
        text-align: center;
        box-shadow: {rank.get("glow", "0 0 10px rgba(0,0,0,0.5)")};
        color: white;
    ">
        <div style="transform: scale(2); margin-bottom: 15px;">{icon_html}</div>
        <div style="font-family: 'Playfair Display', serif; font-size: 1.5em; font-weight: bold;">
            {rank["name"].upper()}
        </div>
        <div style="font-size: 1em; opacity: 0.9;">{int(elo)} Elo</div>
    </div>
    """
    return html
