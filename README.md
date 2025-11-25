# Application d'Aide à la Décision Marketing : Cohortes, RFM & CLV

## Présentation du Projet

Ce projet vise à construire une application interactive d'aide à la décision pour les équipes marketing, en se concentrant sur l'analyse de l'acquisition client par cohortes, la segmentation client (RFM) et l'estimation de la Valeur Vie Client (CLV).

L'application est construite avec **Streamlit** et utilise le jeu de données *Online Retail II* (UCI), contenant les transactions e-commerce d'un détaillant UK de 2009 à 2011.

## Objectifs Clés

* **Diagnostic :** Mesurer la rétention et la dynamique de revenu par cohortes d'acquisition.
* **Priorisation :** Construire des segments RFM (*Recency–Frequency–Monetary*) pour cibler les actions CRM.
* **Prévision :** Estimer la CLV (*Customer Lifetime Value*) via des méthodes empiriques et paramétriques.
* **Simulation :** Tester des scénarios marketing (ex. gain de rétention, variation de marge ou de remise) et quantifier leur impact immédiat sur la CLV et le Chiffre d'Affaires.

## Prérequis

Assurez-vous d'avoir **Python (3.8+)** installé sur votre système.

## Installation et Lancement

Pour utiliser l'application, veuillez suivre impérativement les trois étapes ci-dessous dans l'ordre.

### Étape 1 : Installation de l'environnement

1.  Clonez ce dépôt :
    ```bash
    git clone <URL_DE_VOTRE_DEPOT>
    cd CLV-RFM-Marketing-App
    ```

2.  Créez et activez un environnement virtuel (recommandé) :
    ```bash
    python -m venv venv
    source venv/bin/activate  # Sous Linux/macOS
    # ou .\venv\Scripts\activate  # Sous Windows
    ```

3.  Installez les dépendances nécessaires :
    ```bash
    pip install -r requirements.txt
    ```

### Étape 2 : Génération des données (Obligatoire)

L'application Streamlit ne fonctionnera pas sans les données traitées. Vous devez exécuter le notebook pour générer le fichier CSV nettoyé.

1.  Ouvrez le notebook `notebooks/exploration_donne.ipynb` (via Jupyter Lab, Notebook ou VS Code).
2.  **Exécutez toutes les cellules** du notebook (Menu : *Run All*).
3.  Cette action va traiter les données brutes et créer automatiquement le fichier de données nettoyées (ex. `data_clean.csv`) dans le dossier `app/data/processed/`.

### Étape 3 : Lancement de l'Application Streamlit

Une fois le fichier CSV généré par le notebook, revenez à la racine du projet dans votre terminal et lancez la commande suivante :

## bash
streamlit run app/app.py

## Structure du Projet

L'architecture du projet est organisée comme suit :

```text
.
├── README.md               # Ce fichier
├── requirements.txt        # Liste des dépendances Python
├── notebooks/
│   └── exploration_données.ipynb  # Notebook : Exploration & Génération du CSV nettoyé
├── app/
│   ├── app.py              # Application Streamlit principale
│   ├── utils.py            # Fonctions utilitaires (nettoyage, calculs RFM, CLV)
│   └── data/
│       ├── raw/            # Données brutes (ex. Online Retail II)
│       └── processed/      # Données nettoyées (générées par le notebook)
└── docs/
    └── prez/               # Support de présentation (PowerPoint, PDF, etc.)
