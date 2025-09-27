from datetime import datetime
from typing import Optional, List
from sqlmodel import Field, SQLModel, Relationship
# Importamos el Link Model
from .link_models import UserRoleLink

class User(SQLModel, table=True):
    __tablename__ = "users" 
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=100, nullable=False)
    username: str = Field(max_length=50, unique=True, nullable=False)
    password: str = Field(max_length=100, nullable=False)
    email: str = Field(max_length=100, unique=True, nullable=False)
    
    # Claves Foráneas
    id_role: Optional[int] = Field(default=None, foreign_key="roles.id") # Rol principal/por defecto
    id_status: Optional[int] = Field(default=None, foreign_key="status.id") 
    
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    deleted_at: Optional[datetime] = Field(default=None)

    # Relaciones
    role: "Role" = Relationship(back_populates="users")# Uno a uno a Rol
    status: "Status" = Relationship(back_populates="users") # Uno a uno a Status
    tokens: List["Token"] = Relationship(back_populates="user") # Uno a muchos a Token
    roles: List["Role"] = Relationship(back_populates="users", link_model=UserRoleLink)# Muchos a uno a Rol

from typing import TYPE_CHECKING

if TYPE_CHECKING:   
    from models.roles import Role
    from models.status import Status
    from models.tokens import Token
    from .link_models import UserRoleLink