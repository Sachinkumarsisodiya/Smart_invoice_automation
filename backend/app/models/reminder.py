import uuid
from datetime import date, datetime, timezone
from sqlalchemy import String, Text, Date, DateTime, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, GUID


class ReminderType:
    T_MINUS_3 = "T_MINUS_3"
    T_MINUS_1 = "T_MINUS_1"
    DUE_TODAY = "DUE_TODAY"
    OVERDUE = "OVERDUE"
    MANUAL = "MANUAL"
    CHOICES = [T_MINUS_3, T_MINUS_1, DUE_TODAY, OVERDUE, MANUAL]


class ReminderStatus:
    SENT = "SENT"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class PaymentReminderLog(Base):
    __tablename__ = "payment_reminder_logs"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    invoice_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False, index=True)
    
    reminder_type: Mapped[str] = mapped_column(String(50), nullable=False)
    reminder_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    recipient_email: Mapped[str] = mapped_column(String(255), nullable=False)
    channel: Mapped[str] = mapped_column(String(50), default="EMAIL", nullable=False)
    status: Mapped[str] = mapped_column(String(50), default=ReminderStatus.SENT, nullable=False)
    error_message: Mapped[str] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    invoice = relationship("Invoice")

    __table_args__ = (
        UniqueConstraint("invoice_id", "reminder_type", "reminder_date", name="uq_invoice_reminder_type_date"),
        Index("idx_reminder_invoice_date", "invoice_id", "reminder_date"),
    )
