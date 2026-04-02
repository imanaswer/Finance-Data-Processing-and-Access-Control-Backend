# Finance Dashboard API

A backend for a finance dashboard system built with **FastAPI**, **SQLAlchemy**, and **SQLite**. It supports financial record management, role-based access control (RBAC), JWT authentication, and summary-level analytics.

---

## Table of Contents

- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Setup and Running](#setup-and-running)
- [Running Tests](#running-tests)
- [Role Model and Access Control](#role-model-and-access-control)
- [API Reference](#api-reference)
- [Assumptions and Design Decisions](#assumptions-and-design-decisions)

---

## Tech Stack

| Concern        | Choice                               |
|----------------|--------------------------------------|
| Framework      | FastAPI                              |
| Database       | SQLite via SQLAlchemy ORM            |
| Auth           | JWT (python-jose) + bcrypt passwords |
| Validation     | Pydantic v2                          |
| Testing        | pytest + httpx TestClient            |

---

## Project Structure

```
finance_backend/
├── app/
│   ├── main.py               # App factory, router registration, DB init
│   ├── database.py           # SQLAlchemy engine, session, Base
│   ├── core/
│   │   ├── config.py         # Environment-based settings
│   │   ├── security.py       # Password hashing, JWT encode/decode
│   │   └── dependencies.py   # FastAPI dependency factories for RBAC
│   ├── models/
│   │   ├── user.py           # User ORM model + UserRole enum
│   │   └── transaction.py    # Transaction ORM model + TransactionType enum
│   ├── schemas/
│   │   ├── user.py           # Pydantic schemas for users and auth tokens
│   │   └── transaction.py    # Pydantic schemas for transactions and pagination
│   └── routers/
│       ├── auth.py           # POST /auth/register, /auth/login, GET /auth/me
│       ├── users.py          # CRUD for /users (Admin only)
│       ├── transactions.py   # CRUD for /transactions with filters + pagination
│       └── dashboard.py      # Analytics: summary, categories, trends, recent
└── tests/
    ├── conftest.py           # Fixtures: isolated DB, TestClient, role tokens
    ├── test_auth.py
    ├── test_users.py
    ├── test_transactions.py
    └── test_dashboard.py
```

---

## Setup and Running

### 1. Clone and create a virtual environment

```bash
git clone <repo-url>
cd finance_backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

```bash
cp .env.example .env
# Edit .env and set a strong SECRET_KEY for production
```

| Variable                     | Default                         | Description                          |
|------------------------------|---------------------------------|--------------------------------------|
| `SECRET_KEY`                 | `dev-secret-key-...`            | JWT signing secret — **change this** |
| `ACCESS_TOKEN_EXPIRE_MINUTES`| `1440` (24 hours)               | JWT lifetime                         |
| `DATABASE_URL`               | `sqlite:///./finance.db`        | SQLAlchemy connection string         |

### 4. Start the server

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`.

Interactive API docs are available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc:       `http://localhost:8000/redoc`

### 5. Bootstrap an admin account

The **first user to register** is automatically promoted to `admin`. Subsequent registrations respect the `role` field in the request body.

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "name": "Admin", "password": "secure123"}'
```

---

## Running Tests

Each test function runs against a fresh, isolated SQLite database (`test_finance.db`) that is created before the test and dropped afterwards. Tests can run in any order.

```bash
pytest -v
```

Expected output:

```
tests/test_auth.py::test_first_user_is_promoted_to_admin         PASSED
tests/test_auth.py::test_login_success_returns_token              PASSED
...
tests/test_dashboard.py::test_summary_totals_are_correct          PASSED
...
36 passed in ~5s
```

---

## Role Model and Access Control

Three roles are supported, each a superset of the one above it:

| Role       | Transactions        | Dashboard analytics | User management |
|------------|---------------------|---------------------|-----------------|
| `viewer`   | Read only           | ✗                   | ✗               |
| `analyst`  | Read only           | ✓                   | ✗               |
| `admin`    | Full CRUD           | ✓                   | Full CRUD       |

RBAC is enforced via FastAPI dependency injection. The `require_roles()` factory in `app/core/dependencies.py` returns a dependency function that checks the authenticated user's role before the route handler runs. Pre-built shortcuts (`require_viewer`, `require_analyst`, `require_admin`) are used throughout the routers for readability.

```python
# Example: admin-only route
@router.post("/transactions")
def create_transaction(
    payload: TransactionCreate,
    current_user: User = Depends(require_admin),   # ← enforced here
    db: Session = Depends(get_db),
):
    ...
```

---

## API Reference

All protected routes require:
```
Authorization: Bearer <token>
```

### Authentication

| Method | Path              | Access | Description                           |
|--------|-------------------|--------|---------------------------------------|
| POST   | `/auth/register`  | Public | Register a new user; returns JWT      |
| POST   | `/auth/login`     | Public | Authenticate; returns JWT             |
| GET    | `/auth/me`        | All    | Return current user's profile         |

### Users

| Method | Path            | Access | Description                           |
|--------|-----------------|--------|---------------------------------------|
| GET    | `/users`        | Admin  | List all users                        |
| GET    | `/users/{id}`   | Admin  | Get user by ID                        |
| POST   | `/users`        | Admin  | Create a user with a specific role    |
| PUT    | `/users/{id}`   | Admin  | Update name, role, or active status   |
| DELETE | `/users/{id}`   | Admin  | Deactivate a user (soft delete)       |

### Transactions

| Method | Path                    | Access   | Description                              |
|--------|-------------------------|----------|------------------------------------------|
| GET    | `/transactions`         | Viewer+  | List with filters, search, and pagination |
| GET    | `/transactions/{id}`    | Viewer+  | Get single transaction                   |
| POST   | `/transactions`         | Admin    | Create a new record                      |
| PUT    | `/transactions/{id}`    | Admin    | Update a record (partial update)         |
| DELETE | `/transactions/{id}`    | Admin    | Soft-delete a record                     |

**Query parameters for `GET /transactions`:**

| Parameter   | Type   | Description                              |
|-------------|--------|------------------------------------------|
| `page`      | int    | Page number (default: 1)                 |
| `page_size` | int    | Items per page, max 100 (default: 20)    |
| `type`      | string | `income` or `expense`                    |
| `category`  | string | Partial match, case-insensitive          |
| `date_from` | date   | Start of date range (`YYYY-MM-DD`)       |
| `date_to`   | date   | End of date range (`YYYY-MM-DD`)         |
| `search`    | string | Full-text search across category + notes |

### Dashboard

| Method | Path                        | Access    | Description                              |
|--------|-----------------------------|-----------|------------------------------------------|
| GET    | `/dashboard/summary`        | Analyst+  | Total income, expenses, net balance      |
| GET    | `/dashboard/categories`     | Analyst+  | Totals grouped by category and type      |
| GET    | `/dashboard/trends/monthly` | Analyst+  | Monthly income vs expense over time      |
| GET    | `/dashboard/recent`         | Analyst+  | N most recent transactions               |

`/dashboard/summary` and `/dashboard/categories` accept optional `date_from` and `date_to` query parameters. `/dashboard/trends/monthly` accepts an optional `year` parameter.

---

## Assumptions and Design Decisions

**First-user bootstrap**
There is no out-of-band admin seeding step. The very first `POST /auth/register` call always produces an admin account, regardless of the `role` field sent. This eliminates the chicken-and-egg problem of needing an admin to create an admin.

**Soft delete**
Both transactions and users are never permanently removed. Transactions have an `is_deleted` flag; users have an `is_active` flag. This preserves audit history and avoids orphaned foreign keys.

**Admin self-deactivation guard**
`DELETE /users/{id}` returns `400` when the authenticated admin tries to deactivate their own account, preventing an accidental complete lock-out of the system.

**Analyst vs Viewer on dashboard**
Viewers can read raw records (useful for a simple display table) but are excluded from analytics endpoints. This reflects a realistic split between a read-only stakeholder (viewer) and someone performing analysis (analyst).

**SQLite**
Chosen for zero-configuration local development. The `DATABASE_URL` environment variable makes it trivial to swap in PostgreSQL or another SQLAlchemy-compatible database for production.

**Partial updates**
`PUT` endpoints use `model_dump(exclude_unset=True)` so clients can send only the fields they want to change without overwriting others.

**Pagination response shape**
```json
{
  "total": 42,
  "page": 1,
  "page_size": 20,
  "total_pages": 3,
  "items": [...]
}
```
`total_pages` is included so frontends can render pagination controls without an extra request.

**No rate limiting**
Rate limiting is a cross-cutting infrastructure concern (typically handled by a reverse proxy like nginx or a gateway) and is out of scope for this assignment.
# Finance-Data-Processing-and-Access-Control-Backend
