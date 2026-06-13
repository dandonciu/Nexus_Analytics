import streamlit as st
from streamlit_echarts import st_echarts
import pandas as pd

def render_row2(filtered_livrari_cat, df_produse):
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
