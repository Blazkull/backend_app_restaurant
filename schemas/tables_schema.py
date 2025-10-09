from ast import List
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
    id_user_assigned: Optional[int] = None

class TableStatusUpdate(SQLModel):
    """Schema para actualizar únicamente el ID del estado de la mesa."""
    id_status: int = Field(..., description="El nuevo ID del estado de la mesa.")


class TableFilter(SQLModel):
    """Schema para filtrar mesas en consultas."""
    id_location: Optional[int] = Field(default=None, description="Filtrar por ID de ubicación.")
    id_status: Optional[int] = Field(default=None, description="Filtrar por ID de estado.")
    min_capacity: Optional[int] = Field(default=None, description="Filtrar por capacidad mínima.")
    max_capacity: Optional[int] = Field(default=None, description="Filtrar por capacidad máxima.")

class TableRead(TableBase):
    id: int
    created_at: datetime
    updated_at: datetime
    deleted: bool
    deleted_on: Optional[datetime]
    
    class Config:
        from_attributes = True

class TableListResponse(SQLModel):
    """
    Schema de respuesta para el endpoint de listar mesas, incluyendo paginación.
    """
    items: List[TableRead] = Field(description="Lista de mesas que cumplen con el filtro y paginación.")
    total_count: int = Field(description="Número total de mesas activas que coinciden con los filtros.")
    offset: int = Field(description="El punto de inicio (offset) usado en la consulta.")
    limit: int = Field(description="El límite (limit) usado en la consulta.")
    total_pages: int = Field(description="El número total de páginas disponibles.")
    current_page: int = Field(description="El número de página actual (basado en offset y limit).")