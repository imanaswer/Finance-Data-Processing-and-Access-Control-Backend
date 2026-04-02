from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import APP_NAME, APP_VERSION
from app.database import Base, engine
from app.routers import auth, dashboard, transactions, users

# Create all tables on startup (idempotent — safe to call repeatedly)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description=(
        "Finance Dashboard backend with JWT authentication and role-based access control.\n\n"
        "**Roles**\n"
        "- `viewer` — read-only access to transaction records\n"
        "- `analyst` — read access + dashboard analytics\n"
        "- `admin` — full access including create/update/delete and user management\n\n"
        "Authenticate via `POST /auth/login`, then pass the token as `Authorization: Bearer <token>`."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(transactions.router)
app.include_router(dashboard.router)


@app.get("/", tags=["Health"], summary="Health check")
def health_check():
    return {"status": "ok", "app": APP_NAME, "version": APP_VERSION}
