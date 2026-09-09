import uuid
import pytest
from decimal import Decimal
from datetime import date, datetime, timedelta, timezone
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app.core.celery_app import celery_app
from app.models.user import User, UserRole
from app.models.vendor import Vendor
from app.models.invoice import Invoice, InvoiceStatus, PaymentStatus, ExtractionStatus
from app.models.payment import Payment
from app.models.reminder import PaymentReminderLog, ReminderType, ReminderStatus
from app.models.notification import Notification, NotificationType
from app.models.audit_log import AuditLog, AuditAction
from app.services.audit_service import AuditService
from app.services.email_service import (
    get_email_provider,
    ConsoleMockEmailProvider,
    SMTPEmailProvider,
    EmailTemplateService,
)
from app.services.notification_service import NotificationService
from app.tasks.invoice_tasks import (
    check_overdue_invoices_task,
    send_payment_reminders_task,
    send_manual_reminder_task,
)
from app.core.security import create_access_token, get_password_hash


def test_celery_configuration_and_task_registration():
    """Verify Celery application config, JSON serializers, UTC timezone, and task registration."""
    assert celery_app.conf.task_serializer == "json"
    assert celery_app.conf.result_serializer == "json"
    assert celery_app.conf.timezone == "UTC"
    assert celery_app.conf.enable_utc is True

    # Verify registered tasks
    tasks = list(celery_app.tasks.keys())
    assert "app.tasks.invoice_tasks.check_overdue_invoices_task" in tasks
    assert "app.tasks.invoice_tasks.send_payment_reminders_task" in tasks
    assert "app.tasks.invoice_tasks.send_manual_reminder_task" in tasks

    # Verify Beat schedules
    assert "check-overdue-invoices-daily" in celery_app.conf.beat_schedule
    assert "send-payment-reminders-daily" in celery_app.conf.beat_schedule


def test_email_provider_and_template_rendering():
    """Test Email provider abstraction and HTML/text template rendering."""
    # 1. Test ConsoleMockEmailProvider
    mock_provider = ConsoleMockEmailProvider()
    mock_provider.clear_sent_emails()
    res = mock_provider.send_email(
        to_email="test@supplier.com",
        subject="Test Invoice Reminder",
        html_content="<p>Test reminder</p>",
        text_content="Test reminder"
    )
    assert res is True
    assert len(mock_provider.sent_emails) == 1
    assert mock_provider.sent_emails[0]["to"] == "test@supplier.com"
    assert mock_provider.sent_emails[0]["subject"] == "Test Invoice Reminder"

    # 2. Test Template Rendering
    html, text = EmailTemplateService.render_payment_reminder(
        invoice_number="INV-2026-999",
        vendor_name="Acme Hardware Supplies",
        remaining_amount=Decimal("15000.00"),
        currency="INR",
        due_date_str="2026-09-15",
        days_left=3
    )
    assert "INV-2026-999" in html
    assert "Acme Hardware Supplies" in html
    assert "15,000.00" in html
    assert "due in 3 days" in html
    assert "INV-2026-999" in text

    # Overdue Notice
    ov_html, ov_text = EmailTemplateService.render_overdue_notice(
        invoice_number="INV-2026-999",
        vendor_name="Acme Hardware Supplies",
        remaining_amount=Decimal("15000.00"),
        currency="INR",
        due_date_str="2026-09-01",
        days_overdue=7
    )
    assert "7 Days Overdue" in ov_html
    assert "Action Required: Overdue" in ov_html


