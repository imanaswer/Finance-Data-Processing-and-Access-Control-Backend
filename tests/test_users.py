"""
Tests for /users endpoints — covers CRUD operations and RBAC enforcement.
"""


def test_admin_can_list_users(client, admin_token):
    res = client.get("/users", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    assert isinstance(res.json(), list)
    assert len(res.json()) >= 1  # at least the admin user


def test_viewer_cannot_list_users(client, viewer_token):
    res = client.get("/users", headers={"Authorization": f"Bearer {viewer_token}"})
    assert res.status_code == 403


def test_analyst_cannot_list_users(client, analyst_token):
    res = client.get("/users", headers={"Authorization": f"Bearer {analyst_token}"})
    assert res.status_code == 403


def test_admin_can_create_user(client, admin_token):
    res = client.post(
        "/users",
        json={"email": "newuser@test.com", "name": "New User", "password": "pass123", "role": "analyst"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["email"] == "newuser@test.com"
    assert data["role"] == "analyst"


def test_create_user_duplicate_email_returns_400(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    payload = {"email": "dup@test.com", "name": "D", "password": "pass123", "role": "viewer"}
    client.post("/users", json=payload, headers=headers)
    res = client.post("/users", json=payload, headers=headers)
    assert res.status_code == 400


def test_admin_can_get_user_by_id(client, admin_token, viewer_token):
    users = client.get("/users", headers={"Authorization": f"Bearer {admin_token}"}).json()
    viewer = next(u for u in users if u["email"] == "viewer@test.com")
    res = client.get(f"/users/{viewer['id']}", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    assert res.json()["email"] == "viewer@test.com"


def test_get_nonexistent_user_returns_404(client, admin_token):
    res = client.get("/users/99999", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 404


def test_admin_can_update_user_role(client, admin_token, viewer_token):
    users = client.get("/users", headers={"Authorization": f"Bearer {admin_token}"}).json()
    viewer = next(u for u in users if u["email"] == "viewer@test.com")

    res = client.put(
        f"/users/{viewer['id']}",
        json={"role": "analyst"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 200
    assert res.json()["role"] == "analyst"


def test_admin_can_deactivate_user(client, admin_token, viewer_token):
    users = client.get("/users", headers={"Authorization": f"Bearer {admin_token}"}).json()
    viewer = next(u for u in users if u["email"] == "viewer@test.com")

    res = client.delete(f"/users/{viewer['id']}", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 204

    # Verify is_active is now False
    user_data = client.get(f"/users/{viewer['id']}", headers={"Authorization": f"Bearer {admin_token}"}).json()
    assert user_data["is_active"] is False


def test_admin_cannot_deactivate_own_account(client, admin_token):
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {admin_token}"}).json()
    res = client.delete(f"/users/{me['id']}", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 400
