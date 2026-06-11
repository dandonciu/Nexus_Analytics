import sqlite3
import os
import pandas as pd

# Definim unde stă dB Buffer
DB_PATH = "nexus_buffer.db"

def get_db_connection():
    """Deschide conexiunea cu baza de date SQLite."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Permite returnarea rândurilor ca dicționare
    return conn

def init_db():
    """Creează tabelele necesare dacă nu există și populează datele de test."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Enable Foreign Key support in SQLite
    cursor.execute("PRAGMA foreign_keys = ON;")

    # 1. Tabela pentru Utilizatori (Securitate)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    ''')

    # 2. Tabela pentru Comenzi Live (Rampa / WMS)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders_live (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_number TEXT UNIQUE NOT NULL,
            client_name TEXT NOT NULL,
            status TEXT NOT NULL,
            payload_logistic TEXT,
            payload_fiscal TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 3. Tabela pentru Produse (Catalog și stoc curent)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS produse (
            product TEXT NOT NULL,
            code TEXT PRIMARY KEY,
            stock INTEGER DEFAULT 0,
            unit TEXT,
            category TEXT
        )
    ''')

    # 4. Tabela pentru Livrări (Ieșiri / Vânzări)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS livrari (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_number TEXT,
            client TEXT,
            order_date TEXT, -- Stocat în format ISO YYYY-MM-DD
            month TEXT,
            product_code TEXT,
            quantity INTEGER,
            unit TEXT,
            FOREIGN KEY(product_code) REFERENCES produse(code) ON DELETE CASCADE
        )
    ''')

    # 5. Tabela pentru Recepții (Intrări / NIR-uri)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS receptii (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_number TEXT,
            supplier TEXT,
            order_date TEXT, -- Stocat în format ISO YYYY-MM-DD
            month TEXT,
            product_code TEXT,
            quantity INTEGER,
            unit TEXT,
            FOREIGN KEY(product_code) REFERENCES produse(code) ON DELETE CASCADE
        )
    ''')

    conn.commit()

    # Inserăm utilizatorii de test dacă tabela este goală
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO users (username, password, role) VALUES ('admin', 'admin123', 'arhitect')")
        cursor.execute("INSERT INTO users (username, password, role) VALUES ('rampa', '1234', 'wms')")
        conn.commit()

    conn.close()
    print("✅ dB Buffer a fost structurat cu succes!")
    
    # Importăm datele din CSV-uri dacă există local
    import_csv_data()

def import_csv_data():
    """Importă automat datele din CSV-uri în tabelele SQLite dacă acestea sunt goale."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Import Produse
    cursor.execute("SELECT COUNT(*) FROM produse")
    if cursor.fetchone()[0] == 0:
        csv_path = "produse_test.csv"
        if os.path.exists(csv_path):
            try:
                df = pd.read_csv(csv_path)
                # Redenumim coloanele pentru a se potrivi cu baza de date
                df.columns = [col.strip().lower() for col in df.columns]
                df.to_sql('produse', conn, if_exists='append', index=False)
                print(f"✅ S-au importat {len(df)} produse din {csv_path}")
            except Exception as e:
                print(f"❌ Eroare la importul {csv_path}: {e}")
        else:
            print(f"⚠️ Fișierul {csv_path} nu a fost găsit în directorul curent.")

    # 2. Import Livrări
    cursor.execute("SELECT COUNT(*) FROM livrari")
    if cursor.fetchone()[0] == 0:
        csv_path = "livrari_test.csv"
        if os.path.exists(csv_path):
            try:
                df = pd.read_csv(csv_path)
                # Curățăm numele coloanelor ("Order Number" -> "order_number")
                df.columns = [col.strip().lower().replace(" ", "_") for col in df.columns]
                df.to_sql('livrari', conn, if_exists='append', index=False)
                print(f"✅ S-au importat {len(df)} livrări din {csv_path}")
            except Exception as e:
                print(f"❌ Eroare la importul {csv_path}: {e}")
        else:
            print(f"⚠️ Fișierul {csv_path} nu a fost găsit în directorul curent.")

    # 3. Import Recepții
    cursor.execute("SELECT COUNT(*) FROM receptii")
    if cursor.fetchone()[0] == 0:
        csv_path = "receptii_test.csv"
        if os.path.exists(csv_path):
            try:
                df = pd.read_csv(csv_path)
                df.columns = [col.strip().lower().replace(" ", "_") for col in df.columns]
                df.to_sql('receptii', conn, if_exists='append', index=False)
                print(f"✅ S-au importat {len(df)} recepții din {csv_path}")
            except Exception as e:
                print(f"❌ Eroare la importul {csv_path}: {e}")
        else:
            print(f"⚠️ Fișierul {csv_path} nu a fost găsit în directorul curent.")

    conn.close()

if __name__ == "__main__":
    init_db()
