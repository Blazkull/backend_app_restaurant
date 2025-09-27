from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime

class StatusBase(SQLModel):
    name: str = Field(max_length=20)
    description: Optional[str] = Field(default=None, max_length=50)

class StatusCreate(StatusBase):
    pass

class StatusUpdate(SQLModel):
    name: Optional[str] = Field(default=None, max_length=20)
    description: Optional[str] = Field(default=None, max_length=50)

class StatusRead(StatusBase):
    id: int
    created_at: datetime
    updated_at: datetime