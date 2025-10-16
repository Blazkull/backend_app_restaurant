import os
import sys
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from dotenv import load_dotenv

from fastapi.staticfiles import StaticFiles # Para servir archivos estáticos (imágenes del menú)

# --- Configuración de Path para Módulos Hermanos ---
ROOT_DIR = Path(__file__).parent.parent
sys.path.append(str(ROOT_DIR))
# ------------------------------------------------------------------------

# --- Importaciones de Módulos Core ---
# Importamos la función de ping y el motor para usar en el startup
from core.database import create_db_and_tables, engine, ping_database 

# --- Importación de Routers ---
from routers import auth  
from routers import users 
from routers import roles 
from routers import view
from routers import information_company
from routers import categories
from routers import clients
from routers import locations
from routers import menu_items
from routers import order_items
from routers import orders
from routers import payment_method
from routers import status
from routers import tables
from routers import type_identification
from routers import kitchen_tickets
from routers import invoices



# Cargar variables de entorno desde .env
load_dotenv() 

app = FastAPI(
    title="API Restaurante La Media Luna",
    version="1.0.0",
    description="Backend para la gestión de usuarios, pedidos y facturación."
)

# --- Evento de Inicio ACTUALIZADO ---
@app.on_event("startup")
def startup():
    """
    Función que se ejecuta al iniciar la aplicación.
    1. Crea las tablas.
    2. Realiza un 'ping' a la DB para despertar la conexión.
    """
    print("Ejecutando startup hooks...")
    
    # 1. Crea las tablas de la base de datos si no existen.
    create_db_and_tables()
    print("Tablas verificadas.")
    
    # 2. Despertar/Mantener activa la conexión (Ping a la DB)
    if engine:
        ping_database(engine) 

# --- Configuración de CORS ---
origins = [
    "http://localhost",
    "http://127.0.0.1:5500",
    "http://localhost:8080",
    "https://mi-dominio.com",
    "https://otro-dominio.net",
    
    "*", # Solo para desarrollo
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Montaje de carpeta statica para las imagenes del menu
app.mount("/static", StaticFiles(directory="static"), name="static") 

# --- Inclusión de Routers (Rutas de la API) ---
app.include_router(auth.router)
app.include_router(users.router) 
app.include_router(roles.router) 
app.include_router(view.router)
app.include_router(information_company.router)
app.include_router(categories.router)
app.include_router(clients.router)
app.include_router(locations.router)
app.include_router(menu_items.router)
app.include_router(order_items.router)
app.include_router(orders.router)
app.include_router(payment_method.router)
app.include_router(status.router)
app.include_router(tables.router)
app.include_router(type_identification.router)
app.include_router(kitchen_tickets.router)
app.include_router(invoices.router)



# --- Ruta Raíz de Bienvenida ---
@app.get("/", tags=["API Health"])
def read_root():
    """Verifica que la API está en línea."""
    return {"message": "API de Restaurante La Media Luna en línea"}


# --- Ejecución Local ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)