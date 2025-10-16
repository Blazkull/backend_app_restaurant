from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from sqlmodel import Field, SQLModel, Relationship
from .link_models import UserRoleLink

class User(SQLModel, table=True):
    """Modelo para 'users' (empleados del restaurante)."""
    __tablename__ = "users" 
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=100, nullable=False)
    username: str = Field(max_length=50, unique=True, nullable=False)
    password: str = Field(max_length=100, nullable=False)
    email: str = Field(max_length=100, unique=True, nullable=False)
    
    id_role: Optional[int] = Field(default=None, foreign_key="roles.id")
    id_status: Optional[int] = Field(default=None, foreign_key="status.id")
    
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    last_connection: Optional[datetime] = Field(default=None)
    deleted: bool = Field(default=False, nullable=False)
    deleted_on: Optional[datetime] = Field(default=None)

    # Relaciones
    role: "Role" = Relationship(back_populates="users")
    status: "Status" = Relationship(back_populates="users")
    tokens: List["Token"] = Relationship(back_populates="user")
    roles: List["Role"] = Relationship(back_populates="users", link_model=UserRoleLink)

    # 🔹 NUEVO: Relación con órdenes
    orders: List["Order"] = Relationship(back_populates="user_created")
    tables_assigned: List["Table"] = Relationship(back_populates="user_assigned")


if TYPE_CHECKING:
    from models.status import Status
    from models.roles import Role
    from models.tokens import Token
    from models.orders import Order
    from models.tables import Table
