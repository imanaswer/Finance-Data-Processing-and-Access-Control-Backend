from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import JWTError

from app.database import get_db
from app.core.security import decode_token
from app.models.user import User, UserRole

bearer_scheme = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Decode the JWT and return the authenticated User, or raise 401."""
    token = credentials.credentials
    try:
        payload = decode_token(token)
        user_id: int = int(payload.get("sub"))
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or deactivated")
    return user


def require_roles(*roles: UserRole):
    """
    Factory that returns a dependency enforcing role membership.

    Usage:
        Depends(require_roles(UserRole.ADMIN))
        Depends(require_analyst)        # pre-built shortcut
    """
    def _check(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            allowed = [r.value for r in roles]
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Requires one of: {allowed}",
            )
        return current_user

    return _check


# ---------------------------------------------------------------------------
# Pre-built role guards (use these in routers for clarity)
# ---------------------------------------------------------------------------

# Every authenticated and active user (viewer, analyst, admin)
require_viewer = require_roles(UserRole.VIEWER, UserRole.ANALYST, UserRole.ADMIN)

# Analyst tier and above
require_analyst = require_roles(UserRole.ANALYST, UserRole.ADMIN)

# Admin only
require_admin = require_roles(UserRole.ADMIN)