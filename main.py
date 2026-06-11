from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import init_db, get_db_connection

# Inițializăm aplicația server FastAPI
app = FastAPI(title="NEXUS B2B Backend API")

# Permitem Frontend-ului (Streamlit) să vorbească cu Backend-ul fără erori de securitate
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Când pornește serverul, asigură-te că dB Buffer există
@app.on_event("startup")
def startup_event():
    init_db()

# --- PRIMUL NOSTRU API (Test de conexiune) ---
@app.get("/")
def read_root():
    return {"message": "Salut! NEXUS FastAPI Backend funcționează perfect!"}

# --- API pentru Login ---
@app.get("/api/login")
def login(username: str, password: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    # Căutăm userul în dB Buffer
    cursor.execute("SELECT role FROM users WHERE username = ? AND password = ?", (username, password))
    user = cursor.fetchone()
    conn.close()

    if user:
        return {"success": True, "role": user["role"]}
    else:
        return {"success": False, "message": "Parolă sau utilizator incorect!"}
