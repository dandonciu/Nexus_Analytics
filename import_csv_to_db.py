import sqlite3
import pandas as pd

DB_PATH = "nexus_buffer.db"

def standardize_columns(df):
    """Transformă coloanele din 'Order Date' în 'order_date' (litere mici, spații înlocuite cu _)"""
    df.columns = [col.strip().lower().replace(" ", "_") for col in df.columns]
    return df

def import_with_standardized_columns():
    conn = sqlite3.connect(DB_PATH)
    
    print("📥 Importăm produse_test.csv în tabela 'produse'...")
    try:
        df_prod = pd.read_csv("produse_test.csv")
        df_prod = standardize_columns(df_prod) # coloanele devin: product, code, stock, unit, category
        df_prod.to_sql("produse", conn, if_exists="replace", index=False)
        print(f"✅ Succes! Coloane importate: {list(df_prod.columns)}")
    except Exception as e:
        print(f"❌ Eroare la produse: {e}")

    print("📥 Importăm livrari_test.csv în tabela 'livrari'...")
    try:
        df_livrari = pd.read_csv("livrari_test.csv")
        df_livrari = standardize_columns(df_livrari) # coloanele devin: order_number, client, order_date, month, product_code, quantity, unit
        df_livrari.to_sql("livrari", conn, if_exists="replace", index=False)
        print(f"✅ Succes! Coloane importate: {list(df_livrari.columns)}")
    except Exception as e:
        print(f"❌ Eroare la livrări: {e}")

    print("📥 Importăm receptii_test.csv în tabela 'receptii'...")
    try:
        df_receptii = pd.read_csv("receptii_test.csv")
        df_receptii = standardize_columns(df_receptii) # coloanele devin: order_number, supplier, order_date, month, product_code, quantity, unit
        df_receptii.to_sql("receptii", conn, if_exists="replace", index=False)
        print(f"✅ Succes! Coloane importate: {list(df_receptii.columns)}")
    except Exception as e:
        print(f"❌ Eroare la recepții: {e}")

    conn.close()
    print("\n🚀 IMPORT COMPLET! Toate coloanele au fost standardizate și salvate.")

if __name__ == "__main__":
    import_with_standardized_columns()
