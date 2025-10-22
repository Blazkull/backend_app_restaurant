# database.py

from typing import Annotated
from fastapi import Depends
from sqlmodel import SQLModel, create_engine, Session
from core.config import settings
from sqlalchemy.exc import OperationalError, DBAPIError

# ---
# CONFIGURACIÓN DEL MOTOR DE BASE DE DATOS
# ---

# El motor de la base de datos
# SOLUCIÓN al error (2006, "MySQL server has gone away")
# pool_recycle=3600: Recicla las conexiones inactivas cada 1 hora (3600 segundos)
# Esto previene que MySQL cierre la conexión por inactividad (wait_timeout).
engine = create_engine(
    settings.DATABASE_URL, 
    echo=True, # Muestra las consultas SQL en la consola (útil para debug)
    pool_recycle=3600 # <--- ¡Clave para prevenir desconexiones!
)

def create_db_and_tables():
    """Crea todas las tablas definidas en los modelos si no existen."""
    # Asegúrate de importar TODOS los modelos aquí
    # Aunque no se usen directamente, deben importarse para que SQLModel.metadata las conozca
    from models.users import User
    from models.roles import Role
    from models.information_company import InformationCompany
    from models.categories import Category
    from models.clients import Client
    from models.locations import Location
    from models.menu_items import MenuItem
    from models.order_items import OrderItems
    from models.orders import Order
    from models.payment_methods import PaymentMethod
    from models.status import Status
    from models.tables import Table
    from models.type_identification import TypeIdentification
    from models.views import View
    from models.invoices import Invoice
    from models.tokens import Token

    
    SQLModel.metadata.create_all(engine)

def get_session():
    """Generador para obtener la sesión de la base de datos."""
    with Session(engine) as session:
        yield session

# Tipo de dependencia para inyectar la sesión en los endpoints de FastAPI
SessionDep = Annotated[Session, Depends(get_session)]


def ping_database(engine) -> bool:
    """
    Intenta una consulta simple para verificar la conexión a la base de datos.
    Útil para chequeos de salud (health checks) o para 'despertar' una DB en reposo.
    """
    print("Intentando 'ping' a la base de datos...")
    try:
        with Session(engine) as session:
            # Realiza una consulta mínima que requiere una conexión activa
            # session.exec() es el método de SQLModel/SQLAlchemy para ejecutar comandos
            session.exec("SELECT 1") 
        print("Ping exitoso: Conexión establecida/despertada. ✅")
        return True
    except (OperationalError, DBAPIError, Exception) as e:
        # Captura errores comunes de conexión/operación de la DB
        print(f"Alerta: Fallo el ping a la base de datos. Error: {e} ❌")
        return False