import pandas as pd
import numpy as np
import datetime as dt

# --- 1. FONCTION DE CHARGEMENT ET PRÉPARATION ---
def load_and_prepare_data(file_path):
    """Charge le CSV, nettoie et prépare le DataFrame de base."""
    try:
        df = pd.read_csv(file_path, parse_dates=['InvoiceDate'])
    except FileNotFoundError:
        # Si on lance depuis le dossier app/, le chemin change
        df = pd.read_csv('data_clean.csv', parse_dates=['InvoiceDate'])
    
    # Standardisation des colonnes basées sur votre fichier data_clean.csv
    df.rename(columns={
        'Customer ID': 'CustomerID', 
        'InvoiceDate': 'TransactionDate', 
        'TotalAmount': 'TotalSales', 
        'Invoice': 'InvoiceNo',
        'Price': 'UnitPrice'
    }, inplace=True)
    
    # Conversion ID Client
    df['CustomerID'] = pd.to_numeric(df['CustomerID'], errors='coerce')
    df = df.dropna(subset=['CustomerID'])
    df['CustomerID'] = df['CustomerID'].astype('Int64')
    
    # Identification des retours
    df['is_return'] = df['InvoiceNo'].astype(str).str.startswith('C')
    
    return df

# --- 2. FONCTION DE FILTRAGE ---
def apply_filters(df, start_date, end_date, country_filter, returns_mode):
    """Applique les filtres de date, pays et mode de retours."""
    
    # 1. Filtre Temporel
    mask_date = (df['TransactionDate'] >= pd.to_datetime(start_date)) & (df['TransactionDate'] <= pd.to_datetime(end_date))
    df_filtered = df.loc[mask_date].copy()
    
    # 2. Filtre Pays
    if country_filter != 'Global':
        df_filtered = df_filtered[df_filtered['Country'] == country_filter]
        
    # 3. Mode Retours
    if returns_mode == 'Exclure':
        df_final = df_filtered[df_filtered['is_return'] == False].copy()
    else: 
        # Neutraliser (on garde tout)
        df_final = df_filtered.copy()

    return df_final

# --- 3. FONCTION RFM ---
def calculate_rfm(df_transactions, analysis_date):
    """Calcule R, F, M, les scores et les segments."""
    
    # Préparer les données par client
    rfm_df = df_transactions.groupby('CustomerID').agg(
        Recency=('TransactionDate', lambda x: (analysis_date - x.max()).days),
        Frequency=('InvoiceNo', 'nunique'),
        Monetary=('TotalSales', 'sum')
    ).reset_index()
    
    # S'assurer que Monetary est positif (pour éviter les erreurs de quantiles sur des dettes)
    rfm_df = rfm_df[rfm_df['Monetary'] > 0]
    
    # Score (Quintiles)
    # Recency: plus petit = mieux (labels inversés)
    rfm_df['R_Score'] = pd.qcut(rfm_df['Recency'], 5, labels=[5, 4, 3, 2, 1])
    
    # Frequency & Monetary: plus grand = mieux
    rfm_df['F_Score'] = pd.qcut(rfm_df['Frequency'].rank(method='first'), 5, labels=[1, 2, 3, 4, 5])
    rfm_df['M_Score'] = pd.qcut(rfm_df['Monetary'].rank(method='first'), 5, labels=[1, 2, 3, 4, 5])

    rfm_df['RFM_Score'] = rfm_df['R_Score'].astype(str) + rfm_df['F_Score'].astype(str) + rfm_df['M_Score'].astype(str)

    # Segmentation
    def rfm_label(row):
        r, f, m = int(row['R_Score']), int(row['F_Score']), int(row['M_Score'])
        
        if r >= 5 and f >= 5 and m >= 5: return 'Champions'
        if r >= 4 and f >= 4: return 'Fidèles'
        if r >= 4 and f <= 2: return 'Nouveaux Prometteurs'
        if r <= 2 and f >= 4: return 'À Risque (Haute Valeur)'
        if r <= 2 and f <= 2: return 'Perdus / Dormants'
        return 'Autres'

    rfm_df['Segment_RFM'] = rfm_df.apply(rfm_label, axis=1)

    return rfm_df

# --- 4. FONCTION COHORTES ---
def calculate_cohort_retention(df_transactions):
    """Calcule la matrice de rétention par cohortes."""
    
    df = df_transactions.copy()
    df['TransactionMonth'] = df['TransactionDate'].dt.to_period('M')
    df['CohortMonth'] = df.groupby('CustomerID')['TransactionMonth'].transform('min')
    
    def get_cohort_index(df_in):
        return (df_in['TransactionMonth'].dt.to_timestamp() - df_in['CohortMonth'].dt.to_timestamp()).dt.days // 30
    
    df['CohortIndex'] = get_cohort_index(df)
    
    cohort_data = df.groupby(['CohortMonth', 'CohortIndex'])['CustomerID'].nunique().reset_index()
    cohort_counts = cohort_data.pivot_table(index='CohortMonth', columns='CohortIndex', values='CustomerID')
    
    cohort_sizes = cohort_counts.iloc[:, 0]
    retention_matrix = cohort_counts.divide(cohort_sizes, axis=0) * 100
    retention_matrix.index = retention_matrix.index.strftime('%Y-%m')
    
    return retention_matrix, cohort_sizes

# --- 5. CALCULS CLV & SCÉNARIOS (C'EST ICI QUE CA MANQUAIT PEUT-ÊTRE) ---
def calculate_clv_formula(df_rfm, retention_rate_r, discount_rate_d, avg_margin):
    """Calcule la CLV selon la formule fermée."""
    
    avg_monetary = df_rfm['Monetary'].mean()
    
    contribution_margin = avg_monetary * avg_margin
    churn_rate = 1 - retention_rate_r
    
    denominator = churn_rate + discount_rate_d
    if denominator <= 0: return 0
    
    return contribution_margin / denominator

def run_scenario_simulation(df_base, retention_rate_r, discount_rate_d, margin_pct, remise_pct):
    """Simule l'impact des paramètres."""
    
    df_sim = df_base.copy()
    # Impact remise
    df_sim['TotalSales_Sim'] = df_sim['TotalSales'] * (1 - remise_pct)
    
    # Recalcul RFM simulé
    rfm_sim = df_sim.groupby('CustomerID').agg(
        Monetary=('TotalSales_Sim', 'sum')
    ).reset_index()
    
    # Recalcul CLV simulée
    clv_sim = calculate_clv_formula(rfm_sim, retention_rate_r, discount_rate_d, margin_pct)
    total_sales_sim = df_sim['TotalSales_Sim'].sum()
    
    return clv_sim, total_sales_sim