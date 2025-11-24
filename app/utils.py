import pandas as pd
import numpy as np
import datetime as dt

# --- 1. FONCTION DE CHARGEMENT ET PRÉPARATION ---
def load_and_prepare_data(file_path):
    """Charge le CSV, nettoie et prépare le DataFrame de base."""
    try:
        df = pd.read_csv(file_path, parse_dates=['InvoiceDate'])
    except FileNotFoundError:
        # Fallback si lancé depuis le dossier app/
        try:
            df = pd.read_csv('../data/data_clean.csv', parse_dates=['InvoiceDate'])
        except FileNotFoundError:
            return pd.DataFrame() # Retourne un DF vide si échec total

    # Standardisation des colonnes
    df.rename(columns={
        'Customer ID': 'CustomerID', 
        'InvoiceDate': 'TransactionDate', 
        'TotalAmount': 'TotalSales', 
        'Invoice': 'InvoiceNo',
        'Price': 'UnitPrice'
    }, inplace=True)
    
    # Nettoyage et typage
    df['CustomerID'] = pd.to_numeric(df['CustomerID'], errors='coerce')
    df = df.dropna(subset=['CustomerID'])
    df['CustomerID'] = df['CustomerID'].astype('Int64')
    
    # Identification des retours
    df['is_return'] = df['InvoiceNo'].astype(str).str.startswith('C')
    
    return df

# --- 2. FONCTION DE FILTRAGE AVANCÉE ---
def apply_filters(df, start_date, end_date, country_filter, returns_mode, min_order_val):
    """
    Applique les filtres : Date, Pays, Mode Retours, Seuil Commande.
    """
    if df.empty:
        return df

    # 1. Filtre Temporel
    mask_date = (df['TransactionDate'] >= pd.to_datetime(start_date)) & (df['TransactionDate'] <= pd.to_datetime(end_date))
    df_filtered = df.loc[mask_date].copy()
    
    if df_filtered.empty:
        return df_filtered

    # 2. Filtre Pays
    if country_filter != 'Global':
        df_filtered = df_filtered[df_filtered['Country'] == country_filter]
        
    # 3. Mode Retours
    if returns_mode == 'Exclure':
        df_filtered = df_filtered[df_filtered['is_return'] == False].copy()
    elif returns_mode == 'Neutraliser':
        df_filtered.loc[df_filtered['is_return'] == True, 'TotalSales'] = 0
    
    if df_filtered.empty:
        return df_filtered

    # 4. Filtre Seuil de Commande
    if min_order_val > 0:
        invoice_totals = df_filtered.groupby('InvoiceNo')['TotalSales'].sum()
        valid_invoices = invoice_totals[invoice_totals >= min_order_val].index
        df_filtered = df_filtered[df_filtered['InvoiceNo'].isin(valid_invoices)].copy()

    return df_filtered

# --- 3. FONCTION RFM ENRICHIE ---
def calculate_rfm(df_transactions, analysis_date):
    """Calcule R, F, M, scores, segments."""
    
    if df_transactions.empty:
        # Retourne un DF vide avec les colonnes attendues pour éviter KeyError plus tard
        return pd.DataFrame(columns=['CustomerID', 'Recency', 'Frequency', 'Monetary', 
                                     'R_Score', 'F_Score', 'M_Score', 'RFM_Score', 
                                     'Segment_RFM', 'Priorité_CRM'])

    # Agrégation par client
    rfm_df = df_transactions.groupby('CustomerID').agg(
        Recency=('TransactionDate', lambda x: (analysis_date - x.max()).days),
        Frequency=('InvoiceNo', 'nunique'),
        Monetary=('TotalSales', 'sum')
    ).reset_index()
    
    # Exclusion des clients avec Monetary <= 0 (Biais statistique + Division par zero)
    rfm_df = rfm_df[rfm_df['Monetary'] > 0]
    
    if rfm_df.empty:
        return pd.DataFrame(columns=['CustomerID', 'Recency', 'Frequency', 'Monetary', 
                                     'R_Score', 'F_Score', 'M_Score', 'RFM_Score', 
                                     'Segment_RFM', 'Priorité_CRM'])
    
    # Scoring (Quintiles)
    try:
        rfm_df['R_Score'] = pd.qcut(rfm_df['Recency'], 5, labels=[5, 4, 3, 2, 1])
        rfm_df['F_Score'] = pd.qcut(rfm_df['Frequency'].rank(method='first'), 5, labels=[1, 2, 3, 4, 5])
        rfm_df['M_Score'] = pd.qcut(rfm_df['Monetary'].rank(method='first'), 5, labels=[1, 2, 3, 4, 5])
    except ValueError:
        # Cas où il n'y a pas assez de valeurs uniques pour qcut
        # On fallback sur une assignation simplifiée ou on retourne tel quel
        rfm_df['R_Score'] = 3
        rfm_df['F_Score'] = 3
        rfm_df['M_Score'] = 3

    rfm_df['RFM_Score'] = rfm_df['R_Score'].astype(str) + rfm_df['F_Score'].astype(str) + rfm_df['M_Score'].astype(str)

    # Segmentation & Priorité CRM
    def segment_label(row):
        try:
            r, f, m = int(row['R_Score']), int(row['F_Score']), int(row['M_Score'])
        except:
            return 'Inconnu', 6 # Fallback
        
        if r >= 5 and f >= 5 and m >= 5: return 'Champions', 1
        if r >= 4 and f >= 4: return 'Fidèles', 2
        if r >= 4 and f <= 2: return 'Nouveaux Prometteurs', 3
        if r <= 2 and f >= 4: return 'À Risque (Haute Valeur)', 4
        if r <= 2 and f <= 2: return 'Perdus / Dormants', 6
        if m >= 4: return 'Gros Dépensiers (Risque)', 3
        return 'Potentiels', 5

    rfm_df[['Segment_RFM', 'Priorité_CRM']] = rfm_df.apply(lambda x: pd.Series(segment_label(x)), axis=1)

    return rfm_df

