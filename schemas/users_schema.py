from sqlmodel import SQLModel, Field
from pydantic import EmailStr
from typing import Optional, List
from datetime import datetime

class UserBase(SQLModel):
    name: str = Field(max_length=100)
    username: str = Field(max_length=50)
    email: EmailStr = Field(max_length=100)
    id_role: Optional[int] = None
    id_status: Optional[int] = None
    last_connection: Optional[datetime] = None

class UserLogin(SQLModel):
    username: str = Field(max_length=50)
    password: str = Field(max_length=100)

class UserCreate(UserBase):
    password: str = Field(min_length=6, max_length=100)
    additional_role_ids: List[int] = [] 

class UserUpdate(SQLModel):
    name: Optional[str] = Field(default=None, max_length=100)
    username: Optional[str] = Field(default=None, max_length=50)
    email: Optional[EmailStr] = None
    id_role: Optional[int] = None
    id_status: Optional[int] = None
    additional_role_ids: Optional[List[int]] = None
    deleted: Optional[bool] = None 
    

class UserRead(UserBase):
    id: int
    created_at: datetime
    updated_at: datetime
    deleted: bool = False 
    deleted_on: Optional[datetime] = None
    last_connection: Optional[datetime] = None
    
    class Config:
        from_attributes = True
    
class PasswordUpdate(SQLModel):
    password: str = Field(min_length=6, max_length=100)