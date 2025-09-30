from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel, Relationship

class Invoice(SQLModel, table=True):
    """Modelo para 'invoices' (Facturas)."""
    __tablename__ = "invoices"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Campos de Dinero (Mapeados a float con validación para ser positivos)
    returned: float = Field(ge=0) 
    ammount_paid: float = Field(ge=0)
    total: float = Field(ge=0)
    
    # Claves Foráneas
    id_client: int = Field(foreign_key="clients.id")
    id_order: int = Field(foreign_key="orders.id")
    id_payment_method: int = Field(foreign_key="payment_method.id")
    id_status: Optional[int] = Field(default=None, foreign_key="status.id")
    
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    deleted_at: Optional[datetime] = Field(default=None)
    deleted: bool = Field(default=False)

    # Relaciones
    client: "Client" = Relationship(back_populates="invoices")
    order: "Order" = Relationship(back_populates="invoice")
    payment_method: "PaymentMethod" = Relationship(back_populates="invoices")
    status: "Status" = Relationship(back_populates="invoices")


from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.clients import Client
    from models.orders import Order
    from models.payment_method import PaymentMethod
    from models.status import Status