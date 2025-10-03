from datetime import datetime
from typing import Optional, List
from sqlmodel import Field, SQLModel, Relationship
from .link_models import RoleViewLink


class View(SQLModel, table=True):
    """Modelo para 'views' (permisos/recursos)."""
    __tablename__ = "views"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=100, nullable=False)
    id_status: Optional[int] = Field(default=None, foreign_key="status.id")
    path: str = Field(max_length=150, nullable=False, unique=True, index=True) # Ruta del recurso
    
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    deleted: bool = Field(default=False, nullable=False) # Campo Soft Delete (Estado)
    deleted_on: Optional[datetime] = Field(default=None) # Campo Soft Delete (Fecha)

    # Relaciones
    status: "Status" = Relationship(back_populates="views")
    roles: List["Role"] = Relationship(back_populates="views", link_model=RoleViewLink)

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from models.status import Status
    from models.roles import Role