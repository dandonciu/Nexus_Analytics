import streamlit as st
from rows.row1_kpi import render_row1
from rows.row2_sales import render_row2
from rows.row3_flows import render_row3
from rows.row4_gauge import render_row4
from rows.row5_planning import render_row5

def render_dashboard(filtered_livrari, filtered_receptii, df_produse, filtered_products, filtered_livrari_cat, filtered_receptii_cat, selected_product_row, unit_label, df_livrari, df_receptii, selected_category):
    if selected_category == "Toate categoriile":
        st.markdown("""
        <div style="color: #475569; background-color: #f1f5f9; border-left: 4px solid #EBA11F; padding: 6px 12px; border-radius: 6px; font-size: 12px; margin-bottom: 15px; font-family: sans-serif;">
        ⚠️ <b>Notă de simulare:</b> Datele utilizate sînt incomplete și doar parțial corecte. După finalizarea bazelor de date și sincronizarea cu WMS și SmartBill acest inconvenient dispare.
        <br><br>  
        ℹ️ <b>Precizare:</b> Toate cantitățile de tip Palet au fost convertite automat în Cutii/Bucăți la nivel de memorie (tabel dB) pentru a oferi grafice consolidate. Analiza valorică (financiară), în curs de implementare, va fi posibilă după completarea bazelor de date. Pentru a evita cumularea cantitativă a unor unități de măsură diferite, se recomandă selectarea unei categorii specifice din meniul din stânga.
        </div>
        """, unsafe_allow_html=True)

    # Executăm rândurile izolate
    render_row1(filtered_livrari, filtered_receptii, df_produse)
    st.markdown("---")
    render_row2(filtered_livrari_cat, df_produse)
    st.markdown("---")
    render_row3(filtered_livrari_cat, filtered_receptii_cat, filtered_products, unit_label)
    st.markdown("---")
    render_row4(selected_product_row, df_livrari, df_receptii)
    st.markdown("---")
    render_row5(df_produse, df_livrari, selected_product_row)
