from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from models.orders import Order
    from models.menu_items import MenuItem
    from models.kitchen_tickets import KitchenTicket


class OrderItems(SQLModel, table=True):
    __tablename__ = "order_items"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    id_order: int = Field(foreign_key="orders.id")
    id_menu_item: int = Field(foreign_key="menu_items.id")
    id_kitchen_ticket: Optional[int] = Field(default=None, foreign_key="kitchen_tickets.id")

    quantity: int = Field(gt=0, description="Cantidad del ítem en el pedido")
    note: Optional[str] = Field(default=None, max_length=100, description="Nota especial para el ítem")
    price_at_order: float = Field(gt=0, description="Precio del ítem al momento del pedido")

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relaciones
    order: Optional["Order"] = Relationship(back_populates="items")
    menu_item: Optional["MenuItem"] = Relationship(back_populates="order_items")
    kitchen_ticket: Optional["KitchenTicket"] = Relationship(back_populates="order_items")
