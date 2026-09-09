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
from app.models.notification import Notification, NotificationType
from app.models.audit_log import AuditLog, AuditAction
from app.core.security import get_password_hash
from app.core.logging import logger


def seed_database(db: Session | None = None):
    """
    Seeds comprehensive, production-grade demo data for SmartInvoice.
    Guaranteed idempotent — safe to run multiple times without duplicating entities.
    """
    close_session = False
    if db is None:
        db = SessionLocal()
        close_session = True

    try:
        # Create tables if not existing
        Base.metadata.create_all(bind=engine)

        logger.info("Checking database seed records...")

        demo_users = [
            {
                "email": "sachinsisodiyaofc@gmail.com",
                "password": "Password123!",
                "full_name": "Sachin Sisodiya",
                "role": UserRole.ADMIN
            },
            {
                "email": "admin@smartinvoice.dev",
                "password": "Password123!",
                "full_name": "Admin User",
                "role": UserRole.ADMIN
            },
            {
                "email": "staff@smartinvoice.dev",
                "password": "Password123!",
                "full_name": "Staff User",
                "role": UserRole.STAFF
            },
            {
                "email": "viewer@smartinvoice.dev",
                "password": "Password123!",
                "full_name": "Viewer User",
                "role": UserRole.VIEWER
            },
            {
                "email": "admin@smartinvoice.local",
                "password": "Password123!",
                "full_name": "Admin Local",
                "role": UserRole.ADMIN
            }
        ]

        users_by_role = {}
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
                logger.info(f"Seeded user: {u['email']} ({u['role']})")
            users_by_role[u["role"]] = existing

        admin_user = users_by_role.get(UserRole.ADMIN)

        # 2. Seed Initial Demo Vendors
        demo_vendors = [
            {
                "name": "Sharma Packaging Pvt Ltd",
                "email": "sales@sharmapackaging.com",
                "phone": "+91 98765 43210",
                "gstin": "27AABCS1429B1Z5",
                "address": "Plot 42, MIDC Industrial Area, Pune, MH",
                "category": "Packaging",
                "payment_terms_days": 30
            },
            {
                "name": "Apex Cloud & IT Services",
                "email": "billing@apexcloud.io",
                "phone": "+91 80123 45678",
                "gstin": "29AAACA2145C1Z1",
                "address": "Tower 4, Tech Park, Outer Ring Road, Bengaluru, KA",
                "category": "Software",
                "payment_terms_days": 15
            },
            {
                "name": "National Logistics Express",
                "email": "accounts@nlexpress.in",
                "phone": "+91 11234 56789",
                "gstin": "07AAACN9876D1Z2",
                "address": "Cargo Complex, Terminal 2, New Delhi, DL",
                "category": "Transport",
                "payment_terms_days": 45
            },
            {
                "name": "Delta Office Solutions",
                "email": "support@deltaoffice.com",
                "phone": "+91 22345 67890",
                "gstin": "27AABCD3456E1Z3",
                "address": "Nariman Point, Mumbai, MH",
                "category": "Office Supplies",
                "payment_terms_days": 30
            }
        ]

        vendors_map = {}
        for v in demo_vendors:
            existing_v = db.query(Vendor).filter(Vendor.name == v["name"]).first()
            if not existing_v:
                existing_v = Vendor(**v)
                db.add(existing_v)
                db.flush()
                logger.info(f"Seeded vendor: {v['name']}")
            vendors_map[v["name"]] = existing_v

        today = date.today()

        # 3. Seed Realistic Demo Invoices across lifecycle
        demo_invoices = [
            {
                "vendor_name": "Sharma Packaging Pvt Ltd",
                "invoice_number": "INV-2026-001",
                "invoice_date": today - timedelta(days=20),
                "due_date": today + timedelta(days=10),
                "subtotal": Decimal("25000.00"),
                "tax_amount": Decimal("4500.00"),
                "total_amount": Decimal("29500.00"),
                "paid_amount": Decimal("0.00"),
                "remaining_amount": Decimal("29500.00"),
                "status": InvoiceStatus.APPROVED,
                "payment_status": PaymentStatus.PENDING,
                "notes": "Corrugated packaging boxes delivery batch 1"
            },
            {
                "vendor_name": "Apex Cloud & IT Services",
                "invoice_number": "INV-2026-002",
                "invoice_date": today - timedelta(days=40),
                "due_date": today - timedelta(days=25),
                "subtotal": Decimal("12000.00"),
                "tax_amount": Decimal("2160.00"),
                "total_amount": Decimal("14160.00"),
                "paid_amount": Decimal("14160.00"),
                "remaining_amount": Decimal("0.00"),
                "status": InvoiceStatus.PAID,
                "payment_status": PaymentStatus.PAID,
                "notes": "Cloud infrastructure hosting Q2"
            },
            {
                "vendor_name": "National Logistics Express",
                "invoice_number": "INV-2026-003",
                "invoice_date": today - timedelta(days=50),
                "due_date": today - timedelta(days=5),
                "subtotal": Decimal("18000.00"),
                "tax_amount": Decimal("3240.00"),
                "total_amount": Decimal("21240.00"),
                "paid_amount": Decimal("0.00"),
                "remaining_amount": Decimal("21240.00"),
                "status": InvoiceStatus.OVERDUE,
                "payment_status": PaymentStatus.OVERDUE,
                "notes": "Inter-state freight shipping"
            },
            {
                "vendor_name": "Delta Office Solutions",
                "invoice_number": "INV-2026-004",
                "invoice_date": today - timedelta(days=2),
                "due_date": today + timedelta(days=28),
                "subtotal": Decimal("8500.00"),
                "tax_amount": Decimal("1530.00"),
                "total_amount": Decimal("10030.00"),
                "paid_amount": Decimal("0.00"),
                "remaining_amount": Decimal("10030.00"),
                "status": InvoiceStatus.PENDING_REVIEW,
                "payment_status": PaymentStatus.PENDING,
                "notes": "Quarterly stationery supplies"
            }
        ]

        invoices_map = {}
        for inv_data in demo_invoices:
            vendor = vendors_map.get(inv_data["vendor_name"])
            if not vendor:
                continue

            existing_inv = db.query(Invoice).filter(Invoice.invoice_number == inv_data["invoice_number"]).first()
            if not existing_inv:
                existing_inv = Invoice(
                    vendor_id=vendor.id,
                    invoice_number=inv_data["invoice_number"],
                    invoice_date=inv_data["invoice_date"],
                    due_date=inv_data["due_date"],
                    subtotal=inv_data["subtotal"],
                    tax_amount=inv_data["tax_amount"],
                    total_amount=inv_data["total_amount"],
                    paid_amount=inv_data["paid_amount"],
                    remaining_amount=inv_data["remaining_amount"],
                    status=inv_data["status"],
                    payment_status=inv_data["payment_status"],
                    document_path=f"./storage/invoices/{inv_data['invoice_number']}.pdf",
                    document_hash=f"seed_hash_{inv_data['invoice_number']}",
                    extraction_status=ExtractionStatus.SUCCESS,
                    extraction_confidence=Decimal("0.98"),
                    currency="INR",
                    notes=inv_data["notes"]
                )
                db.add(existing_inv)
                db.flush()
                logger.info(f"Seeded invoice: {inv_data['invoice_number']} ({inv_data['status']})")
            invoices_map[inv_data["invoice_number"]] = existing_inv

        # 4. Seed Payments for Paid Invoices
        paid_inv = invoices_map.get("INV-2026-002")
        if paid_inv and admin_user:
            existing_pay = db.query(Payment).filter(Payment.invoice_id == paid_inv.id).first()
            if not existing_pay:
                new_payment = Payment(
                    invoice_id=paid_inv.id,
                    amount=paid_inv.total_amount,
                    payment_date=today - timedelta(days=26),
                    payment_method=PaymentMethod.BANK_TRANSFER,
                    reference_number="NEFT982341209",
                    notes="Settled in full via corporate net banking",
                    created_by=admin_user.id
                )
                db.add(new_payment)
                logger.info(f"Seeded payment for invoice {paid_inv.invoice_number}")

        # 5. Seed Categorized Expenses
        apex_vendor = vendors_map.get("Apex Cloud & IT Services")
        demo_expenses = [
            {
                "category": "Utilities",
                "description": "Electricity bill for warehouse facilities",
                "amount": Decimal("4850.00"),
                "expense_date": today - timedelta(days=12),
                "payment_method": "UPI",
                "vendor_id": None
            },
            {
                "category": "Software",
                "description": "Monthly team productivity licenses",
                "amount": Decimal("6200.00"),
                "expense_date": today - timedelta(days=5),
                "payment_method": "CREDIT_CARD",
                "vendor_id": apex_vendor.id if apex_vendor else None
            },
            {
                "category": "Transport",
                "description": "Client meeting transport and fuel",
                "amount": Decimal("2300.00"),
                "expense_date": today - timedelta(days=3),
                "payment_method": "CASH",
                "vendor_id": None
            }
        ]

        for exp in demo_expenses:
            existing_exp = db.query(Expense).filter(Expense.description == exp["description"]).first()
            if not existing_exp and admin_user:
                new_exp = Expense(
                    category=exp["category"],
                    description=exp["description"],
                    amount=exp["amount"],
                    expense_date=exp["expense_date"],
                    payment_method=exp["payment_method"],
                    vendor_id=exp["vendor_id"],
                    created_by=admin_user.id
                )
                db.add(new_exp)
                logger.info(f"Seeded expense: {exp['description']}")

        # 6. Seed In-App Notifications
        if admin_user:
            existing_notif = db.query(Notification).filter(Notification.user_id == admin_user.id).first()
            if not existing_notif:
                notif1 = Notification(
                    user_id=admin_user.id,
                    title="Welcome to SmartInvoice!",
                    message="Your business automation workspace is ready with sample vendors and invoices.",
                    type=NotificationType.INFO,
                    link="/dashboard"
                )
                notif2 = Notification(
                    user_id=admin_user.id,
                    title="Action Required: Overdue Invoice",
                    message="Invoice #INV-2026-003 from National Logistics Express is 5 days overdue.",
                    type=NotificationType.ALERT,
                    link="/invoices"
                )
                db.add_all([notif1, notif2])
                logger.info("Seeded initial notifications")

        # 7. Seed Initial Audit Log
        if admin_user:
            existing_audit = db.query(AuditLog).filter(AuditLog.action == AuditAction.USER_LOGIN).first()
            if not existing_audit:
                initial_audit = AuditLog(
                    action=AuditAction.USER_LOGIN,
                    entity="USER",
                    entity_id=str(admin_user.id),
                    user_id=admin_user.id,
                    changes={"seed": True, "message": "Initial database environment seeded"}
                )
                db.add(initial_audit)

        db.commit()
        logger.info("Database seeding completed successfully.")

    except Exception as e:
        db.rollback()
        logger.error(f"Error seeding database: {str(e)}")
        raise
    finally:
        if close_session:
            db.close()


if __name__ == "__main__":
    seed_database()