def test_check_overdue_invoices_task_and_idempotency(db_session: Session):
    """Test overdue invoice detection, status transition, role notifications, and idempotency."""
    # 1. Create Staff User to receive notifications
    staff = User(
        email="staff_p6@smartinvoice.dev",
        hashed_password=get_password_hash("StaffPass123!"),
        full_name="Staff P6",
        role=UserRole.STAFF,
        is_active=True
    )
    db_session.add(staff)

    vendor = Vendor(
        name="Overdue Test Supplier",
        email="overdue@supplier.com",
        category="Hardware",
        payment_terms_days=30
    )
    db_session.add(vendor)
    db_session.flush()

    today = date.today()
    # Unpaid Overdue Invoice (Due 5 days ago)
    inv_overdue = Invoice(
        vendor_id=vendor.id,
        invoice_number="INV-OV-001",
        invoice_date=today - timedelta(days=35),
        due_date=today - timedelta(days=5),
        subtotal=Decimal("5000.00"),
        tax_amount=Decimal("900.00"),
        total_amount=Decimal("5900.00"),
        paid_amount=Decimal("0.00"),
        remaining_amount=Decimal("5900.00"),
        status=InvoiceStatus.APPROVED,
        payment_status=PaymentStatus.PENDING,
        document_path="uploads/test_ov.pdf",
        document_hash="hash_ov_1",
        extraction_status=ExtractionStatus.SUCCESS,
        extraction_confidence=Decimal("0.95"),
        currency="INR"
    )

    # Paid Invoice (Due 10 days ago, but fully paid -> should NOT become overdue)
    inv_paid = Invoice(
        vendor_id=vendor.id,
        invoice_number="INV-PAID-001",
        invoice_date=today - timedelta(days=40),
        due_date=today - timedelta(days=10),
        subtotal=Decimal("2000.00"),
        tax_amount=Decimal("360.00"),
        total_amount=Decimal("2360.00"),
        paid_amount=Decimal("2360.00"),
        remaining_amount=Decimal("0.00"),
        status=InvoiceStatus.PAID,
        payment_status=PaymentStatus.PAID,
        document_path="uploads/test_paid.pdf",
        document_hash="hash_paid_1",
        extraction_status=ExtractionStatus.SUCCESS,
        extraction_confidence=Decimal("0.95"),
        currency="INR"
    )

    db_session.add_all([inv_overdue, inv_paid])
    db_session.commit()

    # 2. Run the Overdue Task
    result1 = check_overdue_invoices_task(db=db_session)
    assert result1["status"] == "success"
    assert result1["updated"] >= 1

    # Verify invoice status transitioned
    db_session.refresh(inv_overdue)
    db_session.refresh(inv_paid)
    assert inv_overdue.status == InvoiceStatus.OVERDUE
    assert inv_overdue.payment_status == PaymentStatus.OVERDUE
    assert inv_paid.status == InvoiceStatus.PAID  # Unchanged!

    # Verify notification created
    notifs = db_session.query(Notification).filter(Notification.user_id == staff.id).all()
    assert len(notifs) >= 1
    assert "Overdue" in notifs[0].title

    # 3. Test Idempotency: Running task a second time should update 0 invoices and create 0 duplicate notifs
    notif_count_before = db_session.query(Notification).count()
    result2 = check_overdue_invoices_task(db=db_session)
    assert result2["updated"] == 0
    notif_count_after = db_session.query(Notification).count()
    assert notif_count_after == notif_count_before


