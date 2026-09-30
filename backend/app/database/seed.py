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


def seed_database(db: Session | None = None, wipe_demo_data: bool = False):
    """
    Initializes clean workspace with primary Admin, Staff, and Viewer users and base configuration.
    """
    close_session = False
    if db is None:
        db = SessionLocal()
        close_session = True

    try:
        Base.metadata.create_all(bind=engine)

        if wipe_demo_data:
            clean_demo_data(db)

        logger.info("Setting up clean user accounts...")

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
            },
            {
                "email": "staff@smartinvoice.local",
                "password": "Password123!",
                "full_name": "Staff Member",
                "role": UserRole.STAFF
            },
            {
                "email": "viewer@smartinvoice.local",
                "password": "Password123!",
                "full_name": "Viewer User",
                "role": UserRole.VIEWER
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
                logger.info(f"Initialized user: {u['email']} ({u['role']})")
            else:
                existing.hashed_password = get_password_hash(u["password"])
                existing.is_active = True
                existing.role = u["role"]
                db.flush()

        # Ensure base Unassigned Vendor exists
        unassigned_v = db.query(Vendor).filter(Vendor.name == "Unassigned Vendor").first()
        if not unassigned_v:
            unassigned_v = Vendor(
                name="Unassigned Vendor",
                email=None,
                category="General",
                payment_terms_days=30,
                active=True
            )
            db.add(unassigned_v)
            db.flush()

        # Seed core base vendors if none exist
        if db.query(Vendor).count() < 3:
            default_vendors = [
                Vendor(name="Apex Cloud & IT Services", email="billing@apexcloud.io", gstin="07AAAAA0000A1Z5", category="IT & Software", payment_terms_days=15, active=True),
                Vendor(name="National Logistics Express", email="accounts@nationallogistics.com", gstin="27BBBBB1111B1Z6", category="Logistics", payment_terms_days=30, active=True),
                Vendor(name="Delta Office Solutions", email="finance@deltaoffice.com", gstin="08CCCCC2222C1Z7", category="Supplies", payment_terms_days=30, active=True),
            ]
            for dv in default_vendors:
                if not db.query(Vendor).filter(Vendor.name == dv.name).first():
                    db.add(dv)
            db.flush()

        # Seed core base invoices/expenses if none exist
        if db.query(Invoice).count() == 0:
            first_v = db.query(Vendor).filter(Vendor.name == "Apex Cloud & IT Services").first() or unassigned_v
            sample_invoices = [
                Invoice(
                    id=uuid.uuid4(),
                    vendor_id=first_v.id,
                    invoice_number="INV-2026-001",
                    invoice_date=date.today() - timedelta(days=10),
                    due_date=date.today() + timedelta(days=20),
                    subtotal=Decimal("50000.00"),
                    tax_amount=Decimal("9000.00"),
                    total_amount=Decimal("59000.00"),
                    paid_amount=Decimal("0.00"),
                    remaining_amount=Decimal("59000.00"),
                    currency="INR",
                    status=InvoiceStatus.PENDING_REVIEW,
                    payment_status=PaymentStatus.PENDING,
                    document_path="./storage/invoices/sample.pdf",
                    document_hash="sample_hash_001",
                    extraction_status=ExtractionStatus.SUCCESS,
                    extraction_confidence=Decimal("95.00")
                ),
                Invoice(
                    id=uuid.uuid4(),
                    vendor_id=first_v.id,
                    invoice_number="INV-2026-002",
                    invoice_date=date.today() - timedelta(days=5),
                    due_date=date.today() + timedelta(days=25),
                    subtotal=Decimal("20000.00"),
                    tax_amount=Decimal("3600.00"),
                    total_amount=Decimal("23600.00"),
                    paid_amount=Decimal("0.00"),
                    remaining_amount=Decimal("23600.00"),
                    currency="INR",
                    status=InvoiceStatus.APPROVED,
                    payment_status=PaymentStatus.PENDING,
                    document_path="./storage/invoices/sample.pdf",
                    document_hash="sample_hash_002",
                    extraction_status=ExtractionStatus.SUCCESS,
                    extraction_confidence=Decimal("92.00")
                ),
                Invoice(
                    id=uuid.uuid4(),
                    vendor_id=first_v.id,
                    invoice_number="INV-2026-003",
                    invoice_date=date.today() - timedelta(days=1),
                    due_date=date.today() + timedelta(days=29),
                    subtotal=Decimal("10000.00"),
                    tax_amount=Decimal("1800.00"),
                    total_amount=Decimal("11800.00"),
                    paid_amount=Decimal("11800.00"),
                    remaining_amount=Decimal("0.00"),
                    currency="INR",
                    status=InvoiceStatus.PAID,
                    payment_status=PaymentStatus.PAID,
                    document_path="./storage/invoices/sample.pdf",
                    document_hash="sample_hash_003",
                    extraction_status=ExtractionStatus.SUCCESS,
                    extraction_confidence=Decimal("99.00")
                )
            ]
            for si in sample_invoices:
                db.add(si)
            db.flush()

        if db.query(Expense).count() == 0:
            sample_expenses = [
                Expense(id=uuid.uuid4(), description="Office internet connectivity", amount=Decimal("2500.00"), category="Utilities", expense_date=date.today()),
                Expense(id=uuid.uuid4(), description="Software cloud hosting fees", amount=Decimal("15000.00"), category="IT", expense_date=date.today()),
                Expense(id=uuid.uuid4(), description="Office pantry supplies", amount=Decimal("1200.00"), category="Supplies", expense_date=date.today()),
            ]
            for se in sample_expenses:
                db.add(se)
            db.flush()

        if db.query(Payment).count() == 0:
            paid_inv = db.query(Invoice).filter(Invoice.status == InvoiceStatus.PAID).first()
            if paid_inv:
                sample_payment = Payment(
                    id=uuid.uuid4(),
                    invoice_id=paid_inv.id,
                    amount=paid_inv.total_amount,
                    payment_date=date.today(),
                    payment_method="BANK_TRANSFER",
                    reference_number="PAY-REF-001"
                )
                db.add(sample_payment)
                db.flush()

        db.commit()
        logger.info("Database initialized successfully.")

    except Exception as e:
        db.rollback()
        logger.error(f"Error initializing database: {str(e)}")
        raise
    finally:
        if close_session:
            db.close()


if __name__ == "__main__":
    seed_database(wipe_demo_data=False)

