"""
Shared pytest fixtures.

KEY DESIGN — why this pattern works
------------------------------------
FastAPI runs synchronous route handlers inside AnyIO's thread pool
(anyio.to_thread.run_sync).  Sharing a single SQLAlchemy Session across
requests means that session object is used from different threads, which
causes subtle state corruption even with check_same_thread=False.

The correct pattern mirrors production exactly:
  * Each HTTP request gets its own Session (created & closed per request).
  * All sessions connect to the SAME in-memory SQLite via StaticPool,
    so committed data from request N is visible to request N+1.
  * Tables are created before each test and dropped afterwards so every
    test starts with a completely empty database.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app

# ---------------------------------------------------------------------------
# Shared in-memory database
# StaticPool forces every engine.connect() call to reuse the same underlying
# SQLite connection, so all sessions see each other's committed data.
# ---------------------------------------------------------------------------
test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


# ---------------------------------------------------------------------------
# Core fixture
# ---------------------------------------------------------------------------

@pytest.fixture()
def client():
    """
    Spin up a fresh schema, wire the app to the test DB via dependency
    override, and yield a synchronous TestClient.

    The override creates a NEW Session per request (matching production
    behaviour) while still using the shared in-memory SQLite.
    """
    Base.metadata.create_all(bind=test_engine)

    def override_get_db():
        db = TestSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=test_engine)


# ---------------------------------------------------------------------------
# Auth token fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def admin_token(client) -> str:
    """Register the first user (auto-promoted to ADMIN) and return their JWT."""
    client.post(
        "/auth/register",
        json={"email": "admin@test.com", "name": "Admin User", "password": "password123"},
    )
    res = client.post("/auth/login", json={"email": "admin@test.com", "password": "password123"})
    assert res.status_code == 200, f"Admin login failed: {res.json()}"
    return res.json()["access_token"]


@pytest.fixture()
def viewer_token(client, admin_token) -> str:
    """Admin creates a VIEWER account; return that user's JWT."""
    r = client.post(
        "/users",
        json={"email": "viewer@test.com", "name": "Viewer User", "password": "password123", "role": "viewer"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 201, f"Viewer creation failed: {r.json()}"
    res = client.post("/auth/login", json={"email": "viewer@test.com", "password": "password123"})
    assert res.status_code == 200, f"Viewer login failed: {res.json()}"
    return res.json()["access_token"]


@pytest.fixture()
def analyst_token(client, admin_token) -> str:
    """Admin creates an ANALYST account; return that user's JWT."""
    r = client.post(
        "/users",
        json={"email": "analyst@test.com", "name": "Analyst User", "password": "password123", "role": "analyst"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 201, f"Analyst creation failed: {r.json()}"
    res = client.post("/auth/login", json={"email": "analyst@test.com", "password": "password123"})
    assert res.status_code == 200, f"Analyst login failed: {res.json()}"
    return res.json()["access_token"]


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def create_transaction(client, token: str, **overrides):
    """POST a transaction as the given user; returns the Response object."""
    payload = {
        "amount": 100.0,
        "type": "income",
        "category": "Salary",
        "date": "2024-01-15",
        "notes": "Monthly salary",
        **overrides,
    }
    return client.post(
        "/transactions",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
