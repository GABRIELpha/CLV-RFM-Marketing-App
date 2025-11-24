import streamlit as st
import pandas as pd
import datetime as dt
import plotly.express as px
import plotly.graph_objects as go

# Importation de nos fonctions depuis utils.py
from utils import load_and_prepare_data, apply_filters, calculate_rfm, calculate_cohort_retention, calculate_clv_formula, run_scenario_simulation

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="Projet Marketing Analytics", layout="wide", page_icon="📊")

st.title("📊 Dashboard Marketing : Cohortes, RFM & CLV")
st.markdown("Outil d'aide à la décision pour piloter la rétention et la valeur client.")

# --- CHARGEMENT DES DONNÉES ---
@st.cache_data
def get_data():
    # Le chemin part de la racine où on lance "streamlit run"
    return load_and_prepare_data('app/data/data_clean.csv')

try:
    df_raw = get_data()
except Exception as e:
    st.error(f"Erreur de chargement des données : {e}")
    st.stop()

# Dates bornes pour les filtres
MIN_DATE = df_raw['TransactionDate'].min()
MAX_DATE = df_raw['TransactionDate'].max()

# --- SIDEBAR : FILTRES ---
with st.sidebar:
    st.header("🔍 Filtres d'analyse")
    
    # Date Range
    date_range = st.date_input(
        "Période d'analyse",
        value=(MIN_DATE, MAX_DATE),
        min_value=MIN_DATE,
        max_value=MAX_DATE
    )
    
    # Sécuriser les dates
    if len(date_range) == 2:
        start_date, end_date = date_range
    else:
        start_date, end_date = MIN_DATE, MAX_DATE

    # Pays
    country_list = ['Global'] + sorted(list(df_raw['Country'].unique()))
    selected_country = st.selectbox("Pays", country_list)
    
    # Retours
    returns_mode = st.radio("Gestion des Retours", ['Neutraliser', 'Exclure'])
    
    st.info(f"📅 Données du {start_date} au {end_date}")

# --- TRAITEMENT DES DONNÉES FILTRÉES ---
df_filtered = apply_filters(df_raw, start_date, end_date, selected_country, returns_mode)

if df_filtered.empty:
    st.warning("Aucune donnée pour cette sélection. Veuillez élargir les filtres.")
    st.stop()

# Calcul RFM sur données filtrées
ANALYSIS_DATE = pd.to_datetime(end_date) + dt.timedelta(days=1)
df_rfm = calculate_rfm(df_filtered, ANALYSIS_DATE)

# --- NAVIGATION (ONGLETS) ---
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📈 Vue d'ensemble", 
    "📅 Cohortes & Rétention", 
    "👥 Segmentation RFM", 
    "🧪 Simulateur & Scénarios",
    "⬇️ Exports"
])

# ================= ONGLET 1 : VUE D'ENSEMBLE =================
with tab1:
    st.subheader("KPIs Globaux")
    
    col1, col2, col3, col4 = st.columns(4)
    
    n_clients = df_rfm['CustomerID'].nunique()
    ca_total = df_rfm['Monetary'].sum()
    panier_moyen = ca_total / df_filtered['InvoiceNo'].nunique()
    clv_avg = df_rfm['Monetary'].mean()
    
    col1.metric("Clients Actifs", f"{n_clients:,}")
    col2.metric("Chiffre d'Affaires", f"{ca_total:,.0f} £")
    col3.metric("Panier Moyen", f"{panier_moyen:.2f} £")
    col4.metric("CLV Moyenne (Empirique)", f"{clv_avg:.2f} £", help="CA moyen par client sur la période")
    
    # Graphique Tendance
    st.markdown("### 📉 Évolution du Chiffre d'Affaires")
    df_trend = df_filtered.set_index('TransactionDate').resample('M')['TotalSales'].sum().reset_index()
    fig_trend = px.line(df_trend, x='TransactionDate', y='TotalSales', markers=True, title="CA Mensuel")
    st.plotly_chart(fig_trend, use_container_width=True)

