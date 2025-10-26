from __future__ import annotations
from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field, Relationship


class KitchenTicketBase(SQLModel):
    """Campos base comunes para todas las operaciones."""
    id_order: int = Field(..., description="ID del pedido asociado")
    id_status: int = Field(..., description="Estado actual del ticket de cocina")


class KitchenTicket(KitchenTicketBase, table=True):
    """Modelo principal de la tabla `kitchen_tickets`."""
    __tablename__ = "kitchen_tickets"

    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    deleted: bool = Field(default=False)
    deleted_on: Optional[datetime] = Field(default=None)

    # Relaciones
    order: Optional["Order"] = Relationship(back_populates="kitchen_tickets")
    status: Optional["Status"] = Relationship(back_populates="kitchen_tickets")


# -----------------------------
# Schemas de validación
# -----------------------------

class KitchenTicketCreate(KitchenTicketBase):
    """Esquema para crear un nuevo ticket de cocina."""
    pass


class KitchenTicketRead(KitchenTicketBase):
    """Esquema de lectura (respuesta API)."""
    id: int
    created_at: datetime
    updated_at: datetime
    deleted: bool
    deleted_on: Optional[datetime] = None


class KitchenTicketUpdate(SQLModel):
    """Esquema para actualizar un ticket existente."""
    id_status: Optional[int] = None
    deleted: Optional[bool] = None
