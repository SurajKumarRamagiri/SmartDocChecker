"""
Authentication API routes.
"""
import logging
from fastapi import APIRouter, HTTPException, Depends, Request
from sqlalchemy.orm import Session

from schemas.user_schema import UserRegister, UserLogin, UserOut, TokenResponse
from core.hashing import hash_password, verify_password
from core.jwt_handler import create_access_token
from dependencies import get_current_user, get_db, limiter
from models.user import User
from config import settings

logger = logging.getLogger(__name__)

# Pre-computed dummy hash for constant-time login (prevents email enumeration)
_DUMMY_HASH = hash_password("dummy-password-for-timing")

router = APIRouter(prefix="/api/auth", tags=["Auth"])


@router.post("/register", response_model=TokenResponse)
@limiter.limit(settings.RATE_LIMIT_AUTH)
async def register(request: Request, body: UserRegister, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == body.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        name=body.name,
        email=body.email,
        hashed_password=hash_password(body.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": user.email, "name": user.name, "user_id": user.id})
    logger.info(f"New user registered: id={user.id}")

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserOut(name=user.name, email=user.email),
    )


@router.post("/login", response_model=TokenResponse)
@limiter.limit(settings.RATE_LIMIT_AUTH)
async def login(request: Request, body: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()
    if not user:
        # Always run verify_password to prevent timing-based email enumeration
        verify_password(body.password, _DUMMY_HASH)
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token({"sub": user.email, "name": user.name, "user_id": user.id})
    logger.info(f"User logged in: id={user.id}")

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserOut(name=user.name, email=user.email),
    )


@router.get("/me", response_model=UserOut)
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """Return the current authenticated user info."""
    return UserOut(name=current_user["name"], email=current_user["email"])
