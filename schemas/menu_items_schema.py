from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime

class MenuItemBase(SQLModel):
    name: str = Field(max_length=100)
    id_category: int
    ingredients: str = Field(max_length=50)
    estimated_time: int
    price: float = Field(ge=0)
    id_status: int
    image: Optional[str] = Field(default=None, max_length=100)

class MenuItemCreate(MenuItemBase):
    pass

class MenuItemUpdate(SQLModel):
    name: Optional[str] = Field(default=None, max_length=100)
    id_category: Optional[int] = None
    ingredients: Optional[str] = Field(default=None, max_length=50)
    estimated_time: Optional[int] = None
    price: Optional[float] = Field(default=None, ge=0)
    id_status: Optional[int] = None
    image: Optional[str] = Field(default=None, max_length=100)

class MenuItemRead(MenuItemBase):
    id: int
    created_at: datetime
    updated_at: datetime