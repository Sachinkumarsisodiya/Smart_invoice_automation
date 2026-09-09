import uuid
from decimal import Decimal
from datetime import date, datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict


class DashboardKPIsResponse(BaseModel):
    total_invoices_count: int
    total_invoiced_amount: Decimal
    total_paid_amount: Decimal
    total_outstanding_amount: Decimal
    overdue_invoices_count: int
    overdue_amount: Decimal
    pending_review_count: int
    total_expenses_amount: Decimal
    total_expenses_count: int
    total_vendors_count: int
    average_ai_confidence: Decimal
    total_settled_transactions: int


class MonthlyCashflowItem(BaseModel):
    month_key: str  # YYYY-MM
    month_label: str  # Sep 2026
    invoiced_amount: Decimal
    paid_amount: Decimal
    expense_amount: Decimal
    net_cashflow: Decimal


class CategoryDistributionItem(BaseModel):
    category: str
    amount: Decimal
    count: int
    percentage: float


class StatusDistributionItem(BaseModel):
    status: str
    count: int
    amount: Decimal


class TopVendorItem(BaseModel):
    vendor_id: uuid.UUID
    vendor_name: str
    category: str
    total_invoiced: Decimal
    total_paid: Decimal
    outstanding_balance: Decimal
    invoice_count: int


class RecentActivityItem(BaseModel):
    id: str
    type: str  # INVOICE, PAYMENT, EXPENSE
    title: str
    subtitle: Optional[str] = None
    amount: Optional[Decimal] = None
    status: Optional[str] = None
    timestamp: datetime


class TaxVendorBreakdown(BaseModel):
    vendor_id: uuid.UUID
    vendor_name: str
    gstin: Optional[str] = None
    subtotal: Decimal
    tax_amount: Decimal
    total_gross: Decimal
    invoice_count: int


class TaxSummaryResponse(BaseModel):
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    total_subtotal: Decimal
    total_tax_amount: Decimal
    total_gross_amount: Decimal
    total_invoices: int
    vendors_breakdown: List[TaxVendorBreakdown]
