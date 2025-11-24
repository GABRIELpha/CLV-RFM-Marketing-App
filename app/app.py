import streamlit as st
import pandas as pd
import numpy as np
import datetime as dt
import plotly.express as px
import plotly.graph_objects as go

# Importation fonctions utils
from utils import load_and_prepare_data, apply_filters, calculate_rfm, calculate_cohort_retention, calculate_clv_formula, run_scenario_simulation

# --- CONFIGURATION PAGE ---
st.set_page_config(page_title="Marketing Decision Tool", layout="wide", page_icon="🎯")

# --- CHARGEMENT DONNÉES ---
@st.cache_data
def get_data():
    return load_and_prepare_data('app/data/data_clean.csv')

try:
    df_raw = get_data()
except Exception as e:
    st.error("Impossible de charger les données. Vérifiez l'emplacement de 'data/data_clean.csv'.")
    st.stop()

if df_raw.empty:
    st.error("Le fichier de données est vide ou invalide.")
    st.stop()

# --- SIDEBAR & FILTRES ---
with st.sidebar:
    st.header("⚙️ Paramètres & Filtres")
    
    # 1. Période
    min_d, max_d = df_raw['TransactionDate'].min(), df_raw['TransactionDate'].max()
    date_range = st.date_input("Période d'analyse", value=(min_d, max_d), min_value=min_d, max_value=max_d)
    start_date, end_date = date_range if len(date_range) == 2 else (min_d, max_d)
    
    # 2. Unité de temps
    time_unit = st.selectbox("Unité de temps (Tendances)", ["Mois", "Trimestre"])
    
    # 3. Pays
    countries = ['Global'] + sorted(df_raw['Country'].unique().tolist())
    country = st.selectbox("Pays", countries)
    
    # 4. Mode Retours
    returns_mode = st.radio("Gestion des Retours", ["Inclure", "Exclure", "Neutraliser"], index=1, 
                            help="Inclure: Garde montant négatif. Exclure: Supprime lignes. Neutraliser: Montant = 0.")
    
    # 5. Seuil Commande
    min_order = st.slider("Seuil minimum commande (£)", 0, 500, 0, step=10)

# --- APPLICATION FILTRES & SÉCURITÉS (A) ---
df_filtered = apply_filters(df_raw, start_date, end_date, country, returns_mode, min_order)
analysis_date = pd.to_datetime(end_date) + dt.timedelta(days=1)

if df_filtered.empty:
    st.warning("⚠️ Aucune donnée pour cette sélection de filtres. Modifiez la période, le pays ou le seuil de commande.")
    st.stop()

# Calculs RFM
df_rfm = calculate_rfm(df_filtered, analysis_date)

if df_rfm.empty:
    st.warning("⚠️ Aucune donnée client valide après filtrage (ex: Clients avec TotalSales <= 0 exclus).")
    st.stop()

# Calculs Cohortes
retention_matrix, arpu_matrix, cohort_sizes = calculate_cohort_retention(df_filtered)

# --- BANDEAU FILTRES ACTIFS ---
active_filters_text = f"**Filtres actifs :** 🗓️ {start_date} à {end_date} | 🌍 {country} | 🔄 {returns_mode} | 🛒 Min £{min_order}"
if returns_mode == "Exclure":
    active_filters_text += " | 🔖 **Retours Exclus**"
st.info(active_filters_text)

# --- NAVIGATION ---
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📈 Vue d'ensemble", 
    "📅 Cohortes & Rétention", 
    "👥 Segmentation RFM", 
    "🧪 Simulateur",
    "⬇️ Exports"
])

