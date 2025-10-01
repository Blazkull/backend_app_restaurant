from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime

class ViewBase(SQLModel):
    name: str = Field(max_length=100)
    id_status: Optional[int] = None

class ViewCreate(ViewBase):
    pass

class ViewUpdate(SQLModel):
    name: Optional[str] = Field(default=None, max_length=100)
    id_status: Optional[int] = None

class ViewRead(ViewBase):
    id: int
    created_at: datetime
    updated_at: datetime
    deleted: bool
    deleted_on: Optional[datetime]
    
    class Config:
        from_attributes = True