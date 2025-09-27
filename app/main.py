import os
import sys
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from dotenv import load_dotenv
ROOT_DIR = Path(__file__).parent.parent
sys.path.append(str(ROOT_DIR))
from core.database import create_db_and_tables


load_dotenv() 

app = FastAPI()

# --- Evento de Inicio ---
@app.on_event("startup")
def startup():
    create_db_and_tables()

# --- Configuración de CORS ---
origins = [
    "http://localhost",
    "http://127.0.0.1:5500",
    "http://localhost:8080",
    # Añade tus dominios de producción aquí
    # "https://mi-dominio.com",
    "*",  # Solo para desarrollo: Cuidado en producción
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



# --- Ruta Raíz de Bienvenida ---
@app.get("/", tags=["TEST_RENDER"])
def read_root():
    return {"message": "API de Restaurante en línea"}


# --- Ejecución Local ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)