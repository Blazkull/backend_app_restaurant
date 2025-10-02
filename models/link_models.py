from typing import Optional, TYPE_CHECKING
from sqlmodel import Field, SQLModel
from datetime import datetime


class UserRoleLink(SQLModel, table=True):
    __tablename__ = "user_role_link"
    
    id_user: Optional[int] = Field(default=None, primary_key=True, foreign_key="users.id")
    id_role: Optional[int] = Field(default=None, primary_key=True, foreign_key="roles.id")


class RoleViewLink(SQLModel, table=True):
    __tablename__ = "role_view_link"
    
    id_role: Optional[int] = Field(default=None, primary_key=True, foreign_key="roles.id")
    id_view: Optional[int] = Field(default=None, primary_key=True, foreign_key="views.id")
    
    # NUEVO CAMPO: Estado del permiso (el checkbox)
    enabled: bool = Field(default=True)
    
    # Campos de Auditoría
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


if TYPE_CHECKING:
    from models.users import User
    from models.roles import Role
    from models.views import View