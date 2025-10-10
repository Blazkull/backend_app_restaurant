from datetime import datetime
from typing import Optional, List
from sqlmodel import Field, SQLModel, Relationship

class PaymentMethod(SQLModel, table=True):
    """Modelo para 'payment_method'."""
    __tablename__ = "payment_method"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=30, nullable=False)
    
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    deleted: bool = Field(default=False, nullable=False) # Campo Soft Delete (Estado)
    deleted_on: Optional[datetime] = Field(default=None) # Campo Soft Delete (Fecha)

    # Relaciones
    invoices: List["Invoice"] = Relationship(back_populates="payment_method")

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.invoices import Invoice