# ================= TAB 1 : VUE D'ENSEMBLE =================
with tab1:
    st.markdown("### KPIs Clés")
    
    col1, col2, col3, col4 = st.columns(4)
    
    nb_clients = df_rfm['CustomerID'].nunique()
    ca_total = df_rfm['Monetary'].sum()
    nb_invoices = df_filtered['InvoiceNo'].nunique()
    panier_moyen = ca_total / nb_invoices if nb_invoices > 0 else 0
    clv_empirique = df_rfm['Monetary'].mean()
    
    col1.metric("Clients Actifs", f"{nb_clients:,}", help="Nombre de clients uniques ayant acheté sur la période.")
    col2.metric("Chiffre d'Affaires", f"£ {ca_total:,.0f}", help="Somme des ventes filtrées (£).")
    col3.metric("Panier Moyen", f"£ {panier_moyen:.2f}", help="CA Total / Nombre de Factures.")
    col4.metric("CLV Moyenne (Empirique)", f"£ {clv_empirique:.2f}", help="CA Total / Nombre de Clients Uniques.")

    st.markdown("---")
    
    with st.expander("🔮 Hypothèses CLV (Formule fermée)", expanded=True):
        hc1, hc2, hc3, hc4 = st.columns(4)
        h_margin = hc1.slider("Marge (%)", 0.05, 0.80, 0.30, 0.05)
        h_retention = hc2.slider("Taux Rétention (r)", 0.1, 0.95, 0.60, 0.05)
        h_discount = hc3.slider("Taux Actualisation (d)", 0.01, 0.30, 0.10, 0.01)
        
        # (D) calculate_clv_formula gère désormais proprement les scalaires
        clv_formula = calculate_clv_formula(clv_empirique, h_retention, h_discount, h_margin)
        hc4.metric("CLV Projetée (Formule)", f"£ {clv_formula:.2f}")

    st.markdown(f"### 📉 Évolution du CA ({time_unit})")
    freq = 'Q' if time_unit == "Trimestre" else 'M'
    
    # Check si df_trend a des données
    if not df_filtered.empty:
        df_trend = df_filtered.set_index('TransactionDate').resample(freq)['TotalSales'].sum().reset_index()
        trend_counts = df_filtered.set_index('TransactionDate').resample(freq)['InvoiceNo'].nunique().reset_index()
        df_trend['InvoiceCount'] = trend_counts['InvoiceNo'].values
        
        fig_trend = px.line(df_trend, x='TransactionDate', y='TotalSales', markers=True, 
                            hover_data=['InvoiceCount'], title=f"CA par {time_unit}")
        st.plotly_chart(fig_trend, use_container_width=True)
    else:
        st.info("Pas de données pour le graphique de tendance.")

# ================= TAB 2 : COHORTES =================
with tab2:
    st.markdown("### Analyse de la Dynamique de Cohorte")
    
    # (B) Robustesse : Si matrices vides, on affiche un message
    if retention_matrix.empty or arpu_matrix.empty:
        st.info("⚠️ Pas assez de données pour calculer les cohortes sur ce périmètre (peut-être une période trop courte ou filtre trop restrictif).")
    else:
        cohort_list = ["Toutes"] + retention_matrix.index.tolist()
        target_cohort = st.selectbox("Cohorte à analyser", cohort_list)
        
        if target_cohort == "Toutes":
            st.subheader("Heatmap de Rétention (%)")
            fig_hm = px.imshow(retention_matrix, text_auto=".1f", aspect="auto", color_continuous_scale="Blues",
                               labels=dict(x="Mois (Index)", y="Cohorte", color="Rétention %"))
            fig_hm.update_xaxes(side="top")
            st.plotly_chart(fig_hm, use_container_width=True)
            
            st.subheader("Courbes de Valeur (CA Moyen Cumulé par Client)")
            # (C) Robustesse : melt sur données existantes
            arpu_long = arpu_matrix.reset_index().melt(id_vars='CohortMonth', var_name='Index', value_name='ARPU')
            fig_arpu = px.line(arpu_long, x='Index', y='ARPU', color='CohortMonth', 
                               title="CA Moyen par Client par âge de cohorte")
            st.plotly_chart(fig_arpu, use_container_width=True)
            
            st.markdown("**Tailles initiales des cohortes (n)**")
            st.dataframe(cohort_sizes.to_frame().T)
            
        else:
            st.subheader(f"Focus : Cohorte {target_cohort}")
            # Sécurité si la cohorte n'existe pas dans l'index (rare mais possible)
            if target_cohort in cohort_sizes.index:
                n_init = cohort_sizes.loc[target_cohort]
                st.metric("Taille Initiale (M+0)", f"{n_init} clients")
                
                col_f1, col_f2 = st.columns(2)
                
                ret_data = retention_matrix.loc[target_cohort]
                fig_ret = px.line(x=ret_data.index, y=ret_data.values, markers=True, 
                                  labels={'x':'Mois (Index)', 'y':'Rétention %'}, title="Courbe de Rétention")
                col_f1.plotly_chart(fig_ret, use_container_width=True)
                
                rev_data = arpu_matrix.loc[target_cohort]
                fig_rev = px.bar(x=rev_data.index, y=rev_data.values, 
                                 labels={'x':'Mois (Index)', 'y':'CA Moyen (£)'}, title="CA Moyen par Client (ARPU)")
                col_f2.plotly_chart(fig_rev, use_container_width=True)

