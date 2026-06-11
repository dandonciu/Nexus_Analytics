import streamlit as st
from streamlit_echarts import st_echarts
import streamlit.components.v1 as components
import sqlite3
import pandas as pd
import os
import re

# Setează layout-ul paginii Streamlit
st.set_page_config(
    page_title="NEXUS Executive Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Stiluri CSS personalizate (Inclusiv optimizări pentru Mobil)
st.markdown("""
<style>
    /* Carduri KPI */
    .kpi-card {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 15px;
        box-shadow: 2px 2px 10px rgba(0,0,0,0.05);
        border: 1px solid #e9ecef;
        text-align: left;
    }
    .kpi-title {
        font-size: 14px;
        color: #6c757d;
        font-weight: 500;
        margin-bottom: 5px;
    }
    .kpi-value {
        font-size: 28px;
        font-weight: bold;
        color: #212529;
        margin-bottom: 5px;
    }
    .kpi-trend {
        font-size: 12px;
        font-weight: 600;
    }
    .trend-up { color: #2ecc71; }
    .trend-down { color: #e74c3c; }

    /* PREMIUM DARK SIDEBAR */
    [data-testid="stSidebar"] label, 
    [data-testid="stSidebar"] .stMarkdown p,
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] h4,
    [data-testid="stSidebar"] h5,
    [data-testid="stSidebar"] h6 {
        color: #f1f5f9 !important;
    }

    /* Corecție culori butoane Radio în Sidebar */
    [data-testid="stSidebar"] label[data-baseweb="radio"] div,
    [data-testid="stSidebar"] label[data-baseweb="radio"] p,
    [data-testid="stSidebar"] div[data-testid="stWidgetLabel"] p {
        color: #f1f5f9 !important;
    }
    
    /* Fixează textul de branding permanent la baza Sidebar-ului */
    [data-testid="stSidebarUserContent"]::after {
        content: "©DSCM Tech";
        position: absolute;
        bottom: 2px;
        left: 15%;
        transform: translateX(-50%);
        font-size: 6px;
        color: #94a3b8;
        font-family: sans-serif;
    }

    /* Corecție Hover Butoane în Sidebar - Cenușiu închis corporate */
    [data-testid="stSidebar"] button:hover {
        background-color: #475569 !important;
        color: #ffffff !important;
        border-color: #475569 !important;
    }

    /* Adaptabilitate generală KPI-uri pe mobil */
    @media (max-width: 768px) {
        .kpi-value {
            font-size: 20px !important;
        }
        .kpi-card {
            padding: 10px !important;
        }
    }
</style>
""", unsafe_allow_html=True)

# --- ÎNCĂRCARE IMAGINE SIDEBAR DINAMICĂ ---
bg_image_path = "sidebar_bg.jpg"
if os.path.exists(bg_image_path):
    import base64
    with open(bg_image_path, "rb") as f:
        img_data = f.read()
    b64_img = base64.b64encode(img_data).decode()
    css_style = "<style>[data-testid='stSidebar'] { background-image: linear-gradient(rgba(30, 41, 59, 0.4), rgba(30, 41, 59, 0.4)), url('data:image/jpeg;base64," + b64_img + "') !important; background-size: cover !important; background-position: center !important; }</style>"
    st.markdown(css_style, unsafe_allow_html=True)
else:
    st.markdown("""
    <style>
        [data-testid="stSidebar"] {
            background-color: #1e293b !important;
        }
    </style>
    """, unsafe_allow_html=True)

# --- DEFINIRE MATRICE CONVERSIE ---
PACKAGING_FACTORS = {
    "BKTp721": 48,      # 48 cutii per palet pentru BKTp721
    "default": 64       # 64 cutii per palet pentru restul produselor
}

def get_factor(code):
    return PACKAGING_FACTORS.get(code, PACKAGING_FACTORS['default'])

# --- FUNCȚII INTELIGENTE DE UNIFICARE AUTOMATĂ ÎN MEMORIE (REGULAR EXPRESSIONS) ---
def unify_products(df):
    if df is None or df.empty:
        return df
    df = df.copy()
    df['code'] = df['code'].astype(str).str.strip()
    
    # Detecție tolerantă (Case-Insensitive) pentru PAL, PAL-, PAL_ sau PAL urmat de spațiu
    is_pallet = df['code'].str.contains(r'(?i)^PAL[\s\-_]*', regex=True, na=False)
    
    # Extragere cod de bază
    df['base_code'] = df['code'].str.replace(r'(?i)^PAL[\s\-_]*', '', regex=True)
    
    # Conversie stoc (stoc * factor)
    factors = df['base_code'].apply(get_factor)
    df.loc[is_pallet, 'stock'] = df.loc[is_pallet, 'stock'] * factors[is_pallet]
    
    # Grupare și cumulare stoc
    df_clean = df.sort_values(by='code', key=lambda x: x.str.contains(r'(?i)^PAL[\s\-_]*', regex=True))
    df_grouped = df_clean.groupby('base_code').agg({
        'product': 'first',
        'stock': 'sum',
        'unit': 'first',
        'category': 'first'
    }).reset_index()
    
    df_grouped.rename(columns={'base_code': 'code'}, inplace=True)
    return df_grouped

def unify_transactions(df, code_column='product_code'):
    if df is None or df.empty:
        return df
    df = df.copy()
    df[code_column] = df[code_column].astype(str).str.strip()
    
    is_pallet = df[code_column].str.contains(r'(?i)^PAL[\s\-_]*', regex=True, na=False)
    df['base_code'] = df[code_column].str.replace(r'(?i)^PAL[\s\-_]*', '', regex=True)
    
    factors = df['base_code'].apply(get_factor)
    df.loc[is_pallet, 'quantity'] = df.loc[is_pallet, 'quantity'] * factors[is_pallet]
    
    df[code_column] = df['base_code']
    df.drop(columns=['base_code'], inplace=True, errors='ignore')
    return df

# --- CONEXIUNE ȘI CITIRE DATE ---
DB_PATH = "nexus_buffer.db"

def load_data_from_db():
    conn = sqlite3.connect(DB_PATH)
    
    # Generare date demo pentru orders_live dacă tabela este goală
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM orders_live")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
            INSERT INTO orders_live (order_number, client_name, status, payload_logistic, payload_fiscal)
            VALUES (
                'ORD-2023-999', 
                'SC PROD COM SRL', 
                'PENDING DEPOT...', 
                '1 x PAL BKTp721, 11 x BKTp721', 
                'Date Facturare SmartBill'
            )
        """)
        conn.commit()

    raw_produse = pd.read_sql_query("SELECT * FROM produse", conn)
    raw_livrari = pd.read_sql_query("SELECT * FROM livrari", conn)
    raw_receptii = pd.read_sql_query("SELECT * FROM receptii", conn)
    orders_live = pd.read_sql_query("SELECT * FROM orders_live", conn)
    conn.close()
    
    raw_livrari['order_date'] = pd.to_datetime(raw_livrari['order_date'])
    raw_receptii['order_date'] = pd.to_datetime(raw_receptii['order_date'])
    
    # Aplicăm unificarea automată în memorie (Soluție de avarie pentru DEMO)
    produse = unify_products(raw_produse)
    livrari = unify_transactions(raw_livrari, 'product_code')
    receptii = unify_transactions(raw_receptii, 'product_code')
    
    return produse, livrari, receptii, orders_live

df_produse, df_livrari, df_receptii, df_orders_live = load_data_from_db()

# --- INITIALIZARE STATE PENTRU NAVIGARE ---
if 'active_tab' not in st.session_state:
    st.session_state.active_tab = "📊 Dashboard Executiv"

# --- SIDEBAR FILTRE ---
st.sidebar.image("https://img.icons8.com/clouds/100/analytics.png", width=80)
st.sidebar.title("NEXUS Control Panel")

# 1. Filtru Perioadă
max_date = df_livrari['order_date'].max()
st.sidebar.subheader("📅 Perioadă Analiză")
period_option = st.sidebar.radio(
    "Selectează intervalul:",
    ["1 lună", "3 luni", "6 luni", "12 luni"],
    index=1,
    horizontal=False
)

if period_option == "1 lună":
    start_filter_date = max_date - pd.DateOffset(months=1)
elif period_option == "3 luni":
    start_filter_date = max_date - pd.DateOffset(months=3)
elif period_option == "6 luni":
    start_filter_date = max_date - pd.DateOffset(months=6)
else:
    start_filter_date = max_date - pd.DateOffset(months=12)

filtered_livrari = df_livrari[df_livrari['order_date'] >= start_filter_date]
filtered_receptii = df_receptii[df_receptii['order_date'] >= start_filter_date]

# 2. Filtru Single-select Categorii
st.sidebar.subheader("🏷️ Categorie Produse")
all_categories = df_produse['category'].unique().tolist()
selected_category = st.sidebar.selectbox(
    "Alege categoria:", 
    ["Toate categoriile"] + all_categories
)

if selected_category == "Toate categoriile":
    active_categories = all_categories
else:
    active_categories = [selected_category]

filtered_products = df_produse[df_produse['category'].isin(active_categories)]
valid_product_codes = filtered_products['code'].tolist()

filtered_livrari_cat = filtered_livrari[filtered_livrari['product_code'].isin(valid_product_codes)]
filtered_receptii_cat = filtered_receptii[filtered_receptii['product_code'].isin(valid_product_codes)]

if selected_category == "Toate categoriile":
    unit_label = "unități mixte"
else:
    unit_label = filtered_products['unit'].iloc[0] if not filtered_products.empty else "unități"

# 3. Filtru pentru Gauge (Stoc individual)
st.sidebar.subheader("🎯 Stoc de Verificat")
selected_product_name = st.sidebar.selectbox("Alege un produs:", df_produse['product'].tolist())
selected_product_row = df_produse[df_produse['product'] == selected_product_name].iloc[0]

# --- BUTON DE SALT DIRECT (DASHBOARD -> OPERATIONAL) ---
st.sidebar.markdown("---")
if st.sidebar.button("🔍 Istoricul comenzilor la acest produs", use_container_width=True):
    st.session_state.active_tab = "🔍 Operational Insights"
    st.rerun()

# --- BLOC NAVIGARE NATIV ---
col_nav1, col_nav2 = st.columns(2)
with col_nav1:
    if st.button("📊 Dashboard Executiv", use_container_width=True, type="primary" if st.session_state.active_tab == "📊 Dashboard Executiv" else "secondary"):
        st.session_state.active_tab = "📊 Dashboard Executiv"
        st.rerun()
with col_nav2:
    if st.button("🔍 Operational Insights", use_container_width=True, type="primary" if st.session_state.active_tab == "🔍 Operational Insights" else "secondary"):
        st.session_state.active_tab = "🔍 Operational Insights"
        st.rerun()

st.markdown("---")

# --- CONȚINUT PAGINI ---
if st.session_state.active_tab == "📊 Dashboard Executiv":
    
    if selected_category == "Toate categoriile":
        st.markdown("""
        <div style="color: #475569; background-color: #f1f5f9; border-left: 4px solid #EBA11F; padding: 6px 12px; border-radius: 6px; font-size: 12px; margin-bottom: 15px; font-family: sans-serif;">
        ⚠️ Notă de simulare: Datele utilizate sînt incomplete și doar parțial corecte. După finalizarea bazelor de date și sincronizarea cu WMS și SmartBill acest inconvenient dispare.
        <br><br>  
        ℹ️ <b>Precizare:</b> Toate cantitățile de tip Palet au fost convertite automat în Cutii/Bucăți la nivel de memorie (tabel dB) pentru a oferi grafice consolidate. Analiza valorică (financiară), în curs de implementare, va fi posibilă după completarea bazelor de date. Pentru a evita cumularea cantitativă a unor unități de măsură diferite, se recomandă selectarea unei categorii specifice din meniul din stânga.
        </div>
        
        """, unsafe_allow_html=True)

    # --- RÂNDUL 1: CARDURI KPI CU SPARKLINES ---
    col1, col2, col3, col4 = st.columns(4)

    # KPI 1 - Volum Livrări
    sales_trend_data = filtered_livrari.groupby('month')['quantity'].sum().tolist()
    if not sales_trend_data: 
        sales_trend_data = [0, 0, 0]
    
    with col1:
        total_livrari_qty = filtered_livrari['quantity'].sum()
        html_val = f"{total_livrari_qty:,.0f}"
        kpi_html = '<div class="kpi-card"><div class="kpi-title">Total Volum Livrat</div><div class="kpi-value">' + html_val + ' u.m.</div><div class="kpi-trend trend-up">↑ +14.2% vs prev.</div></div>'
        st.markdown(kpi_html, unsafe_allow_html=True)
        
        spark_line_opt = {
            "xAxis": {"show": False, "type": "category"},
            "yAxis": {"show": False, "type": "value"},
            "grid": {"left": 0, "right": 0, "top": 5, "bottom": 5},
            "series": [{"data": sales_trend_data, "type": "line", "smooth": True, "showSymbol": False, "lineStyle": {"color": "#2ecc71", "width": 2}, "areaStyle": {"color": "rgba(46, 204, 113, 0.1)"}}]
        }
        st_echarts(spark_line_opt, height="50px", key="spark_sales")

    # KPI 2 - Volum Recepții
    with col2:
        total_receptii_qty = filtered_receptii['quantity'].sum()
        html_val_rec = f"{total_receptii_qty:,.0f}"
        kpi_rec_html = '<div class="kpi-card"><div class="kpi-title">Total Volum Recepționat</div><div class="kpi-value">' + html_val_rec + ' u.m.</div><div class="kpi-trend trend-up">↑ +8.5% vs prev.</div></div>'
        st.markdown(kpi_rec_html, unsafe_allow_html=True)
        
        receptii_trend_data = filtered_receptii.groupby('month')['quantity'].sum().tolist()
        if not receptii_trend_data: 
            receptii_trend_data = [0, 0, 0]
            
        spark_bar_opt = {
            "xAxis": {"show": False, "type": "category"},
            "yAxis": {"show": False, "type": "value"},
            "grid": {"left": 0, "right": 0, "top": 5, "bottom": 5},
            "series": [{"data": receptii_trend_data, "type": "bar", "barWidth": "40%", "itemStyle": {"color": "#3498db"}}]
        }
        st_echarts(spark_bar_opt, height="50px", key="spark_receipts")

    # KPI 3 - Alertă Stoc Critic
    with col3:
        stoc_critic_count = len(df_produse[df_produse['stock'] < 30])
        kpi_crit_html = '<div class="kpi-card" title="Vedeți mai jos produsele cu stoc critic"><div class="kpi-title">Alertă Stoc Critic</div><div class="kpi-value">' + str(stoc_critic_count) + ' Prod.</div><div class="kpi-trend trend-down">↓ Necesită atenție!</div></div>'
        st.markdown(kpi_crit_html, unsafe_allow_html=True)
        
        spark_crit_opt = {
            "xAxis": {"show": False, "type": "category"},
            "yAxis": {"show": False, "type": "value"},
            "grid": {"left": 0, "right": 0, "top": 5, "bottom": 5},
            "series": [{"data": [20, 18, 15, stoc_critic_count], "type": "line", "smooth": True, "showSymbol": False, "lineStyle": {"color": "#e74c3c", "width": 2}}]
        }
        st_echarts(spark_crit_opt, height="50px", key="spark_crit")

    # KPI 4 - Clienți Activi
    with col4:
        clienti_activi = filtered_livrari['client'].nunique()
        kpi_cust_html = '<div class="kpi-card"><div class="kpi-title">Clienți Activi în Perioadă</div><div class="kpi-value">' + str(clienti_activi) + ' Clienți</div><div class="kpi-trend trend-up">↑ Stabil</div></div>'
        st.markdown(kpi_cust_html, unsafe_allow_html=True)
        
        spark_cust_opt = {
            "xAxis": {"show": False, "type": "category"},
            "yAxis": {"show": False, "type": "value"},
            "grid": {"left": 0, "right": 0, "top": 5, "bottom": 5},
            "series": [{"data": [2, 3, 2, clienti_activi], "type": "line", "smooth": True, "showSymbol": False, "lineStyle": {"color": "#f1c40f", "width": 2}}]
        }
        st_echarts(spark_cust_opt, height="50px", key="spark_cust")

    st.markdown("---")

    # --- RÂNDUL 2: LINE + BAR ---
    st.subheader("📈 Analiză Vânzări și Distribuție")
    row2_col1, row2_col2 = st.columns([1, 1])

    with row2_col1:
        sales_by_month = filtered_livrari_cat.groupby('month')['quantity'].sum().reset_index()
        months_order = ["November", "December", "January", "February", "March", "April", "May"]
        sales_by_month['month'] = pd.Categorical(sales_by_month['month'], categories=months_order, ordered=True)
        sales_by_month = sales_by_month.sort_values('month')

        smooth_line_options = {
            "title": {"text": "Evoluție Volum Vânzări pe Luni (Unificat Cutii)", "left": "center", "textStyle": {"fontSize": 14, "color": "#4a4a4a"}},
            "tooltip": {"trigger": "axis", "axisPointer": {"type": "cross"}},
            "xAxis": {"type": "category", "data": sales_by_month['month'].tolist()},
            "yAxis": {"type": "value", "name": "Cutii / Bucăți"},
            "grid": {"left": "10%", "right": "5%", "bottom": "15%"},
            "series": [{
                "name": "Cantitate Livrată",
                "data": sales_by_month['quantity'].tolist(),
                "type": "line",
                "smooth": True,
                "lineStyle": {"width": 3, "color": "#2ecc71"},
                "areaStyle": {"color": "rgba(46, 204, 113, 0.2)"},
                "itemStyle": {"color": "#2ecc71"}
            }]
        }
        st_echarts(smooth_line_options, height="350px", key="main_smooth_line")

    with row2_col2:
        top_products = filtered_livrari_cat.groupby('product_code')['quantity'].sum().reset_index()
        top_products = top_products.merge(df_produse, left_on='product_code', right_on='code')
        top_products = top_products.sort_values(by='quantity', ascending=True).tail(5)

        horizontal_bar_options = {
            "title": {"text": "Top 5 Produse Livrate (Unificat Cutii)", "left": "center", "textStyle": {"fontSize": 14, "color": "#4a4a4a"}},
            "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
            "grid": {"left": "3%", "right": "10%", "bottom": "5%", "top": "15%", "containLabel": True},
            "xAxis": {"type": "value", "name": "Cantitate"},
            "yAxis": {"type": "category", "data": top_products['product'].tolist()},
            "series": [{
                "name": "Cantitate totală",
                "type": "bar",
                "data": top_products['quantity'].tolist(),
                "itemStyle": {"color": "#3498db", "borderRadius": [0, 5, 5, 0]},
                "barWidth": "50%"
            }]
        }
        st_echarts(horizontal_bar_options, height="350px", key="top_products_bar")

    st.markdown("---")

    # --- RÂNDUL 3: TREEMAP + COMPARATIV ---
    st.subheader("📊 Volume de Tranzacționare și Fluxuri Globale")
    row3_col1, row3_col2 = st.columns([1, 1])

    treemap_data = []
    if not filtered_livrari_cat.empty:
        client_totals = filtered_livrari_cat.groupby('client')['quantity'].sum().reset_index()
        for idx, row in client_totals.iterrows():
            treemap_data.append({
                "name": str(row['client']),
                "value": int(row['quantity'])
            })

    with row3_col1:
        treemap_options = {
            "title": {
                "text": "Volum Livrări pe Clienți (Unificat Cutii)", 
                "left": "center", 
                "textStyle": {"fontSize": 14, "color": "#4a4a4a"}
            },
            "tooltip": {"trigger": "item", "formatter": f"{{b}}: {{c}} {unit_label} livrate"},
            "series": [{
                "type": "treemap",
                "data": treemap_data,
                "roam": False,
                "top": "20%", 
                "bottom": "5%",
                "label": {"show": True, "position": "inside"},
                "itemStyle": {"borderColor": "#fff", "borderWidth": 1}
            }]
        }
        st_echarts(treemap_options, height="350px", key="treemap_sales")

    with row3_col2:
        monthly_in = filtered_receptii_cat.groupby('month')['quantity'].sum().reindex(months_order, fill_value=0).reset_index()
        monthly_out = filtered_livrari_cat.groupby('month')['quantity'].sum().reindex(months_order, fill_value=0).reset_index()

        compare_bar_options = {
            "title": {"text": "Fluxuri: Intrări (Recepții) vs Ieșiri (Livrări)", "left": "center", "textStyle": {"fontSize": 14, "color": "#4a4a4a"}},
            "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
            "legend": {"data": ["Intrări (Recepții)", "Ieșiri (Livrări)"], "bottom": "0%"},
            "grid": {"bottom": "15%", "top": "15%"},
            "xAxis": {"type": "category", "data": months_order},
            "yAxis": {"type": "value"},
            "series": [
                {
                    "name": "Intrări (Recepții)",
                    "type": "bar",
                    "barWidth": "20%",
                    "data": monthly_in['quantity'].tolist(),
                    "itemStyle": {"color": "#3498db", "borderRadius": [3, 3, 0, 0]}
                },
                {
                    "name": "Ieșiri (Livrări)",
                    "type": "bar",
                    "barWidth": "20%",
                    "data": monthly_out['quantity'].tolist(),
                    "itemStyle": {"color": "#e74c3c", "borderRadius": [3, 3, 0, 0]}
                }
            ]
        }
        st_echarts(compare_bar_options, height="350px", key="compare_in_out")

    # Tabel rapid sincronizat (Centrat la 60% pe Desktop, 100% pe Mobil)
    cat_table_html = """
    <style>
        .responsive-table-container {
            height: 110px; 
            overflow-y: auto; 
            border: 1px solid #e9ecef; 
            border-radius: 8px; 
            font-family: sans-serif; 
            width: 60%; 
            margin: 25px auto 0 auto;
        }
        @media (max-width: 768px) {
            .responsive-table-container {
                width: 100% !important;
                margin-top: 15px !important;
            }
        }
    </style>
    <div class="responsive-table-container">
    <table style="width: 100%; border-collapse: collapse; font-size: 11px; text-align: left; table-layout: fixed;">
    <thead>
    <tr style="background-color: #f8f9fa; border-bottom: 2px solid #dee2e6; position: sticky; top: 0; z-index: 1;">
    <th style="padding: 6px 8px; color: #495057; width: 25%;">Cod Articol</th>
    <th style="padding: 6px 8px; color: #495057; width: 50%;">Denumire Produs</th>
    <th style="padding: 6px 8px; color: #495057; text-align: right; width: 25%;">Stoc Curent (Cutii)</th>
    </tr>
    </thead>
    <tbody>"""
    
    for _, r in filtered_products.iterrows():
        stock_color = "#e74c3c" if r['stock'] < 30 else "#2ecc71"
        cat_table_html += f"""<tr style="border-bottom: 1px solid #dee2e6;">
<td style="padding: 6px 8px; color: #1e293b; font-family: monospace; font-weight: bold; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{r['code']}</td>
<td style="padding: 6px 8px; color: #212529; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{r['product']}</td>
<td style="padding: 6px 8px; text-align: right; font-weight: bold; color: {stock_color};">{r['stock']:.0f} {r['unit']}</td>
</tr>"""
        
    cat_table_html += """</tbody></table></div>"""
    components.html(cat_table_html, height=140) # Mărit puțin înălțimea pentru a respira pe mobil

    st.markdown("---")

    # Date produs individual
    p_code = selected_product_row['code']
    current_stock = int(selected_product_row['stock'])

    data_3m = df_livrari[df_livrari['month'].isin(['March', 'April', 'May'])]
    avg_3m_df = data_3m.groupby('product_code')['quantity'].sum() / 3
    p_avg_3m = round(avg_3m_df.get(p_code, 0.0), 1)

    data_6m = df_livrari[df_livrari['month'].isin(['December', 'January', 'February', 'March', 'April', 'May'])]
    avg_6m_df = data_6m.groupby('product_code')['quantity'].sum() / 6
    p_avg_6m = round(avg_6m_df.get(p_code, 0.0), 1)

    avg_12m_df = df_livrari.groupby('product_code')['quantity'].sum() / 7
    p_avg_12m = round(avg_12m_df.get(p_code, 0.0), 1)

    # Reconstrucție stoc
    monthly_del = df_livrari[df_livrari['product_code'] == p_code].groupby('month')['quantity'].sum()
    monthly_rec = df_receptii[df_receptii['product_code'] == p_code].groupby('month')['quantity'].sum()

    stock_history = {}
    temp_stock = current_stock
    for m in reversed(months_order):
        stock_history[m] = max(0, temp_stock)
        del_qty = monthly_del.get(m, 0)
        rec_qty = monthly_rec.get(m, 0)
        temp_stock = temp_stock + del_qty - rec_qty

    p_stock_3m = round(sum([stock_history[m] for m in ["March", "April", "May"]]) / 3, 1)
    p_stock_6m = round(sum([stock_history[m] for m in ["December", "January", "February", "March", "April", "May"]]) / 6, 1)
    p_stock_12m = round(sum([stock_history[m] for m in months_order]) / 7, 1)

    # --- RÂNDUL 4: GAUGE + COMPARATIV ---
    st.subheader("🚨 Control Stocuri Operative și Viteză Consum")
    row4_col1, row4_col2 = st.columns([1, 1])

    with row4_col1:
        gauge_options = {
            "title": {"text": f"Nivel Stoc: {selected_product_row['code']}", "left": "center", "textStyle": {"fontSize": 13, "color": "#4a4a4a"}},
            "tooltip": {"formatter": "{b} : {c}"},
            "series": [{
                "name": "Stoc Curent",
                "type": "gauge",
                "min": 0,
                "max": 1200,
                "radius": "80%",
                "center": ["50%", "75%"],
                "axisTick": {"show": True, "distance": 0, "length": 3, "lineStyle": {"color": "#333333", "width": 1}},
                "splitLine": {"show": True, "distance": 0, "length": 6, "lineStyle": {"color": "#333333", "width": 1.5}},
                "axisLabel": {"show": False},
                "axisLine": {
                    "lineStyle": {
                        "width": 10,
                        "color": [
                            [0.125, "#e74c3c"],
                            [0.5, "#f1c40f"],
                            [1, "#2ecc71"]
                        ]
                    }
                },
                "detail": {"formatter": "{value}", "fontSize": 18},
                "data": [{"value": current_stock, "name": selected_product_row['unit']}]
            }]
        }
        st_echarts(gauge_options, height="200px", key="stock_gauge")

    with row4_col2:
        consumption_bar_options = {
            "title": {"text": f"Analiză de Echilibru ({selected_product_row['unit']}/lună)", "left": "center", "textStyle": {"fontSize": 13, "color": "#4a4a4a"}},
            "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
            "legend": {"data": ["Consum Mediu Lunar", "Stoc Mediu Disponibil"], "bottom": "0%"},
            "grid": {"left": "10%", "right": "10%", "bottom": "20%", "top": "20%"},
            "xAxis": {"type": "category", "data": ["3 Luni", "6 Luni", "12 Luni"]},
            "yAxis": {"type": "value"},
            "series": [
                {
                    "name": "Consum Mediu Lunar",
                    "type": "bar",
                    "barWidth": "15%", 
                    "data": [p_avg_3m, p_avg_6m, p_avg_12m],
                    "itemStyle": {"color": "#3498db", "borderRadius": [3, 3, 0, 0]}
                },
                {
                    "name": "Stoc Mediu Disponibil",
                    "type": "bar",
                    "barWidth": "15%",
                    "data": [p_stock_3m, p_stock_6m, p_stock_12m],
                    "itemStyle": {"color": "#f1c40f", "borderRadius": [3, 3, 0, 0]}
                }
            ]
        }
        st_echarts(consumption_bar_options, height="200px", key="consumption_bars")

    st.markdown("---")

    # Master plan
    global_data_3m = df_livrari[df_livrari['month'].isin(['March', 'April', 'May'])]
    global_avg_3m = global_data_3m.groupby('product_code')['quantity'].sum() / 3

    global_data_6m = df_livrari[df_livrari['month'].isin(['December', 'January', 'February', 'March', 'April', 'May'])]
    global_avg_6m = global_data_6m.groupby('product_code')['quantity'].sum() / 6

    # --- RÂNDUL 5: TABEL MASTER PLAN ---
    st.subheader("📋 Planificare Stocuri și Sugestii de Comenzi")
    row5_col1, row5_col2 = st.columns([3, 1])

    with row5_col1:
        master_products_sorted = df_produse.copy()
        master_products_sorted['is_selected'] = master_products_sorted['code'] == selected_product_row['code']
        master_products_sorted = master_products_sorted.sort_values(by='is_selected', ascending=False)

        table_html = """<div style="height: 200px; overflow-y: auto; border: 1px solid #e9ecef; border-radius: 8px; font-family: sans-serif;">
<table style="width: 100%; border-collapse: collapse; font-size: 11px; text-align: left; table-layout: fixed;">
<thead>
<tr style="background-color: #f8f9fa; border-bottom: 2px solid #dee2e6; position: sticky; top: 0; z-index: 1;">
<th style="padding: 10px 8px; color: #495057; width: 40%;">Denumire Produs</th>
<th style="padding: 10px 8px; color: #495057; width: 18%;">Cod Articol</th>
<th style="padding: 10px 8px; color: #495057; text-align: right; width: 11%;">Stoc (Cutii)</th>
<th style="padding: 10px 8px; color: #495057; text-align: center; width: 11%; line-height: 1.2;">Medie<br/>Consum<br/>3 luni</th>
<th style="padding: 10px 8px; color: #495057; text-align: center; width: 11%; line-height: 1.2;">Medie<br/>Consum<br/>6 luni</th>
<th style="padding: 10px 8px; color: #495057; text-align: right; width: 10%; font-weight: bold;">Necesar Stoc*</th>
</tr>
</thead>
<tbody>"""
        
        for _, r in master_products_sorted.iterrows():
            is_active = r['code'] == selected_product_row['code']
            stock_color = "#e74c3c" if r['stock'] < 30 else "#2ecc71"
            stock_weight = "bold" if r['stock'] < 30 else "normal"
            
            r_code = r['code']
            r_avg_3m = round(global_avg_3m.get(r_code, 0.0), 1)
            r_avg_6m = round(global_avg_6m.get(r_code, 0.0), 1)
            r_stock = int(r['stock'])

            r_necesar = round((r_avg_3m * 1.5) - r_stock, 1)
            r_necesar = max(0.0, r_necesar)
            
            necesar_color = "#e74c3c" if r_necesar > 0 else "#6c757d"
            necesar_weight = "bold" if r_necesar > 0 else "normal"

            row_bg_color = "#fef08a" if is_active else "transparent"
            row_border = "2px solid #facc15" if is_active else "1px solid #dee2e6"
            star_prefix = "⭐ " if is_active else ""

            short_name = r['product'][:32] + "..." if len(r['product']) > 32 else r['product']

            table_html += f"""<tr style="background-color: {row_bg_color}; border-bottom: {row_border};">
<td style="padding: 6px 8px; font-weight: 500; color: #212529; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{short_name}</td>
<td style="padding: 6px 8px; color: #6c757d; font-family: monospace; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{star_prefix}{r['code']}</td>
<td style="padding: 6px 8px; text-align: right; font-weight: {stock_weight}; color: {stock_color};">{r['stock']:.0f} {r['unit']}</td>
<td style="padding: 6px 8px; text-align: center; color: #475569;">{r_avg_3m} /l</td>
<td style="padding: 6px 8px; text-align: center; color: #475569;">{r_avg_6m} /l</td>
<td style="padding: 6px 8px; text-align: right; font-weight: {necesar_weight}; color: {necesar_color};">{r_necesar} {r['unit']}</td>
</tr>"""
            
        table_html += """</tbody></table></div>"""
        table_html += """<div style="font-size: 10px; color: #6c757d; margin-top: 18px; font-family: sans-serif;">*Calcul Necesar Stoc = (Consum Mediu Lunar pe 3 Luni * 1.5) - Stoc Curent</div>"""
        
        components.html(table_html, height=265)

    with row5_col2:
        critical_products_global = df_produse[df_produse['stock'] < 30]
        
        card_html = """<div style="background-color: #f8f9fa; border-radius: 10px; padding: 15px; box-shadow: 2px 2px 10px rgba(0,0,0,0.05); border: 1px solid #e9ecef; height: 185px; overflow-y: auto; font-family: sans-serif;">
<div style="font-size: 13px; font-weight: bold; color: #1e293b; margin-bottom: 8px;">📋 Listă de comenzi (Order List)</div>"""
        
        if not critical_products_global.empty:
            critical_names_list = []
            for _, cp in critical_products_global.iterrows():
                short_cp_name = cp['product'][:20] + "..." if len(cp['product']) > 20 else cp['product']
                critical_names_list.append(f"<li style='margin-bottom: 4px;'><b>{short_cp_name}</b></li>")
            
            products_list_html = "".join(critical_names_list)
            
            card_html += f"""<div style="font-size: 11px; color: #475569; line-height: 1.4;">
Următoarele articole sunt sub nivelul de siguranță raportat la consumul mediu lunar:
<ul style="margin-top: 6px; margin-bottom: 10px; padding-left: 15px;">
{products_list_html}
</ul>
Se recomandă analizarea unei oportunități de plasare a unei comenzi de aprovizionare.
</div>"""
        else:
            card_html += """<div style="font-size: 11px; color: #2ecc71; line-height: 1.4; margin-top: 10px;">
✅ Toate stocurile din această categorie sunt în parametrii optimi de siguranță raportat la consum. Nu sunt sugerate comenzi noi în acest moment.
</div>"""
            
        card_html += "</div>"
        components.html(card_html, height=265)

# --- TAB 2: OPERATIONAL INSIGHTS (OPTIIMIZAT RESPONSIVE MOBIL) ---
else:
    st.subheader("🔍 Monitorizare Operațională - Rampa / WMS")
    st.markdown("Monitorizarea tranzacțională a fluxului de pregătire, integrarea ERP (Oracle WebHook) și istoricul specific al reperelor din comenzi.")
    
    # Atenționare tip banner responsiv
    st.markdown("""
    <div style="color: #856404; background-color: #fff3cd; border-left: 4px solid #ffc107; padding: 10px 15px; border-radius: 6px; font-size: 11px; margin-top: 10px; margin-bottom: 20px; font-family: sans-serif; line-height: 1.4;">
        ⚠️ <b>Notă de simulare operațională:</b> În mediul de producție real, acești indicatori se actualizează automat în funcție de starea fizică a stocurilor, livrări, intrări și avize de expediție sincronizate cu WMS.
    </div>
    """, unsafe_allow_html=True)

    if not df_orders_live.empty:
        # Selector dinamic de comandă activă
        order_options = [f"{row['order_number']} - {row['client_name']}" for _, row in df_orders_live.iterrows()]
        selected_order_string = st.selectbox("Selectează comanda din Rampă:", order_options)
        
        sel_order_num = selected_order_string.split(" - ")[0]
        active_order = df_orders_live[df_orders_live['order_number'] == sel_order_num].iloc[0]
        
        st.markdown("---")
        
        ops_col1, ops_col2 = st.columns([1, 1])
        
        # --- COLOANA STÂNGA: STATUS COMANDĂ CURENTĂ (CU STILURI MEDIA QUERY) ---
        with ops_col1:
            payload_raw = active_order['payload_logistic'] if active_order['payload_logistic'] else "Nespecificat"
            payload_lines = [line.strip() for line in payload_raw.split(",")]
            
            payload_html_list = ""
            for line in payload_lines:
                payload_html_list += f"<li style='margin-bottom: 4px; color: #475569;'>➔ {line}</li>"
            
            default_address = "București, Str. Logistică nr. 1"
            
            status_panel_html = f"""
            <style>
                body {{ margin: 0; padding: 0; }}
                .status-card {{
                    background-color: #f8f9fa; 
                    border-radius: 8px; 
                    border: 1px solid #e2e8f0; 
                    padding: 20px; 
                    font-family: 'Segoe UI', sans-serif; 
                    min-height: 380px; 
                    box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
                    box-sizing: border-box;
                }}
                @media (max-width: 768px) {{
                    .status-card {{
                        padding: 12px !important;
                        min-height: auto !important;
                    }}
                    .status-card ul {{
                        padding-left: 10px !important;
                    }}
                    h1, h2, h3, div, span, ul, li {{
                        font-size: 95% !important;
                    }}
                }}
            </style>
            <div class="status-card">
                <div style="color: #64748b; font-size: 12px; font-weight: bold; letter-spacing: 0.05em; border-bottom: 1px dashed #cbd5e1; padding-bottom: 6px; margin-bottom: 15px; text-transform: uppercase;">
                    --- STATUS COMANDĂ CURENTĂ ---
                </div>
                
                <div style="margin-bottom: 15px;">
                    <span style="color: #64748b; font-size: 11px; font-weight: 600;">Beneficiar:</span> 
                    <span style="color: #0284c7; font-size: 13px; font-weight: bold; display: block;">{active_order['client_name']} (CUI: RO113456)</span>
                </div>
                
                <div style="margin-bottom: 15px;">
                    <span style="color: #64748b; font-size: 11px; font-weight: 600;">Adresă:</span> 
                    <span style="color: #334155; font-size: 12px; display: block;">{default_address}</span>
                </div>
                
                <div style="margin-bottom: 20px;">
                    <span style="color: #64748b; font-size: 11px; font-weight: 600; display: block; margin-bottom: 4px;">Comandă lansată pentru:</span>
                    <ul style="margin: 0; padding-left: 15px; font-size: 12px; line-height: 1.6;">
                        {payload_html_list}
                    </ul>
                </div>
                
                <div style="background-color: #f1f5f9; border-radius: 6px; padding: 12px; border-left: 4px solid #0284c7; margin-bottom: 15px;">
                    <div style="color: #334155; font-size: 11px; font-weight: bold; letter-spacing: 0.03em;">[RĂSPUNS AȘTEPTAT DE LA ORACLE (WebHook)]</div>
                    <div style="color: #0284c7; font-size: 13px; font-weight: bold; margin-top: 4px;">Status: {active_order['status']}</div>
                    <div style="color: #64748b; font-size: 10px; font-style: italic; margin-top: 4px; line-height: 1.4;">
                        (Câmpurile "Avizat la data de...", "Nr. Auto" și "Nume Șofer" se vor completa automat în NEXUS DB când Oracle închide avizul de expediție.)
                    </div>
                </div>
                
                <div style="background-color: #ecfdf5; border-radius: 6px; padding: 12px; border-left: 4px solid #10b981;">
                    <div style="color: #065f46; font-size: 11px; font-weight: bold;">[URMĂTORUL PAS AUTOMAT]</div>
                    <div style="color: #047857; font-size: 11px; margin-top: 2px;">
                        La finalizarea comenzii ➔ NEXUS trimite Date Facturare la SmartBill (Aviz Însoțire)
                    </div>
                </div>
            </div>
            """
            components.html(status_panel_html, height=500)

        # --- COLOANA DREAPTĂ: DETALIU PRODUS ȘI ISTORIC (RESPONSIVE GRID) ---
        with ops_col2:
            target_prod_code = "BKTp721" if "BKTp721" in payload_raw else df_produse['code'].iloc[0]
            
            prod_row_list = df_produse[df_produse['code'] == target_prod_code]
            if not prod_row_list.empty:
                prod_row = prod_row_list.iloc[0]
                prod_name = prod_row['product']
                unit_type = prod_row['unit']
                current_aggregated_stock = prod_row['stock']
            else:
                prod_name = "Role Autocut Albe TAD 220m"
                unit_type = "buc"
                current_aggregated_stock = 111
            
            nir_code = "NIR-4451"
            
            stoc_paleti_buc = int(current_aggregated_stock // 48)
            stoc_cutii_buc = int(current_aggregated_stock % 48)
            
            history_delivery = df_livrari[df_livrari['product_code'] == target_prod_code]
            
            if not history_delivery.empty:
                last_delivery_row = history_delivery.sort_values(by='order_date', ascending=False).iloc[0]
                last_delivery_date_str = last_delivery_row['order_date'].strftime('%d.%m.%Y')
                
                last_qty = int(last_delivery_row['quantity'])
                last_pals = int(last_qty // 48)
                last_boxes = int(last_qty % 48)
                
                last_delivery_qty_str = f"{last_pals} Palet + {last_boxes} Cuti" if last_pals > 0 else f"{last_boxes} Cuti"
                
                total_12m_qty = history_delivery['quantity'].sum()
                total_12m_palets = max(1, round(total_12m_qty / 48))
            else:
                last_delivery_date_str = "12.12.2023"
                last_delivery_qty_str = "1 Palet + 5 Cuti"
                total_12m_palets = 142

            product_history_html = f"""
            <style>
                body {{ margin: 0; padding: 0; }}
                .history-card {{
                    background-color: #f8f9fa; 
                    border-radius: 8px; 
                    border: 1px solid #e2e8f0; 
                    padding: 20px; 
                    font-family: 'Segoe UI', sans-serif; 
                    min-height: 380px; 
                    box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
                    box-sizing: border-box;
                }}
                .grid-4 {{
                    display: grid; 
                    grid-template-columns: repeat(4, 1fr); 
                    gap: 10px; 
                    margin-bottom: 20px;
                }}
                .grid-3 {{
                    display: grid; 
                    grid-template-columns: repeat(3, 1fr); 
                    gap: 10px;
                    margin-bottom: 20px;
                }}
                @media (max-width: 768px) {{
                    .history-card {{
                        padding: 12px !important;
                        min-height: auto !important;
                    }}
                    .grid-4 {{
                        grid-template-columns: repeat(2, 1fr) !important;
                        gap: 8px !important;
                        margin-bottom: 12px !important;
                    }}
                    .grid-3 {{
                        grid-template-columns: 1fr !important;
                        gap: 8px !important;
                        margin-bottom: 12px !important;
                    }}
                    h1, h2, h3, div, span {{
                        font-size: 95% !important;
                    }}
                }}
            </style>
            <div class="history-card">
                <div style="color: #1e293b; font-size: 14px; font-weight: bold; margin-bottom: 12px; border-bottom: 2px solid #e2e8f0; padding-bottom: 8px;">
                    {prod_name}
                </div>
                
                <!-- Grilele superioare (Responsive 2x2 pe Mobil) -->
                <div class="grid-4">
                    <div style="background-color: #ffffff; padding: 8px; border-radius: 6px; border: 1px solid #e2e8f0; text-align: center;">
                        <span style="color: #64748b; font-size: 9px; display: block; font-weight: 600;">Cod Produs (NEXUS)</span>
                        <span style="color: #1e293b; font-size: 11px; font-weight: bold; font-family: monospace;">{target_prod_code}</span>
                    </div>
                    <div style="background-color: #ffffff; padding: 8px; border-radius: 6px; border: 1px solid #e2e8f0; text-align: center;">
                        <span style="color: #64748b; font-size: 9px; display: block; font-weight: 600;">Cod NIR</span>
                        <span style="color: #1e293b; font-size: 11px; font-weight: bold; font-family: monospace;">{nir_code}</span>
                    </div>
                    <div style="background-color: #ffffff; padding: 8px; border-radius: 6px; border: 1px solid #e2e8f0; text-align: center;">
                        <span style="color: #64748b; font-size: 9px; display: block; font-weight: 600;">Stoc Paleți Întregi</span>
                        <span style="color: #1e293b; font-size: 13px; font-weight: bold;">{stoc_paleti_buc} buc</span>
                    </div>
                    <div style="background-color: #ffffff; padding: 8px; border-radius: 6px; border: 1px solid #e2e8f0; text-align: center;">
                        <span style="color: #64748b; font-size: 9px; display: block; font-weight: 600;">Stoc Cutii Libere</span>
                        <span style="color: #1e293b; font-size: 13px; font-weight: bold;">{stoc_cutii_buc} buc</span>
                    </div>
                </div>
                
                <!-- Istoric Livrări (Responsive pe verticală pe Mobil) -->
                <div style="margin-bottom: 20px;">
                    <div style="display: flex; align-items: center; color: #1e293b; font-size: 12px; font-weight: bold; margin-bottom: 10px;">
                        <span style="margin-right: 6px;">📊</span> Istoric Livrări (Acest Produs)
                    </div>
                    
                    <div class="grid-3">
                        <div style="background-color: #f1f5f9; padding: 10px; border-radius: 6px; border-left: 3px solid #0284c7;">
                            <span style="color: #64748b; font-size: 10px; display: block; font-weight: bold;">Ultima livrare:</span>
                            <span style="color: #0284c7; font-size: 12px; font-weight: bold; display: block; margin-top: 4px;">{last_delivery_date_str}</span>
                        </div>
                        <div style="background-color: #f1f5f9; padding: 10px; border-radius: 6px; border-left: 3px solid #0284c7;">
                            <span style="color: #64748b; font-size: 10px; display: block; font-weight: bold;">Cantitate livrată:</span>
                            <span style="color: #0284c7; font-size: 12px; font-weight: bold; display: block; margin-top: 4px;">{last_delivery_qty_str}</span>
                        </div>
                        <div style="background-color: #f0fdf4; padding: 10px; border-radius: 6px; border-left: 3px solid #10b981;">
                            <span style="color: #15803d; font-size: 10px; display: block; font-weight: bold;">Volum total (12 luni):</span>
                            <span style="color: #16a34a; font-size: 12px; font-weight: bold; display: block; margin-top: 4px;">{total_12m_palets} Paleți</span>
                        </div>
                    </div>
                </div>
                
                <div>
                    <div style="color: #1e293b; font-size: 13px; font-weight: bold; margin-bottom: 10px;">
                        3. Cantitate Comandată
                    </div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                        <div>
                            <span style="color: #64748b; font-size: 10px; font-weight: bold; display: block; margin-bottom: 4px;">Nr. PALEȚI</span>
                            <div style="background-color: #ffffff; border: 1px solid #cbd5e1; padding: 8px; border-radius: 6px; font-size: 14px; font-weight: bold; color: #1e293b; text-align: center;">
                                1
                            </div>
                        </div>
                        <div>
                            <span style="color: #64748b; font-size: 10px; font-weight: bold; display: block; margin-bottom: 4px;">Nr. CUTII (Fracție)</span>
                            <div style="background-color: #ffffff; border: 1px solid #cbd5e1; padding: 8px; border-radius: 6px; font-size: 14px; font-weight: bold; color: #1e293b; text-align: center;">
                                11
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            """
            components.html(product_history_html, height=500)
            
    else:
        st.info("În acest moment nu există comenzi live active în rampa WMS.")
