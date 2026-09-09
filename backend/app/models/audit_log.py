import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, JSON, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, GUID


class AuditAction:
    USER_REGISTER = "USER_REGISTER"
    USER_LOGIN = "USER_LOGIN"
    USER_CREATED = "USER_CREATED"
    USER_UPDATED = "USER_UPDATED"
    USER_DELETED = "USER_DELETED"
    INVOICE_UPLOADED = "INVOICE_UPLOADED"
    INVOICE_EXTRACTED = "INVOICE_EXTRACTED"
    INVOICE_APPROVED = "INVOICE_APPROVED"
    INVOICE_REJECTED = "INVOICE_REJECTED"
    INVOICE_EDITED = "INVOICE_EDITED"
    INVOICE_DELETED = "INVOICE_DELETED"
    PAYMENT_RECORDED = "PAYMENT_RECORDED"
    INVOICE_MARKED_PAID = "INVOICE_MARKED_PAID"
    VENDOR_CREATED = "VENDOR_CREATED"
    VENDOR_UPDATED = "VENDOR_UPDATED"
    VENDOR_DELETED = "VENDOR_DELETED"
    EXPENSE_CREATED = "EXPENSE_CREATED"
    EXPENSE_UPDATED = "EXPENSE_UPDATED"
    EXPENSE_DELETED = "EXPENSE_DELETED"
    INVOICE_MARKED_OVERDUE = "INVOICE_MARKED_OVERDUE"
    PAYMENT_REMINDER_SENT = "PAYMENT_REMINDER_SENT"
    PAYMENT_REMINDER_FAILED = "PAYMENT_REMINDER_FAILED"
    NOTIFICATION_CREATED = "NOTIFICATION_CREATED"


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    entity: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # INVOICE, VENDOR, EXPENSE, etc.
    entity_id: Mapped[str] = mapped_column(String(100), nullable=True, index=True)
    
    changes: Mapped[dict] = mapped_column(JSON, nullable=True)
    ip_address: Mapped[str] = mapped_column(String(50), nullable=True)
    
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
        index=True
    )

    # Relationships
    user = relationship("User", back_populates="audit_logs")