# ================= TAB 3 : RFM =================
with tab3:
    st.subheader("Segmentation & Priorisation CRM")
    
    # (E) Robustesse Table RFM
    # On construit le dictionnaire d'aggrégation dynamiquement pour éviter les KeyError
    agg_dict = {
        'CustomerID': 'count',
        'Monetary': ['sum', 'mean'],
        'Recency': 'mean'
    }
    # On ajoute Priorité_CRM seulement si elle existe
    if 'Priorité_CRM' in df_rfm.columns:
        agg_dict['Priorité_CRM'] = 'first'
    
    rfm_stats = df_rfm.groupby('Segment_RFM').agg(agg_dict).round(1)
    
    # Aplatir les colonnes MultiIndex proprement
    # Les colonnes seront [CustomerID, Monetary_sum, Monetary_mean, Recency, Priorité_CRM] dans l'ordre
    rfm_stats.columns = ['_'.join(col).strip() if col[1] else col[0] for col in rfm_stats.columns.values]
    
    # Renommage explicite pour affichage
    rename_map = {
        'CustomerID_count': 'Nb Clients',
        'Monetary_sum': 'CA Total',
        'Monetary_mean': 'CA Moyen',
        'Recency_mean': 'Récence Moy',
        'Priorité_CRM_first': 'Priorité'
    }
    # Nettoyage si Priorité n'existe pas
    if 'Priorité_CRM' not in df_rfm.columns:
        rename_map.pop('Priorité_CRM_first', None)
        
    rfm_stats = rfm_stats.rename(columns=rename_map)
    
    # Calcul CLV Formule par segment (Series)
    rfm_stats['CLV Estimée (Formule)'] = calculate_clv_formula(rfm_stats['CA Moyen'], h_retention, h_discount, h_margin)
    
    # Tri sécurisé
    sort_col = 'Priorité' if 'Priorité' in rfm_stats.columns else 'CA Total'
    st.dataframe(rfm_stats.sort_values(sort_col), use_container_width=True)
    
    # Visualisations
    col_v1, col_v2 = st.columns(2)
    
    rfm_counts = df_rfm['Segment_RFM'].value_counts().reset_index()
    rfm_counts.columns = ['Segment', 'Count']
    # Variable fig_tree stockée pour l'export plus tard
    fig_tree = px.treemap(rfm_counts, path=['Segment'], values='Count', 
                          title="Poids des Segments (Volume)", color='Count', color_continuous_scale='RdBu')
    col_v1.plotly_chart(fig_tree, use_container_width=True)
    
    fig_scatter = px.scatter(df_rfm, x='Recency', y='Frequency', color='Segment_RFM', 
                             size='Monetary', size_max=40, opacity=0.6,
                             hover_data=['CustomerID', 'Monetary'],
                             title="Carte Récence vs Fréquence")
    col_v2.plotly_chart(fig_scatter, use_container_width=True)

