import uuid
from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, Any, List

from sqlalchemy.orm import Session
from sqlalchemy import select, and_, or_

from app.core.celery_app import celery_app
from app.database.session import SessionLocal
from app.models.invoice import Invoice, InvoiceStatus, PaymentStatus
from app.models.vendor import Vendor
from app.models.user import UserRole
from app.models.reminder import PaymentReminderLog, ReminderType, ReminderStatus
from app.models.notification import NotificationType
from app.models.audit_log import AuditAction
from app.services.email_service import get_email_provider, EmailTemplateService
from app.services.notification_service import NotificationService
from app.services.audit_service import AuditService
from app.core.logging import logger
from app.config import settings


@celery_app.task(
    name="app.tasks.invoice_tasks.check_overdue_invoices_task",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    retry_backoff=True
)
def check_overdue_invoices_task(self=None, db: Session | None = None) -> Dict[str, Any]:
    """
    Automated background worker detecting invoices past their credit terms.
    Transitions unpaid overdue records and notifies accounting staff.
    Guaranteed idempotent.
    """
    today = date.today()
    own_session = False
    if db is None:
        db = SessionLocal()
        own_session = True
        
    updated_count = 0
    scanned_count = 0

    try:
        # Find active unpaid invoices where due_date has passed
        query = (
            select(Invoice, Vendor)
            .join(Vendor, Invoice.vendor_id == Vendor.id)
            .where(
                Invoice.due_date < today,
                Invoice.remaining_amount > Decimal("0.00"),
                Invoice.status != InvoiceStatus.PAID,
                Invoice.status != InvoiceStatus.REJECTED
            )
        )
        results = db.execute(query).all()
        scanned_count = len(results)

        for invoice, vendor in results:
            # Check if transition is needed
            needs_update = (
                invoice.status != InvoiceStatus.OVERDUE or
                invoice.payment_status != PaymentStatus.OVERDUE
            )

            if needs_update:
                invoice.status = InvoiceStatus.OVERDUE
                invoice.payment_status = PaymentStatus.OVERDUE
                db.flush()

                days_overdue = (today - invoice.due_date).days

                # 1. Create In-App Notification for Accounting Staff & Admin
                NotificationService.create_role_notification(
                    db=db,
                    roles=[UserRole.ADMIN, UserRole.STAFF],
                    title=f"Invoice #{invoice.invoice_number} is Overdue",
                    message=f"Payment for {vendor.name} ({invoice.currency} {invoice.remaining_amount:,.2f}) is {days_overdue} days past due date.",
                    type=NotificationType.ALERT,
                    link=f"/invoices/{invoice.id}"
                )

                # 2. Record Audit Log
                AuditService.log_action(
                    db=db,
                    action=AuditAction.INVOICE_MARKED_OVERDUE,
                    entity="INVOICE",
                    entity_id=invoice.id,
                    details={
                        "invoice_number": invoice.invoice_number,
                        "due_date": str(invoice.due_date),
                        "remaining_amount": str(invoice.remaining_amount),
                        "days_overdue": days_overdue
                    }
                )
                updated_count += 1

        db.commit()
        logger.info(f"[Task: check_overdue_invoices] Scanned {scanned_count}, updated {updated_count} overdue invoices.")
        return {
            "status": "success",
            "date": str(today),
            "scanned": scanned_count,
            "updated": updated_count
        }
    except Exception as exc:
        db.rollback()
        logger.error(f"[Task: check_overdue_invoices] Execution error: {exc}")
        if self is not None and hasattr(self, "retry"):
            raise self.retry(exc=exc)
        raise exc
    finally:
        if own_session:
            db.close()


