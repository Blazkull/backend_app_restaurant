from sqlmodel import SQLModel, Field
from typing import Optional, List
from datetime import datetime

# Importamos la relación de permisos
from schemas.role_view_link_schema import RoleViewRead 

class RoleBase(SQLModel):
    name: str = Field(max_length=50)
    id_status: Optional[int] = None

class RoleCreate(RoleBase):
    pass 

class RoleUpdate(SQLModel):
    name: Optional[str] = Field(default=None, max_length=50)
    id_status: Optional[int] = None

class RoleRead(RoleBase):
    id: int
    created_at: datetime
    updated_at: datetime
    deleted: bool
    deleted_on: Optional[datetime]
    # RELACIÓN: Incluimos los permisos asociados al rol
    permissions: List[RoleViewRead] = []
    
    class Config:
        from_attributes = True