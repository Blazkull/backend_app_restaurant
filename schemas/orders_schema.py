from sqlmodel import SQLModel, Field
from typing import Optional, List
from datetime import datetime
from typing import TYPE_CHECKING

from schemas.order_items_schema import OrderItemRead




class OrderBase(SQLModel):
    id_table: int
    id_status: int
    id_user_created: int
    total_value: float


class OrderCreate(OrderBase):
    pass    

class OrderUpdate(SQLModel):
    id_table: Optional[int] = None
    id_status: Optional[int] = None
    id_user_created: Optional[int] = None
    total_value: Optional[float] = None
    deleted: Optional[bool] = None 

class OrderRead(OrderBase):
    id: int
    created_at: datetime
    updated_at: datetime
    deleted: bool
    deleted_on: Optional[datetime]
    
    class Config:
        from_attributes = True

class OrderFilter(SQLModel):
    id_table: Optional[int] = None
    id_status: Optional[int] = None
    id_user_created: Optional[int] = None
    total_value: Optional[float] = None
    deleted: Optional[bool] = None 

class OrderReadFull(OrderRead):
    items: List[OrderItemRead] = []
    
    class Config:
        from_attributes = True