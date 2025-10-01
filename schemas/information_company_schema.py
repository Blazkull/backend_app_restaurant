from sqlmodel import SQLModel, Field
from pydantic import EmailStr
from typing import Optional
from datetime import datetime

class InformationCompanyBase(SQLModel):
    name: str = Field(max_length=50)
    address: str = Field(max_length=30)
    location: str = Field(max_length=50)
    identification_number: str = Field(max_length=50)
    email: EmailStr = Field(max_length=100)

class InformationCompanyCreate(InformationCompanyBase):
    pass

class InformationCompanyUpdate(SQLModel):
    name: Optional[str] = Field(default=None, max_length=50)
    address: Optional[str] = Field(default=None, max_length=30)
    location: Optional[str] = Field(default=None, max_length=50)
    identification_number: Optional[str] = Field(default=None, max_length=50)
    email: Optional[EmailStr] = None

class InformationCompanyRead(InformationCompanyBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True