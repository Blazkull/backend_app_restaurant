from sqlmodel import SQLModel
from typing import Optional, List
from datetime import datetime

class OrderBase(SQLModel):
    id_table: int
    id_status: int

class OrderCreate(OrderBase):
    items: List["OrderItemCreate"] = []

class OrderUpdate(SQLModel):
    id_table: Optional[int] = None
    id_status: Optional[int] = None

class OrderRead(OrderBase):
    id: int
    created_at: datetime
    updated_at: datetime
    items: List[OrderItemRead]


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from schemas.order_items_schema import OrderItemCreate, OrderItemRead