# ================= TAB 4 : SIMULATEUR =================
with tab4:
    st.subheader("Simulateur de Scénarios Marketing")
    
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        st.markdown("**Paramètres Structurels**")
        sim_margin = st.slider("Marge Brute (%) ", 0.05, 0.8, 0.3, 0.01, key='sim_m')
        sim_retention = st.slider("Taux Rétention (r)", 0.1, 0.95, 0.6, 0.01, key='sim_r')
        sim_discount = st.number_input("Taux Actualisation (d)", 0.01, 0.5, 0.1, key='sim_d')
        
    with col_s2:
        st.markdown("**Levier Commercial (Remise)**")
        disc_mode = st.selectbox("Mode de remise", ["Globale (tous les clients)", "Par segment RFM (simple)"])
        
        target_seg = None
        if disc_mode == "Par segment RFM (simple)":
            target_seg = st.selectbox("Segment Cible", df_rfm['Segment_RFM'].unique())
            
        sim_disc_pct = st.slider("Pourcentage de Remise (%)", 0.0, 0.5, 0.0, 0.01)

    # Exécution Simulation
    clv_sim, ca_sim = run_scenario_simulation(df_filtered, df_rfm, sim_retention, sim_discount, sim_margin, disc_mode, sim_disc_pct, target_seg)
    
    # Baseline
    clv_base = calculate_clv_formula(df_rfm['Monetary'].mean(), sim_retention, sim_discount, sim_margin)
    ca_base = df_rfm['Monetary'].sum()
    
    st.markdown("---")
    res_c1, res_c2 = st.columns(2)
    
    fig_clv = go.Figure(data=[
        go.Bar(name='Baseline', x=['CLV'], y=[clv_base], marker_color='lightgrey'),
        go.Bar(name='Scénario', x=['CLV'], y=[clv_sim], marker_color='blue')
    ])
    fig_clv.update_layout(title="Impact CLV Moyenne (£)", barmode='group')
    res_c1.plotly_chart(fig_clv, use_container_width=True)
    res_c1.metric("Delta CLV", f"£ {clv_sim - clv_base:.2f}")

    fig_ca = go.Figure(data=[
        go.Bar(name='Baseline', x=['CA Total'], y=[ca_base], marker_color='lightgrey'),
        go.Bar(name='Scénario', x=['CA Total'], y=[ca_sim], marker_color='green')
    ])
    fig_ca.update_layout(title="Impact CA Total (£)", barmode='group')
    res_c2.plotly_chart(fig_ca, use_container_width=True)
    res_c2.metric("Delta CA", f"£ {ca_sim - ca_base:,.0f}")
    
    st.markdown("#### Analyse de Sensibilité : CLV en fonction de la Rétention (r)")
    r_values = np.linspace(0.3, 0.9, 20)
    avg_monetary_for_curve = (ca_sim / len(df_rfm)) if len(df_rfm) > 0 else 0
    sens_y = [calculate_clv_formula(avg_monetary_for_curve, r, sim_discount, sim_margin) for r in r_values]
    
    fig_sens = px.line(x=r_values, y=sens_y, labels={'x':'Taux Rétention (r)', 'y':'CLV (£)'}, markers=True)
    fig_sens.add_vline(x=sim_retention, line_dash="dash", line_color="red", annotation_text="r choisi")
    st.plotly_chart(fig_sens, use_container_width=True)

# ================= TAB 5 : EXPORTS =================
with tab5:
    st.subheader("Exporter les Données et Plans d'Action")
    
    col_ex1, col_ex2 = st.columns(2)
    
    # Export RFM
    df_export_rfm = df_rfm.copy()
    # (D) calculate_clv_formula gère Series proprement
    df_export_rfm['CLV_Formule'] = calculate_clv_formula(df_export_rfm['Monetary'], h_retention, h_discount, h_margin)
    
    csv_rfm = df_export_rfm.to_csv(index=False).encode('utf-8')
    col_ex1.download_button("📥 Télécharger Liste Activable (RFM + CLV)", csv_rfm, 'plan_action_rfm.csv', 'text/csv')
    
    # Export Raw
    csv_trans = df_filtered.to_csv(index=False).encode('utf-8')
    col_ex2.download_button("📥 Télécharger Transactions Filtrées", csv_trans, 'transactions_filtered.csv', 'text/csv')
    
    st.markdown("---")
    st.markdown("**Export des Graphiques**")
    st.info("💡 Utilisez l'icône appareil photo sur les graphiques pour un PNG rapide.")
    
    # (F) Bouton Spécifique Treemap (Sécurisé)
    # On vérifie si fig_tree est défini dans le scope local (il l'est si Tab 3 a été exécuté par le script)
    # Streamlit exécute le script de haut en bas, donc fig_tree existe.
    if 'fig_tree' in locals():
        try:
            # Fallback en cas d'absence de librairie graphique serveur (kaleido)
            img_bytes = fig_tree.to_image(format="png")
            st.download_button("📷 Télécharger Image Segments (Treemap)", img_bytes, "segments_treemap.png", "image/png")
        except Exception as e:
            # On n'affiche pas l'erreur complète à l'utilisateur, juste une info
            st.caption("Le téléchargement direct bouton n'est pas disponible (librairie manquante). Utilisez l'icône caméra du graphique.")