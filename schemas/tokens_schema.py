from sqlmodel import SQLModel,Field
from typing import Optional
from datetime import datetime

class TokenBase(SQLModel):
    id_user: int
    token: str = Field(max_length=255)
    status_token: int
    expiration: datetime
    date_token: datetime

class TokenCreate(TokenBase):
    pass

class TokenRead(TokenBase):
    id: int

class AccessTokenResponse(SQLModel):
    """Schema usado para la respuesta del endpoint de login."""
    access_token: str
    token_type: str = Field(default="bearer")
    role_name: str