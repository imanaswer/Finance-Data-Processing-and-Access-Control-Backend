"""
Tests for /dashboard endpoints — summary, categories, trends, recent, RBAC.
"""
from tests.conftest import create_transaction


# ---------------------------------------------------------------------------
# RBAC — viewers are blocked from all dashboard routes
# ---------------------------------------------------------------------------

def test_viewer_cannot_access_summary(client, viewer_token):
    res = client.get("/dashboard/summary", headers={"Authorization": f"Bearer {viewer_token}"})
    assert res.status_code == 403


def test_viewer_cannot_access_categories(client, viewer_token):
    res = client.get("/dashboard/categories", headers={"Authorization": f"Bearer {viewer_token}"})
    assert res.status_code == 403


def test_viewer_cannot_access_trends(client, viewer_token):
    res = client.get("/dashboard/trends/monthly", headers={"Authorization": f"Bearer {viewer_token}"})
    assert res.status_code == 403


def test_viewer_cannot_access_recent(client, viewer_token):
    res = client.get("/dashboard/recent", headers={"Authorization": f"Bearer {viewer_token}"})
    assert res.status_code == 403


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

def test_summary_totals_are_correct(client, admin_token, analyst_token):
    create_transaction(client, admin_token, amount=1000, type="income",  category="Salary")
    create_transaction(client, admin_token, amount=300,  type="expense", category="Rent")
    create_transaction(client, admin_token, amount=200,  type="expense", category="Food")

    res = client.get("/dashboard/summary", headers={"Authorization": f"Bearer {analyst_token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["total_income"] == 1000.0
    assert data["total_expenses"] == 500.0
    assert data["net_balance"] == 500.0
    assert data["transaction_count"] == 3


def test_summary_with_date_filter(client, admin_token, analyst_token):
    create_transaction(client, admin_token, amount=500,  type="income",  date="2024-01-10")
    create_transaction(client, admin_token, amount=200,  type="expense", date="2024-06-01")
    create_transaction(client, admin_token, amount=1000, type="income",  date="2024-12-25")

    # Only the June expense falls in the window
    res = client.get(
        "/dashboard/summary?date_from=2024-05-01&date_to=2024-07-31",
        headers={"Authorization": f"Bearer {analyst_token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total_expenses"] == 200.0
    assert data["total_income"] == 0.0
    assert data["transaction_count"] == 1


def test_summary_empty_database(client, analyst_token):
    res = client.get("/dashboard/summary", headers={"Authorization": f"Bearer {analyst_token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["total_income"] == 0.0
    assert data["total_expenses"] == 0.0
    assert data["net_balance"] == 0.0


# ---------------------------------------------------------------------------
# Category breakdown
# ---------------------------------------------------------------------------

def test_category_breakdown_aggregates_correctly(client, admin_token, analyst_token):
    create_transaction(client, admin_token, amount=500, category="Salary",   type="income")
    create_transaction(client, admin_token, amount=100, category="Food",     type="expense")
    create_transaction(client, admin_token, amount=150, category="Food",     type="expense")

    res = client.get("/dashboard/categories", headers={"Authorization": f"Bearer {analyst_token}"})
    assert res.status_code == 200

    rows = {(r["category"], r["type"]): r for r in res.json()}
    assert rows[("Food", "expense")]["total"] == 250.0
    assert rows[("Food", "expense")]["count"] == 2
    assert rows[("Salary", "income")]["total"] == 500.0


# ---------------------------------------------------------------------------
# Monthly trends
# ---------------------------------------------------------------------------

def test_monthly_trends_structure(client, admin_token, analyst_token):
    create_transaction(client, admin_token, amount=500,  type="income",  date="2024-01-10")
    create_transaction(client, admin_token, amount=200,  type="expense", date="2024-01-20")
    create_transaction(client, admin_token, amount=700,  type="income",  date="2024-02-05")

    res = client.get(
        "/dashboard/trends/monthly?year=2024",
        headers={"Authorization": f"Bearer {analyst_token}"},
    )
    assert res.status_code == 200
    pivot = {row["month"]: row for row in res.json()}

    assert pivot["2024-01"]["income"] == 500.0
    assert pivot["2024-01"]["expense"] == 200.0
    assert pivot["2024-02"]["income"] == 700.0
    assert pivot["2024-02"].get("expense", 0.0) == 0.0


def test_monthly_trends_without_year_filter(client, admin_token, analyst_token):
    create_transaction(client, admin_token, amount=100, date="2023-06-01")
    create_transaction(client, admin_token, amount=200, date="2024-03-15")

    res = client.get("/dashboard/trends/monthly", headers={"Authorization": f"Bearer {analyst_token}"})
    assert res.status_code == 200
    months = [row["month"] for row in res.json()]
    assert "2023-06" in months
    assert "2024-03" in months


# ---------------------------------------------------------------------------
# Recent activity
# ---------------------------------------------------------------------------

def test_recent_returns_latest_transactions(client, admin_token, analyst_token):
    for i in range(5):
        create_transaction(client, admin_token, amount=float(i + 1) * 10, date=f"2024-0{i + 1}-01")

    res = client.get("/dashboard/recent?limit=3", headers={"Authorization": f"Bearer {analyst_token}"})
    assert res.status_code == 200
    items = res.json()
    assert len(items) == 3
    # Most recent date first
    dates = [item["date"] for item in items]
    assert dates == sorted(dates, reverse=True)


def test_recent_limit_is_enforced(client, admin_token, analyst_token):
    for i in range(20):
        create_transaction(client, admin_token, amount=10.0)

    res = client.get("/dashboard/recent?limit=5", headers={"Authorization": f"Bearer {analyst_token}"})
    assert len(res.json()) == 5


def test_analyst_can_access_all_dashboard_routes(client, analyst_token):
    headers = {"Authorization": f"Bearer {analyst_token}"}
    assert client.get("/dashboard/summary",        headers=headers).status_code == 200
    assert client.get("/dashboard/categories",     headers=headers).status_code == 200
    assert client.get("/dashboard/trends/monthly", headers=headers).status_code == 200
    assert client.get("/dashboard/recent",         headers=headers).status_code == 200
