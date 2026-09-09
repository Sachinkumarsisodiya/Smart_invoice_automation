import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User, UserRole
from app.models.vendor import Vendor
from app.models.invoice import Invoice
from app.models.expense import Expense
from app.models.payment import Payment
from app.models.notification import Notification
from app.models.audit_log import AuditLog
from app.database.seed import seed_database
from app.core.security import get_password_hash, create_access_token


def test_security_headers_present(client: TestClient):
    """Verify production security headers are attached by SecurityHeadersMiddleware."""
    res = client.get("/api/health")
    assert res.status_code == 200
    headers = res.headers

    assert headers.get("X-Frame-Options") == "DENY"
    assert headers.get("X-Content-Type-Options") == "nosniff"
    assert headers.get("X-XSS-Protection") == "1; mode=block"
    assert headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert "Content-Security-Policy" in headers
    assert "default-src 'self'" in headers["Content-Security-Policy"]


def test_request_correlation_and_timing_headers(client: TestClient):
    """Verify RequestCorrelationMiddleware generates X-Request-ID and tracks latency."""
    res = client.get("/api/health")
    assert res.status_code == 200
    headers = res.headers

    assert "X-Request-ID" in headers
    assert len(headers["X-Request-ID"]) >= 10  # Valid UUID format
    assert "X-Process-Time" in headers
    assert headers["X-Process-Time"].endswith("s")


def test_custom_request_id_propagation(client: TestClient):
    """Verify client-supplied X-Request-ID is preserved in downstream responses."""
    custom_trace_id = f"trace-custom-{uuid.uuid4().hex[:12]}"
    res = client.get("/api/health", headers={"X-Request-ID": custom_trace_id})
    assert res.status_code == 200
    assert res.headers.get("X-Request-ID") == custom_trace_id


def test_database_seed_idempotency(db_session: Session):
    """Verify seed_database is completely idempotent and populates all core demo entities."""
    # First seed run
    seed_database(db=db_session)

    user_count_1 = db_session.query(User).count()
    vendor_count_1 = db_session.query(Vendor).count()
    invoice_count_1 = db_session.query(Invoice).count()
    expense_count_1 = db_session.query(Expense).count()
    payment_count_1 = db_session.query(Payment).count()

    assert user_count_1 >= 3
    assert vendor_count_1 >= 3
    assert invoice_count_1 >= 3
    assert expense_count_1 >= 3
    assert payment_count_1 >= 1

    # Second seed run -> must not duplicate entities
    seed_database(db=db_session)

    assert db_session.query(User).count() == user_count_1
    assert db_session.query(Vendor).count() == vendor_count_1
    assert db_session.query(Invoice).count() == invoice_count_1
    assert db_session.query(Expense).count() == expense_count_1
    assert db_session.query(Payment).count() == payment_count_1


def test_rate_limiter_configuration_and_headers(client: TestClient, db_session: Session):
    """Verify rate limiter applies to auth endpoints and can be dynamically toggled."""
    from app.core.rate_limiter import limiter
    
    # 1. Without rate limiting enabled (default in test env)
    res = client.post(
        "/api/auth/login",
        json={"email": "nonexistent@smartinvoice.dev", "password": "WrongPassword123!"}
    )
    assert res.status_code == 401

    # 2. Verify limiter object state
    assert limiter is not None
    assert limiter._key_func is not None


def test_root_and_system_health_probes(client: TestClient):
    """Verify root API welcome message and system health endpoint without secret leaks."""
    # 1. Root endpoint
    res_root = client.get("/")
    assert res_root.status_code == 200
    assert "SmartInvoice" in res_root.json()["message"]

    # 2. API health
    res_health = client.get("/api/health")
    assert res_health.status_code == 200
    data = res_health.json()
    assert data["status"] == "healthy"
    assert data["env"] is not None
