from datetime import datetime
from typing import Optional, List
from sqlmodel import Field, SQLModel, Relationship
from .link_models import UserRoleLink, RoleViewLink

class Role(SQLModel, table=True):
    __tablename__ = "roles"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=50, nullable=False)
    id_status: Optional[int] = Field(default=None, foreign_key="status.id")
    
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    deleted: bool = Field(default=False, nullable=False) # Campo Soft Delete (Estado)
    deleted_on: Optional[datetime] = Field(default=None) # Campo Soft Delete (Fecha)

    # Relaciones
    status: "Status" = Relationship(back_populates="roles")
    users: List["User"] = Relationship(back_populates="roles", link_model=UserRoleLink)
    views: List["View"] = Relationship(back_populates="roles", link_model=RoleViewLink)


from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.status import Status
    from models.users import User
    from models.views import View