# Dictionnaire des Données - Projet Online Retail

Ce document décrit les variables présentes dans les fichiers de données utilisés par l'application Streamlit (`processed_data.csv`).

## 1. Données Transactionnelles (Brutes & Nettoyées)
*Source : Online Retail II (UCI)*

| Variable | Type | Description | Règles de gestion / Nettoyage |
| :--- | :--- | :--- | :--- |
| **InvoiceNo** | String | Identifiant unique de la transaction | Les factures commençant par 'C' (Annulations) ont été traitées/exclues. |
| **StockCode** | String | Code unique du produit | |
| **Description** | String | Libellé du produit | |
| **Quantity** | Integer | Quantité de produits achetés | Les quantités négatives (retours) sont conservées mais flaggées. |
| **InvoiceDate** | Datetime | Date et heure de l'achat | Format : YYYY-MM-DD HH:MM:SS |
| **UnitPrice** | Float | Prix unitaire du produit (£) | |
| **CustomerID** | String | Identifiant unique du client | Les lignes sans ID ont été supprimées. Converti en chaîne de caractère. |
| **Country** | String | Pays de résidence du client | |

## 2. Variables Calculées (Feature Engineering)
*Variables créées pour l'analyse Marketing*

| Variable | Type | Description | Formule / Logique |
| :--- | :--- | :--- | :--- |
| **TotalAmount** | Float | Montant total de la ligne (£) | `Quantity * UnitPrice` |
| **InvoiceMonth** | String | Mois de la transaction | Format YYYY-MM |
| **CohortMonth** | Date | Mois de la toute première commande du client | Utilisé pour l'analyse de rétention |
| **CohortIndex** | Integer | Nombre de mois écoulés depuis la première commande | 0 = mois d'acquisition, 1 = mois suivant, etc. |

## 3. Segmentation RFM & KPIs
*Métriques agrégées au niveau Client*

| Variable | Type | Description |
| :--- | :--- | :--- |
| **Recency (R)** | Integer | Nombre de jours depuis la dernière commande | Point de référence : Date max du dataset + 1 jour. |
| **Frequency (F)** | Integer | Nombre total de transactions (InvoiceNo uniques) | |
| **Monetary (M)** | Float | Chiffre d'affaires total généré par le client | Somme de `TotalAmount`. |
| **R_Score** | 1-4 | Score de Récence (quartiles) | 4 = Acheté très récemment, 1 = Acheté il y a longtemps. |
| **F_Score** | 1-4 | Score de Fréquence | 4 = Très fréquent. |
| **M_Score** | 1-4 | Score Monétaire | 4 = Gros dépensier. |
| **RFM_Segment** | String | Concaténation des scores (ex: "411") | |
| **RFM_Label** | String | Segment Marketing (ex: "Champions", "À risque") | Basé sur les règles définies dans `utils.py`. |