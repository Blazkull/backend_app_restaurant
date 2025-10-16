from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from sqlmodel import Field, SQLModel, Relationship


class Order(SQLModel, table=True):
    __tablename__ = "orders"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Claves Foráneas
    id_table: int = Field(foreign_key="tables.id")
    id_status: int = Field(foreign_key="status.id")
    id_user_created: int = Field(foreign_key="users.id")
    total_value: float = Field(ge=0, description="Valor total del pedido")
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    deleted: bool = Field(default=False, nullable=False)
    deleted_on: Optional[datetime] = Field(default=None)

    # Relaciones
    user_created: "User" = Relationship(back_populates="orders")
    table: "Table" = Relationship(back_populates="orders")
    status: "Status" = Relationship(back_populates="orders")
    order_items: List["OrderItems"] = Relationship(back_populates="order")
    kitchen_tickets: List["KitchenTicket"] = Relationship(back_populates="order")
    invoice: Optional["Invoice"] = Relationship(back_populates="order")


if TYPE_CHECKING:
    from models.tables import Table
    from models.status import Status
    from models.order_items import OrderItems
    from models.invoices import Invoice
    from models.users import User
    from models.kitchen_tickets import KitchenTicket
