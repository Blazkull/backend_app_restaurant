from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime

class LocationBase(SQLModel):
    name: str = Field(max_length=50)
    description: Optional[str] = Field(default=None, max_length=50)

class LocationCreate(LocationBase):
    pass

class LocationUpdate(SQLModel):
    name: Optional[str] = Field(default=None, max_length=50)
    description: Optional[str] = Field(default=None, max_length=50)

class LocationRead(LocationBase):
    id: int
    created_at: datetime
    updated_at: datetime
    deleted: bool
    deleted_on: Optional[datetime]
    
    class Config:
        from_attributes = True