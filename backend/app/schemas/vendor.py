import uuid
from decimal import Decimal
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class VendorBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=50)
    gstin: Optional[str] = Field(None, max_length=50)
    address: Optional[str] = None
    category: str = Field(default="General", max_length=100)
    payment_terms_days: int = Field(default=30, ge=0, le=365)
    active: bool = True


class VendorCreate(VendorBase):
    pass


class VendorUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=50)
    gstin: Optional[str] = Field(None, max_length=50)
    address: Optional[str] = None
    category: Optional[str] = Field(None, max_length=100)
    payment_terms_days: Optional[int] = Field(None, ge=0, le=365)
    active: Optional[bool] = None


class VendorResponse(VendorBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class VendorDetailResponse(VendorResponse):
    total_invoices: int = 0
    total_invoiced_amount: Decimal = Decimal("0.00")
    total_paid_amount: Decimal = Decimal("0.00")
    outstanding_balance: Decimal = Decimal("0.00")
