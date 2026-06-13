import streamlit as st
from streamlit_echarts import st_echarts
import streamlit.components.v1 as components

def render_row3(filtered_livrari_cat, filtered_receptii_cat, filtered_products, unit_label):
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

    months_order = ["November", "December", "January", "February", "March", "April", "May"]

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

    # Tabel rapid sincronizat (Responsiv pe Mobil / Centrat la 60% pe Desktop)
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
        stock_color = "#e74c3c" if r['stock'] < 150 else "#2ecc71"  # Sincronizare prag 150
        cat_table_html += f"""<tr style="border-bottom: 1px solid #dee2e6;">
<td style="padding: 6px 8px; color: #1e293b; font-family: monospace; font-weight: bold; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{r['code']}</td>
<td style="padding: 6px 8px; color: #212529; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{r['product']}</td>
<td style="padding: 6px 8px; text-align: right; font-weight: bold; color: {stock_color};">{r['stock']:.0f} {r['unit']}</td>
</tr>"""
        
    cat_table_html += """</tbody></table></div>"""
    components.html(cat_table_html, height=140)
