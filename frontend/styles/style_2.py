set_style_2 = """
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
    """