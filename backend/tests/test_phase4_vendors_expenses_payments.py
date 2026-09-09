import pytest
from decimal import Decimal
from datetime import date
from app.models.user import User, UserRole
from app.models.vendor import Vendor
from app.models.invoice import Invoice, InvoiceStatus, PaymentStatus, ExtractionStatus
from app.models.expense import Expense
from app.models.payment import Payment
from app.models.audit_log import AuditLog, AuditAction
from app.core.security import get_password_hash


def create_sample_pdf() -> bytes:
    import fitz
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text(
        (50, 72),
        "TAX INVOICE\n"
        "Vendor: Apex Cloud & IT Services\n"
        "Invoice Number: INV-APEX-900\n"
        "Subtotal: 20000.00\n"
        "Tax: 3600.00\n"
        "Total: 23600.00\n"
    )
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


@pytest.fixture(autouse=True)
def setup_phase4_data(db_session):
    admin = User(
        email="admin@test.com",
        hashed_password=get_password_hash("AdminPass123!"),
        full_name="Admin User",
        role=UserRole.ADMIN,
        is_active=True
    )
    staff = User(
        email="staff@test.com",
        hashed_password=get_password_hash("StaffPass123!"),
        full_name="Staff User",
        role=UserRole.STAFF,
        is_active=True
    )
    viewer = User(
        email="viewer@test.com",
        hashed_password=get_password_hash("ViewerPass123!"),
        full_name="Viewer User",
        role=UserRole.VIEWER,
        is_active=True
    )
    vendor = Vendor(
        name="Apex Cloud & IT Services",
        email="billing@apexcloud.io",
        phone="+91 80123 45678",
        gstin="29AAACA2145C1Z1",
        category="Software",
        payment_terms_days=30,
        active=True
    )
    db_session.add_all([admin, staff, viewer, vendor])
    db_session.commit()


def get_token_for(client, email: str, password: str = "AdminPass123!") -> str:
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    return res.json()["access_token"]


# ==========================================
# 1. VENDOR MANAGEMENT TESTS
# ==========================================

def test_vendor_crud_and_metrics(client, db_session):
    admin_token = get_token_for(client, "admin@test.com", "AdminPass123!")
    staff_token = get_token_for(client, "staff@test.com", "StaffPass123!")

    # Create new vendor
    create_res = client.post(
        "/api/vendors",
        headers={"Authorization": f"Bearer {staff_token}"},
        json={
            "name": "Tata Telecommunications",
            "email": "enterprise@tatatele.com",
            "phone": "+91 22666 55555",
            "gstin": "27AAACT2727Q1ZW",
            "category": "Utilities",
            "payment_terms_days": 15,
            "active": True
        }
    )
    assert create_res.status_code == 201
    vendor_data = create_res.json()
    vendor_id = vendor_data["id"]
    assert vendor_data["name"] == "Tata Telecommunications"

    # List vendors
    list_res = client.get("/api/vendors", headers={"Authorization": f"Bearer {staff_token}"})
    assert list_res.status_code == 200
    assert list_res.json()["total"] >= 2

    # Get vendor details (with aggregated financial metrics)
    detail_res = client.get(f"/api/vendors/{vendor_id}", headers={"Authorization": f"Bearer {staff_token}"})
    assert detail_res.status_code == 200
    detail_json = detail_res.json()
    assert detail_json["total_invoices"] == 0
    assert detail_json["outstanding_balance"] == "0.00"

    # Update vendor
    update_res = client.put(
        f"/api/vendors/{vendor_id}",
        headers={"Authorization": f"Bearer {staff_token}"},
        json={"payment_terms_days": 45}
    )
    assert update_res.status_code == 200
    assert update_res.json()["payment_terms_days"] == 45

    # Delete vendor (Admin only)
    del_res = client.delete(f"/api/vendors/{vendor_id}", headers={"Authorization": f"Bearer {admin_token}"})
    assert del_res.status_code == 200


def test_vendor_viewer_role_forbidden_to_mutate(client):
    viewer_token = get_token_for(client, "viewer@test.com", "ViewerPass123!")

    res = client.post(
        "/api/vendors",
        headers={"Authorization": f"Bearer {viewer_token}"},
        json={"name": "Unauthorized Vendor"}
    )
    assert res.status_code == 403


# ==========================================
# 2. EXPENSE MANAGEMENT TESTS
# ==========================================

