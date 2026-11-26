# backend/app/routers/auth.py
import os

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from pydantic import BaseModel
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import bcrypt
from jose import jwt

from app.dependencies import get_db, ROLE_VALUES

router = APIRouter(prefix="/auth", tags=["auth"])

# -----------------------------------------------------------------
# Configuration
# JWT secret must be provided through the environment.
# Validate it immediately when the application imports this module.
# -----------------------------------------------------------------

def get_secret_key() -> str:
    secret_key = os.getenv("SECRET_KEY")

    if not secret_key:
        raise RuntimeError("SECRET_KEY environment variable is required")

    if len(secret_key) < 32:
        raise RuntimeError("SECRET_KEY must be at least 32 characters long")

    return secret_key


SECRET_KEY = get_secret_key()
ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 12


# -----------------------------------------------------------------
# Pydantic schemas — defines the shape of request and response JSON
# -----------------------------------------------------------------

class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    token: str
    user_id: int
    name: str
    role: str


# -----------------------------------------------------------------
# Helper: create a JWT token
# -----------------------------------------------------------------

def create_token(user_id: int, name: str, role: str) -> str:
    """
    Creates a signed JWT token containing user_id, name, and role.
    Token expires after TOKEN_EXPIRE_HOURS hours.
    """
    expire = datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRE_HOURS)
    payload = {
        "sub": str(user_id),   # 'sub' = subject — standard JWT claim
        "name": name,
        "role": role,
        "exp": expire
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


# -----------------------------------------------------------------
# Helper: verify a JWT token (used by protected routes)
# -----------------------------------------------------------------

def decode_token(token: str) -> dict:
    """
    Decodes and validates a JWT token.
    Raises HTTPException if invalid or expired.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("role") not in ROLE_VALUES or not payload.get("sub"):
            raise ValueError("Invalid token role or subject")
        return payload
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )


# -----------------------------------------------------------------
# POST /auth/login
# -----------------------------------------------------------------

@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest, conn=Depends(get_db)):
    """
    Accepts email + password.
    Returns a JWT token if credentials are valid.
    """
    # 1. Find user by email
    row = conn.execute(
        text("SELECT id, name, email, password_hash, role, is_active "
             "FROM users WHERE email = :email"),
        {"email": body.email}
    ).fetchone()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    # 2. Check account is active
    if not row.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive"
        )

    # 3. Verify password
    # bcrypt.checkpw needs bytes
    password_matches = bcrypt.checkpw(
        body.password.encode("utf-8"),
        row.password_hash.encode("utf-8")
    )

    if not password_matches:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    # 4. Create and return token
    token = create_token(row.id, row.name, row.role)

    return LoginResponse(
        token=token,
        user_id=row.id,
        name=row.name,
        role=row.role
    )