import streamlit as st
from streamlit_echarts import st_echarts

def render_row4(selected_product_row, df_livrari, df_receptii):
    st.subheader("🚨 Control Stocuri Operative și Viteză Consum")
    row4_col1, row4_col2 = st.columns([1, 1])

    p_code = selected_product_row['code']
    current_stock = int(selected_product_row['stock'])
    months_order = ["November", "December", "January", "February", "March", "April", "May"]

    # Date istoric vânzări (3m, 6m, 12m)
    data_3m = df_livrari[df_livrari['month'].isin(['March', 'April', 'May'])]
    avg_3m_df = data_3m.groupby('product_code')['quantity'].sum() / 3
    p_avg_3m = round(avg_3m_df.get(p_code, 0.0), 1)

    data_6m = df_livrari[df_livrari['month'].isin(['December', 'January', 'February', 'March', 'April', 'May'])]
    avg_6m_df = data_6m.groupby('product_code')['quantity'].sum() / 6
    p_avg_6m = round(avg_6m_df.get(p_code, 0.0), 1)

    avg_12m_df = df_livrari.groupby('product_code')['quantity'].sum() / 7
    p_avg_12m = round(avg_12m_df.get(p_code, 0.0), 1)

    # Reconstrucție istoric stocuri
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
                            [0.125, "#e74c3c"],  # Zona roșie corelată sub 150 unități (150/1200 = 0.125)
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
