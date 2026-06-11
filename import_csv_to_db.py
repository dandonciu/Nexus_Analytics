import sqlite3
import pandas as pd

DB_PATH = "nexus_buffer.db"

def import_data():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("🧹 Curățăm tabelele de sandbox existente...")
    cursor.execute("DROP TABLE IF EXISTS sandbox_sales")
    cursor.execute("DROP TABLE IF EXISTS sandbox_stock")
    cursor.execute("DROP TABLE IF EXISTS sandbox_products")
    cursor.execute("DROP TABLE IF EXISTS sandbox_suppliers")
    cursor.execute("DROP TABLE IF EXISTS sandbox_clients")
    conn.commit()

    print("📥 Importăm produsele din produse_test.csv...")
    try:
        df_prod = pd.read_csv("produse_test.csv")
        # Cream tabelul de produse din structura CSV-ului
        df_prod.to_sql("sandbox_products", conn, if_exists="replace", index=False)
        print(f"✅ S-au importat {len(df_prod)} produse.")
    except Exception as e:
        print(f"❌ Eroare la produse: {e}")

    print("📥 Importăm vânzările din livrari_test.csv...")
    try:
        df_livrari = pd.read_csv("livrari_test.csv")
        df_livrari.to_sql("sandbox_sales", conn, if_exists="replace", index=False)
        print(f"✅ S-au importat {len(df_livrari)} tranzacții de vânzare.")
    except Exception as e:
        print(f"❌ Eroare la livrări: {e}")

    print("📥 Importăm recepțiile din receptii_test.csv...")
    try:
        df_receptii = pd.read_csv("receptii_test.csv")
        df_receptii.to_sql("sandbox_stock", conn, if_exists="replace", index=False)
        print(f"✅ S-au importat {len(df_receptii)} tranzacții de recepție.")
    except Exception as e:
        print(f"❌ Eroare la recepții: {e}")

    conn.close()
    print("🚀 IMPORT COMPLET! Baza de date nexus_buffer.db conține acum datele tale reale de test.")

if __name__ == "__main__":
    import_data()
