"""
Application configuration loaded from environment variables / .env file.
"""
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # ── App ──
    APP_NAME: str = "SmartDocChecker API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # ── Database ──
    DATABASE_URL: str = "sqlite:///./smartdocchecker.db"

    # ── Supabase Storage ──
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_KEY: str = ""
    SUPABASE_BUCKET: str = "documents"

    # ── JWT / Auth ──
    SECRET_KEY: str = "smartdocchecker-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # ── CORS ──
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
    ]

    # ── AI Models ──
    MODEL_CACHE_DIR: str = "./.model_cache"
    HF_TOKEN: str = ""
    NLI_BATCH_SIZE: int = 64

    # ── Rate Limiting ──
    RATE_LIMIT_DEFAULT: str = "60/minute"
    RATE_LIMIT_AUTH: str = "10/minute"
    RATE_LIMIT_UPLOAD: str = "20/minute"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"          # ignore unknown vars in .env


settings = Settings()

# ── Security: reject the default placeholder secret in production ──
_DEFAULT_SECRET = "smartdocchecker-secret-key-change-in-production"
if settings.SECRET_KEY == _DEFAULT_SECRET and not settings.DEBUG:
    import sys
    print(
        "\n❌ FATAL: SECRET_KEY is set to the insecure default!\n"
        "   Set a strong, random SECRET_KEY in your .env file.\n"
        "   Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(64))\"\n",
        file=sys.stderr,
    )
    raise SystemExit(1)
