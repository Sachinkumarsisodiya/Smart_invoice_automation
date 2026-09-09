import uuid
from decimal import Decimal
from datetime import date
from sqlalchemy import String, Text, Date, Numeric, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, TimestampMixin, GUID


class ExpenseCategory:
    OFFICE = "Office"
    TRANSPORT = "Transport"
    PACKAGING = "Packaging"
    ELECTRONICS = "Electronics"
    SOFTWARE = "Software"
    MARKETING = "Marketing"
    RENT = "Rent"
    UTILITIES = "Utilities"
    OTHER = "Other"
    CHOICES = [OFFICE, TRANSPORT, PACKAGING, ELECTRONICS, SOFTWARE, MARKETING, RENT, UTILITIES, OTHER]


class Expense(Base, TimestampMixin):
    __tablename__ = "expenses"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    invoice_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("invoices.id", ondelete="SET NULL"), nullable=True, index=True)
    vendor_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("vendors.id", ondelete="SET NULL"), nullable=True, index=True)
    
    category: Mapped[str] = mapped_column(String(50), default=ExpenseCategory.OTHER, nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    expense_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    payment_method: Mapped[str] = mapped_column(String(50), default="BANK_TRANSFER", nullable=False)
    
    created_by: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    invoice = relationship("Invoice", back_populates="expenses")
    vendor = relationship("Vendor", back_populates="expenses")
    creator = relationship("User")