# ================= ONGLET 2 : COHORTES =================
with tab2:
    st.subheader("Analyse de la Rétention")
    st.markdown("Lecture : Pour la cohorte '2010-01', quel % de clients a re-commandé après X mois ?")
    
    retention_matrix, cohort_sizes = calculate_cohort_retention(df_filtered)
    
    if not retention_matrix.empty:
        # Heatmap
        fig_cohort = px.imshow(
            retention_matrix,
            text_auto=".1f",
            aspect="auto",
            color_continuous_scale="Blues",
            labels=dict(x="Mois après acquisition", y="Cohorte", color="Rétention %")
        )
        fig_cohort.update_layout(xaxis_side="top")
        st.plotly_chart(fig_cohort, use_container_width=True)
        
        # Tailles
        st.markdown("### 📊 Taille des Cohortes (Nouveaux Clients)")
        st.bar_chart(cohort_sizes)
    else:
        st.info("Pas assez de données pour afficher les cohortes.")

# ================= ONGLET 3 : RFM =================
with tab3:
    st.subheader("Segmentation Client")
    
    # Graphique Répartition Segments (Treemap)
    rfm_counts = df_rfm['Segment_RFM'].value_counts().reset_index()
    rfm_counts.columns = ['Segment', 'Count']
    
    fig_tree = px.treemap(rfm_counts, path=['Segment'], values='Count', 
                          title="Répartition des Clients par Segment RFM",
                          color='Count', color_continuous_scale='RdBu')
    st.plotly_chart(fig_tree, use_container_width=True)
    
    # Tableau Détails Segments
    rfm_stats = df_rfm.groupby('Segment_RFM').agg({
        'CustomerID': 'count',
        'Monetary': ['sum', 'mean'],
        'Recency': 'mean'
    }).round(1)
    
    rfm_stats.columns = ['Nb Clients', 'CA Total', 'CA Moyen', 'Récence Moyenne']
    st.dataframe(rfm_stats.sort_values('CA Total', ascending=False), use_container_width=True)
    
    st.markdown("---")
    st.markdown("**Matrice Récence vs Fréquence**")
    fig_scatter = px.scatter(df_rfm, x='Recency', y='Frequency', color='Segment_RFM', 
                             log_y=True, size='Monetary', hover_data=['CustomerID'],
                             title="Carte des Clients (Taille = CA)")
    st.plotly_chart(fig_scatter, use_container_width=True)

# ================= ONGLET 4 : SCÉNARIOS =================
with tab4:
    st.subheader("Simulateur d'Impact Business")
    st.markdown("Ajustez les leviers pour voir l'impact sur la CLV estimée et le CA.")
    
    col_param1, col_param2 = st.columns(2)
    
    with col_param1:
        st.markdown("#### Hypothèses Actuelles")
        p_margin = st.slider("Marge Brute (%)", 0.05, 0.80, 0.30, 0.05)
        p_retention = st.slider("Taux de Rétention Annuel (r)", 0.1, 0.95, 0.5, 0.05)
        p_discount = st.number_input("Taux d'actualisation (d)", 0.01, 0.50, 0.10)
        
    with col_param2:
        st.markdown("#### Action Marketing")
        p_remise = st.slider("Remise Commerciale (%)", 0.0, 0.50, 0.0, 0.01, help="Simule une baisse de prix globale")
        
    # Calculs Baseline vs Simulation
    clv_baseline = calculate_clv_formula(df_rfm, p_retention, p_discount, p_margin) # Sans remise
    clv_sim, ca_sim = run_scenario_simulation(df_filtered, p_retention, p_discount, p_margin, p_remise)
    
    st.markdown("---")
    st.subheader("Résultats de la Simulation")
    
    res_col1, res_col2 = st.columns(2)
    
    diff_clv = clv_sim - clv_baseline
    res_col1.metric("CLV Projetée (Formule)", f"{clv_sim:.2f} £", delta=f"{diff_clv:.2f} £")
    
    ca_base = df_rfm['Monetary'].sum()
    diff_ca = ca_sim - ca_base
    res_col2.metric("Chiffre d'Affaires Projeté", f"{ca_sim:,.0f} £", delta=f"{diff_ca:,.0f} £")
    
    if p_remise > 0:
        st.warning(f"⚠️ Une remise de {p_remise*100}% réduit mécaniquement le CA et la Marge par client, donc la CLV baisse si la rétention n'augmente pas en conséquence.")

# ================= ONGLET 5 : EXPORTS =================
with tab5:
    st.subheader("Téléchargement des données")
    
    # Préparer le fichier
    csv_rfm = df_rfm.to_csv(index=False).encode('utf-8')
    
    st.download_button(
        label="📥 Télécharger la liste qualifiée (RFM)",
        data=csv_rfm,
        file_name='segments_rfm.csv',
        mime='text/csv'
    )
    
    st.dataframe(df_rfm.head(50))