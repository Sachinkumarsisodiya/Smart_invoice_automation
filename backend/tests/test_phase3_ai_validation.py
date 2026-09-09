import pytest
from decimal import Decimal
from app.models.user import User, UserRole
from app.models.vendor import Vendor
from app.models.invoice import Invoice, InvoiceStatus, ExtractionStatus
from app.models.audit_log import AuditLog, AuditAction
from app.core.security import get_password_hash
from app.ai.mock_provider import MockAIProvider
from app.ai.provider import ExtractedInvoiceSchema, ExtractedItemSchema
from app.services.validation_service import ValidationService
from app.services.duplicate_service import DuplicateService


def create_sample_pdf() -> bytes:
    import fitz
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text(
        (50, 72),
        "TAX INVOICE\n"
        "Vendor: Sharma Packaging Pvt Ltd\n"
        "Invoice Number: INV-1045\n"
        "Invoice Date: 2026-09-07\n"
        "Due Date: 2026-09-30\n"
        "Item: Corrugated Boxes\n"
        "Subtotal: 10000.00\n"
        "Tax (GST 18%): 1800.00\n"
        "Total Amount: 11800.00\n"
    )
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


@pytest.fixture(autouse=True)
def setup_phase3_data(db_session):
    admin = User(
        email="admin@test.com",
        hashed_password=get_password_hash("AdminPass123!"),
        full_name="Admin Test",
        role=UserRole.ADMIN,
        is_active=True
    )
    staff = User(
        email="staff@test.com",
        hashed_password=get_password_hash("StaffPass123!"),
        full_name="Staff Test",
        role=UserRole.STAFF,
        is_active=True
    )
    vendor = Vendor(
        name="Sharma Packaging Pvt Ltd",
        email="sales@sharmapackaging.com",
        phone="+91 98765 43210",
        gstin="27AABCS1429B1Z5",
        category="Packaging",
        payment_terms_days=30
    )
    db_session.add_all([admin, staff, vendor])
    db_session.commit()


def get_token_for(client, email: str, password: str = "AdminPass123!") -> str:
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    return res.json()["access_token"]


def test_mock_ai_provider_extraction():
    import asyncio
    provider = MockAIProvider()
    raw_text = "Vendor: Sharma Packaging Pvt Ltd\nInvoice: INV-1045\nTotal: INR 11800.00\nSubtotal: 10000.00\nTax: 1800.00"
    extracted = asyncio.run(provider.extract_invoice(raw_text))

    assert extracted.vendor_name == "Sharma Packaging Pvt Ltd"
    assert extracted.invoice_number == "INV-1045"
    assert extracted.subtotal == Decimal("10000.00")
    assert extracted.tax_amount == Decimal("1800.00")
    assert extracted.total_amount == Decimal("11800.00")
    assert extracted.currency == "INR"
    assert extracted.is_mock is True
    assert extracted.confidence_score >= Decimal("80.00")


def test_deterministic_validation_valid_math():
    valid_data = ExtractedInvoiceSchema(
        vendor_name="Sharma Packaging Pvt Ltd",
        invoice_number="INV-1045",
        invoice_date="2026-09-07",
        due_date="2026-09-30",
        subtotal=Decimal("10000.00"),
        tax_amount=Decimal("1800.00"),
        total_amount=Decimal("11800.00"),
        currency="INR",
        items=[
            ExtractedItemSchema(description="Boxes", quantity=Decimal("10.000"), unit_price=Decimal("1000.00"), amount=Decimal("10000.00"))
        ]
    )

    is_valid, errors, meta = ValidationService.validate_extracted_invoice(valid_data)
    assert is_valid is True
    assert len(errors) == 0
    assert meta["math_consistent"] is True


def test_deterministic_validation_invalid_math_fails():
    # 10,000 + 1,800 != 13,800 (Fails!)
    invalid_data = ExtractedInvoiceSchema(
        vendor_name="Sharma Packaging Pvt Ltd",
        invoice_number="INV-1045",
        invoice_date="2026-09-07",
        due_date="2026-09-30",
        subtotal=Decimal("10000.00"),
        tax_amount=Decimal("1800.00"),
        total_amount=Decimal("13800.00"),  # Mismatched sum!
        currency="INR"
    )

    is_valid, errors, meta = ValidationService.validate_extracted_invoice(invalid_data)
    assert is_valid is False
    assert len(errors) > 0
    assert meta["math_consistent"] is False
    assert any("Mathematical inconsistency" in err for err in errors)


