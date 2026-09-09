import uuid
from decimal import Decimal
from datetime import date, datetime
from typing import List, Optional, Any
from pydantic import BaseModel, ConfigDict, Field


class InvoiceItemBase(BaseModel):
    description: str
    quantity: Decimal = Decimal("1.000")
    unit_price: Decimal = Decimal("0.00")
    amount: Decimal = Decimal("0.00")


class InvoiceItemCreate(InvoiceItemBase):
    pass


class InvoiceItemResponse(InvoiceItemBase):
    id: uuid.UUID
    invoice_id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class VendorSnippet(BaseModel):
    id: uuid.UUID
    name: str
    email: Optional[str] = None
    gstin: Optional[str] = None
    category: str

    model_config = ConfigDict(from_attributes=True)


class InvoiceBase(BaseModel):
    invoice_number: str
    invoice_date: date
    due_date: date
    subtotal: Decimal = Decimal("0.00")
    tax_amount: Decimal = Decimal("0.00")
    total_amount: Decimal = Decimal("0.00")
    currency: str = "INR"
    status: str = "PENDING_REVIEW"
    payment_status: str = "PENDING"
    notes: Optional[str] = None


class InvoiceCreate(InvoiceBase):
    vendor_id: uuid.UUID
    document_path: str
    document_hash: str
    extraction_confidence: Decimal = Decimal("0.00")
    items: List[InvoiceItemCreate] = []


class InvoiceUpdate(BaseModel):
    invoice_number: Optional[str] = None
    vendor_id: Optional[uuid.UUID] = None
    invoice_date: Optional[date] = None
    due_date: Optional[date] = None
    subtotal: Optional[Decimal] = None
    tax_amount: Optional[Decimal] = None
    total_amount: Optional[Decimal] = None
    currency: Optional[str] = None
    status: Optional[str] = None
    payment_status: Optional[str] = None
    notes: Optional[str] = None


class InvoiceResponse(BaseModel):
    id: uuid.UUID
    vendor_id: uuid.UUID
    invoice_number: str
    invoice_date: date
    due_date: date
    subtotal: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    paid_amount: Decimal
    remaining_amount: Decimal
    currency: str
    status: str
    payment_status: str
    document_path: str
    document_hash: str
    extraction_status: str
    extraction_confidence: Decimal
    created_at: datetime
    updated_at: datetime
    vendor: Optional[VendorSnippet] = None

    model_config = ConfigDict(from_attributes=True)


class InvoiceDetailResponse(InvoiceResponse):
    raw_extracted_data: Optional[Any] = None
    validation_errors: Optional[Any] = None
    notes: Optional[str] = None
    items: List[InvoiceItemResponse] = []

    model_config = ConfigDict(from_attributes=True)


class InvoiceUploadResponse(BaseModel):
    invoice: InvoiceDetailResponse
    extracted_text_snippet: str
    char_count: int
    page_count: int
    is_digital: bool
    needs_ocr: bool
    message: str
