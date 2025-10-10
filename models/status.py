from datetime import datetime
from typing import Optional, List
from sqlmodel import Field, SQLModel, Relationship



class Status(SQLModel, table=True):
    __tablename__ = "status"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=20, nullable=False)
    description: Optional[str] = Field(default=None, max_length=50)
    
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    deleted: bool = Field(default=False, nullable=False) # Campo Soft Delete (Estado)
    deleted_on: Optional[datetime] = Field(default=None) # Campo Soft Delete (Fecha)

    # Relaciones
    roles: List["Role"] = Relationship(back_populates="status")
    users: List["User"] = Relationship(back_populates="status")
    views: List["View"] = Relationship(back_populates="status")
    menu_items: List["MenuItem"] = Relationship(back_populates="status")
    tables: List["Table"] = Relationship(back_populates="status")
    orders: List["Order"] = Relationship(back_populates="status")
    invoices: List["Invoice"] = Relationship(back_populates="status")
    kitchen_tickets: List["KitchenTickets"] = Relationship(back_populates="status")

from typing import TYPE_CHECKING
if TYPE_CHECKING:       
    from models.roles import Role
    from models.users import User
    from models.views import View
    from models.menu_items import MenuItem
    from models.tables import Table
    from models.orders import Order
    from models.invoices import Invoice
    from models.kitchen_tickets import KitchenTickets
