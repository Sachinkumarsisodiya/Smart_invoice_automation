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


def clean_demo_data(db: Session):
    """Deletes all dummy/seed records for a 100% clean production workspace."""
    logger.info("Cleaning demo data...")
    try:
        # Delete demo payments & reminder logs
        db.query(PaymentReminderLog).delete()
        db.query(Payment).delete()
        db.query(InvoiceItem).delete()
        db.query(Invoice).delete()
        db.query(Expense).delete()
        db.query(Notification).delete()
        db.query(Vendor).delete()
        db.commit()
        logger.info("Demo data wiped successfully. Clean workspace initialized.")
    except Exception as e:
        db.rollback()
        logger.error(f"Error cleaning demo data: {e}")


def seed_database(db: Session | None = None, wipe_demo_data: bool = True):
    """
    Initializes clean workspace with primary Admin user and zero dummy invoices/expenses.
    """
    close_session = False
    if db is None:
        db = SessionLocal()
        close_session = True

    try:
        # Create tables if not existing
        Base.metadata.create_all(bind=engine)

        if wipe_demo_data:
            clean_demo_data(db)

        logger.info("Setting up clean admin accounts...")

        demo_users = [
            {
                "email": "sachinsisodiyaofc@gmail.com",
                "password": "Password123!",
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

