import streamlit as st
import pandas as pd
import io
import os
from streamlit_echarts import st_echarts

# --- DATE DE REZERVĂ (FALLBACKS) ÎN CAZ CĂ FIȘIERELE CSV NU SUNT ÎNCĂ SALVATE ---
ALERTA_STOC_DEFAULT = """Produs,Stoc curent (cutii),Stoc în paleți,Paleți ocupați,Grad ocupare,Consum mediu lunar,Luni acoperire,Termen aprovizionare,Gap,Punct comandă,Urgență,Acțiune,Furnizor,Categorie
Hârtie igienică,150,1.5,2,75%,1500,0.1,1.5,-1.4,2550,🔴 CRITIC,Comandă 24 paleți (2.400 cutii),China Import,Hârtie
Șervețele,800,2.7,3,90%,3000,0.3,0.25,-0.05,4500,🟡 MARE,Comandă 39 paleți (3.900 cutii),Europa Dist,Hârtie
Soluție geamuri,2100,7,7,100%,1200,1.75,0.5,1.25,2400,🟢 OK,Așteaptă 2 săptămâni,Furnizor Local,Soluții
"""

ANALIZA_ROTATIE_DEFAULT = """Produs,Valoare stoc,Rotație anuală,Zile în stoc,Clasificare ABC,% din venituri,% din spațiu depozit,Decizie recomandată,Categorie
Hârtie igienică 2 straturi,15000,12,30,A,35%,25%,✅ Menține stoc de siguranță mare,Hârtie
Șervețele profesionale,8500,8,45,B,18%,15%,⚠️ Optimizează cantități comandă,Hârtie
Soluție geamuri premium,12000,2,180,C,3%,20%,❌ Redu stoc masiv / elimină din portofoliu,Soluții
"""

ANOMALII_DEFAULT = """Produs,Vânzări săptămâna asta,Media 4 săptămâni,Variație %,Trend,Posibilă cauză,Acțiune,Categorie
Hârtie igienică 2 straturi,1200,680,76,↑↑,Hotel Central a deschis aripă nouă,Verifică dacă e temporar,Hârtie
Soluție geamuri 5L,45,120,-62,↓↓,Client Office Park a trecut la concurență,Sună imediat clientul,Soluții
Șervețele colorate,380,150,153,↑↑,Sezon evenimente?,Verifică stocul disponibil,Hârtie
"""

DECID_APROVIZIONARE_DEFAULT = """Produs,Stoc curent,Consum mediu lunar,Trend %,Sezon,Punct de comandă,Stoc minim dinamic,Gap vs punct comandă,Cantitate recomandată,Paleți necesari,Grad umplere,Cost/palet,Cost total,Acțiune,Furnizor
Hârtie igienică,150,1500,15,↑,2550,300,-2400,2400,24,100%,50,1200,🔴 COMANDĂ ACUM,China Import
Șervețele,800,3000,-5,→,4500,600,-3700,3900,39,45%,40,1560,🔴 COMANDĂ ACUM,Europa Dist
Soluție geamuri,2100,1200,-20,↓,2400,400,-300,600,6,100%,60,360,🟡 COMANDĂ,Furnizor Local
Prosoape extra,3500,3000,2,→,4500,600,1000,0,0,0%,0,0,🟢 AȘTEAPTĂ,Europa Dist
"""

PLANIFICARE_COMENZI_DEFAULT = """Produs,Stoc curent,Vânzări medii/zi,Zile acoperire,Termen aprovizionare,Gap (zile),Cantitate recomandată,Furnizor,Cost estimat,Prioritate,Categorie
Hârtie igienică 2 straturi,150,50,3,45,-42,2250,China Import,8500,🔴 URGENT,Hârtie
Șervețele profesionale,800,100,8,7,-1,1500,Europa Dist,1200,🟡 MARE,Hârtie
Prosoape hârtie extra,2100,100,21,14,7,0,Europa Dist,0,🟢 NORMAL,Hârtie
"""

STATUS_LIVRARE_DEFAULT = """Nr. comandă,Furnizor,Dată comandă,Dată promisă livrare,Întârziere (zile),Produse,Valoare,Status,Impact dacă nu vine,Acțiune
PO-2026-089,China Import,1 mai,15 iunie,0,Hârtie igienică,8500,🟡 În tranzit,47 clienți fără marfă 42 zile,Sună forwarder
PO-2026-091,Europa Dist,5 iunie,12 iunie,-3,Șervețele,1200,🟢 OK,-,Monitorizează
PO-2026-085,China Import,15 aprilie,1 iunie,12,Prosoape extra,3200,🔴 ÎNTÂRZIAT,15 clienți afectați,Sună furnizor cere penalizări
"""

