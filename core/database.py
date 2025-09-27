
from typing import Annotated
from fastapi import Depends
from sqlmodel import SQLModel, create_engine, Session
from core.config import settings

engine = create_engine(settings.DATABASE_URL, echo=True)

def create_db_and_tables():
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
    with Session(engine) as session:
        yield session

SessionDep = Annotated[Session, Depends(get_session)]