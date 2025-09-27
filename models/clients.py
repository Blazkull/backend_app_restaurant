
from datetime import datetime
from typing import Optional, List
from sqlmodel import Field, SQLModel, Relationship

class Client(SQLModel, table=True):
    __tablename__ = "clients"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    fullname: str = Field(max_length=100, nullable=False)
    address: Optional[str] = Field(default=None, max_length=100)
    phone_number: str = Field(max_length=20, unique=True, nullable=False)
    identification_number: str = Field(max_length=100, unique=True, nullable=False)
    email: str = Field(max_length=100, unique=True, nullable=False)
    
    # Clave Foránea
    id_type_identificacion: int = Field(foreign_key="type_identification.id")
    
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    deleted_at: Optional[datetime] = Field(default=None)

    # Relaciones
    type_identification: "TypeIdentification" = Relationship(back_populates="clients")
    invoices: List["Invoice"] = Relationship(back_populates="client")

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .type_identification import TypeIdentification
    from .invoices import Invoice