@celery_app.task(
    name="app.tasks.invoice_tasks.send_payment_reminders_task",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    retry_backoff=True
)
def send_payment_reminders_task(self=None, db: Session | None = None) -> Dict[str, Any]:
    """
    Automated background worker detecting invoices approaching their due dates.
    Dispatches notifications at T-3 days, T-1 day, and T-0 (Due Today).
    Strictly database-idempotent via payment_reminder_logs.
    """
    today = date.today()
    own_session = False
    if db is None:
        db = SessionLocal()
        own_session = True

    reminders_sent = 0
    reminders_skipped = 0
    email_provider = get_email_provider()

    try:
        # Target due dates: today, today + 1 day, today + 3 days
        target_dates = [today, today + timedelta(days=1), today + timedelta(days=3)]

        query = (
            select(Invoice, Vendor)
            .join(Vendor, Invoice.vendor_id == Vendor.id)
            .where(
                Invoice.due_date.in_(target_dates),
                Invoice.remaining_amount > Decimal("0.00"),
                Invoice.status != InvoiceStatus.PAID,
                Invoice.status != InvoiceStatus.REJECTED
            )
        )
        candidates = db.execute(query).all()

        for invoice, vendor in candidates:
            days_left = (invoice.due_date - today).days

            if days_left == 3:
                reminder_type = ReminderType.T_MINUS_3
            elif days_left == 1:
                reminder_type = ReminderType.T_MINUS_1
            elif days_left == 0:
                reminder_type = ReminderType.DUE_TODAY
            else:
                continue

            # Idempotency check: Have we already logged this reminder for today?
            existing_log = db.scalar(
                select(PaymentReminderLog).where(
                    PaymentReminderLog.invoice_id == invoice.id,
                    PaymentReminderLog.reminder_type == reminder_type,
                    PaymentReminderLog.reminder_date == today
                )
            )
            if existing_log:
                reminders_skipped += 1
                continue

            recipient_email = vendor.email or settings.EMAILS_FROM_EMAIL
            html_content, text_content = EmailTemplateService.render_payment_reminder(
                invoice_number=invoice.invoice_number,
                vendor_name=vendor.name,
                remaining_amount=invoice.remaining_amount,
                currency=invoice.currency,
                due_date_str=str(invoice.due_date),
                days_left=days_left
            )

            subject = f"Payment Reminder: Invoice #{invoice.invoice_number} ({vendor.name})"

            try:
                email_provider.send_email(
                    to_email=recipient_email,
                    subject=subject,
                    html_content=html_content,
                    text_content=text_content
                )

                # Record idempotency log
                log_entry = PaymentReminderLog(
                    invoice_id=invoice.id,
                    reminder_type=reminder_type,
                    reminder_date=today,
                    recipient_email=recipient_email,
                    channel="EMAIL",
                    status=ReminderStatus.SENT
                )
                db.add(log_entry)

                # Create in-app notification for admin/staff
                NotificationService.create_role_notification(
                    db=db,
                    roles=[UserRole.ADMIN, UserRole.STAFF],
                    title=f"Reminder Sent: #{invoice.invoice_number}",
                    message=f"Upcoming payment reminder ({reminder_type}) dispatched to {recipient_email} for {invoice.currency} {invoice.remaining_amount:,.2f}.",
                    type=NotificationType.INFO,
                    link=f"/invoices/{invoice.id}"
                )

                # Record Audit Log
                AuditService.log_action(
                    db=db,
                    action=AuditAction.PAYMENT_REMINDER_SENT,
                    entity="INVOICE",
                    entity_id=invoice.id,
                    details={
                        "invoice_number": invoice.invoice_number,
                        "reminder_type": reminder_type,
                        "recipient_email": recipient_email,
                        "days_left": days_left
                    }
                )
                reminders_sent += 1
            except Exception as mail_err:
                logger.error(f"Failed to dispatch reminder email for invoice {invoice.id}: {mail_err}")
                failed_log = PaymentReminderLog(
                    invoice_id=invoice.id,
                    reminder_type=reminder_type,
                    reminder_date=today,
                    recipient_email=recipient_email,
                    channel="EMAIL",
                    status=ReminderStatus.FAILED,
                    error_message=str(mail_err)
                )
                db.add(failed_log)
                AuditService.log_action(
                    db=db,
                    action=AuditAction.PAYMENT_REMINDER_FAILED,
                    entity="INVOICE",
                    entity_id=invoice.id,
                    details={"error": str(mail_err)}
                )

        db.commit()
        logger.info(f"[Task: send_payment_reminders] Sent: {reminders_sent}, Skipped/Duplicate: {reminders_skipped}")
        return {
            "status": "success",
            "date": str(today),
            "sent": reminders_sent,
            "skipped": reminders_skipped
        }
    except Exception as exc:
        db.rollback()
        logger.error(f"[Task: send_payment_reminders] Task execution failed: {exc}")
        if self is not None and hasattr(self, "retry"):
            raise self.retry(exc=exc)
        raise exc
    finally:
        if own_session:
            db.close()


