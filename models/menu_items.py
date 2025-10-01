from sqlmodel import Field, Relationship, SQLModel
from typing import Optional
from datetime import datetime

# Asumiendo que Category y Status ya están definidos y tienen 'id'
# from models.categories import Category # Importación circular, mejor usar strings y TYPE_CHECKING
# from models.status import Status 

class MenuItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=100, index=True)
    id_category: int = Field(foreign_key="category.id")
    ingredients: Optional[str] = Field(default=None, max_length=255) # Cambiado a 255 por si son muchos
    estimated_time: int = Field(description="Tiempo estimado de preparación en minutos")
    price: float = Field(gt=0, description="Precio del ítem del menú")
    id_status: int = Field(foreign_key="status.id")
    image: Optional[str] = Field(default=None, max_length=100)
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"onupdate": datetime.utcnow})
    deleted: bool = Field(default=False)
    deleted_on: Optional[datetime] = Field(default=None)

    # Relaciones
    category: Optional["Category"] = Relationship(back_populates="menu_items")
    status_rel: Optional["Status"] = Relationship(back_populates="menu_items") # Nombre diferente para evitar colisión con 'status'
    
    # Si tienes order_items
    order_items: list["OrderItem"] = Relationship(back_populates="menu_item_rel")

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from models.categories import Category
    from models.status import Status
    from models.order_items import OrderItem