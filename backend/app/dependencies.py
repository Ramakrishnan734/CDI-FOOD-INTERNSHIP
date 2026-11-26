# backend/app/dependencies.py

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# Existing database role values; keep these stable for current users and JWTs.
ROLE_VALUES = frozenset({"salesman", "admin", "production", "auditor", "owner"})

# HTTPBearer reads the "Authorization: Bearer <token>" header automatically
bearer_scheme = HTTPBearer()


def get_db():
    """
    Provides a database connection to route handlers.
    Connection is returned to the pool after the request completes.
    """
    from app.database import engine
    with engine.connect() as conn:
        yield conn


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
):
    """
    Extracts and validates the JWT from the Authorization header.
    Returns the token payload: { sub, name, role }

    Usage in a route:
        @router.get("/something")
        def my_route(user=Depends(get_current_user)):
            if user["role"] != "admin":
                raise HTTPException(403, "Forbidden")
    """
    # Import here to avoid circular import
    from app.routers.auth import decode_token
    return decode_token(credentials.credentials)


def require_role(*roles: str):
    """
    Factory that returns a dependency enforcing role-based access.

    Usage:
        @router.post("/approve")
        def approve(user=Depends(require_role("admin"))):
            ...
    """
    def _check(user=Depends(get_current_user)):
        if user["role"] not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role: {list(roles)}"
            )
        return user
    _check.required_roles = frozenset(roles)
    return _check