"""
SmartDocChecker API — Application entrypoint.

This file creates the FastAPI app, attaches middleware, and includes
all sub-routers.  Run with:
    uvicorn main:app --reload
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

import os

from config import settings
from api.router import api_router
from db.session import engine, SessionLocal
from db.base import Base
from dependencies import limiter

# ── Import models so Base.metadata knows about them ──
from models.user import User
from models.document import Document
from models.contradiction import Contradiction
from models.clause import Clause
from models.comparison import ComparisonSession
from models.cross_contradiction import CrossContradiction

# ── Logging ──
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ── Lifespan: startup & shutdown logic ──
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: create tables, warm models, seed admin."""
    try:
        logger.info("Creating database tables (if they don't exist)…")
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        logger.error(f"Database table creation failed: {e}")
        logger.warning("App will start without DB — some endpoints may fail.")

    from core.hashing import hash_password

    db = SessionLocal()
    try:
        # ── Model Warming ──
        logger.info("Warming AI models…")
        try:
            from services.embedding_service import _load_sbert_model
            from services.nli_service import _load_nli_model
            _load_sbert_model()
            _load_nli_model()
            logger.info("AI models warmed and ready.")
        except Exception as e:
            logger.error(f"Model warming failed: {e}")
            logger.warning("App will start without pre-loaded models.")

        try:
            admin = db.query(User).filter(User.email == "admin@smartdoc.com").first()
            if not admin:
                admin_password = os.environ.get("ADMIN_PASSWORD")
                if not admin_password:
                    if settings.DEBUG:
                        admin_password = "Admin123!"
                        logger.warning(
                            "⚠  ADMIN_PASSWORD not set — using insecure default (DEBUG mode only)"
                        )
                    else:
                        logger.warning(
                            "⚠  ADMIN_PASSWORD env var not set. "
                            "Skipping admin seed in production."
                        )
                if admin_password:
                    admin = User(
                        name="Admin",
                        email="admin@smartdoc.com",
                        hashed_password=hash_password(admin_password),
                    )
                    db.add(admin)
                    db.commit()
                    logger.info("Seeded default admin user: admin@smartdoc.com")
            else:
                logger.info("Admin user already exists, skipping seed.")
        except Exception as e:
            logger.error(f"Admin seeding failed: {e}")
    finally:
        db.close()

    logger.info(f"✓ {settings.APP_NAME} v{settings.APP_VERSION} ready")
    yield
    logger.info("Shutting down SmartDocChecker API…")


# ── FastAPI app ──
app = FastAPI(
    title=settings.APP_NAME,
    description="Enterprise-grade contradiction detection API",
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    root_path=os.environ.get("ROOT_PATH", ""),
)

# ── Rate Limiting Middleware ──
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── CORS ──
if not settings.DEBUG and any("localhost" in o for o in settings.CORS_ORIGINS):
    logger.warning(
        "⚠  CORS_ORIGINS contains localhost URLs in production. "
        "Set CORS_ORIGINS in .env for your deployment domain."
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)


# ── Security Headers Middleware ──
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    # Prevent caching of authenticated responses
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response


# ── Include all API routes ──
app.include_router(api_router)


# ── Root health check (required by HF Spaces) ──
@app.get("/", include_in_schema=False)
def root():
    return {"status": "ok", "app": settings.APP_NAME, "version": settings.APP_VERSION}


@app.get("/health", include_in_schema=False)
def health():
    return {"status": "ok"}

