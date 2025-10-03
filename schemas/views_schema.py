from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime

class ViewBase(SQLModel):
    name: str = Field(max_length=100)
    path: str = Field(max_length=150) 

class ViewCreate(ViewBase):
    id_status: Optional[int] = None # Permitir asignar un status al crear (si no lo hereda de ViewBase)

class ViewUpdate(SQLModel):
    name: Optional[str] = Field(default=None, max_length=100)
    path: Optional[str] = Field(default=None, max_length=150) 
    id_status: Optional[int] = None

class ViewRead(ViewBase):
    id: int
    id_status: Optional[int]
    created_at: datetime
    updated_at: datetime
    deleted: bool
    deleted_on: Optional[datetime]
    
    class Config:
        from_attributes = True