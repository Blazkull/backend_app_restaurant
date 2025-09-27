from datetime import datetime
from typing import Optional, List
from sqlmodel import Field, SQLModel, Relationship

class Location(SQLModel, table=True):
    __tablename__ = "locations"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=50, nullable=False)
    description: Optional[str] = Field(default=None, max_length=50)
    
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    deleted_at: Optional[datetime] = Field(default=None)

    # Relaciones
    tables: List["Table"] = Relationship(back_populates="location")

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.tables import Table