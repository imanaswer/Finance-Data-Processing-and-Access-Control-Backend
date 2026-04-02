# Finance Dashboard API

A REST API for managing personal or small-business finances. Handles transactions, user accounts with role-based permissions, and a dashboard layer for aggregated reporting.

Built with FastAPI + SQLAlchemy. SQLite out of the box, swappable for Postgres with a one-line config change.

---

## What it does

- **Auth** — register, login, JWT tokens, `/me` endpoint
- **Users** — admin can create accounts and assign roles (viewer / analyst / admin), soft-deactivate them
- **Transactions** — create, read, update, soft-delete financial records. Paginated listing with filters for type, category, date range, and free-text search
- **Dashboard** — summary totals, category breakdown, monthly trends, recent activity. Analyst and admin only.

The first user to register automatically becomes admin — no bootstrapping step needed.

---

## Roles

| Role | What they can do |
|---|---|
| `viewer` | Read transactions |
| `analyst` | Read transactions + access all dashboard routes |
| `admin` | Everything — create/edit/delete transactions, manage users |

---

## Getting started

```bash

cd finance_backend

python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env       # set your SECRET_KEY here
```

Start the server:

```bash
uvicorn app.main:app --reload
```

API is at `http://localhost:8000`. Swagger docs at `http://localhost:8000/docs`.

The SQLite database file is created automatically on first run.

---

## Environment variables

```
SECRET_KEY=your-secret-here          # change this, don't leave the default
ACCESS_TOKEN_EXPIRE_MINUTES=1440     # 24h default
DATABASE_URL=sqlite:///./finance.db  # swap for postgresql://... in prod
```

---

## API overview

```
POST   /auth/register
POST   /auth/login
GET    /auth/me

GET    /users              # admin only
POST   /users              # admin only
GET    /users/{id}         # admin only
PUT    /users/{id}         # admin only
DELETE /users/{id}         # admin only — soft deactivate

GET    /transactions       # viewer+, supports pagination and filters
POST   /transactions       # admin only
GET    /transactions/{id}  # viewer+
PUT    /transactions/{id}  # admin only
DELETE /transactions/{id}  # admin only — soft delete

GET    /dashboard/summary          # analyst+
GET    /dashboard/categories       # analyst+
GET    /dashboard/trends/monthly   # analyst+
GET    /dashboard/recent           # analyst+
```

Full request/response schemas are in the Swagger UI at `/docs`.

---

## Running tests

```bash
pytest -v
```

54 tests covering auth, user management, transactions, and dashboard endpoints. Each test runs against a fresh in-memory SQLite instance so they're fully isolated.

---

## Project structure

```
app/
  core/
    config.py        # env vars
    security.py      # JWT creation and verification
    dependencies.py  # FastAPI auth dependencies / role guards
  models/
    user.py
    transaction.py
  routers/
    auth.py
    users.py
    transactions.py
    dashboard.py
  schemas/
    user.py
    transaction.py
  database.py
  main.py
tests/
  conftest.py
  test_auth.py
  test_users.py
  test_transactions.py
  test_dashboard.py
```

---

## Notes

Soft deletes are used for both transactions and user deactivation. Records are never removed from the database — deleted transactions are just excluded from all queries, and deactivated users can't log in but their data stays intact.

Admins can't deactivate their own account (to avoid accidental lockout).

Token expiry is validated on every request against the live database, so deactivating a user takes effect immediately even if they still hold a valid token.
