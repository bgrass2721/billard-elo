set_style = """
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
"""
