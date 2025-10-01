from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime

class OrderItemBase(SQLModel):
    id_menu_item: Optional[int] = None
    quantity: int = Field(gt=0)
    note: Optional[str] = Field(default=None, max_length=50)

class OrderItemCreate(OrderItemBase):
    pass
    
class OrderItemUpdate(SQLModel):
    quantity: Optional[int] = Field(default=None, gt=0)
    note: Optional[str] = Field(default=None, max_length=50)

class OrderItemRead(OrderItemBase):
    id: int
    id_order: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    deleted: bool
    deleted_on: Optional[datetime]
    
    class Config:
        from_attributes = True