import streamlit as st
import sqlite3
import pandas as pd
import os

# Importuri din modulele restructurate
from utils import unify_products, unify_transactions
from views.dashboard_view import render_dashboard
from views.insights_view import render_insights

# Configurare layout pagină
st.set_page_config(
    page_title="NEXUS Executive Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Stiluri CSS globale integrate (cu optimizări pentru rezoluții de mobil)
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

    /* Premium Dark Sidebar styles */
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

    [data-testid="stSidebar"] label[data-baseweb="radio"] div,
    [data-testid="stSidebar"] label[data-baseweb="radio"] p,
    [data-testid="stSidebar"] div[data-testid="stWidgetLabel"] p {
        color: #f1f5f9 !important;
    }
    
    [data-testid="stSidebarUserContent"]::after {
        content: "©DSCM Tech";
        position: absolute;
        bottom: 2px;
        left: 15%;
        transform: translateX(-50%);
        font-size: 8px;
        color: #DEDEDE;
        font-family: sans-serif;
    }

    [data-testid="stSidebar"] button:hover {
        background-color: #C7C5C6 !important;
        color: #ffffff !important;
        border-color: #475569 !important;
    }

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

# Fundal Sidebar personalizat
bg_image_path = "sidebar_bg.jpg"
if os.path.exists(bg_image_path):
    import base64
    with open(bg_image_path, "rb") as f:
        img_data = f.read()
    b64_img = base64.b64encode(img_data).decode()
    css_style = "<style>[data-testid='stSidebar'] { background-image: linear-gradient(rgba(30, 41, 59, 0.4), rgba(30, 41, 59, 0.4)), url('data:image/jpeg;base64," + b64_img + "') !important; background-size: cover !important; background-position: center !important; }</style>"
    st.markdown(css_style, unsafe_allow_html=True)
else:
    st.markdown("<style>[data-testid='stSidebar'] { background-color: #1e293b !important; }</style>", unsafe_allow_html=True)

# Încărcare centralizată a datelor din SQLite
DB_PATH = "nexus_buffer.db"

def load_data_from_db():
    conn = sqlite3.connect(DB_PATH)
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
    
    # Procesare unificată prin modulul utilitar (calculat o singură dată)
    produse = unify_products(raw_produse)
    livrari = unify_transactions(raw_livrari, 'product_code')
    receptii = unify_transactions(raw_receptii, 'product_code')
    
    return produse, livrari, receptii, orders_live

df_produse, df_livrari, df_receptii, df_orders_live = load_data_from_db()

# Gestiune sesiune pentru navigare nativă
if 'active_tab' not in st.session_state:
    st.session_state.active_tab = "📊 Dashboard Executiv"

# --- SIDEBAR INTERFAȚĂ & FILTRE ---
st.sidebar.image("https://img.icons8.com/clouds/100/analytics.png", width=80)
st.sidebar.title("NEXUS Control Panel")

# 1. Selector Perioadă de Analiză
max_date = df_livrari['order_date'].max()
st.sidebar.subheader("📅 Perioadă Analiză")
period_option = st.sidebar.radio(
    "Selectează intervalul:",
    ["1 lună", "3 luni", "6 luni", "12 luni"],
    index=2,
    key="global_period_selector"
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

# 2. Selector Categorii
st.sidebar.subheader("🏷️ Categorie Produse")
all_categories = df_produse['category'].unique().tolist()
selected_category = st.sidebar.selectbox(
    "Alege categoria:", 
    ["Toate categoriile"] + all_categories,
    key="global_category_selector"
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

# 3. Selector Produs Individual (utilizat pentru Gauge)
st.sidebar.subheader("🎯 Stoc de Verificat")
selected_product_name = st.sidebar.selectbox("Alege un produs:", df_produse['product'].tolist(), key="global_product_selector")
selected_product_row = df_produse[df_produse['product'] == selected_product_name].iloc[0]

# Salt dinamic din Sidebar către pagina de date operaționale
st.sidebar.markdown("---")
if st.sidebar.button("🔍 Istoricul comenzilor la acest produs", use_container_width=True, key="sidebar_jump_button"):
    st.session_state.active_tab = "🔍 Operational & Strategic Insights"
    st.rerun()

# Structura header de navigare nativă
col_nav1, col_nav2 = st.columns(2)
with col_nav1:
    if st.button("📊 Dashboard Executiv", use_container_width=True, type="primary" if st.session_state.active_tab == "📊 Dashboard Executiv" else "secondary", key="nav_dash_btn"):
        st.session_state.active_tab = "📊 Dashboard Executiv"
        st.rerun()
with col_nav2:
    if st.button("🔍 Operational & Strategic Insights", use_container_width=True, type="primary" if st.session_state.active_tab == "🔍 Operational & Strategic Insights" else "secondary", key="nav_insights_btn"):
        st.session_state.active_tab = "🔍 Operational & Strategic Insights"
        st.rerun()

st.markdown("---")

# Rutare către paginile corespunzătoare bazată pe starea sesiunii
if st.session_state.active_tab == "📊 Dashboard Executiv":
    render_dashboard(
        filtered_livrari, 
        filtered_receptii, 
        df_produse, 
        filtered_products, 
        filtered_livrari_cat, 
        filtered_receptii_cat, 
        selected_product_row, 
        unit_label, 
        df_livrari, 
        df_receptii,
        selected_category
    )
else:
    render_insights(df_orders_live, df_produse, df_livrari, df_receptii)
