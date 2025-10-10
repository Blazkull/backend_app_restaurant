from datetime import datetime
from typing import Optional, List
from sqlmodel import Field, SQLModel, Relationship

class Table(SQLModel, table=True):
    __tablename__ = "tables"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=20, nullable=False)
    capacity: int = Field(nullable=False)
    
    # Claves Foráneas
    id_location: int = Field(foreign_key="locations.id")
    id_status: int = Field(foreign_key="status.id", default=5)
    id_user_assigned: int = Field(foreign_key="users.id")
    
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    deleted: bool = Field(default=False, nullable=False) # Campo Soft Delete (Estado)
    deleted_on: Optional[datetime] = Field(default=None) # Campo Soft Delete (Fecha)

    # Relaciones
    location: "Location" = Relationship(back_populates="tables")
    status: "Status" = Relationship(back_populates="tables")
    orders: List["Order"] = Relationship(back_populates="table")
    id_user_assigned: "User" = Relationship(back_populates="tables")


from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.locations import Location
    from models.status import Status
    from models.orders import Order
    from models.users import User