from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL, make_url

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

    # Database demo của các API /api/*. DATABASE_URL giờ là Supabase (xem SupabaseSettings bên dưới).
    DATABASE_URL: str = (
        os.getenv("LOCAL_DATABASE_URL") or f"sqlite:///{(BASE_DIR / 'connector_screen.db').as_posix()}"
    )
    # Bảng demo không có RLS: database demo khác SQLite phải bật rõ ràng (xem app/db/init_db.py)
    ALLOW_NON_SQLITE_LOCAL_DB: bool = os.getenv("ALLOW_NON_SQLITE_LOCAL_DB", "false").lower() == "true"
    # Đặt false khi lên production: các API /api/* chưa kiểm tra đăng nhập
    ENABLE_DEMO_API: bool = os.getenv("ENABLE_DEMO_API", "true").lower() == "true"

    CORS_ORIGINS: list[str] = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()]

    GOCLAW_BASE_URL: str = os.getenv("GOCLAW_BASE_URL", "https://api.goclaw.com")
    GOCLAW_API_KEY: str = os.getenv("GOCLAW_API_KEY", "")


settings = Settings()

# Giữ tên cũ để code cũ vẫn import được
APP_TITLE = settings.APP_TITLE
APP_VERSION = settings.APP_VERSION
JWT_SECRET = settings.JWT_SECRET


class SupabaseNotConfigured(RuntimeError):
    """Chưa cấu hình đúng Supabase. API mobile trả 503, API demo vẫn chạy bình thường."""


class SupabaseSettings(BaseSettings):
    """Cấu hình của các API mobile (/auth, /me, /agents, /conversations, /search)."""

    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", env_file_encoding="utf-8", extra="ignore")

    # Supabase -> Project Settings -> Database -> Connection string -> Session pooler (cổng 5432).
    # Để mật khẩu riêng ở DB_PASSWORD cho khỏi phải mã hóa ký tự đặc biệt trong URL.
    database_url: str
    db_password: str | None = None

    # Khóa ký JWT của app mobile (ít nhất 32 ký tự). Đổi khóa = mọi người phải đăng nhập lại.
    auth_jwt_secret: str | None = None
    access_token_minutes: int = 30
    refresh_token_days: int = 30
    # Khóa Fernet mã hóa agents.key. Mất hoặc đổi khóa thì phải đặt lại API key của các agent.
    agent_key_encryption_key: str | None = None

    # Mặc định chỉ nhận số Việt Nam
    allow_international_phones: bool = False

    # mock: trả lời giả, để chạy app khi chưa có GoClaw. openai: gọi /v1/chat/completions.
    goclaw_mode: Literal["mock", "openai"] = "mock"
    goclaw_api_key: str | None = None       # dự phòng khi agent chưa có key
    goclaw_default_model: str = "default"   # bảng agents không có id agent bên GoClaw, nên dùng chung một model
    goclaw_session_header: str = "x-openclaw-session-key"
    goclaw_timeout_seconds: float = 120

    @property
    def sqlalchemy_url(self) -> URL:
        url = make_url(self.database_url)
        if url.get_backend_name() not in ("postgres", "postgresql"):
            raise SupabaseNotConfigured("DATABASE_URL phải là Postgres của Supabase (database demo dùng LOCAL_DATABASE_URL)")
        url = url.set(drivername="postgresql+psycopg")
        if self.db_password:
            url = url.set(password=self.db_password)
        return url


@lru_cache
def get_settings() -> SupabaseSettings:
    try:
        return SupabaseSettings()
    except ValidationError as e:
        missing = ", ".join(str(err["loc"][0]).upper() for err in e.errors())
        raise SupabaseNotConfigured(f"Thiếu cấu hình Supabase trong backend/.env: {missing}") from e