def test_send_payment_reminders_task_and_idempotency(db_session: Session):
    """Test payment reminder scan (T-3, T-1, T-0), email dispatch, and database-backed idempotency."""
    ConsoleMockEmailProvider.clear_sent_emails()

    vendor = Vendor(
        name="Reminder Test Supplier",
        email="reminder@supplier.com",
        category="Software",
        payment_terms_days=30
    )
    db_session.add(vendor)
    db_session.flush()

    today = date.today()
    # 1. Invoice due in 3 days (T-3)
    inv_t3 = Invoice(
        vendor_id=vendor.id,
        invoice_number="INV-REM-T3",
        invoice_date=today - timedelta(days=27),
        due_date=today + timedelta(days=3),
        subtotal=Decimal("3000.00"),
        tax_amount=Decimal("540.00"),
        total_amount=Decimal("3540.00"),
        paid_amount=Decimal("0.00"),
        remaining_amount=Decimal("3540.00"),
        status=InvoiceStatus.APPROVED,
        payment_status=PaymentStatus.PENDING,
        document_path="uploads/t3.pdf",
        document_hash="hash_t3",
        extraction_status=ExtractionStatus.SUCCESS,
        extraction_confidence=Decimal("0.95"),
        currency="INR"
    )

    # 2. Invoice due tomorrow (T-1)
    inv_t1 = Invoice(
        vendor_id=vendor.id,
        invoice_number="INV-REM-T1",
        invoice_date=today - timedelta(days=29),
        due_date=today + timedelta(days=1),
        subtotal=Decimal("1000.00"),
        tax_amount=Decimal("180.00"),
        total_amount=Decimal("1180.00"),
        paid_amount=Decimal("0.00"),
        remaining_amount=Decimal("1180.00"),
        status=InvoiceStatus.APPROVED,
        payment_status=PaymentStatus.PENDING,
        document_path="uploads/t1.pdf",
        document_hash="hash_t1",
        extraction_status=ExtractionStatus.SUCCESS,
        extraction_confidence=Decimal("0.95"),
        currency="INR"
    )

    # 3. Invoice due today (T-0)
    inv_t0 = Invoice(
        vendor_id=vendor.id,
        invoice_number="INV-REM-T0",
        invoice_date=today - timedelta(days=30),
        due_date=today,
        subtotal=Decimal("2000.00"),
        tax_amount=Decimal("360.00"),
        total_amount=Decimal("2360.00"),
        paid_amount=Decimal("0.00"),
        remaining_amount=Decimal("2360.00"),
        status=InvoiceStatus.APPROVED,
        payment_status=PaymentStatus.PENDING,
        document_path="uploads/t0.pdf",
        document_hash="hash_t0",
        extraction_status=ExtractionStatus.SUCCESS,
        extraction_confidence=Decimal("0.95"),
        currency="INR"
    )

    # 4. Invoice due in 10 days -> Should NOT get a reminder
    inv_future = Invoice(
        vendor_id=vendor.id,
        invoice_number="INV-REM-FUTURE",
        invoice_date=today,
        due_date=today + timedelta(days=10),
        subtotal=Decimal("500.00"),
        tax_amount=Decimal("90.00"),
        total_amount=Decimal("590.00"),
        paid_amount=Decimal("0.00"),
        remaining_amount=Decimal("590.00"),
        status=InvoiceStatus.APPROVED,
        payment_status=PaymentStatus.PENDING,
        document_path="uploads/future.pdf",
        document_hash="hash_future",
        extraction_status=ExtractionStatus.SUCCESS,
        extraction_confidence=Decimal("0.95"),
        currency="INR"
    )

    # 5. Fully paid invoice due today -> Should NOT get a reminder
    inv_paid_t0 = Invoice(
        vendor_id=vendor.id,
        invoice_number="INV-REM-PAID-T0",
        invoice_date=today - timedelta(days=30),
        due_date=today,
        subtotal=Decimal("800.00"),
        tax_amount=Decimal("144.00"),
        total_amount=Decimal("944.00"),
        paid_amount=Decimal("944.00"),
        remaining_amount=Decimal("0.00"),
        status=InvoiceStatus.PAID,
        payment_status=PaymentStatus.PAID,
        document_path="uploads/paid_t0.pdf",
        document_hash="hash_paid_t0",
        extraction_status=ExtractionStatus.SUCCESS,
        extraction_confidence=Decimal("0.95"),
        currency="INR"
    )

    db_session.add_all([inv_t3, inv_t1, inv_t0, inv_future, inv_paid_t0])
    db_session.commit()

    # Run the reminder task
    res1 = send_payment_reminders_task(db=db_session)
    assert res1["status"] == "success"
    assert res1["sent"] >= 3

    # Verify logs in DB
    logs = db_session.query(PaymentReminderLog).all()
    reminder_types = [l.reminder_type for l in logs]
    assert ReminderType.T_MINUS_3 in reminder_types
    assert ReminderType.T_MINUS_1 in reminder_types
    assert ReminderType.DUE_TODAY in reminder_types

    # Verify Mock Email Dispatch count
    assert len(ConsoleMockEmailProvider.sent_emails) >= 3

    # Test Idempotency: Re-running immediately must skip all 3
    ConsoleMockEmailProvider.clear_sent_emails()
    res2 = send_payment_reminders_task(db=db_session)
    assert res2["sent"] == 0
    assert res2["skipped"] >= 3
    assert len(ConsoleMockEmailProvider.sent_emails) == 0


