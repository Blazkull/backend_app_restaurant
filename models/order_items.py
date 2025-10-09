from datetime import datetime
from typing import Optional

from pydantic import Field
from sqlmodel import Relationship, SQLModel


class OrderItems(SQLModel, table=True):
    __tablename__ = "order_items"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    id_order: int = Field(foreign_key="orders.id")
    id_menu_item: int = Field(foreign_key="menu_items.id")
    quantity: int = Field(gt=0, description="Cantidad del ítem en el pedido")
    note: Optional[str] = Field(default=None, max_length=100, description="Nota especial para el ítem")
    price_at_order: float = Field(gt=0, description="Precio del ítem al momento del pedido")
    id_kitchen_ticket: Optional[int] = Field(default=None, foreign_key="kitchen_tickets.id")
    
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    
    # Relaciones
    order: "Order" = Relationship(back_populates="items")
    menu_item: "MenuItem" = Relationship(back_populates="order_items")
    kitchen_ticket: Optional["KitchenTicket"] = Relationship(back_populates="order_items")

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from models.orders import Order
    from models.menu_items import MenuItem
    from models.kitchen_tickets import KitchenTicket