# 🎱 BlackBall Compétition - Système de Classement Elo

Bienvenue sur l'application officielle de classement pour notre club de billard ! Ce projet permet de suivre les performances des joueurs en temps réel grâce à un algorithme de calcul Elo personnalisé.

## 🚀 Fonctionnalités principales

* **🏆 Leaderboard en temps réel** : Visualisez le tableau des joueurs triés par leur score Elo.
* **🎯 Déclaration Simplifiée** : Enregistrez vos victoires directement depuis votre smartphone au bord du tapis.
* **📑 Double Validation** : Pour garantir l'équité, l'adversaire doit confirmer sa défaite avant que les points ne soient transférés.
* **⚖️ Gestion des Litiges** : Un système intégré permet de rejeter une erreur de saisie ou de déclarer un litige pour intervention admin.
* **🔧 Panel Administration** : Accès réservé pour révoquer des matchs ou trancher les conflits.
* **💾 Session Persistante** : Grâce à une gestion avancée des cookies et de Supabase Auth, vous restez connecté même après avoir rafraîchi la page ou fermé votre navigateur.

## 🛠️ Installation et Configuration

### Prérequis
* Python 3.10+
* Un compte [Supabase](https://supabase.com) (Base de données et Authentification)
* Un compte [Streamlit Cloud](https://share.streamlit.io) pour l'hébergement

### Installation locale

1. **Cloner le projet** :
   ```bash
   git clone https://github.com/bgrass2721/Billard-Elo.git
   cd Billard-Elo
   ```

2. **Installer les dépendances** :
   ```bash
   pip install -r requirements.txt
   ```

3. **Configurer les secrets** :
   Créez un dossier `.streamlit` et un fichier `secrets.toml` à la racine de votre projet avec le contenu suivant :
   ```toml
   SUPABASE_URL = "votre_url_supabase"
   SUPABASE_KEY = "votre_cle_anon"
   INVITE_CODE = "votre_code_secret"
   ```

## 🔒 Sécurité

* **Code d'invitation** : L'inscription est protégée par un code secret (stocké dans les secrets) pour éviter les utilisateurs inconnus sur l'application.
* **Secrets Streamlit** : Toutes les clés d'API sont stockées de manière sécurisée dans l'interface de Streamlit Cloud et ne sont jamais exposées dans le code source public.
* **Authentification Supabase** : Gestion sécurisée des identifiants et des sessions utilisateurs.

## 📈 Calcul des points

Le système utilise un calcul Elo dynamique :
* Le gain de points dépend de la différence de niveau (Elo) entre les deux joueurs.
* Un joueur qui bat un adversaire beaucoup plus fort gagnera plus de points.
* Les points ne sont mis à jour qu'une fois le match validé par le perdant pour garantir l'intégrité des données.

## 👨‍💻 Auteur
Développé par **Benjamin GRASS**.

[REVIEW en cours. Des perturbations peuvent se présenter]