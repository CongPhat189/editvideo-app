from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # python-dotenv là tuỳ chọn
    load_dotenv = None

# Thư mục backend/
BASE_DIR = Path(__file__).resolve().parents[2]

if load_dotenv is not None:
    load_dotenv(BASE_DIR / ".env")


class Settings:
    APP_TITLE: str = os.getenv("APP_TITLE", "Connector Screen BE")
    APP_VERSION: str = os.getenv("APP_VERSION", "1.0.0")
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "4000"))
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    JWT_SECRET: str = os.getenv("JWT_SECRET", "connector-screen-demo-secret")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")

    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", f"sqlite:///{(BASE_DIR / 'connector_screen.db').as_posix()}"
    )

    CORS_ORIGINS: list[str] = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()]

    GOCLAW_BASE_URL: str = os.getenv("GOCLAW_BASE_URL", "https://api.goclaw.com")
    GOCLAW_API_KEY: str = os.getenv("GOCLAW_API_KEY", "")


settings = Settings()

# Giữ tên cũ để code cũ vẫn import được
APP_TITLE = settings.APP_TITLE
APP_VERSION = settings.APP_VERSION
JWT_SECRET = settings.JWT_SECRET
