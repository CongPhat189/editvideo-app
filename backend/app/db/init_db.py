from __future__ import annotations

import os

from sqlalchemy.engine import make_url

from app.core.config import settings
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models import Account, IntegrationConfig, User


def check_local_database() -> None:
    """Không tạo bảng demo trên database thật: các bảng này không có RLS và có tài khoản, key demo."""
    url = make_url(settings.DATABASE_URL)
    if url.get_backend_name() == "sqlite":
        return
    supabase_url = make_url(os.environ["DATABASE_URL"]) if os.environ.get("DATABASE_URL") else None
    same_as_supabase = supabase_url is not None and (url.host, url.port, url.database) == (
        supabase_url.host,
        supabase_url.port,
        supabase_url.database,
    )
    if same_as_supabase or "supabase" in (url.host or ""):
        raise RuntimeError("LOCAL_DATABASE_URL không được trỏ vào Supabase")
    if not settings.ALLOW_NON_SQLITE_LOCAL_DB:
        raise RuntimeError("LOCAL_DATABASE_URL không phải SQLite: đặt ALLOW_NON_SQLITE_LOCAL_DB=true nếu thật sự muốn")


def init_db() -> None:
    check_local_database()
    Base.metadata.create_all(bind=engine)
    seed_demo_data()


def seed_demo_data() -> None:
    db = SessionLocal()
    try:
        if db.query(User).count() == 0:
            user = User(full_name="Demo Admin", email="abc@gmail.com", phone="0900000000", is_active=True)
            db.add(user)
            db.commit()
            db.refresh(user)

            db.add(
                Account(
                    user_id=user.id,
                    provider="local",
                    email="abc@gmail.com",
                    password_hash=hash_password("123456"),
                    is_active=True,
                )
            )
            db.add(
                IntegrationConfig(
                    user_id=user.id,
                    provider="goclaw",
                    name="Goclaw Demo",
                    api_key="demo_goclaw_key",
                    api_secret="demo_goclaw_secret",
                    base_url="https://api.goclaw.com",
                    project_id="demo-project",
                    config_json={"workspace": "demo"},
                    is_active=True,
                )
            )
            db.add(
                IntegrationConfig(
                    user_id=user.id,
                    provider="cloudinary",
                    name="Cloudinary Demo",
                    api_key="demo_cloudinary_key",
                    api_secret="demo_cloudinary_secret",
                    base_url="https://res.cloudinary.com",
                    project_id="demo-project",
                    config_json={"cloud_name": "demo-cloud"},
                    is_active=True,
                )
            )
            db.commit()
    finally:
        db.close()
