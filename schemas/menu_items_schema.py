from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime


class MenuItemBase(SQLModel):
    name: str = Field(max_length=100)
    id_category: int
    ingredients: Optional[str] = Field(default=None, max_length=255)
    estimated_time: int
    price: float
    id_status: int
    image: Optional[str] = Field(default=None, max_length=100) # Nombre del archivo


class MenuItemCreate(MenuItemBase):
    pass

class MenuItemUpdate(SQLModel):
    name: Optional[str] = Field(default=None, max_length=100)
    id_category: Optional[int] = None
    ingredients: Optional[str] = Field(default=None, max_length=255)
    estimated_time: Optional[int] = None
    price: Optional[float] = None
    id_status: Optional[int] = None
    image: Optional[str] = Field(default=None, max_length=255)
    deleted: Optional[bool] = None 

class MenuItemFilter(SQLModel):
    name: Optional[str] = None
    id_category: Optional[int] = None
    id_status: Optional[int] = None 

class MenuItemRead(MenuItemBase):
    id: int
    created_at: datetime
    updated_at: datetime
    deleted: bool
    deleted_on: Optional[datetime]
    id_category: Optional[int] = None
    id_status: Optional[int] = None 
    image_url: Optional[str] = None 
    
    class Config:
        from_attributes = True

# Esquema para listar con paginación
class MenuItemListResponse(SQLModel):
    items: list[MenuItemRead]
    total_items: int
    page: int
    page_size: int
    total_pages: int

class MenuItemFilter(SQLModel):
    name: Optional[str] = None
    id_category: Optional[int] = None
    id_status: Optional[int] = None

    class Config:
        from_attributes = True