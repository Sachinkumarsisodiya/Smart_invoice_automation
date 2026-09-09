import pytest
from app.models.user import User, UserRole
from app.models.vendor import Vendor
from app.core.security import get_password_hash


def create_minimal_pdf() -> bytes:
    import fitz
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 72), "INVOICE #INV-1045\nVendor: Sharma Packaging Pvt Ltd\nTotal: INR 11800.00\nSubtotal: 10000.00\nTax: 1800.00")
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


@pytest.fixture(autouse=True)
def setup_phase2_data(db_session):
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
    viewer = User(
        email="viewer@test.com",
        hashed_password=get_password_hash("ViewerPass123!"),
        full_name="Viewer Test",
        role=UserRole.VIEWER,
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
    db_session.add_all([admin, staff, viewer, vendor])
    db_session.commit()


def get_token_for(client, email: str, password: str = "AdminPass123!") -> str:
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    return res.json()["access_token"]


def test_upload_invalid_extension(client):
    token = get_token_for(client, "staff@test.com", "StaffPass123!")
    files = {"file": ("malicious.exe", b"malicious executable content", "application/octet-stream")}
    res = client.post("/api/invoices/upload", headers={"Authorization": f"Bearer {token}"}, files=files)
    assert res.status_code == 422
    assert "Unsupported file format" in res.json()["error"]["message"]


def test_upload_corrupted_header(client):
    token = get_token_for(client, "staff@test.com", "StaffPass123!")
    files = {"file": ("invoice.pdf", b"NOT A REAL PDF HEADER CONTENT", "application/pdf")}
    res = client.post("/api/invoices/upload", headers={"Authorization": f"Bearer {token}"}, files=files)
    assert res.status_code == 422
    assert "Corrupted file" in res.json()["error"]["message"]


def test_upload_valid_pdf_and_text_extraction(client):
    token = get_token_for(client, "staff@test.com", "StaffPass123!")
    pdf_content = create_minimal_pdf()
    files = {"file": ("sample_invoice.pdf", pdf_content, "application/pdf")}
    
    res = client.post("/api/invoices/upload", headers={"Authorization": f"Bearer {token}"}, files=files)
    assert res.status_code == 201
    data = res.json()
    
    assert "invoice" in data
    assert data["is_digital"] is True
    assert data["char_count"] > 30
    assert "INVOICE #INV-1045" in data["extracted_text_snippet"]
    assert data["invoice"]["status"] in ["PENDING_REVIEW", "PROCESSING"]


def test_list_and_filter_invoices(client):
    token = get_token_for(client, "staff@test.com", "StaffPass123!")
    pdf_content = create_minimal_pdf()
    files = {"file": ("invoice_test.pdf", pdf_content, "application/pdf")}
    client.post("/api/invoices/upload", headers={"Authorization": f"Bearer {token}"}, files=files)

    res = client.get("/api/invoices", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1


def test_get_invoice_detail_and_document_streaming(client):
    token = get_token_for(client, "staff@test.com", "StaffPass123!")
    pdf_content = create_minimal_pdf()
    files = {"file": ("streaming_test.pdf", pdf_content, "application/pdf")}
    upload_res = client.post("/api/invoices/upload", headers={"Authorization": f"Bearer {token}"}, files=files)
    inv_id = upload_res.json()["invoice"]["id"]

    detail_res = client.get(f"/api/invoices/{inv_id}", headers={"Authorization": f"Bearer {token}"})
    assert detail_res.status_code == 200
    assert detail_res.json()["id"] == inv_id

    doc_res = client.get(f"/api/invoices/{inv_id}/document", headers={"Authorization": f"Bearer {token}"})
    assert doc_res.status_code == 200
    assert doc_res.headers["content-type"] == "application/pdf"
    assert len(doc_res.content) == len(pdf_content)


def test_viewer_role_cannot_upload(client):
    viewer_token = get_token_for(client, "viewer@test.com", "ViewerPass123!")
    pdf_content = create_minimal_pdf()
    files = {"file": ("invoice.pdf", pdf_content, "application/pdf")}
    res = client.post("/api/invoices/upload", headers={"Authorization": f"Bearer {viewer_token}"}, files=files)
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "FORBIDDEN"


def test_admin_can_delete_invoice(client):
    staff_token = get_token_for(client, "staff@test.com", "StaffPass123!")
    admin_token = get_token_for(client, "admin@test.com", "AdminPass123!")
    
    pdf_content = create_minimal_pdf()
    files = {"file": ("delete_test.pdf", pdf_content, "application/pdf")}
    upload_res = client.post("/api/invoices/upload", headers={"Authorization": f"Bearer {staff_token}"}, files=files)
    inv_id = upload_res.json()["invoice"]["id"]

    staff_del = client.delete(f"/api/invoices/{inv_id}", headers={"Authorization": f"Bearer {staff_token}"})
    assert staff_del.status_code == 403

    admin_del = client.delete(f"/api/invoices/{inv_id}", headers={"Authorization": f"Bearer {admin_token}"})
    assert admin_del.status_code == 204

    get_res = client.get(f"/api/invoices/{inv_id}", headers={"Authorization": f"Bearer {admin_token}"})
    assert get_res.status_code == 404
