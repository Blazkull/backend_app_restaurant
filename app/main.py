import os
import sys
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from dotenv import load_dotenv

# --- Configuración de Path para Módulos Hermanos (SOLUCIÓN al error) ---
# Esto añade el directorio raíz (padre de 'app' y 'core') al sys.path
ROOT_DIR = Path(__file__).parent.parent
sys.path.append(str(ROOT_DIR))
# ------------------------------------------------------------------------

# --- Importaciones de Módulos Core ---
from core.database import create_db_and_tables

# --- Importación de Routers ---
from routers import users 


# Cargar variables de entorno desde .env (debe estar en la raíz del proyecto)
load_dotenv() 

app = FastAPI(
    title="API Restaurante La Media Luna",
    version="1.0.0",
    description="Backend para la gestión de usuarios, pedidos y facturación."
)

# --- Evento de Inicio ---
@app.on_event("startup")
def startup():
    """
    Función que se ejecuta al iniciar la aplicación.
    Crea las tablas de la base de datos si no existen.
    """
    create_db_and_tables()

# --- Configuración de CORS ---
origins = [
    "http://localhost",
    "http://127.0.0.1:5500",
    "http://localhost:8080",
    "*",  # Advertencia: Usar "*" solo en desarrollo.
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Inclusión de Routers (Rutas de la API) ---
app.include_router(users.router, prefix="/api/users", tags=["Usuarios"])


# --- Ruta Raíz de Bienvenida ---
@app.get("/", tags=["API Health"])
def read_root():
    """Verifica que la API está en línea."""
    return {"message": "API de Restaurante La Media Luna en línea"}


# --- Ejecución Local ---
if __name__ == "__main__":
    # Obtener el puerto del entorno, o usar 10000 por defecto
    port = int(os.environ.get("PORT", 10000))
    
    # Ejecución como módulo. Debes ejecutar este archivo desde el directorio padre.
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)