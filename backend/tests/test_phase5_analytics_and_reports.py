import csv
import io
import uuid
import pytest
from decimal import Decimal
from datetime import date, datetime, timedelta, timezone
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app.models.user import User, UserRole
from app.models.vendor import Vendor
from app.models.invoice import Invoice, InvoiceStatus, PaymentStatus, ExtractionStatus
from app.models.payment import Payment
from app.models.expense import Expense
from app.services.analytics_service import AnalyticsService
from app.services.report_service import ReportService
from app.core.security import create_access_token


def test_dashboard_kpis_calculation(db_session: Session):
    """Test KPI aggregation calculations on fresh test data."""
    # 1. Create a vendor
    vendor = Vendor(
        name="Phase 5 Test Supplier",
        email="supplier@phase5.com",
        category="Hardware",
        payment_terms_days=30
    )
    db_session.add(vendor)
    db_session.flush()

    # 2. Create Invoices
    today = date.today()
    inv1 = Invoice(
        vendor_id=vendor.id,
        invoice_number="INV-P5-001",
        invoice_date=today,
        due_date=today + timedelta(days=15),
        subtotal=Decimal("1000.00"),
        tax_amount=Decimal("180.00"),
        total_amount=Decimal("1180.00"),
        paid_amount=Decimal("500.00"),
        remaining_amount=Decimal("680.00"),
        status=InvoiceStatus.APPROVED,
        payment_status=PaymentStatus.PARTIALLY_PAID,
        document_path="uploads/test1.pdf",
        document_hash="hash1",
        extraction_status=ExtractionStatus.SUCCESS,
        extraction_confidence=Decimal("0.95"),
        currency="INR"
    )
    # Overdue invoice
    inv2 = Invoice(
        vendor_id=vendor.id,
        invoice_number="INV-P5-002",
        invoice_date=today - timedelta(days=40),
        due_date=today - timedelta(days=10),
        subtotal=Decimal("2000.00"),
        tax_amount=Decimal("360.00"),
        total_amount=Decimal("2360.00"),
        paid_amount=Decimal("0.00"),
        remaining_amount=Decimal("2360.00"),
        status=InvoiceStatus.APPROVED,
        payment_status=PaymentStatus.PENDING,
        document_path="uploads/test2.pdf",
        document_hash="hash2",
        extraction_status=ExtractionStatus.SUCCESS,
        extraction_confidence=Decimal("0.90"),
        currency="INR"
    )
    # Rejected invoice (should be ignored in active totals)
    inv3 = Invoice(
        vendor_id=vendor.id,
        invoice_number="INV-P5-003",
        invoice_date=today,
        due_date=today + timedelta(days=15),
        subtotal=Decimal("500.00"),
        tax_amount=Decimal("90.00"),
        total_amount=Decimal("590.00"),
        paid_amount=Decimal("0.00"),
        remaining_amount=Decimal("590.00"),
        status=InvoiceStatus.REJECTED,
        payment_status=PaymentStatus.PENDING,
        document_path="uploads/test3.pdf",
        document_hash="hash3",
        extraction_status=ExtractionStatus.SUCCESS,
        extraction_confidence=Decimal("0.80"),
        currency="INR"
    )
    db_session.add_all([inv1, inv2, inv3])
    db_session.flush()

    # 3. Create Expense
    exp = Expense(
        expense_date=today,
        category="Office Supplies",
        description="Printer toner cartridges",
        amount=Decimal("250.00"),
        payment_method="CORPORATE_CARD"
    )
    db_session.add(exp)
    db_session.flush()

    # 4. Create Payment
    pay = Payment(
        invoice_id=inv1.id,
        amount=Decimal("500.00"),
        payment_date=today,
        payment_method="BANK_TRANSFER"
    )
    db_session.add(pay)
    db_session.commit()

    # Compute KPIs
    kpis = AnalyticsService.get_dashboard_kpis(db_session)

    # Validations
    assert kpis.total_invoices_count >= 2
    assert kpis.total_invoiced_amount >= Decimal("3540.00")
    assert kpis.total_paid_amount >= Decimal("500.00")
    assert kpis.total_outstanding_amount >= Decimal("3040.00")
    assert kpis.overdue_invoices_count >= 1
    assert kpis.overdue_amount >= Decimal("2360.00")
    assert kpis.total_expenses_amount >= Decimal("250.00")
    assert kpis.total_settled_transactions >= 1


def test_monthly_cashflow_service(db_session: Session):
    """Test monthly cashflow trend generation."""
    cashflow = AnalyticsService.get_monthly_cashflow(db_session, num_months=6)
    assert len(cashflow) == 6
    for item in cashflow:
        assert item.month_key is not None
        assert item.month_label is not None
        assert item.invoiced_amount >= Decimal("0.00")
        assert item.paid_amount >= Decimal("0.00")
        assert item.expense_amount >= Decimal("0.00")


def test_category_distribution_service(db_session: Session):
    """Test expense and invoice spend category aggregation."""
    cats = AnalyticsService.get_category_distribution(db_session)
    assert isinstance(cats, list)
    if len(cats) > 0:
        total_pct = sum(c.percentage for c in cats)
        assert total_pct <= 100.1  # Floating point rounding allowance


