from pydantic import BaseModel
from sqlmodel import SQLModel, Field
from typing import List, Optional
from datetime import datetime

class PaymentMethodBase(SQLModel):
    name: str = Field(max_length=30)

class PaymentMethodCreate(PaymentMethodBase):
    pass

class PaymentMethodUpdate(SQLModel):
    name: Optional[str] = Field(default=None, max_length=30)

class PaymentMethodRead(PaymentMethodBase):
    id: int
    created_at: datetime
    updated_at: datetime
    deleted: bool
    deleted_on: Optional[datetime]
    
    class Config:
        from_attributes = True

class PaymentMethodListResponse(BaseModel):
    items: List[PaymentMethodRead]
    total_items: int
    page: int
    page_size: int
    total_pages: int