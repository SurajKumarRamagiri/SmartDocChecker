"""
Shared FastAPI dependencies.
"""
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from slowapi import Limiter
from slowapi.util import get_remote_address

from core.security import oauth2_scheme
from core.jwt_handler import decode_access_token, JWTError
from db.session import SessionLocal
from models.user import User
from config import settings

# ── Shared rate limiter (single instance for the whole app) ──
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[settings.RATE_LIMIT_DEFAULT],
)


def get_db():
    """Yield a SQLAlchemy session, closing it after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> dict:
    """Decode JWT, verify user still exists in DB, and return user info."""
    credentials_exception = HTTPException(
        status_code=401,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        email: str = payload.get("sub")
        user_id: int = payload.get("user_id")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    # Verify user still exists (handles deleted / deactivated accounts)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=401,
            detail="User account not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {"email": user.email, "name": user.name, "user_id": user.id}
