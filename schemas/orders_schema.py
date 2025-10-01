from sqlmodel import SQLModel, Field
from typing import Optional, List
from datetime import datetime
from typing import TYPE_CHECKING

# 💡 NOTA: Asumiendo que StatusRead y OrderItemRead están accesibles
# Si StatusRead está en status_schema.py, necesitarías importar StatusRead.
# Aquí lo definimos en el mismo archivo para simplificar la dependencia.

# --- Definición simplificada de esquemas relacionados (para tipado) ---
# Debes asegurar que estos esquemas existan en tus archivos correspondientes.
class StatusRead(SQLModel):
    id: int
    name: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class OrderItemRead(SQLModel):
    id: int
    id_menu_item: Optional[int] = None
    quantity: int = Field(gt=0)
    note: Optional[str] = Field(default=None, max_length=50)
    created_at: datetime
    updated_at: datetime
# ----------------------------------------------------------------------


class OrderItemBase(SQLModel):
    id_menu_item: Optional[int] = None
    quantity: int = Field(gt=0)
    note: Optional[str] = Field(default=None, max_length=50)

class OrderItemCreate(OrderItemBase):
    pass
    
class OrderItemUpdate(SQLModel):
    quantity: Optional[int] = Field(default=None, gt=0)
    note: Optional[str] = Field(default=None, max_length=50)


class OrderBase(SQLModel):
    id_table: int
    id_status: int # Se mantiene para Create/Base/Update

class OrderCreate(OrderBase):
    items: List["OrderItemCreate"] = []

class OrderUpdate(SQLModel):
    id_table: Optional[int] = None
    id_status: Optional[int] = None

# 🔑 ESQUEMA CLAVE: OrderRead (incluye el objeto Status completo)
class OrderRead(SQLModel):
    id: int
    id_table: int
    status: StatusRead 
    
    created_at: datetime
    updated_at: datetime
    items: List[OrderItemRead]


# --- Esquema Kitchen (para el PATCH flexible) ---
class OrderKitchenUpdate(SQLModel):
    """Esquema flexible para actualizar la orden en la cocina."""
    status_name: Optional[str] = Field(default=None, description="Nuevo nombre de estado.")
    id_table: Optional[int] = None
# ----------------------------------------------------------------------