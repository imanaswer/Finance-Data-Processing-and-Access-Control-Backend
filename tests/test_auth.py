"""
Tests for /auth endpoints: registration, login, JWT, and the /auth/me shortcut.
"""


def test_first_user_is_promoted_to_admin(client):
    res = client.post(
        "/auth/register",
        json={"email": "first@test.com", "name": "First", "password": "password123", "role": "viewer"},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["user"]["role"] == "admin", "First registered user must be admin"
    assert "access_token" in data


def test_subsequent_user_keeps_requested_role(client):
    # Create admin (first user)
    client.post("/auth/register", json={"email": "a@test.com", "name": "A", "password": "pass123"})
    # Second user requests viewer role
    res = client.post(
        "/auth/register",
        json={"email": "b@test.com", "name": "B", "password": "pass123", "role": "viewer"},
    )
    assert res.status_code == 201
    assert res.json()["user"]["role"] == "viewer"


def test_register_duplicate_email_returns_400(client):
    client.post("/auth/register", json={"email": "dup@test.com", "name": "A", "password": "pass123"})
    res = client.post("/auth/register", json={"email": "dup@test.com", "name": "B", "password": "pass456"})
    assert res.status_code == 400


def test_register_short_password_returns_422(client):
    res = client.post(
        "/auth/register",
        json={"email": "x@test.com", "name": "X", "password": "abc"},  # < 6 chars
    )
    assert res.status_code == 422


def test_login_success_returns_token(client):
    client.post("/auth/register", json={"email": "u@test.com", "name": "U", "password": "secret99"})
    res = client.post("/auth/login", json={"email": "u@test.com", "password": "secret99"})
    assert res.status_code == 200
    assert "access_token" in res.json()
    assert res.json()["token_type"] == "bearer"


def test_login_wrong_password_returns_401(client):
    client.post("/auth/register", json={"email": "u@test.com", "name": "U", "password": "correct"})
    res = client.post("/auth/login", json={"email": "u@test.com", "password": "wrong"})
    assert res.status_code == 401


def test_login_unknown_email_returns_401(client):
    res = client.post("/auth/login", json={"email": "ghost@test.com", "password": "pass"})
    assert res.status_code == 401


def test_protected_route_without_token_returns_403(client):
    res = client.get("/users")
    assert res.status_code == 403


def test_protected_route_with_invalid_token_returns_401(client):
    res = client.get("/users/me", headers={"Authorization": "Bearer notavalidtoken"})
    assert res.status_code == 401


def test_get_me_returns_current_user(client, admin_token):
    res = client.get("/auth/me", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    assert res.json()["email"] == "admin@test.com"


def test_deactivated_user_cannot_login(client, admin_token):
    # Create viewer then deactivate them
    client.post(
        "/users",
        json={"email": "bye@test.com", "name": "Bye", "password": "pass123", "role": "viewer"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    users = client.get("/users", headers={"Authorization": f"Bearer {admin_token}"}).json()
    uid = next(u["id"] for u in users if u["email"] == "bye@test.com")
    client.delete(f"/users/{uid}", headers={"Authorization": f"Bearer {admin_token}"})

    res = client.post("/auth/login", json={"email": "bye@test.com", "password": "pass123"})
    assert res.status_code == 403
