from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime

# Esquemas anidados para Category y Status
class CategoryReadForMenuItem(SQLModel):
    name: str

class StatusReadForMenuItem(SQLModel):
    name: str

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
    image: Optional[str] = Field(default=None, max_length=100) # Solo el nombre del archivo si se actualiza
    # Para soft delete
    deleted: Optional[bool] = None 


class MenuItemRead(MenuItemBase):
    id: int
    created_at: datetime
    updated_at: datetime
    deleted: bool
    deleted_on: Optional[datetime]

    # Relaciones para mostrar en la respuesta
    category: Optional[CategoryReadForMenuItem] = None
    status: Optional[StatusReadForMenuItem] = None 
    
    # Campo adicional para enviar la URL completa de la imagen al frontend
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

