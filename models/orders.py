from datetime import datetime
from typing import Optional, List
from sqlmodel import Field, SQLModel, Relationship

class Order(SQLModel, table=True):
    __tablename__ = "orders"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Claves Foráneas
    id_table: int = Field(foreign_key="tables.id")
    id_status: int = Field(foreign_key="status.id")
    
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    deleted: bool = Field(default=False, nullable=False) # Campo Soft Delete (Estado)
    deleted_on: Optional[datetime] = Field(default=None) # Campo Soft Delete (Fecha)

    # Relaciones
    table: "Table" = Relationship(back_populates="orders")
    status: "Status" = Relationship(back_populates="orders")
    order_items: List["OrderItem"] = Relationship(back_populates="order")
    invoice: Optional["Invoice"] = Relationship(back_populates="order")


from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.tables import Table
    from models.status import Status
    from models.order_items import OrderItem
    from models.invoices import Invoice