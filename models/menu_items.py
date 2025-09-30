from datetime import datetime
from typing import Optional, List
from sqlmodel import Field, SQLModel, Relationship

class MenuItem(SQLModel, table=True):
    __tablename__ = "menu_items"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=100, nullable=False)
    ingredients: str = Field(max_length=50, nullable=False)
    estimated_time: int = Field(nullable=False)
    price: float = Field(ge=0) # DECIMAL(10, 2) se mapea a float, usamos ge=0 para validación
    image: Optional[str] = Field(default=None, max_length=100)
    
    # Claves Foráneas
    id_category: int = Field(foreign_key="categories.id")
    id_status: int = Field(foreign_key="status.id")
    
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    deleted_at: Optional[datetime] = Field(default=None)

    # Relaciones
    category: "Category" = Relationship(back_populates="menu_items")
    status: "Status" = Relationship(back_populates="menu_items")
    order_items: List["OrderItem"] = Relationship(back_populates="menu_item")


from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.categories import Category
    from models.status import Status
    from models.order_items import OrderItem