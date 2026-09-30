import uuid
from decimal import Decimal
from datetime import date
from sqlalchemy import String, Text, Date, Numeric, JSON, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, TimestampMixin, GUID


class InvoiceStatus:
    PROCESSING = "PROCESSING"
    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    PAID = "PAID"
    OVERDUE = "OVERDUE"
    DUPLICATE = "DUPLICATE"
    CHOICES = [PROCESSING, PENDING_REVIEW, APPROVED, REJECTED, PAID, OVERDUE, DUPLICATE]


class PaymentStatus:
    PENDING = "PENDING"
    PARTIALLY_PAID = "PARTIALLY_PAID"
    PAID = "PAID"
    OVERDUE = "OVERDUE"
    CHOICES = [PENDING, PARTIALLY_PAID, PAID, OVERDUE]


class ExtractionStatus:
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    MANUAL = "MANUAL"
    CHOICES = [PENDING, SUCCESS, FAILED, MANUAL]


class Invoice(Base, TimestampMixin):
    __tablename__ = "invoices"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    vendor_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("vendors.id", ondelete="RESTRICT"), nullable=False, index=True)
    
    invoice_number: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    invoice_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    due_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    
    # Financial values with strict Numeric(14, 2) Decimal precision
    subtotal: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0.00"), nullable=False)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0.00"), nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0.00"), nullable=False)
    paid_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0.00"), nullable=False)
    remaining_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0.00"), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)
    
    # Statuses
    status: Mapped[str] = mapped_column(String(50), default=InvoiceStatus.PROCESSING, nullable=False, index=True)
    payment_status: Mapped[str] = mapped_column(String(50), default=PaymentStatus.PENDING, nullable=False, index=True)
    
    # Document storage & extraction
    document_path: Mapped[str] = mapped_column(String(500), nullable=False)
    document_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)  # SHA-256
    extraction_status: Mapped[str] = mapped_column(String(50), default=ExtractionStatus.PENDING, nullable=False)
    extraction_confidence: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0.00"), nullable=False)
    
    # Metadata payloads
    raw_extracted_data: Mapped[dict] = mapped_column(JSON, nullable=True)
    validation_errors: Mapped[dict] = mapped_column(JSON, nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True)

    # Relationships
    vendor = relationship("Vendor", back_populates="invoices")
    items = relationship("InvoiceItem", back_populates="invoice", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="invoice", cascade="all, delete-orphan")
    expenses = relationship("Expense", back_populates="invoice")

    __table_args__ = (
        UniqueConstraint("vendor_id", "invoice_number", name="uq_vendor_invoice_number"),
        Index("idx_invoices_status_due_date", "status", "due_date"),
        Index("idx_invoices_vendor_date", "vendor_id", "invoice_date"),
    )


class InvoiceItem(Base, TimestampMixin):
    __tablename__ = "invoice_items"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    invoice_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False, index=True)
    
    description: Mapped[str] = mapped_column(Text, nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 3), default=Decimal("1.000"), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0.00"), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0.00"), nullable=False)

    # Relationships
    invoice = relationship("Invoice", back_populates="items")
