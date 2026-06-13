import streamlit as st
import streamlit.components.v1 as components

def render_row5(df_produse, df_livrari, selected_product_row):
    st.subheader("📋 Planificare Stocuri și Sugestii de Comenzi")
    row5_col1, row5_col2 = st.columns([3, 1])

    # Date consum global mediu
    global_data_3m = df_livrari[df_livrari['month'].isin(['March', 'April', 'May'])]
    global_avg_3m = global_data_3m.groupby('product_code')['quantity'].sum() / 3

    global_data_6m = df_livrari[df_livrari['month'].isin(['December', 'January', 'February', 'March', 'April', 'May'])]
    global_avg_6m = global_data_6m.groupby('product_code')['quantity'].sum() / 6

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
            stock_color = "#e74c3c" if r['stock'] < 150 else "#2ecc71"  # Prag sincronizat la 150
            stock_weight = "bold" if r['stock'] < 150 else "normal"
            
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
        critical_products_global = df_produse[df_produse['stock'] < 150]  # Prag sincronizat la 150
        
        card_html = """<div style="background-color: #f8f9fa; border-radius: 10px; padding: 15px; box-shadow: 2px 2px 10px rgba(0,0,0,0.05); border: 1px solid #e9ecef; height: 185px; overflow-y: auto; font-family: sans-serif;">
<div style="font-size: 13px; font-weight: bold; color: #1e293b; margin-bottom: 8px;">📋 Listă de comenzi (Order List)</div>"""
        
        if not critical_products_global.empty:
            critical_names_list = []
            for _, cp in critical_products_global.iterrows():
                short_cp_name = cp['product'][:20] + "..." if len(cp['product']) > 20 else cp['product']
                critical_names_list.append(f"<li style='margin-bottom: 4px;'><b>{short_cp_name}</b></li>")
            
            products_list_html = "".join(critical_names_list)
            
            card_html += f"""<div style="font-size: 11px; color: #475569; line-height: 1.4;">
Următoarele articole sunt sub pragul de alertă unitar de 150 unități:
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