def test_expense_crud_and_summary(client, db_session):
    admin_token = get_token_for(client, "admin@test.com", "AdminPass123!")
    staff_token = get_token_for(client, "staff@test.com", "StaffPass123!")

    # Create Expense
    exp_res = client.post(
        "/api/expenses",
        headers={"Authorization": f"Bearer {staff_token}"},
        json={
            "category": "Office",
            "amount": "4500.00",
            "expense_date": "2026-09-08",
            "description": "Ergonomic Chairs and Desks",
            "payment_method": "BANK_TRANSFER"
        }
    )
    assert exp_res.status_code == 201
    exp_id = exp_res.json()["id"]

    # Create another expense
    client.post(
        "/api/expenses",
        headers={"Authorization": f"Bearer {staff_token}"},
        json={
            "category": "Marketing",
            "amount": "12000.00",
            "expense_date": "2026-09-08",
            "description": "Google Search Ads Q3 Campaign",
            "payment_method": "CREDIT_CARD"
        }
    )

    # List Expenses
    list_res = client.get("/api/expenses", headers={"Authorization": f"Bearer {staff_token}"})
    assert list_res.status_code == 200
    assert list_res.json()["total"] == 2

    # Get Expense Summary (Category breakdown)
    summary_res = client.get("/api/expenses/summary", headers={"Authorization": f"Bearer {staff_token}"})
    assert summary_res.status_code == 200
    sum_data = summary_res.json()
    assert sum_data["total_count"] == 2
    assert Decimal(sum_data["total_expenses_amount"]) == Decimal("16500.00")
    assert len(sum_data["by_category"]) == 2

    # Update Expense
    update_res = client.put(
        f"/api/expenses/{exp_id}",
        headers={"Authorization": f"Bearer {staff_token}"},
        json={"amount": "5000.00"}
    )
    assert update_res.status_code == 200
    assert Decimal(update_res.json()["amount"]) == Decimal("5000.00")

    # Delete Expense (Admin only)
    del_res = client.delete(f"/api/expenses/{exp_id}", headers={"Authorization": f"Bearer {admin_token}"})
    assert del_res.status_code == 200


# ==========================================
# 3. PAYMENT SETTLEMENT & ATOMIC LEDGER TESTS
# ==========================================

def test_atomic_payment_settlement_lifecycle(client, db_session):
    staff_token = get_token_for(client, "staff@test.com", "StaffPass123!")
    pdf_bytes = create_sample_pdf()

    # 1. Upload & Extract Invoice
    upload_res = client.post(
        "/api/invoices/upload",
        headers={"Authorization": f"Bearer {staff_token}"},
        files={"file": ("apex_invoice.pdf", pdf_bytes, "application/pdf")}
    )
    inv_id = upload_res.json()["invoice"]["id"]

    # Extract
    extract_res = client.post(f"/api/invoices/{inv_id}/extract", headers={"Authorization": f"Bearer {staff_token}"})
    assert extract_res.status_code == 200

    # Approve Invoice
    approve_res = client.post(f"/api/invoices/{inv_id}/approve", headers={"Authorization": f"Bearer {staff_token}"})
    assert approve_res.status_code == 200
    assert approve_res.json()["status"] == InvoiceStatus.APPROVED

    inv_before = db_session.get(Invoice, inv_id)
    assert inv_before.total_amount == Decimal("23600.00")
    assert inv_before.paid_amount == Decimal("0.00")
    assert inv_before.remaining_amount == Decimal("23600.00")
    assert inv_before.payment_status == PaymentStatus.PENDING

    # 2. Test Partial Payment: Settle 10,000.00
    pay1_res = client.post(
        "/api/payments",
        headers={"Authorization": f"Bearer {staff_token}"},
        json={
            "invoice_id": inv_id,
            "amount": "10000.00",
            "payment_date": "2026-09-08",
            "payment_method": "BANK_TRANSFER",
            "reference_number": "UTR-1002938471"
        }
    )
    assert pay1_res.status_code == 201
    pay1_data = pay1_res.json()
    assert pay1_data["invoice_payment_status"] == PaymentStatus.PARTIALLY_PAID

    # Verify Invoice database record updated atomically
    db_session.expire_all()
    inv_after_p1 = db_session.get(Invoice, inv_id)
    assert inv_after_p1.paid_amount == Decimal("10000.00")
    assert inv_after_p1.remaining_amount == Decimal("13600.00")
    assert inv_after_p1.payment_status == PaymentStatus.PARTIALLY_PAID

    # 3. Test Overpayment Guard: Attempt to settle 15,000.00 (exceeds 13,600.00)
    pay_over_res = client.post(
        "/api/payments",
        headers={"Authorization": f"Bearer {staff_token}"},
        json={
            "invoice_id": inv_id,
            "amount": "15000.00",
            "payment_date": "2026-09-08",
            "payment_method": "BANK_TRANSFER"
        }
    )
    assert pay_over_res.status_code == 422

    # 4. Test Final Payment: Settle exact remaining balance 13,600.00
    pay2_res = client.post(
        "/api/payments",
        headers={"Authorization": f"Bearer {staff_token}"},
        json={
            "invoice_id": inv_id,
            "amount": "13600.00",
            "payment_date": "2026-09-08",
            "payment_method": "UPI",
            "reference_number": "UPI-8839201948"
        }
    )
    assert pay2_res.status_code == 201
    pay2_data = pay2_res.json()
    assert pay2_data["invoice_payment_status"] == PaymentStatus.PAID

    # Verify Invoice is now fully settled and status updated to PAID
    db_session.expire_all()
    inv_final = db_session.get(Invoice, inv_id)
    assert inv_final.paid_amount == Decimal("23600.00")
    assert inv_final.remaining_amount == Decimal("0.00")
    assert inv_final.payment_status == PaymentStatus.PAID
    assert inv_final.status == InvoiceStatus.PAID

    # 5. List Payments Ledger
    payments_list_res = client.get(
        f"/api/payments?invoice_id={inv_id}",
        headers={"Authorization": f"Bearer {staff_token}"}
    )
    assert payments_list_res.status_code == 200
    assert payments_list_res.json()["total"] == 2
