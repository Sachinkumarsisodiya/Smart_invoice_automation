import uuid
from decimal import Decimal
from datetime import date, datetime
from typing import Optional, List, Dict
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.vendor import VendorResponse


class ExpenseBase(BaseModel):
    category: str = Field(..., max_length=50)
    amount: Decimal = Field(..., gt=Decimal("0.00"), decimal_places=2)
    expense_date: date
    description: str = Field(..., min_length=2)
    payment_method: str = Field(default="BANK_TRANSFER", max_length=50)
    vendor_id: Optional[uuid.UUID] = None
    invoice_id: Optional[uuid.UUID] = None


class ExpenseCreate(ExpenseBase):
    pass


class ExpenseUpdate(BaseModel):
    category: Optional[str] = Field(None, max_length=50)
    amount: Optional[Decimal] = Field(None, gt=Decimal("0.00"), decimal_places=2)
    expense_date: Optional[date] = None
    description: Optional[str] = Field(None, min_length=2)
    payment_method: Optional[str] = Field(None, max_length=50)
    vendor_id: Optional[uuid.UUID] = None
    invoice_id: Optional[uuid.UUID] = None


class ExpenseResponse(ExpenseBase):
    id: uuid.UUID
    created_by: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime
    vendor: Optional[VendorResponse] = None

    model_config = ConfigDict(from_attributes=True)


class ExpenseCategoryBreakdown(BaseModel):
    category: str
    total_amount: Decimal
    count: int
    percentage: float


class ExpenseSummaryResponse(BaseModel):
    total_expenses_amount: Decimal
    total_count: int
    by_category: List[ExpenseCategoryBreakdown]
