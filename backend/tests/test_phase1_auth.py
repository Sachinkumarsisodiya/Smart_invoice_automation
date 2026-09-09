import pytest
from app.models.user import User, UserRole
from app.core.security import get_password_hash


@pytest.fixture(autouse=True)
def setup_users(db_session):
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
    db_session.add_all([admin, staff])
    db_session.commit()


def test_health_check(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_login_success(client):
    response = client.post("/api/auth/login", json={
        "email": "admin@test.com",
        "password": "AdminPass123!"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["email"] == "admin@test.com"
    assert data["user"]["role"] == "ADMIN"


def test_login_invalid_password(client):
    response = client.post("/api/auth/login", json={
        "email": "admin@test.com",
        "password": "WrongPassword"
    })
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_register_new_user(client):
    response = client.post("/api/auth/register", json={
        "email": "newuser@test.com",
        "password": "NewUserPass123!",
        "full_name": "New User",
        "role": "VIEWER"
    })
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert data["user"]["email"] == "newuser@test.com"
    assert data["user"]["role"] == "VIEWER"


def test_get_me_authenticated(client):
    login_res = client.post("/api/auth/login", json={
        "email": "staff@test.com",
        "password": "StaffPass123!"
    })
    token = login_res.json()["access_token"]

    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["email"] == "staff@test.com"
    assert response.json()["role"] == "STAFF"


def test_get_me_unauthorized(client):
    response = client.get("/api/auth/me")
    assert response.status_code == 401
