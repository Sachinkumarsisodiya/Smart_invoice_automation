import uuid
from abc import ABC, abstractmethod
from decimal import Decimal
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class ExtractedItemSchema(BaseModel):
    description: str
    quantity: Decimal = Field(default=Decimal("1.000"))
    unit_price: Decimal = Field(default=Decimal("0.00"))
    amount: Decimal = Field(default=Decimal("0.00"))


class ExtractedInvoiceSchema(BaseModel):
    vendor_name: str
    vendor_gstin: Optional[str] = None
    vendor_email: Optional[str] = None
    invoice_number: str
    invoice_date: str  # YYYY-MM-DD
    due_date: str      # YYYY-MM-DD
    subtotal: Decimal = Field(default=Decimal("0.00"))
    tax_amount: Decimal = Field(default=Decimal("0.00"))
    total_amount: Decimal = Field(default=Decimal("0.00"))
    currency: str = "INR"
    items: List[ExtractedItemSchema] = []
    confidence_score: Decimal = Field(default=Decimal("85.00"))
    raw_response: Optional[Dict[str, Any]] = None
    is_mock: bool = False


class BaseAIProvider(ABC):
    """Abstract interface for AI invoice extraction providers."""

    @abstractmethod
    async def extract_invoice(self, text_content: str, metadata: Optional[Dict[str, Any]] = None) -> ExtractedInvoiceSchema:
        """Extracts structured invoice information from raw document text."""
        pass