def test_notification_service_and_rest_endpoints(client: TestClient, db_session: Session):
    """Test user-scoped notification CRUD, unread counter, and mark all read."""
    # 1. Create two users
    user_a = User(
        email="user_a@smartinvoice.dev",
        hashed_password=get_password_hash("Pass123!"),
        full_name="User A",
        role=UserRole.STAFF,
        is_active=True
    )
    user_b = User(
        email="user_b@smartinvoice.dev",
        hashed_password=get_password_hash("Pass123!"),
        full_name="User B",
        role=UserRole.STAFF,
        is_active=True
    )
    db_session.add_all([user_a, user_b])
    db_session.commit()
    db_session.refresh(user_a)
    db_session.refresh(user_b)

    # 2. Create notifications
    n1 = NotificationService.create_notification(
        db=db_session,
        user_id=user_a.id,
        title="Alert for User A",
        message="Invoice has been processed.",
        type=NotificationType.INFO,
        link="/invoices/1"
    )
    n2 = NotificationService.create_notification(
        db=db_session,
        user_id=user_a.id,
        title="Warning for User A",
        message="Invoice is approaching due date.",
        type=NotificationType.WARNING
    )
    n_b = NotificationService.create_notification(
        db=db_session,
        user_id=user_b.id,
        title="Private alert for User B",
        message="Only User B should see this.",
        type=NotificationType.ALERT
    )

    token_a = create_access_token(subject=user_a.id, role=user_a.role)
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # 3. GET /api/notifications for User A
    res = client.get("/api/notifications", headers=headers_a)
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 2
    assert data["unread_count"] == 2
    titles = [i["title"] for i in data["items"]]
    assert "Alert for User A" in titles
    assert "Private alert for User B" not in titles  # User B's alert is private!

    # 4. GET /api/notifications/unread-count
    count_res = client.get("/api/notifications/unread-count", headers=headers_a)
    assert count_res.status_code == 200
    assert count_res.json()["unread_count"] == 2

    # 5. PUT /api/notifications/{id}/read
    read_res = client.put(f"/api/notifications/{n1.id}/read", headers=headers_a)
    assert read_res.status_code == 200
    assert read_res.json()["is_read"] is True

    # Check unread count decremented
    count_res2 = client.get("/api/notifications/unread-count", headers=headers_a)
    assert count_res2.json()["unread_count"] == 1

    # 6. User A cannot read User B's notification
    forbidden_res = client.put(f"/api/notifications/{n_b.id}/read", headers=headers_a)
    assert forbidden_res.status_code == 404

    # 7. PUT /api/notifications/read-all
    all_res = client.put("/api/notifications/read-all", headers=headers_a)
    assert all_res.status_code == 200
    assert all_res.json()["marked_count"] == 1

    # 8. DELETE /api/notifications/{id}
    del_res = client.delete(f"/api/notifications/{n1.id}", headers=headers_a)
    assert del_res.status_code == 200


def test_audit_logs_api_admin_restricted(client: TestClient, db_session: Session):
    """Test audit logs listing, filtering, and admin-only role enforcement."""
    admin = User(
        email="admin_audit@smartinvoice.dev",
        hashed_password=get_password_hash("AdminPass123!"),
        full_name="Admin Audit",
        role=UserRole.ADMIN,
        is_active=True
    )
    viewer = User(
        email="viewer_audit@smartinvoice.dev",
        hashed_password=get_password_hash("ViewerPass123!"),
        full_name="Viewer Audit",
        role=UserRole.VIEWER,
        is_active=True
    )
    db_session.add_all([admin, viewer])
    db_session.commit()
    db_session.refresh(admin)
    db_session.refresh(viewer)

    # Log some actions
    AuditService.log_action(db=db_session, action=AuditAction.USER_LOGIN, entity="USER", entity_id=admin.id, user_id=admin.id)
    AuditService.log_action(db=db_session, action=AuditAction.INVOICE_UPLOADED, entity="INVOICE", entity_id=str(uuid.uuid4()), user_id=admin.id)

    token_admin = create_access_token(subject=admin.id, role=admin.role)
    token_viewer = create_access_token(subject=viewer.id, role=viewer.role)

    # 1. Admin can access audit logs
    res_admin = client.get("/api/audit-logs", headers={"Authorization": f"Bearer {token_admin}"})
    assert res_admin.status_code == 200
    data = res_admin.json()
    assert data["total"] >= 2
    assert "items" in data

    # 2. Filter by action
    res_filter = client.get(f"/api/audit-logs?action={AuditAction.USER_LOGIN}", headers={"Authorization": f"Bearer {token_admin}"})
    assert res_filter.status_code == 200
    for item in res_filter.json()["items"]:
        assert item["action"] == AuditAction.USER_LOGIN

    # 3. Viewer is Forbidden (403)
    res_viewer = client.get("/api/audit-logs", headers={"Authorization": f"Bearer {token_viewer}"})
    assert res_viewer.status_code == 403