@celery_app.task(
    name="app.tasks.invoice_tasks.send_manual_reminder_task",
    bind=True,
    max_retries=2,
    default_retry_delay=30
)
def send_manual_reminder_task(
    self=None,
    invoice_id: str = "",
    sender_user_id: str | None = None,
    db: Session | None = None
) -> Dict[str, Any]:
    """
    On-demand payment reminder triggered manually by accounting staff.
    """
    today = date.today()
    own_session = False
    if db is None:
        db = SessionLocal()
        own_session = True

    email_provider = get_email_provider()

    try:
        inv_uuid = uuid.UUID(invoice_id)
        invoice = db.scalar(select(Invoice).where(Invoice.id == inv_uuid))
        if not invoice:
            raise ValueError(f"Invoice {invoice_id} not found.")

        vendor = db.scalar(select(Vendor).where(Vendor.id == invoice.vendor_id))
        recipient_email = (vendor.email if vendor else None) or settings.EMAILS_FROM_EMAIL
        days_left = (invoice.due_date - today).days

        html_content, text_content = EmailTemplateService.render_payment_reminder(
            invoice_number=invoice.invoice_number,
            vendor_name=vendor.name if vendor else "Supplier",
            remaining_amount=invoice.remaining_amount,
            currency=invoice.currency,
            due_date_str=str(invoice.due_date),
            days_left=max(days_left, 0)
        )

        subject = f"Payment Reminder: Invoice #{invoice.invoice_number}"

        email_provider.send_email(
            to_email=recipient_email,
            subject=subject,
            html_content=html_content,
            text_content=text_content
        )

        # Log manual reminder
        log_entry = PaymentReminderLog(
            invoice_id=invoice.id,
            reminder_type=ReminderType.MANUAL,
            reminder_date=today,
            recipient_email=recipient_email,
            channel="EMAIL",
            status=ReminderStatus.SENT
        )
        db.add(log_entry)

        # Audit Log
        AuditService.log_action(
            db=db,
            action=AuditAction.PAYMENT_REMINDER_SENT,
            entity="INVOICE",
            entity_id=invoice.id,
            user_id=uuid.UUID(sender_user_id) if sender_user_id else None,
            details={"manual": True, "recipient_email": recipient_email}
        )

        db.commit()
        return {"status": "success", "invoice_id": invoice_id, "recipient": recipient_email}
    except Exception as exc:
        db.rollback()
        logger.error(f"[Task: send_manual_reminder] Failed: {exc}")
        if self is not None and hasattr(self, "retry"):
            raise self.retry(exc=exc)
        raise exc
    finally:
        if own_session:
            db.close()


@celery_app.task(
    name="app.tasks.invoice_tasks.fetch_invoices_from_email_task",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    retry_backoff=True
)
def fetch_invoices_from_email_task(self=None, db: Session | None = None) -> Dict[str, Any]:
    """
    Automated background worker syncing unread email invoices from configured IMAP mailbox.
    """
    from app.services.email_ingestion_service import EmailIngestionService
    own_session = False
    if db is None:
        db = SessionLocal()
        own_session = True

    try:
        result = EmailIngestionService.sync_mailbox(db=db)
        logger.info(f"[Task: fetch_invoices_from_email] Result: {result.get('message')}")
        return result
    except Exception as exc:
        logger.error(f"[Task: fetch_invoices_from_email] Failed: {exc}")
        if self is not None and hasattr(self, "retry"):
            raise self.retry(exc=exc)
        raise exc
    finally:
        if own_session:
            db.close()
