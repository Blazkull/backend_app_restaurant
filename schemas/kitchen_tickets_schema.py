
from datetime import datetime
from typing import Optional
from pydantic import Field
from sqlmodel import SQLModel


class KitchenTicketBase (SQLModel):
    __tablename__ = "kitchen_tickets"
    id: Optional[int] = Field(default=None, primary_key=True)
    id_order: int = Field(foreign_key="orders.id")
    id_status: int = Field(foreign_key="statuses.id")
    created_at: datetime = Field(default=datetime.utcnow)
    updated_at: datetime = Field(default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_on: Optional[datetime] = Field(default=None)
    deleted: bool = Field(default=False)

class KitchenTicketCreate(KitchenTicketBase):
    pass

class KitchenTicketStatusUpdate(SQLModel):
    id_status: int = Field(foreign_key="statuses.id")
    updated_at: datetime = Field(default=datetime.utcnow, onupdate=datetime.utcnow)

class KitchenTicketRead(KitchenTicketBase):
    pass

class KitchenTicketUpdate(SQLModel):
    id_order: Optional[int] = Field(default=None, foreign_key="orders.id")
    id_status: Optional[int] = Field(default=None, foreign_key="statuses.id")
    updated_at: datetime = Field(default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_on: Optional[datetime] = Field(default=None)
    deleted: Optional[bool] = Field(default=None)

class KitchenTicketFilter(SQLModel):
    id: Optional[int] = None
    id_order: Optional[int] = None
    id_status: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    deleted_on: Optional[datetime] = None
    deleted: Optional[bool] = None
