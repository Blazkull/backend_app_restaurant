from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime

class InvoiceBase(SQLModel):
    id_client: int
    id_order: int
    id_payment_method: int
    returned: float = Field(ge=0)
    ammount_paid: float = Field(ge=0)
    total: float = Field(ge=0)
    id_status: Optional[int] = None

class InvoiceCreate(InvoiceBase):
    pass

class InvoiceUpdate(SQLModel):
    id_client: Optional[int] = None
    id_order: Optional[int] = None
    id_payment_method: Optional[int] = None
    returned: Optional[float] = Field(default=None, ge=0)
    ammount_paid: Optional[float] = Field(default=None, ge=0)
    total: Optional[float] = Field(default=None, ge=0)
    id_status: Optional[int] = None

class InvoiceRead(InvoiceBase):
    id: int
    created_at: datetime
    updated_at: datetime