from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL, make_url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Supabase -> Project Settings -> Database -> Connection string -> Session pooler (cổng 5432).
    # Để mật khẩu riêng ở DB_PASSWORD cho khỏi phải mã hóa ký tự đặc biệt trong URL.
    database_url: str
    db_password: str | None = None

    supabase_url: str                       # https://<ref>.supabase.co
    supabase_jwt_secret: str | None = None  # chỉ cần nếu project còn dùng JWT secret cũ (HS256)
    supabase_publishable_key: str | None = None  # gọi Supabase Auth (đăng ký, đăng nhập...)
    # Tùy chọn, dùng thay publishable key để báo IP thật của user cho Supabase (xem app/supabase_auth.py)
    supabase_secret_key: str | None = None

    # mock: trả lời giả, để chạy app khi chưa có GoClaw. openai: gọi /v1/chat/completions.
    goclaw_mode: Literal["mock", "openai"] = "mock"
    goclaw_api_key: str | None = None       # dự phòng khi workspace chưa gắn secret trong Vault
    goclaw_session_header: str = "x-openclaw-session-key"
    goclaw_timeout_seconds: float = 120

    cors_origins: list[str] = ["*"]

    @property
    def sqlalchemy_url(self) -> URL:
        url = make_url(self.database_url)
        if url.drivername in ("postgres", "postgresql"):
            url = url.set(drivername="postgresql+psycopg")
        if self.db_password:
            url = url.set(password=self.db_password)
        return url

    @property
    def jwt_issuer(self) -> str:
        return f"{self.supabase_url.rstrip('/')}/auth/v1"

    @property
    def jwks_url(self) -> str:
        return f"{self.jwt_issuer}/.well-known/jwks.json"


@lru_cache
def get_settings() -> Settings:
    return Settings()
