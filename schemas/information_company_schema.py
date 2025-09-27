from sqlmodel import SQLModel, Field
from pydantic import EmailStr
from typing import Optional

class InformationCompanyBase(SQLModel):
    name: str = Field(max_length=50)
    adress: str = Field(max_length=30)
    location: str = Field(max_length=50)
    identification_number: str = Field(max_length=50)
    email: EmailStr = Field(max_length=100)

class InformationCompanyCreate(InformationCompanyBase):
    pass

class InformationCompanyUpdate(SQLModel):
    name: Optional[str] = Field(default=None, max_length=50)
    adress: Optional[str] = Field(default=None, max_length=30)
    location: Optional[str] = Field(default=None, max_length=50)
    identification_number: Optional[str] = Field(default=None, max_length=50)
    email: Optional[EmailStr] = None

class InformationCompanyRead(InformationCompanyBase):
    id: int