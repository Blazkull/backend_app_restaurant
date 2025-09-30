from sqlmodel import SQLModel, Field
from typing import Optional, List
from datetime import datetime

class RoleBase(SQLModel):
    name: str = Field(max_length=50)
    id_status: Optional[int] = None

class RoleCreate(RoleBase):
    view_ids: List[int] = [] 

class RoleUpdate(SQLModel):
    name: Optional[str] = Field(default=None, max_length=50)
    id_status: Optional[int] = None
    view_ids: Optional[List[int]] = None

class RoleRead(RoleBase):
    id: int
    created_at: datetime
    updated_at: datetime