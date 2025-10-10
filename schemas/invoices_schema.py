from sqlmodel import SQLModel, Field
from typing import List, Optional
from datetime import datetime

from schemas.kitchen_tickets_schema import KitchenTicketRead
from schemas.order_items_schema import OrderItemRead
from schemas.orders_schema import OrderRead
from schemas.tables_schema import TableRead

class InvoiceBase(SQLModel):
    id_client: int
    id_order: int
    id_payment_method: int
    id_status: Optional[int] = None
    returned: float = Field(ge=0)
    ammount_paid: float = Field(ge=0)
    total: float = Field(ge=0)
    

class InvoiceCreate(InvoiceBase):
    pass

class InvoiceUpdate(SQLModel):
    id_client: Optional[int] = None
    id_order: Optional[int] = None
    id_payment_method: Optional[int] = None
    returned: Optional[float] = Field(default=None, ge=0)
    ammount_paid: Optional[float] = Field(default=None, ge=0)
    total: Optional[float] = Field(default=None, ge=0)
    id_status: Optional[int] = None

class InvoiceRead(InvoiceBase):
    id: int
    created_at: datetime
    updated_at: datetime

class InvoiceStatusUpdate(SQLModel):
    status: str


class InvoiceFilter(SQLModel):
    id: Optional[int] = None
    id_client: Optional[int] = None
    id_order: Optional[int] = None
    id_payment_method: Optional[int] = None
    id_status: Optional[int] = None
    returned: Optional[float] = None
    ammount_paid: Optional[float] = None
    total: Optional[float] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    deleted: Optional[bool] = None
    deleted_on: Optional[datetime] = None
    min_date: Optional[datetime] = None
    max_date: Optional[datetime] = None

# Schemas de Lectura Compuestos (Vistas)
class OrderReadFull(OrderRead):
    items: List[OrderItemRead]
    kitchen_tickets: List[KitchenTicketRead]
class TableReadWithOrders(TableRead):
    orders: List[OrderReadFull]