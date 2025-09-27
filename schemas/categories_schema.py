from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime

class CategoryBase(SQLModel):
    name: str = Field(max_length=50)
    description: Optional[str] = Field(default=None, max_length=50)

class CategoryCreate(CategoryBase):
    pass

class CategoryUpdate(SQLModel):
    name: Optional[str] = Field(default=None, max_length=50)
    description: Optional[str] = Field(default=None, max_length=50)

class CategoryRead(CategoryBase):
    id: int
    created_at: datetime
    updated_at: datetime