from sqlmodel import SQLModel, Field
from pydantic import EmailStr
from typing import Optional
from datetime import datetime

class ClientBase(SQLModel):
    fullname: str = Field(max_length=100)
    address: Optional[str] = Field(default=None, max_length=100)
    phone_number: str = Field(max_length=20)
    identification_number: str = Field(max_length=100)
    email: EmailStr = Field(max_length=100)
    id_type_identificacion: int

class ClientCreate(ClientBase):
    pass

class ClientUpdate(SQLModel):
    fullname: Optional[str] = Field(default=None, max_length=100)
    address: Optional[str] = Field(default=None, max_length=100)
    phone_number: Optional[str] = Field(default=None, max_length=20)
    identification_number: Optional[str] = Field(default=None, max_length=100)
    email: Optional[EmailStr] = None
    id_type_identificacion: Optional[int] = None

class ClientRead(ClientBase):
    id: int
    created_at: datetime
    updated_at: datetime
    deleted: bool
    deleted_on: Optional[datetime]

    class Config:
        from_attributes = True