import uuid
from decimal import Decimal
from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from app.models.payment import PaymentMethod


class PaymentBase(BaseModel):
    invoice_id: uuid.UUID
    amount: Decimal = Field(..., gt=Decimal("0.00"), decimal_places=2)
    payment_date: date
    payment_method: str = Field(default=PaymentMethod.BANK_TRANSFER, max_length=50)
    reference_number: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None


class PaymentCreate(PaymentBase):
    pass


class PaymentResponse(PaymentBase):
    id: uuid.UUID
    created_by: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaymentWithInvoiceResponse(PaymentResponse):
    invoice_number: Optional[str] = None
    vendor_name: Optional[str] = None
    invoice_total: Optional[Decimal] = None
    invoice_remaining: Optional[Decimal] = None
    invoice_payment_status: Optional[str] = None
