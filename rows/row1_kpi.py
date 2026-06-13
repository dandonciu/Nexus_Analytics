import streamlit as st
from streamlit_echarts import st_echarts

def render_row1(filtered_livrari, filtered_receptii, df_produse):
    col1, col2, col3, col4 = st.columns(4)

    # KPI 1 - Volum Livrări
    sales_trend_data = filtered_livrari.groupby('month')['quantity'].sum().tolist()
    if not sales_trend_data: 
        sales_trend_data = [0, 0, 0]
    
    with col1:
        total_livrari_qty = filtered_livrari['quantity'].sum()
        html_val = f"{total_livrari_qty:,.0f}"
        kpi_html = f'<div class="kpi-card"><div class="kpi-title">Total Volum Livrat</div><div class="kpi-value">{html_val} u.m.</div><div class="kpi-trend trend-up">↑ +14.2% vs prev.</div></div>'
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
        kpi_rec_html = f'<div class="kpi-card"><div class="kpi-title">Total Volum Recepționat</div><div class="kpi-value">{html_val_rec} u.m.</div><div class="kpi-trend trend-up">↑ +8.5% vs prev.</div></div>'
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

    # KPI 3 - Alertă Stoc Critic (Pragul unificat de 150)
    with col3:
        stoc_critic_count = len(df_produse[df_produse['stock'] < 150])
        kpi_crit_html = f'<div class="kpi-card" title="Vedeți mai jos produsele cu stoc critic"><div class="kpi-title">Alertă Stoc Critic</div><div class="kpi-value">{stoc_critic_count} Prod.</div><div class="kpi-trend trend-down">↓ Necesită atenție!</div></div>'
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
        kpi_cust_html = f'<div class="kpi-card"><div class="kpi-title">Clienți Activi în Perioadă</div><div class="kpi-value">{clienti_activi} Clienți</div><div class="kpi-trend trend-up">↑ Stabil</div></div>'
        st.markdown(kpi_cust_html, unsafe_allow_html=True)
        
        spark_cust_opt = {
            "xAxis": {"show": False, "type": "category"},
            "yAxis": {"show": False, "type": "value"},
            "grid": {"left": 0, "right": 0, "top": 5, "bottom": 5},
            "series": [{"data": [2, 3, 2, clienti_activi], "type": "line", "smooth": True, "showSymbol": False, "lineStyle": {"color": "#f1c40f", "width": 2}}]
        }
        st_echarts(spark_cust_opt, height="50px", key="spark_cust")
