from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime

class TypeIdentificationBase(SQLModel):
    # NOTA: Se corrige 'type_identificaction' a 'type_identification' por convención
    type_identification: Optional[str] = Field(default=None, max_length=20)

class TypeIdentificationCreate(TypeIdentificationBase):
    pass

class TypeIdentificationUpdate(SQLModel):
    type_identification: Optional[str] = Field(default=None, max_length=20)

class TypeIdentificationRead(TypeIdentificationBase):
    id: int
    created_at: datetime
    updated_at: datetime
    deleted: bool
    deleted_on: Optional[datetime]
    
    class Config:
        from_attributes = True