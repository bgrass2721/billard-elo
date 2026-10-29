def draw_luxury_table(data_list, title=None, columns=None, is_ranking=True):
    """Génère un tableau HTML au design 'Snook'R Héraldique' avec option podium"""
    if not data_list:
        return ""

    html = ""
    if title:
        html += (
            f"<h4 style=\"font-family: 'Playfair Display', serif; color: #C69C25; "
            f"margin-bottom: 15px; margin-top: 20px;\">{title}</h4>"
        )

    html += (
        "<table style='width: 100%; border-collapse: collapse; margin-bottom: 25px; "
        "background: rgba(255,255,255, 0.03); border-radius: 8px; overflow: hidden; "
        "border: 1px solid rgba(198, 156, 37, 0.3);'>"
    )

    # En-tête
    if not columns:
        columns = list(data_list[0].keys())

    html += (
        "<thead style='background-color: rgba(198, 156, 37, 0.1); "
        "border-bottom: 2px solid #C69C25;'><tr>"
    )
    for col in columns:
        # On aligne les textes longs à gauche, les chiffres au centre
        align = "left" if col in ["Joueur", "Nom", "Détails du Match"] else "center"
        html += (
            f"<th style='padding: 12px; text-align: {align}; color: #C69C25; "
            f"font-size: 0.85em; text-transform: uppercase; letter-spacing: 1px;'>{col}</th>"
        )
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
            except (ValueError, TypeError):
                actual_rank = i

            if actual_rank == 1:
                bg_row = "rgba(198, 156, 37, 0.08)"  # Or subtil
                rank_color = "#FFD700"
                rank_icon = "🥇"
            elif actual_rank == 2:
                bg_row = "rgba(224, 255, 255, 0.04)"  # Argent très léger
                rank_color = "#E0FFFF"
                rank_icon = "🥈"
            elif actual_rank == 3:
                bg_row = "rgba(205, 127, 50, 0.04)"  # Bronze très léger
                rank_color = "#CD7F32"
                rank_icon = "🥉"
            else:
                rank_icon = str(actual_rank)

        html += (
            f"<tr style='background-color: {bg_row}; "
            f"border-bottom: 1px solid rgba(198, 156, 37, 0.15);'>"
        )
        for col in columns:
            val = row.get(col, "")
            align = "left" if col in ["Joueur", "Nom", "Détails du Match"] else "center"

            if is_ranking and col in ["Rang", "Numéro"]:
                html += (
                    f"<td style='padding: 12px; text-align: {align}; font-weight: bold; "
                    f"color: {rank_color}; font-size: 1.2em;'>{rank_icon}</td>"
                )
            elif col in ["Joueur", "Nom"]:
                html += (
                    f"<td style='padding: 12px; text-align: {align}; font-weight: 600;'>{val}</td>"
                )
            else:
                html += f"<td style='padding: 12px; text-align: {align}; opacity: 0.9;'>{val}</td>"
        html += "</tr>"

    html += "</tbody></table>"
    return html
