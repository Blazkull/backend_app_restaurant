from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime

class TypeIdentificationBase(SQLModel):
    type_identificaction: Optional[str] = Field(default=None, max_length=20)

class TypeIdentificationCreate(TypeIdentificationBase):
    pass

class TypeIdentificationUpdate(SQLModel):
    type_identificaction: Optional[str] = Field(default=None, max_length=20)

class TypeIdentificationRead(TypeIdentificationBase):
    id: int
    created_at: datetime
    updated_at: datetime