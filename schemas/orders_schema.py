from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime
from typing import TYPE_CHECKING
from schemas.order_items_schema import OrderItemCreate, OrderItemRead 
# Asegúrate de importar OrderItemCreate y OrderItemRead desde el archivo correcto

# --- Esquemas Base ---

class OrderBase(SQLModel):
    # Campos comunes del modelo Order (excluyendo IDs auto-generados y fechas)
    id_table: int
    id_status: int
    id_user_created: int
    total_value: float

# --- Esquemas de Creación (Input) ---

# 1. Crear orden con ítems (POST /api/orders)
class OrderCreate(SQLModel):
    id_table: int
    id_status: int
    id_user_created: int
    total_value: float = 0.0 
    items: list[OrderItemCreate]


# 2. Crear orden vacía (POST /api/orders/create-empty)
class OrderCreateEmpty(SQLModel):
    """Permite crear una orden vacía asociada a una mesa y mesero"""
    id_table: int
    id_status: int
    id_user_created: int
    
# --- Esquemas de Actualización y Lectura ---

# Esquema para actualizar (PATCH /api/orders/{order_id})
class OrderUpdate(SQLModel):
    id_table: Optional[int] = None
    id_status: Optional[int] = None
    id_user_created: Optional[int] = None
    deleted: Optional[bool] = None 

# Esquema de lectura básica (GET /api/orders/{order_id})
class OrderRead(OrderBase):
    id: int
    created_at: datetime
    updated_at: datetime
    deleted: bool
    deleted_on: Optional[datetime]
    
    class Config:
        from_attributes = True

# Esquema de filtro (usado en GET /api/orders?...)
class OrderFilter(SQLModel):
    id_table: Optional[int] = None
    id_status: Optional[int] = None
    id_user_created: Optional[int] = None
    total_value: Optional[float] = None
    deleted: Optional[bool] = None 

class OrderReadFull(OrderRead):
    order_items: list[OrderItemRead] = []
    
    class Config:
        from_attributes = True