import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from sqlalchemy.orm import Session
from app.database.session import SessionLocal, engine
from app.database.base import Base
from app.models.user import User, UserRole
from app.models.vendor import Vendor
from app.models.invoice import Invoice, InvoiceStatus, PaymentStatus, ExtractionStatus, InvoiceItem
from app.models.payment import Payment, PaymentMethod
from app.models.expense import Expense
from app.models.reminder import PaymentReminderLog
from app.models.notification import Notification, NotificationType
from app.models.audit_log import AuditLog, AuditAction
from app.core.security import get_password_hash
from app.core.logging import logger


def clean_demo_data(db: Session):
    """Safely purges ALL dummy records, false 300k placeholder extractions, and resets to clean state."""
    logger.info("Purging dummy demo and false placeholder records from database...")
    try:
        # 1. Delete all demo expenses
        demo_expense_descs = [
            "Electricity bill for warehouse facilities",
            "Monthly team productivity licenses",
            "Client meeting transport and fuel"
        ]
        db.query(Expense).filter(Expense.description.in_(demo_expense_descs)).delete(synchronize_session=False)

        # 2. Delete demo invoices, zero-amount failed extractions, and placeholder numbers
        demo_inv_numbers = ["INV-2026-001", "INV-2026-002", "INV-2026-003", "INV-2026-004", "CONFIRMATION", "CORPORATE", "INV-UNKNOWN"]
        false_invoices = db.query(Invoice).filter(
            (Invoice.invoice_number.in_(demo_inv_numbers)) |
            (Invoice.total_amount == Decimal("0.00")) |
            (Invoice.tax_amount == Decimal("1.00"))
        ).all()
        for d_inv in false_invoices:
            db.query(PaymentReminderLog).filter(PaymentReminderLog.invoice_id == d_inv.id).delete(synchronize_session=False)
            db.query(Payment).filter(Payment.invoice_id == d_inv.id).delete(synchronize_session=False)
            db.query(InvoiceItem).filter(InvoiceItem.invoice_id == d_inv.id).delete(synchronize_session=False)
            db.delete(d_inv)

        # 3. Clean up demo and OCR error vendors
        ocr_error_vendors = db.query(Vendor).filter(Vendor.name.like("[%")).all()
        for ov in ocr_error_vendors:
            db.query(Invoice).filter(Invoice.vendor_id == ov.id).delete(synchronize_session=False)
            db.delete(ov)

        demo_vendor_names = [
            "Sharma Packaging Pvt Ltd",
            "Apex Cloud & IT Services",
            "National Logistics Express",
            "Delta Office Solutions"
        ]
        
        demo_vendors = db.query(Vendor).filter(Vendor.name.in_(demo_vendor_names)).all()
        demo_vendor_ids = [v.id for v in demo_vendors]

        if demo_vendor_ids:
            orphan_invoices = db.query(Invoice).filter(Invoice.vendor_id.in_(demo_vendor_ids)).all()
            for inv in orphan_invoices:
                target_v_name = "Lavish Home Interiors" if "0894" in (inv.invoice_number or "") else "Real Supplier"
                real_v = db.query(Vendor).filter(Vendor.name == target_v_name).first()
                if not real_v:
                    real_v = Vendor(name=target_v_name, category="General", payment_terms_days=30)
                    db.add(real_v)
                    db.flush()
                inv.vendor_id = real_v.id

            db.query(Vendor).filter(Vendor.id.in_(demo_vendor_ids)).delete(synchronize_session=False)

        # 4. Delete demo audit logs
        db.query(AuditLog).filter(
            AuditLog.action.in_([AuditAction.USER_LOGIN, AuditAction.EXPENSE_CREATED, AuditAction.INVOICE_UPLOADED, AuditAction.INVOICE_APPROVED])
        ).delete(synchronize_session=False)

        # 5. Delete demo notifications
        db.query(Notification).delete()

        # 6. Delete unused demo users
        demo_user_emails = [
            "admin@smartinvoice.dev",
            "staff@smartinvoice.dev",
            "viewer@smartinvoice.dev",
            "staff@smartinvoice.local",
            "viewer@smartinvoice.local"
        ]
        db.query(User).filter(User.email.in_(demo_user_emails)).delete(synchronize_session=False)

        db.commit()
        logger.info("Successfully purged all dummy and false placeholder records.")
    except Exception as e:
        db.rollback()
        logger.error(f"Error purging demo data: {e}")


def seed_database(db: Session | None = None, wipe_demo_data: bool = True):
    """
    Initializes clean workspace with primary Admin user and zero dummy invoices/expenses.
    """
    close_session = False
    if db is None:
        db = SessionLocal()
        close_session = True

    try:
        Base.metadata.create_all(bind=engine)

        if wipe_demo_data:
            clean_demo_data(db)

        logger.info("Setting up clean admin accounts...")

        demo_users = [
            {
                "email": "sachinsisodiyaofc@gmail.com",
                "password": "@Sisodiya0506$",
                "full_name": "Sachin Sisodiya",
                "role": UserRole.ADMIN
            },
            {
                "email": "admin@smartinvoice.local",
                "password": "Password123!",
                "full_name": "Admin Local",
                "role": UserRole.ADMIN
            }
        ]

        for u in demo_users:
            existing = db.query(User).filter(User.email == u["email"]).first()
            if not existing:
                existing = User(
                    email=u["email"],
                    hashed_password=get_password_hash(u["password"]),
                    full_name=u["full_name"],
                    role=u["role"],
                    is_active=True
                )
                db.add(existing)
                db.flush()
                logger.info(f"Initialized Admin user: {u['email']}")
            else:
                existing.hashed_password = get_password_hash(u["password"])
                existing.is_active = True
                existing.role = u["role"]
                db.flush()
                logger.info(f"Updated password hash for Admin: {u['email']}")

        db.commit()
        logger.info("Fresh database initialized with 0 dummy records.")

    except Exception as e:
        db.rollback()
        logger.error(f"Error initializing database: {str(e)}")
        raise
    finally:
        if close_session:
            db.close()


if __name__ == "__main__":
    seed_database(wipe_demo_data=True)
