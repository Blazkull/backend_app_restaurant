from typing import Optional
from datetime import datetime
from sqlmodel import Field, SQLModel

class InformationCompany(SQLModel, table=True):
    """Modelo para 'information_company'."""
    __tablename__ = "information_company"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=50, nullable=False)
    address: str = Field(max_length=30, nullable=False)
    location: str = Field(max_length=50, nullable=False)
    identification_number: str = Field(max_length=50, nullable=False)
    email: str = Field(max_length=100, unique=True, nullable=False)
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)