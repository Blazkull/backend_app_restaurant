from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel, Relationship

class OrderItem(SQLModel, table=True):
    __tablename__ = "order_items"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    quantity: int = Field(nullable=False, gt=0)
    note: Optional[str] = Field(default=None, max_length=50)
    
    # Claves Foráneas
    id_order: Optional[int] = Field(default=None, foreign_key="orders.id")
    id_menu_item: Optional[int] = Field(default=None, foreign_key="menu_items.id")
    
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    deleted: bool = Field(default=False, nullable=False) # Campo Soft Delete (Estado)
    deleted_on: Optional[datetime] = Field(default=None) # Campo Soft Delete (Fecha)

    # Relaciones
    order: "Order" = Relationship(back_populates="order_items")
    menu_item: "MenuItem" = Relationship(back_populates="order_items")

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.orders import Order
    from models.menu_items import MenuItem