def test_status_distribution_service(db_session: Session):
    """Test lifecycle status distribution."""
    statuses = AnalyticsService.get_status_distribution(db_session)
    assert isinstance(statuses, list)
    assert all(s.count >= 0 and s.amount >= Decimal("0.00") for s in statuses)


def test_top_vendors_service(db_session: Session):
    """Test top vendor spend ranking."""
    top_vendors = AnalyticsService.get_top_vendors(db_session, limit=5)
    assert isinstance(top_vendors, list)
    assert len(top_vendors) <= 5
    if len(top_vendors) > 1:
        assert top_vendors[0].total_invoiced >= top_vendors[1].total_invoiced


def test_recent_activity_service(db_session: Session):
    """Test recent activity timeline."""
    activity = AnalyticsService.get_recent_activity(db_session, limit=10)
    assert isinstance(activity, list)
    assert len(activity) <= 10
    for act in activity:
        assert act.type in ["INVOICE", "PAYMENT", "EXPENSE"]
        assert act.title is not None
        assert act.timestamp is not None


def test_tax_summary_and_export(db_session: Session):
    """Test tax summary calculation and CSV generation."""
    tax_summary = ReportService.get_tax_summary(db_session)
    assert tax_summary.total_subtotal >= Decimal("0.00")
    assert tax_summary.total_tax_amount >= Decimal("0.00")
    assert tax_summary.total_gross_amount >= Decimal("0.00")

    # Test CSV Invoices Export
    inv_csv = ReportService.export_invoices_csv(db_session)
    reader = csv.reader(io.StringIO(inv_csv))
    headers = next(reader)
    assert "Invoice Number" in headers
    assert "Vendor Name" in headers
    assert "Tax Amount" in headers

    # Test CSV Expenses Export
    exp_csv = ReportService.export_expenses_csv(db_session)
    exp_reader = csv.reader(io.StringIO(exp_csv))
    exp_headers = next(exp_reader)
    assert "Expense ID" in exp_headers
    assert "Category" in exp_headers
    assert "Amount" in exp_headers

    # Test CSV Payments Export
    pay_csv = ReportService.export_payments_csv(db_session)
    pay_reader = csv.reader(io.StringIO(pay_csv))
    pay_headers = next(pay_reader)
    assert "Payment ID" in pay_headers
    assert "Amount Settled" in pay_headers


from app.core.security import create_access_token, get_password_hash


def test_dashboard_and_reports_api_endpoints(client: TestClient, db_session: Session):
    """Test full HTTP endpoints for dashboard stats and reports with JWT auth."""
    admin_user = User(
        email="admin_phase5@smartinvoice.dev",
        hashed_password=get_password_hash("AdminPass123!"),
        full_name="Phase 5 Admin",
        role=UserRole.ADMIN,
        is_active=True
    )
    db_session.add(admin_user)
    db_session.commit()
    db_session.refresh(admin_user)

    token = create_access_token(subject=admin_user.id, role=admin_user.role)
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Dashboard Stats
    res = client.get("/api/dashboard/stats", headers=headers)
    assert res.status_code == 200
    stats = res.json()
    assert "total_invoiced_amount" in stats
    assert "total_paid_amount" in stats

    # 2. Monthly Cashflow
    res = client.get("/api/dashboard/monthly-cashflow?months=6", headers=headers)
    assert res.status_code == 200
    assert isinstance(res.json(), list)

    # 3. Category Distribution
    res = client.get("/api/dashboard/category-distribution", headers=headers)
    assert res.status_code == 200
    assert isinstance(res.json(), list)

    # 4. Status Distribution
    res = client.get("/api/dashboard/status-distribution", headers=headers)
    assert res.status_code == 200
    assert isinstance(res.json(), list)

    # 5. Top Vendors
    res = client.get("/api/dashboard/top-vendors?limit=5", headers=headers)
    assert res.status_code == 200
    assert isinstance(res.json(), list)

    # 6. Recent Activity
    res = client.get("/api/dashboard/recent-activity?limit=5", headers=headers)
    assert res.status_code == 200
    assert isinstance(res.json(), list)

    # 7. Tax Summary
    res = client.get("/api/reports/tax-summary", headers=headers)
    assert res.status_code == 200
    tax_data = res.json()
    assert "total_tax_amount" in tax_data
    assert "vendors_breakdown" in tax_data

    # 8. Invoices CSV Export
    res = client.get("/api/reports/invoices/export", headers=headers)
    assert res.status_code == 200
    assert "text/csv" in res.headers["content-type"]
    assert "invoices_export" in res.headers["content-disposition"]

    # 9. Expenses CSV Export
    res = client.get("/api/reports/expenses/export", headers=headers)
    assert res.status_code == 200
    assert "text/csv" in res.headers["content-type"]
    assert "expenses_export" in res.headers["content-disposition"]

    # 10. Payments CSV Export
    res = client.get("/api/reports/payments/export", headers=headers)
    assert res.status_code == 200
    assert "text/csv" in res.headers["content-type"]
    assert "payments_export" in res.headers["content-disposition"]