# --- 4. FONCTION COHORTES (Robustesse améliorée) ---
def calculate_cohort_retention(df_transactions):
    """Calcule la matrice de rétention (%) et la matrice de CA Moyen (ARPU)."""
    
    # (B) Robustesse : Gestion DF vide
    if df_transactions.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.Series(dtype="float")

    df = df_transactions.copy()
    df['TransactionMonth'] = df['TransactionDate'].dt.to_period('M')
    df['CohortMonth'] = df.groupby('CustomerID')['TransactionMonth'].transform('min')
    
    # Cohort Index
    def get_cohort_index(df_in):
        return (df_in['TransactionMonth'].dt.to_timestamp() - df_in['CohortMonth'].dt.to_timestamp()).dt.days // 30
    
    df['CohortIndex'] = get_cohort_index(df)
    
    # 1. Matrice Rétention
    cohort_data = df.groupby(['CohortMonth', 'CohortIndex'])['CustomerID'].nunique().reset_index()
    if cohort_data.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.Series(dtype="float")

    cohort_counts = cohort_data.pivot_table(index='CohortMonth', columns='CohortIndex', values='CustomerID')
    cohort_sizes = cohort_counts.iloc[:, 0]
    retention_matrix = cohort_counts.divide(cohort_sizes, axis=0) * 100
    
    # 2. Matrice CA Moyen (ARPU)
    cohort_revenue = df.groupby(['CohortMonth', 'CohortIndex'])['TotalSales'].sum().reset_index()
    revenue_matrix = cohort_revenue.pivot_table(index='CohortMonth', columns='CohortIndex', values='TotalSales')
    arpu_matrix = revenue_matrix.divide(cohort_sizes, axis=0)

    # Formatage index
    retention_matrix.index = retention_matrix.index.strftime('%Y-%m')
    arpu_matrix.index = arpu_matrix.index.strftime('%Y-%m')
    
    return retention_matrix, arpu_matrix, cohort_sizes

# --- 5. CALCULS CLV & SCÉNARIOS ---
def calculate_clv_formula(monetary_value, retention_rate_r, discount_rate_d, avg_margin):
    """
    Formule CLV = (Valeur Client * Marge) / (Taux Attrition + Taux Actualisation)
    Gère scalaires et Series de manière robuste (D).
    """
    contribution_margin = monetary_value * avg_margin
    churn_rate = 1 - retention_rate_r
    denominator = churn_rate + discount_rate_d
    
    # Gestion division par zéro ou négative
    if isinstance(denominator, (int, float)):
        if denominator <= 0.0001: return 0.0
        return contribution_margin / denominator
    else:
        # Cas vectoriel (Pandas Series)
        # On remplace les 0 par NaN pour éviter Inf, puis on fillna(0)
        return (contribution_margin / denominator).fillna(0)

def run_scenario_simulation(df_base, df_rfm, retention_r, discount_d, margin_pct, discount_mode, discount_pct, target_segment):
    """
    Simule l'impact des paramètres sur CLV et CA.
    """
    # Check inputs
    if df_rfm.empty:
        return 0.0, 0.0

    df_sim_rfm = df_rfm.copy()
    
    if discount_mode == 'Globale (tous les clients)':
        df_sim_rfm['Monetary_Sim'] = df_sim_rfm['Monetary'] * (1 - discount_pct)
    else:
        mask_segment = df_sim_rfm['Segment_RFM'] == target_segment
        df_sim_rfm['Monetary_Sim'] = np.where(mask_segment, 
                                              df_sim_rfm['Monetary'] * (1 - discount_pct), 
                                              df_sim_rfm['Monetary'])
    
    avg_monetary_sim = df_sim_rfm['Monetary_Sim'].mean()
    # Utilisation de la fonction robustifiée
    clv_sim = calculate_clv_formula(avg_monetary_sim, retention_r, discount_d, margin_pct)
    total_sales_sim = df_sim_rfm['Monetary_Sim'].sum()
    
    return clv_sim, total_sales_sim