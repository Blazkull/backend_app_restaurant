from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from pydantic import Field
from sqlmodel import Relationship, SQLModel


class KitchenTickets(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    id_order: int = Field(foreign_key="orders.id")
    id_status: int = Field(foreign_key="statuses.id")
    items:List[OrderItems] = Relationship(back_populates="kitchen_ticket")

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"onupdate": datetime.utcnow})
    deleted_on: Optional[datetime] = Field(default=None) 
    deleted: bool = Field(default=False)

    order: "Orders" = Relationship(back_populates="kitchen_tickets")
    status: "Statuses" = Relationship(back_populates="kitchen_tickets")


type Checking = TYPE_CHECKING
if TYPE_CHECKING:
    from models.orders import Orders
    from models.status import Statuses
    from models.order_items import OrderItems