from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime

# Base Schema (Campos de entrada/negocio)
class CategoryBase(SQLModel):
    name: str = Field(max_length=50)
    description: Optional[str] = Field(default=None, max_length=50)

class CategoryCreate(CategoryBase):
    pass

class CategoryUpdate(SQLModel):
    name: Optional[str] = Field(default=None, max_length=50)
    description: Optional[str] = Field(default=None, max_length=50)

# Schema para la lectura (incluye ID y todos los campos de auditoría)
class CategoryRead(CategoryBase):
    id: int
    created_at: datetime
    updated_at: datetime
    deleted: bool
    deleted_on: Optional[datetime]
    
    class Config:
        from_attributes = True