# --- FUNCȚIE AJUTĂTOARE DE CITIRE DIRECTĂ CU DETECTARE UTF-8 BOM ---
def safe_read_csv(filename, default_str):
    if os.path.exists(filename):
        try:
            return pd.read_csv(filename, encoding='utf-8-sig')
        except Exception:
            pass
    return pd.read_csv(io.StringIO(default_str))

# --- RENDERER PAGINĂ PRINCIPALĂ ---
def render_insights(df_orders_live, df_produse, df_livrari, df_receptii):
    # Încărcare dinamică a fișierelor CSV (Fizic sau Fallback automat)
    df_alerta_stoc = safe_read_csv("alerta_stoc.csv", ALERTA_STOC_DEFAULT)
    df_rotatie = safe_read_csv("analiza_rotatie_&_ABC.csv", ANALIZA_ROTATIE_DEFAULT)
    df_anomalii = safe_read_csv("anomalii&trenduri.csv", ANOMALII_DEFAULT)
    df_decizie_aprov = safe_read_csv("decizie_aprovizionare_predictiva.csv", DECID_APROVIZIONARE_DEFAULT)
    df_plan_comenzi = safe_read_csv("planificare_comenzi.csv", PLANIFICARE_COMENZI_DEFAULT)
    df_status_livrari = safe_read_csv("status_livrare.csv", STATUS_LIVRARE_DEFAULT)

    # 3 SUB-TAB-URI STRUCTURATE CONFORM PLANULUI
    tab_a, tab_b, tab_c = st.tabs([
        "👥 2.a) Sănătate Clienți & Anomalii", 
        "🚛 2.b) Aprovizionare & Furnizori", 
        "📊 2.c) Prioritizare Clienți (Pareto 80/20)"
    ])

    # =========================================================================
    # TAB 2.a) ISTORIC COMENZI & ANOMALII DE CONSUM
    # =========================================================================
    with tab_a:
        st.markdown("### 👥 Identificare Clienți în Risc și Anomalii de Vânzare")
        
        col_st, col_dr = st.columns([1, 1])
        
        with col_st:
            st.markdown("##### 🔴 Alerte Clienți Inactivi (Fără comenzi în ultimele 14 zile)")
            # Calcul dinamic pe baza livrărilor reale din baza de date
            if not df_livrari.empty:
                max_date = df_livrari['order_date'].max()
                client_last_order = df_livrari.groupby('client')['order_date'].max().reset_index()
                client_last_order['Zile de la ultima comandă'] = (max_date - client_last_order['order_date']).dt.days
                
                # Definim riscul la 14 zile inactivitate
                clienți_risc = client_last_order[client_last_order['Zile de la ultima comandă'] >= 14].copy()
                clienți_risc['Acțiune Urgentă'] = "🔴 DE SUNAT ACUM"
                
                if not clienți_risc.empty:
                    st.dataframe(
                        clienți_risc.sort_values(by='Zile de la ultima comandă', ascending=False),
                        use_container_width=True,
                        hide_index=True
                    )
                else:
                    st.success("Toți clienții din bază au comandat în ultimele 14 zile.")
            else:
                st.info("Lipsă date tranzacționale în DB.")

        with col_dr:
            st.markdown("##### 📈 Anomalii și Deviații de Consum în Săptămâna Curentă")
            
            # Filtru interactiv pentru variație minimă
            min_var = st.slider("Filtrează după variație minimă (%)", min_value=10, max_value=200, value=30, key="slider_var_anomalii")
            
            # Procesare date din anomalii&trenduri.csv
            df_anomalii_filtered = df_anomalii.copy()
            # Curățăm caracterul '%' dacă există și convertim în float
            if df_anomalii_filtered['Variație %'].dtype == object:
                df_anomalii_filtered['Var_Float'] = df_anomalii_filtered['Variație %'].str.replace('%', '').str.replace('+', '').astype(float)
            else:
                df_anomalii_filtered['Var_Float'] = df_anomalii_filtered['Variație %'].astype(float)
                
            df_anomalii_show = df_anomalii_filtered[df_anomalii_filtered['Var_Float'].abs() >= min_var]
            
            st.dataframe(
                df_anomalii_show.drop(columns=['Var_Float'], errors='ignore'),
                use_container_width=True,
                hide_index=True
            )

    # =========================================================================
    # TAB 2.b) APROVIZIONARE & FURNIZORI (MODULUL LOGISTIC)
    # =========================================================================
    with tab_b:
        st.markdown("### 🚛 Managementul Aprovizionării și Evaluarea Riscului la Furnizor")
        
        # Filtre globale pentru panoul de aprovizionare
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            all_furnizori = list(df_alerta_stoc['Furnizor'].dropna().unique()) if 'Furnizor' in df_alerta_stoc.columns else ["China Import", "Europa Dist", "Furnizor Local"]
            sel_furnizor = st.multiselect("Filtrează după Furnizor:", all_furnizori, default=all_furnizori, key="multisel_furnizori")
        with col_f2:
            all_urgencies = list(df_alerta_stoc['Urgență'].dropna().unique())
            sel_urgency = st.multiselect("Filtrează după Nivel Urgență:", all_urgencies, default=all_urgencies, key="multisel_urgente")
            
        st.markdown("---")
        
        # TABEL 1: Alertă stoc cu context decizional (alerta_stoc.csv)
        st.markdown("##### ⚠️ Tabel 1: Alerte Stoc Operativ cu Context de Achiziție")
        df_t1_filtered = df_alerta_stoc[
            df_alerta_stoc['Urgență'].isin(sel_urgency) & 
            df_alerta_stoc['Furnizor'].isin(sel_furnizor)
        ] if 'Furnizor' in df_alerta_stoc.columns else df_alerta_stoc[df_alerta_stoc['Urgență'].isin(sel_urgency)]
        
        st.dataframe(df_t1_filtered, use_container_width=True, hide_index=True)
        
        # TABEL 2: Rotație & Analiză ABC (analiza_rotatie_&_ABC.csv)
        st.markdown("##### 🔄 Tabel 2: Optimizarea Spațiului - Analiză Rotație & Clasificare ABC")
        col_abc1, col_abc2 = st.columns([3, 1])
        with col_abc1:
            st.dataframe(df_rotatie, use_container_width=True, hide_index=True)
        with col_abc2:
            st.info("💡 **Regulă depozitare:** Dacă un produs **clasa C** ocupă peste **15% din spațiu** dar aduce sub **5% din venituri** (cum este cazul *Soluției de geamuri premium*), se recomandă reducerea stocului cu 50% pentru a elibera depozitul.")

        # TABEL 3 & 4: Planificare și Status Livrări în paralel
        col_stoc, col_livr = st.columns([1, 1])
        
        with col_stoc:
            st.markdown("##### 📅 Tabel 3: Planificare Comenzi Directe (Plan Aprovizionare)")
            st.dataframe(df_plan_comenzi, use_container_width=True, hide_index=True)
            
        with col_livr:
            st.markdown("##### 🚢 Tabel 4: Monitorizare Comenzi Furnizori în Tranzit (Status Livrări)")
            # Colorare simplă bazată pe status
            st.dataframe(df_status_livrari, use_container_width=True, hide_index=True)

        # TABEL 5: Decizie Aprovizionare Predictivă cu Regula de umplere palet
        st.markdown("##### 🎯 Tabel 5: Decizie de Aprovizionare Predictivă & Optimizare Volumetrică")
        
        # Aplicăm detaliul de finețe: Atenționare pe gradul de umplere palet sub 50%
        df_dec_show = df_decizie_aprov.copy()
        
        def check_pallet_filling(row):
            try:
                val_str = str(row['Grad umplere']).replace('%', '').strip()
                val = float(val_str)
                if val < 50.0 and val > 0:
                    return f"⚠️ Atenție: Grad de umplere sub 50% ({val_str}%)"
                return "Optimizat (Palet plin)"
            except Exception:
                return "OK"
                
        df_dec_show['Volum Palet Status'] = df_dec_show.apply(check_pallet_filling, axis=1)
        st.dataframe(df_dec_show, use_container_width=True, hide_index=True)

    # =========================================================================
    # TAB 2.c) CLIENȚI & LIVRĂRI (ANLIZĂ PARETO DINAMICĂ 80/20)
    # =========================================================================
    with tab_c:
        st.markdown("### 📊 Prioritizarea Clienților - Regula de Aur 80/20 (Pareto)")
        st.markdown("Determinarea clienților critici din zona de 80% din vânzări, pentru a ști unde alocăm marfa prioritar în caz de criză de stoc.")
        
        # Calcul Pareto dinamic din datele din Livrări
        if not df_livrari.empty:
            # Grupăm vânzările pe clienți
            client_sales = df_livrari.groupby('client')['quantity'].sum().reset_index()
            # Sortăm descrescător
            client_sales = client_sales.sort_values(by='quantity', ascending=False)
            
            # Calcul procente
            total_qty = client_sales['quantity'].sum()
            client_sales['Procent_Individual'] = (client_sales['quantity'] / total_qty) * 100
            client_sales['Cumulat_%'] = client_sales['Procent_Individual'].cumsum()
            
            # Clasificare Pareto
            client_sales['Zona Pareto'] = client_sales['Cumulat_%'].apply(
                lambda x: "🔴 ZONA CRITICĂ (A) - Aduce 80%" if x <= 82.0 else "🟢 ZONA SECUNDARĂ (B/C)"
            )
            
            # 2 COLOANE: Grafic Pareto stânga, Tabel dreapta
            col_chart, col_tbl = st.columns([4, 3])
            
            with col_chart:
                # Construim optiunile pentru ECharts Pareto dual-axis
                names = client_sales['client'].tolist()
                quantities = client_sales['quantity'].tolist()
                cumulative = [round(x, 1) for x in client_sales['Cumulat_%'].tolist()]
                
                pareto_option = {
                    "title": {"text": "Analiza Pareto Reală pe Portofoliu", "left": "center"},
                    "tooltip": {
                        "trigger": "axis",
                        "axisPointer": {"type": "cross"}
                    },
                    "grid": {"bottom": "20%", "left": "10%", "right": "10%"},
                    "xAxis": [
                        {
                            "type": "category",
                            "data": names,
                            "axisPointer": {"type": "shadow"},
                            "axisLabel": {"interval": 0, "rotate": 30}
                        }
                    ],
                    "yAxis": [
                        {
                            "type": "value",
                            "name": "Volume (Cutii)",
                            "min": 0
                        },
                        {
                            "type": "value",
                            "name": "Procent Cumulat",
                            "min": 0,
                            "max": 100,
                            "axisLabel": {"formatter": "{value} %"}
                        }
                    ],
                    "series": [
                        {
                            "name": "Volum Livrat",
                            "type": "bar",
                            "data": quantities,
                            "itemStyle": {"color": "#3498db"}
                        },
                        {
                            "name": "Cumulat %",
                            "type": "line",
                            "yAxisIndex": 1,
                            "data": cumulative,
                            "itemStyle": {"color": "#e74c3c"},
                            "lineStyle": {"width": 3},
                            # Linie prag de 80%
                            "markLine": {
                                "data": [{"yAxis": 80, "name": "Prag 80%"}],
                                "lineStyle": {"type": "dashed", "color": "red", "width": 2}
                            }
                        }
                    ]
                }
                st_echarts(pareto_option, height="380px")
                
            with col_tbl:
                st.markdown("##### 👥 Clasificare Clienți")
                st.dataframe(
                    client_sales.rename(columns={
                        'client': 'Client',
                        'quantity': 'Volum Total',
                        'Cumulat_%': 'Cumulat %'
                    })[['Client', 'Volum Total', 'Cumulat %', 'Zona Pareto']],
                    use_container_width=True,
                    hide_index=True
                )
                
            st.markdown("---")
            
            # TABEL OPERAȚIONAL: Clienți afectați de stoc critic
            st.markdown("##### 🚨 Tabel Decizional: Clienți mari în Risc Direct (Penurie Stoc)")
            
            # Căutăm produsele care au stocul sub 150
            critical_products = df_produse[df_produse['stock'] < 150]['code'].tolist()
            
            # Filtram ultimele livrări pe aceste produse ca să vedem ce clienți depind de ele
            if critical_products:
                comenzi_afectate = df_livrari[df_livrari['product_code'].isin(critical_products)].copy()
                comenzi_afectate = comenzi_afectate.merge(df_produse, left_on='product_code', right_on='code')
                
                # Clasificăm urgența în funcție de clientul Pareto (dacă e din top sau nu)
                top_clients = client_sales[client_sales['Cumulat_%'] <= 82.0]['client'].tolist()
                
                def evaluate_risk(row):
                    if row['client'] in top_clients:
                        return "🔴 URGENT (Client din Top 8% Pareto)"
                    return "🟡 MEDIU (Așteaptă reaprovizionare)"
                    
                comenzi_afectate['Urgență Livrare'] = comenzi_afectate.apply(evaluate_risk, axis=1)
                
                st.dataframe(
                    comenzi_afectate[['client', 'product', 'quantity', 'stock', 'Urgență Livrare']].rename(columns={
                        'client': 'Client afectat',
                        'product': 'Articol lipsă',
                        'quantity': 'Cantitate solicitată (u.m.)',
                        'stock': 'Stoc rămas în depozit'
                    }).sort_values(by='Urgență Livrare'),
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.success("Excelent! Nu există articole critice în acest moment, riscul de ne-livrare este zero.")
        else:
            st.info("Nu s-au putut încărca datele de tranzacții din DB pentru analiza Pareto.")
