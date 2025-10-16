



from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel


class OrderItemBase(SQLModel):
    id_order: int
    id_menu_item: int
    quantity: int = Field(gt=0, description="Cantidad del ítem en el pedido")
    note: Optional[str] = Field(default=None, max_length=100)
    price_at_order: float = Field(gt=0, description="Precio del ítem en el momento del pedido")
    id_kitchen_ticket: Optional[int] = None

class OrderItemCreate(SQLModel):
    id_menu_item: int
    quantity: int = Field(gt=0, description="Cantidad del ítem en el pedido")
    note: Optional[str] = Field(default=None, max_length=100)
    price_at_order: float = Field(gt=0, description="Precio del ítem en el momento del pedido")


class OrderItemUpdate(SQLModel):
    id_order: Optional[int] = None
    id_menu_item: Optional[int] = None
    quantity: Optional[int] = Field(default=None, gt=0, description="Cantidad del ítem en el pedido")
    note: Optional[str] = Field(default=None, max_length=100)
    price_at_order: Optional[float] = Field(default=None, gt=0, description="Precio del ítem en el momento del pedido")
    id_kitchen_ticket: Optional[int] = None

class OrderItemRead(SQLModel):
    id: int
    id_order: int
    id_menu_item: int
    quantity: int
    note: Optional[str]
    price_at_order: float
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OrderItemBulkCreate(SQLModel):
    id_order: int
    items: list[OrderItemCreate]