def test_system_health_and_manual_triggers(client: TestClient, db_session: Session):
    """Test system health probes, Celery status, and manual scan triggers with RBAC."""
    admin = User(
        email="admin_sys@smartinvoice.dev",
        hashed_password=get_password_hash("AdminPass123!"),
        full_name="Admin Sys",
        role=UserRole.ADMIN,
        is_active=True
    )
    viewer = User(
        email="viewer_sys@smartinvoice.dev",
        hashed_password=get_password_hash("ViewerPass123!"),
        full_name="Viewer Sys",
        role=UserRole.VIEWER,
        is_active=True
    )
    db_session.add_all([admin, viewer])
    db_session.commit()
    db_session.refresh(admin)
    db_session.refresh(viewer)

    token_admin = create_access_token(subject=admin.id, role=admin.role)
    token_viewer = create_access_token(subject=viewer.id, role=viewer.role)

    # 1. System Health
    res_health = client.get("/api/system/health")
    assert res_health.status_code == 200
    h_data = res_health.json()
    assert h_data["database"] == "healthy"
    assert "email_provider" in h_data
    # Assert no secrets exposed
    assert "password" not in str(h_data).lower()
    assert "secret_key" not in str(h_data).lower()

    # 2. Celery Status
    res_celery = client.get("/api/system/celery-status", headers={"Authorization": f"Bearer {token_admin}"})
    assert res_celery.status_code == 200
    c_data = res_celery.json()
    assert "beat_schedule" in c_data
    assert "registered_tasks" in c_data

    # 3. Admin can trigger due date scan
    res_trigger = client.post("/api/system/trigger-due-date-scan", headers={"Authorization": f"Bearer {token_admin}"})
    assert res_trigger.status_code == 200
    assert "Overdue invoices scan executed" in res_trigger.json()["message"]

    # 4. Viewer cannot trigger scan (403)
    res_v_trigger = client.post("/api/system/trigger-due-date-scan", headers={"Authorization": f"Bearer {token_viewer}"})
    assert res_v_trigger.status_code == 403


def test_manual_invoice_reminder_endpoint(client: TestClient, db_session: Session):
    """Test POST /api/invoices/{id}/send-reminder endpoint with state checks and RBAC."""
    admin = User(
        email="admin_rem@smartinvoice.dev",
        hashed_password=get_password_hash("AdminPass123!"),
        full_name="Admin Rem",
        role=UserRole.ADMIN,
        is_active=True
    )
    viewer = User(
        email="viewer_rem@smartinvoice.dev",
        hashed_password=get_password_hash("ViewerPass123!"),
        full_name="Viewer Rem",
        role=UserRole.VIEWER,
        is_active=True
    )
    vendor = Vendor(
        name="Manual Rem Vendor",
        email="manual@vendor.com",
        category="Logistics",
        payment_terms_days=15
    )
    db_session.add_all([admin, viewer, vendor])
    db_session.commit()

    today = date.today()
    inv_unpaid = Invoice(
        vendor_id=vendor.id,
        invoice_number="INV-MANUAL-001",
        invoice_date=today,
        due_date=today + timedelta(days=5),
        subtotal=Decimal("1000.00"),
        tax_amount=Decimal("180.00"),
        total_amount=Decimal("1180.00"),
        paid_amount=Decimal("0.00"),
        remaining_amount=Decimal("1180.00"),
        status=InvoiceStatus.APPROVED,
        payment_status=PaymentStatus.PENDING,
        document_path="uploads/manual.pdf",
        document_hash="hash_manual",
        extraction_status=ExtractionStatus.SUCCESS,
        extraction_confidence=Decimal("0.95"),
        currency="INR"
    )
    inv_paid = Invoice(
        vendor_id=vendor.id,
        invoice_number="INV-MANUAL-PAID",
        invoice_date=today,
        due_date=today + timedelta(days=5),
        subtotal=Decimal("1000.00"),
        tax_amount=Decimal("180.00"),
        total_amount=Decimal("1180.00"),
        paid_amount=Decimal("1180.00"),
        remaining_amount=Decimal("0.00"),
        status=InvoiceStatus.PAID,
        payment_status=PaymentStatus.PAID,
        document_path="uploads/manual_paid.pdf",
        document_hash="hash_manual_paid",
        extraction_status=ExtractionStatus.SUCCESS,
        extraction_confidence=Decimal("0.95"),
        currency="INR"
    )
    db_session.add_all([inv_unpaid, inv_paid])
    db_session.commit()

    token_admin = create_access_token(subject=admin.id, role=admin.role)
    token_viewer = create_access_token(subject=viewer.id, role=viewer.role)

    # 1. Admin sends reminder for unpaid invoice -> 200 OK
    res = client.post(f"/api/invoices/{inv_unpaid.id}/send-reminder", headers={"Authorization": f"Bearer {token_admin}"})
    assert res.status_code == 200
    assert "dispatched successfully" in res.json()["message"]

    # 2. Cannot send reminder for fully paid invoice -> 400 Bad Request
    res_paid = client.post(f"/api/invoices/{inv_paid.id}/send-reminder", headers={"Authorization": f"Bearer {token_admin}"})
    assert res_paid.status_code == 400

    # 3. Viewer cannot send reminder -> 403 Forbidden
    res_viewer = client.post(f"/api/invoices/{inv_unpaid.id}/send-reminder", headers={"Authorization": f"Bearer {token_viewer}"})
    assert res_viewer.status_code == 403
