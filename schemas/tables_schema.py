from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime

class TableBase(SQLModel):
    name: str = Field(max_length=20)
    id_location: int
    capacity: int
    id_status: int

class TableCreate(TableBase):
    pass

class TableUpdate(SQLModel):
    name: Optional[str] = Field(default=None, max_length=20)
    id_location: Optional[int] = None
    capacity: Optional[int] = None
    id_status: Optional[int] = None

class TableRead(TableBase):
    id: int
    created_at: datetime
    updated_at: datetime