from datetime import datetime
from typing import Optional, List
from sqlmodel import Field, SQLModel, Relationship

class TypeIdentification(SQLModel, table=True):
    __tablename__ = "type_identification"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    type_identification: Optional[str] = Field(default=None, max_length=20)
    
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    deleted: bool = Field(default=False, nullable=False) # Campo Soft Delete (Estado)
    deleted_on: Optional[datetime] = Field(default=None) # Campo Soft Delete (Fecha)

    # Relaciones
    clients: List["Client"] = Relationship(back_populates="type_identification")
    
from typing import TYPE_CHECKING

if TYPE_CHECKING: 
    from models.clients import Client