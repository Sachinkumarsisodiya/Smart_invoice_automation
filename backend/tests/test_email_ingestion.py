import io
import email
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.models.user import User, UserRole
from app.models.invoice import Invoice
from app.services.email_ingestion_service import EmailIngestionService
from app.core.security import create_access_token, get_password_hash


def test_email_ingestion_unconfigured(db_session):
    """When IMAP credentials are empty, sync_mailbox should return a clean error without crashing."""
    with patch.object(settings, "IMAP_PASSWORD", ""):
        result = EmailIngestionService.sync_mailbox(db=db_session)
        assert result["success"] is False
        assert "IMAP credentials not configured" in result["message"]
        assert result["fetched_count"] == 0


def test_email_ingestion_with_mock_imap(db_session, client):
    """Test full email ingestion flow using a simulated IMAP mailbox with PDF invoice attachment."""
    # Ensure user exists
    user = db_session.query(User).filter(User.email == "sachinsisodiyaofc@gmail.com").first()
    if not user:
        user = User(
            email="sachinsisodiyaofc@gmail.com",
            hashed_password=get_password_hash("Password123!"),
            full_name="Sachin Sisodiya",
            role=UserRole.ADMIN
        )
        db_session.add(user)
        db_session.commit()

    # Build a simulated RFC822 multipart email with PDF attachment
    msg = MIMEMultipart()
    msg["Subject"] = "Invoice INV-2026-990 from CloudHost Ltd"
    msg["From"] = "billing@cloudhost.com"
    msg["To"] = "sachinsisodiyaofc@gmail.com"
    msg.attach(MIMEText("Please find attached the invoice for services rendered.", "plain"))

    # Minimal valid PDF bytes
    sample_pdf_bytes = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF"
    pdf_attachment = MIMEApplication(sample_pdf_bytes, _subtype="pdf")
    pdf_attachment.add_header("Content-Disposition", "attachment", filename="invoice_cloudhost_990.pdf")
    msg.attach(pdf_attachment)

    raw_email_bytes = msg.as_bytes()

    # Mock imaplib.IMAP4_SSL
    mock_imap = MagicMock()
    mock_imap.login.return_value = ("OK", [b"Logged in"])
    mock_imap.select.return_value = ("OK", [b"1"])
    mock_imap.search.return_value = ("OK", [b"101"])
    mock_imap.fetch.return_value = ("OK", [(b"101 (RFC822 {1000}", raw_email_bytes)])
    mock_imap.store.return_value = ("OK", [b"Flags updated"])

    with patch("imaplib.IMAP4_SSL", return_value=mock_imap), \
         patch.object(settings, "IMAP_PASSWORD", "mock-app-password-16"), \
         patch.object(settings, "IMAP_USER", "sachinsisodiyaofc@gmail.com"):

        result = EmailIngestionService.sync_mailbox(db=db_session, user=user)

        assert result["success"] is True
        assert result["fetched_count"] >= 1
        assert len(result["invoices"]) >= 1
        inv_item = result["invoices"][0]
        assert inv_item["filename"] == "invoice_cloudhost_990.pdf"
        assert "billing@cloudhost.com" in inv_item["sender"]


def test_fetch_from_email_api_endpoint(db_session, client):
    """Test POST /api/v1/invoices/fetch-from-email endpoint with RBAC authentication."""
    # 1. Test without auth -> 401
    resp = client.post("/api/invoices/fetch-from-email")
    assert resp.status_code == 401

    # 2. Test with Admin Auth
    admin = db_session.query(User).filter(User.email == "sachinsisodiyaofc@gmail.com").first()
    if not admin:
        admin = User(
            email="sachinsisodiyaofc@gmail.com",
            hashed_password=get_password_hash("Password123!"),
            full_name="Sachin Sisodiya",
            role=UserRole.ADMIN
        )
        db_session.add(admin)
        db_session.commit()
        db_session.refresh(admin)
    role_val = admin.role.value if hasattr(admin.role, "value") else str(admin.role)
    token = create_access_token(subject=str(admin.id), role=role_val)
    headers = {"Authorization": f"Bearer {token}"}

    with patch.object(EmailIngestionService, "sync_mailbox") as mock_sync:
        mock_sync.return_value = {
            "success": True,
            "message": "Synced 2 invoices from sachinsisodiyaofc@gmail.com.",
            "fetched_count": 2,
            "invoices": [{"invoice_id": "test-id", "filename": "inv.pdf"}],
            "errors": []
        }

        resp = client.post("/api/invoices/fetch-from-email", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["fetched_count"] == 2
