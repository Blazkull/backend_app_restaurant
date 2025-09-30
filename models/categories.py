from datetime import datetime
from typing import Optional, List
from sqlmodel import Field, SQLModel, Relationship

class Category(SQLModel, table=True):
    """Modelo para 'categories' (del menú)."""
    __tablename__ = "categories"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=50, nullable=False)
    description: Optional[str] = Field(default=None, max_length=50)
    
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    deleted_at: Optional[datetime] = Field(default=None)

    # Relaciones
    menu_items: List["MenuItem"] = Relationship(back_populates="category")
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .menu_items import MenuItem