def test_deterministic_validation_due_date_earlier_fails():
    invalid_dates = ExtractedInvoiceSchema(
        vendor_name="Sharma Packaging Pvt Ltd",
        invoice_number="INV-1045",
        invoice_date="2026-09-30",
        due_date="2026-09-01",  # Due date earlier than invoice date!
        subtotal=Decimal("1000.00"),
        tax_amount=Decimal("180.00"),
        total_amount=Decimal("1180.00"),
        currency="INR"
    )

    is_valid, errors, meta = ValidationService.validate_extracted_invoice(invalid_dates)
    assert is_valid is False
    assert any("cannot be earlier than invoice date" in err for err in errors)


def test_duplicate_detection_rules(client, db_session):
    staff_token = get_token_for(client, "staff@test.com", "StaffPass123!")
    pdf_bytes = create_sample_pdf()

    # Upload first invoice
    res1 = client.post(
        "/api/invoices/upload",
        headers={"Authorization": f"Bearer {staff_token}"},
        files={"file": ("invoice1.pdf", pdf_bytes, "application/pdf")}
    )
    inv1_id = res1.json()["invoice"]["id"]
    inv1 = db_session.query(Invoice).filter(Invoice.id == inv1_id).first()
    inv1.invoice_number = "INV-DUPLICATE-TEST"
    db_session.commit()

    # Test Primary Check: Same vendor and invoice number
    is_dup, reason, matched_id = DuplicateService.check_duplicate(
        db=db_session,
        vendor_id=inv1.vendor_id,
        invoice_number="INV-DUPLICATE-TEST",
        document_hash="DIFFERENT_HASH"
    )
    assert is_dup is True
    assert reason == "VENDOR_AND_INVOICE_NUMBER"
    assert matched_id == inv1.id

    # Test Secondary Check: Same document hash
    is_dup_hash, reason_hash, matched_id_hash = DuplicateService.check_duplicate(
        db=db_session,
        vendor_id=inv1.vendor_id,
        invoice_number="DIFFERENT_NUM",
        document_hash=inv1.document_hash
    )
    assert is_dup_hash is True
    assert reason_hash == "DOCUMENT_HASH"
    assert matched_id_hash == inv1.id


def test_ai_extraction_and_approval_workflow(client, db_session):
    staff_token = get_token_for(client, "staff@test.com", "StaffPass123!")
    pdf_bytes = create_sample_pdf()

    # 1. Upload Invoice
    upload_res = client.post(
        "/api/invoices/upload",
        headers={"Authorization": f"Bearer {staff_token}"},
        files={"file": ("sample_workflow.pdf", pdf_bytes, "application/pdf")}
    )
    inv_id = upload_res.json()["invoice"]["id"]

    # 2. Trigger AI Extraction Endpoint
    extract_res = client.post(
        f"/api/invoices/{inv_id}/extract",
        headers={"Authorization": f"Bearer {staff_token}"}
    )
    assert extract_res.status_code == 200
    extract_data = extract_res.json()
    assert extract_data["invoice_number"] == "INV-1045"
    assert extract_data["total_amount"] == "11800.00"
    assert extract_data["status"] == "PENDING_REVIEW"
    assert len(extract_data["items"]) >= 1

    # 3. Approve Invoice Endpoint
    approve_res = client.post(
        f"/api/invoices/{inv_id}/approve",
        headers={"Authorization": f"Bearer {staff_token}"}
    )
    assert approve_res.status_code == 200
    assert approve_res.json()["status"] == "APPROVED"

    # Verify Audit Log
    audit = db_session.query(AuditLog).filter(
        AuditLog.entity == "INVOICE",
        AuditLog.entity_id == inv_id,
        AuditLog.action == AuditAction.INVOICE_APPROVED
    ).first()
    assert audit is not None


def test_reject_invoice_workflow(client, db_session):
    staff_token = get_token_for(client, "staff@test.com", "StaffPass123!")
    pdf_bytes = create_sample_pdf()

    upload_res = client.post(
        "/api/invoices/upload",
        headers={"Authorization": f"Bearer {staff_token}"},
        files={"file": ("reject_test.pdf", pdf_bytes, "application/pdf")}
    )
    inv_id = upload_res.json()["invoice"]["id"]

    reject_res = client.post(
        f"/api/invoices/{inv_id}/reject?reason=Tax+calculation+incorrect",
        headers={"Authorization": f"Bearer {staff_token}"}
    )
    assert reject_res.status_code == 200
    assert reject_res.json()["status"] == "REJECTED"
    assert "Tax calculation incorrect" in reject_res.json()["notes"]
