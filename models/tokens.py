from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel, Relationship

class Token(SQLModel, table=True):

    __tablename__ = "tokens"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    id_user: int = Field(foreign_key="users.id")
    token: str = Field(max_length=255, nullable=False)
    status_token: bool = Field(default=True)
    expiration: datetime = Field(nullable=False)
    date_token: datetime = Field(nullable=False)

    # Relaciones
    user: "User" = Relationship(back_populates="tokens")

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.users import User