import uuid
from decimal import Decimal
from datetime import date
from sqlalchemy import String, Text, Date, Numeric, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, TimestampMixin, GUID


class PaymentMethod:
    BANK_TRANSFER = "BANK_TRANSFER"
    UPI = "UPI"
    CREDIT_CARD = "CREDIT_CARD"
    CASH = "CASH"
    CHEQUE = "CHEQUE"
    OTHER = "OTHER"
    CHOICES = [BANK_TRANSFER, UPI, CREDIT_CARD, CASH, CHEQUE, OTHER]


class Payment(Base, TimestampMixin):
    __tablename__ = "payments"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    invoice_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False, index=True)
    
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    payment_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    payment_method: Mapped[str] = mapped_column(String(50), default=PaymentMethod.BANK_TRANSFER, nullable=False)
    reference_number: Mapped[str] = mapped_column(String(100), nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    
    created_by: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    invoice = relationship("Invoice", back_populates="payments")
    creator = relationship("User")
