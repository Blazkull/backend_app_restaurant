from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from models.orders import Order
    from models.status import Status
    from models.order_items import OrderItems


class KitchenTicket(SQLModel, table=True):
    """
    Representa una comanda o ticket de cocina asociado a una orden.
    """
    __tablename__ = "kitchen_tickets"

    id: Optional[int] = Field(default=None, primary_key=True)
    id_order: int = Field(foreign_key="orders.id", nullable=False)
    id_status: int = Field(foreign_key="status.id", nullable=False)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"onupdate": datetime.utcnow})
    deleted: bool = Field(default=False)
    deleted_on: Optional[datetime] = Field(default=None)

    # Relaciones
    order: Optional["Order"] = Relationship(back_populates="kitchen_tickets")
    status: Optional["Status"] = Relationship(back_populates="kitchen_tickets")
    order_items: List["OrderItems"] = Relationship(back_populates="kitchen_ticket")
