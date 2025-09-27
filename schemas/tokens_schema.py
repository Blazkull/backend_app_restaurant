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