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

class TableStatusUpdate(SQLModel):
    """Schema para actualizar únicamente el ID del estado de la mesa."""
    id_status: int = Field(..., description="El nuevo ID del estado de la mesa.")

class TableRead(TableBase):
    id: int
    created_at: datetime
    updated_at: datetime
    deleted: bool
    deleted_on: Optional[datetime]
    
    class Config:
        from_attributes = True