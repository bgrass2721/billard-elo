import streamlit as st

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
