"""
Tests for /transactions endpoints — CRUD, filters, search, pagination, RBAC.
"""
from tests.conftest import create_transaction


# ---------------------------------------------------------------------------
# RBAC
# ---------------------------------------------------------------------------

def test_admin_can_create_transaction(client, admin_token):
    res = create_transaction(client, admin_token)
    assert res.status_code == 201
    data = res.json()
    assert data["amount"] == 100.0
    assert data["category"] == "Salary"
    assert data["type"] == "income"


def test_viewer_cannot_create_transaction(client, viewer_token):
    res = create_transaction(client, viewer_token)
    assert res.status_code == 403


def test_analyst_cannot_create_transaction(client, analyst_token):
    res = create_transaction(client, analyst_token)
    assert res.status_code == 403


def test_viewer_can_read_transactions(client, admin_token, viewer_token):
    create_transaction(client, admin_token)
    res = client.get("/transactions", headers={"Authorization": f"Bearer {viewer_token}"})
    assert res.status_code == 200


def test_viewer_cannot_update_transaction(client, admin_token, viewer_token):
    txn_id = create_transaction(client, admin_token).json()["id"]
    res = client.put(
        f"/transactions/{txn_id}",
        json={"amount": 999},
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert res.status_code == 403


def test_viewer_cannot_delete_transaction(client, admin_token, viewer_token):
    txn_id = create_transaction(client, admin_token).json()["id"]
    res = client.delete(
        f"/transactions/{txn_id}",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert res.status_code == 403


# ---------------------------------------------------------------------------
# CRUD correctness
# ---------------------------------------------------------------------------

def test_get_transaction_by_id(client, admin_token):
    txn_id = create_transaction(client, admin_token).json()["id"]
    res = client.get(f"/transactions/{txn_id}", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    assert res.json()["id"] == txn_id


def test_get_nonexistent_transaction_returns_404(client, admin_token):
    res = client.get("/transactions/99999", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 404


def test_update_transaction_amount(client, admin_token):
    txn_id = create_transaction(client, admin_token, amount=100.0).json()["id"]
    res = client.put(
        f"/transactions/{txn_id}",
        json={"amount": 250.0},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 200
    assert res.json()["amount"] == 250.0


def test_update_nonexistent_transaction_returns_404(client, admin_token):
    res = client.put(
        "/transactions/99999",
        json={"amount": 1.0},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 404


def test_soft_delete_hides_transaction(client, admin_token):
    txn_id = create_transaction(client, admin_token).json()["id"]

    del_res = client.delete(
        f"/transactions/{txn_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert del_res.status_code == 204

    # Should now be 404 from both the single-item and list endpoints
    get_res = client.get(f"/transactions/{txn_id}", headers={"Authorization": f"Bearer {admin_token}"})
    assert get_res.status_code == 404

    list_res = client.get("/transactions", headers={"Authorization": f"Bearer {admin_token}"})
    ids = [t["id"] for t in list_res.json()["items"]]
    assert txn_id not in ids


def test_create_transaction_with_negative_amount_returns_422(client, admin_token):
    res = create_transaction(client, admin_token, amount=-50)
    assert res.status_code == 422


def test_create_transaction_with_zero_amount_returns_422(client, admin_token):
    res = create_transaction(client, admin_token, amount=0)
    assert res.status_code == 422


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------

def test_pagination_total_and_pages(client, admin_token):
    for i in range(7):
        create_transaction(client, admin_token, amount=float(i + 1) * 10, category=f"Cat{i}")

    headers = {"Authorization": f"Bearer {admin_token}"}
    res = client.get("/transactions?page=1&page_size=3", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 7
    assert data["total_pages"] == 3
    assert len(data["items"]) == 3


def test_pagination_second_page(client, admin_token):
    for i in range(5):
        create_transaction(client, admin_token, amount=float(i + 1) * 10)

    headers = {"Authorization": f"Bearer {admin_token}"}
    page1 = client.get("/transactions?page=1&page_size=3", headers=headers).json()["items"]
    page2 = client.get("/transactions?page=2&page_size=3", headers=headers).json()["items"]

    ids_p1 = {t["id"] for t in page1}
    ids_p2 = {t["id"] for t in page2}
    assert ids_p1.isdisjoint(ids_p2), "Pages must not overlap"


# ---------------------------------------------------------------------------
# Filters & search
# ---------------------------------------------------------------------------

def test_filter_by_type(client, admin_token):
    create_transaction(client, admin_token, type="income", amount=500)
    create_transaction(client, admin_token, type="expense", amount=200)

    headers = {"Authorization": f"Bearer {admin_token}"}
    res = client.get("/transactions?type=income", headers=headers)
    assert res.status_code == 200
    assert all(t["type"] == "income" for t in res.json()["items"])


def test_filter_by_category(client, admin_token):
    create_transaction(client, admin_token, category="Rent")
    create_transaction(client, admin_token, category="Groceries")

    headers = {"Authorization": f"Bearer {admin_token}"}
    res = client.get("/transactions?category=rent", headers=headers)
    assert res.json()["total"] == 1
    assert res.json()["items"][0]["category"] == "Rent"


def test_filter_by_date_range(client, admin_token):
    create_transaction(client, admin_token, date="2024-01-10", amount=100)
    create_transaction(client, admin_token, date="2024-06-15", amount=200)
    create_transaction(client, admin_token, date="2024-12-01", amount=300)

    headers = {"Authorization": f"Bearer {admin_token}"}
    res = client.get("/transactions?date_from=2024-03-01&date_to=2024-09-30", headers=headers)
    assert res.json()["total"] == 1
    assert res.json()["items"][0]["amount"] == 200.0


def test_search_by_notes(client, admin_token):
    create_transaction(client, admin_token, notes="Netflix subscription", category="Entertainment")
    create_transaction(client, admin_token, notes="Gym membership", category="Health")

    headers = {"Authorization": f"Bearer {admin_token}"}
    res = client.get("/transactions?search=netflix", headers=headers)
    assert res.json()["total"] == 1


def test_search_by_category(client, admin_token):
    create_transaction(client, admin_token, category="Transport", notes="Bus pass")
    create_transaction(client, admin_token, category="Food", notes="Lunch")

    headers = {"Authorization": f"Bearer {admin_token}"}
    res = client.get("/transactions?search=transport", headers=headers)
    assert res.json()["total"] == 1
