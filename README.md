Application d'Aide à la Décision Marketing : Cohortes, RFM & CLV

Présentation du Projet

Ce projet vise à construire une application interactive d'aide à la décision pour les équipes marketing, en se concentrant sur l'analyse de l'acquisition client par cohortes, la segmentation client (RFM) et l'estimation de la Valeur Vie Client (CLV).

L'application est construite avec Streamlit et utilise le jeu de données Online Retail II (UCI), contenant les transactions e-commerce d'un détaillant UK de 2009 à 2011.

Objectifs Clés

Diagnostic : Mesurer la rétention et la dynamique de revenu par cohortes d'acquisition.

Priorisation : Construire des segments RFM (Recency–Frequency–Monetary) pour cibler les actions CRM.

Prévision : Estimer la CLV (Customer Lifetime Value) via des méthodes empiriques et paramétriques.

Simulation : Tester des scénarios marketing (ex. gain de rétention, variation de marge ou de remise) et quantifier leur impact immédiat sur la CLV et le Chiffre d'Affaires.

Structure du Projet

Conformément aux spécifications, l'architecture du projet est la suivante :

.
├── README.md               # Ce fichier
├── requirements.txt        # Liste des dépendances Python
├── notebooks/
│   └── 01_exploration.ipynb  # Notebook d'exploration visuelle complète (Partie I)
├── app/
│   ├── app.py              # Application Streamlit principale (Partie II)
│   ├── utils.py            # Fonctions utilitaires (nettoyage, calculs RFM, CLV)
│   └── data/
│       ├── raw/            # Données brutes (ex. Online Retail II)
│       └── processed/      # Données nettoyées ou agrégées (ex. DF Cohortes)
└── docs/
    └── prez/               # Support de présentation (PowerPoint, PDF, etc.)


Prérequis

Assurez-vous d'avoir Python (3.8+) installé sur votre système.

Installation

Clonez ce dépôt :

git clone <URL_DE_VOTRE_DEPOT>
cd CLV-RFM-Marketing-App


Créez et activez un environnement virtuel (recommandé) :

python -m venv venv
source venv/bin/activate  # Sous Linux/macOS
# ou .\venv\Scripts\activate  # Sous Windows


Installez les dépendances :

pip install -r requirements.txt


Utilisation de l'Application Streamlit

Après avoir installé les dépendances, vous pouvez lancer l'application Streamlit depuis le dossier app :

cd app
streamlit run app.py


L'application sera accessible dans votre navigateur (généralement à http://localhost:8501).