from sqlmodel import SQLModel, Field
from typing import List, Optional
from datetime import datetime

# Asume que estos imports existen en tu proyecto
from schemas.kitchen_tickets_schema import KitchenTicketRead
from schemas.order_items_schema import OrderItemRead
from schemas.orders_schema import OrderRead
from schemas.tables_schema import TableRead
from schemas.status_schema import StatusRead # Asumo que existe StatusRead

# ----------------------------------------------------------------------
# SCHEMAS BASE DE LA FACTURA
# ----------------------------------------------------------------------

class InvoiceBase(SQLModel):
    """Campos base requeridos para crear una factura."""
    id_client: int
    id_order: int
    id_payment_method: int
    id_status: Optional[int] = None
    returned: float = Field(ge=0, description="Monto devuelto al cliente (cambio).")
    ammount_paid: float = Field(ge=0, description="Monto pagado por el cliente.")
    total: float = Field(ge=0, description="Monto total adeudado de la factura.")
    note: Optional[str] = Field(default=None, max_length=100, description="Notas o motivo de anulación.")

class InvoiceCreate(InvoiceBase):
    """Schema para la creación de una factura singular (uso Legacy/Admin)."""
    pass

class InvoiceUpdate(SQLModel):
    """Schema para actualizar campos de una factura existente."""
    id_client: Optional[int] = None
    id_order: Optional[int] = None
    id_payment_method: Optional[int] = None
    returned: Optional[float] = Field(default=None, ge=0)
    ammount_paid: Optional[float] = Field(default=None, ge=0)
    total: Optional[float] = Field(default=None, ge=0)
    id_status: Optional[int] = None
    note: Optional[str] = Field(default=None, max_length=100)

class InvoiceRead(InvoiceBase):
    """Schema de lectura que incluye metadatos y Soft Delete."""
    id: int
    created_at: datetime
    updated_at: datetime
    deleted: bool = Field(description="Indica si la factura está eliminada (Soft Delete).")
    deleted_on: Optional[datetime] = Field(description="Fecha de eliminación (Soft Delete).")

class InvoiceStatusUpdate(SQLModel):
    """Schema simple para un cambio de estado genérico (usado en tu definición original)."""
    status: str

class InvoiceFilter(SQLModel):
    """Schema para recibir filtros de búsqueda avanzados (no usado directamente en la API)."""
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

# ----------------------------------------------------------------------
# SCHEMAS DE FUNCIONALIDAD Y DASHBOARD
# ----------------------------------------------------------------------

class InvoiceCreateConsolidated(SQLModel):
    """Schema para recibir los datos de pago y las órdenes a consolidar desde el POS."""
    order_ids: List[int] = Field(description="Lista de IDs de órdenes a consolidar.")
    id_client: int
    id_payment_method: int
    ammount_paid: float = Field(..., ge=0, description="Monto entregado por el cliente para el pago.")
    id_status: Optional[int] = None
    note: Optional[str] = Field(default=None, max_length=100)

class InvoiceCountResponse(SQLModel):
    """Schema de salida para el recuento total de facturas por estado (Dashboard)."""
    total_count: int
    paid_count: int
    unpaid_count: int
    draft_count: int
    overdue_count: int
    annulled_count: int

class InvoiceAnnulment(SQLModel):
    """Schema para anular una factura, usando la nota como razón."""
    annulment_reason: Optional[str] = Field(None, max_length=100, description="Motivo de la anulación.")


# ----------------------------------------------------------------------
# SCHEMAS COMPUESTOS (Relaciones de Lectura)
# ----------------------------------------------------------------------

class OrderReadFull(OrderRead):
    """Orden de lectura completa incluyendo ítems y tickets de cocina."""
    items: List[OrderItemRead]
    kitchen_tickets: List[KitchenTicketRead]

class TableReadWithOrders(TableRead):
    """Mesa de lectura incluyendo sus órdenes completas."""
    orders: List[OrderReadFull]


class InvoicePaymentUpdate(SQLModel):
    """Schema para registrar el pago o cambiar el estado/monto."""
    id_status: int = Field(..., description="Nuevo ID de estado.")
    id_payment_method: Optional[int] = None
    ammount_paid: Optional[float] = Field(default=None, ge=0, description="Monto pagado.")
    note: Optional[str] = Field(default=None, max_length=100)