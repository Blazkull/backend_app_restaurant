from typing import Optional
from sqlmodel import Field, SQLModel


class UserRoleLink(SQLModel, table=True):
    __tablename__ = "user_roles"
    
    id_user: Optional[int] = Field(default=None, primary_key=True, foreign_key="users.id")
    id_role: Optional[int] = Field(default=None, primary_key=True, foreign_key="roles.id")


class RoleViewLink(SQLModel, table=True):
    __tablename__ = "role_views"
    
    id_role: Optional[int] = Field(default=None, primary_key=True, foreign_key="roles.id")
    id_view: Optional[int] = Field(default=None, primary_key=True, foreign_key="views.id")


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from models.users import User
    from models.roles import Role
    from models.views import View