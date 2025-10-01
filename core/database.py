from typing import Annotated
from fastapi import Depends
from sqlmodel import SQLModel, create_engine, Session
from core.config import settings

# El motor de la base de datos
engine = create_engine(settings.DATABASE_URL, echo=True)

def create_db_and_tables():
    """Crea todas las tablas definidas en los modelos si no existen."""
    # Asegúrate de importar TODOS los modelos aquí
    from models.type_identification import TypeIdentification
    from models.status import Status
    from models.locations import Location
    from models.categories import Category
    from models.payment_method import PaymentMethod
    from models.information_company import InformationCompany
    from models.clients import Client
    from models.views import View
    from models.roles import Role
    from models.users import User
    from models.tokens import Token
    from models.tables import Table
    from models.menu_items import MenuItem
    from models.orders import Order
    from models.order_items import OrderItem
    from models.invoices import Invoice
    from models.link_models import UserRoleLink, RoleViewLink
    
    SQLModel.metadata.create_all(engine)

def get_session():
    """Generador para obtener la sesión de la base de datos."""
    with Session(engine) as session:
        yield session

SessionDep = Annotated[Session, Depends(get_session)]


def ping_database(engine) -> bool:
    """
    Intenta una consulta simple para despertar la base de datos, 
    especialmente útil para servicios que hibernan (como Hostinger).
    """
    print("Intentando 'ping' a la base de datos...")
    try:
        with Session(engine) as session:
            # Realiza una consulta mínima que requiere una conexión activa
            # Se usa .exec("SELECT 1") en lugar de session.execute(text("SELECT 1")) 
            # ya que SQLModel lo soporta y es más simple.
            session.exec("SELECT 1") 
        print("Ping exitoso: Conexión establecida/despertada. ✅")
        return True
    except Exception as e:
        print(f"Alerta: Fallo el ping a la base de datos. Error: {e} ❌")
        return False