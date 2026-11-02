"""Hai nhóm API chạy chung một app: nhóm này hỏng không được kéo nhóm kia, bảng demo không được lên Supabase."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import main
from app.api.v1.router import build_api_router
from app.core import config
from app.core.config import SupabaseNotConfigured, SupabaseSettings, get_settings
from app.db import init_db, supabase
from app.main import app


@pytest.mark.parametrize(
    "local_url, allow, refused",
    [
        ("sqlite:///x.db", False, False),
        ("postgresql://u:p@localhost:5432/demo", True, False),
        ("postgresql://u:p@localhost:5432/demo", False, True),
        ("postgresql://u:p@aws-0-eu-west-2.pooler.supabase.com:5432/postgres", True, True),
        ("postgresql://u:p@db.internal:5432/app", True, True),  # trùng DATABASE_URL
    ],
)
def test_demo_tables_never_created_on_supabase(monkeypatch, local_url, allow, refused):
    monkeypatch.setattr(init_db.settings, "DATABASE_URL", local_url, raising=False)
    monkeypatch.setattr(init_db.settings, "ALLOW_NON_SQLITE_LOCAL_DB", allow, raising=False)
    monkeypatch.setenv("DATABASE_URL", "postgresql://other@db.internal:5432/app")
    if refused:
        with pytest.raises(RuntimeError):
            init_db.check_local_database()
    else:
        init_db.check_local_database()


def test_missing_supabase_config_gives_clear_error(monkeypatch):
    monkeypatch.delenv("DATABASE_URL")
    monkeypatch.setitem(SupabaseSettings.model_config, "env_file", None)
    get_settings.cache_clear()
    try:
        with pytest.raises(SupabaseNotConfigured, match="DATABASE_URL"):
            get_settings()
    finally:
        get_settings.cache_clear()


@pytest.mark.parametrize("url", ["sqlite:///x.db", "mysql://u@h/d"])
def test_database_url_must_be_postgres(url):
    with pytest.raises(SupabaseNotConfigured):
        SupabaseSettings(database_url=url, _env_file=None).sqlalchemy_url


def test_old_psycopg2_url_uses_installed_driver():
    settings = SupabaseSettings(database_url="postgresql+psycopg2://u@h/d", _env_file=None)
    assert settings.sqlalchemy_url.drivername == "postgresql+psycopg"


def test_mobile_api_returns_503_and_demo_api_keeps_working(client, monkeypatch):
    def not_configured():
        raise SupabaseNotConfigured("thiếu")

    monkeypatch.setattr(supabase, "get_sessionmaker", not_configured)
    assert client.get("/health").status_code == 503
    assert client.get("/api/health").status_code == 200
    assert client.post("/api/auth/login", json={"email": "abc@gmail.com", "password": "123456"}).status_code == 200


def test_broken_demo_database_does_not_stop_the_app(monkeypatch):
    def broken():
        raise OSError("đĩa đầy")

    monkeypatch.setattr(main, "init_db", broken)
    with TestClient(app) as c:
        assert c.get("/api/health").status_code == 200


def test_demo_api_can_be_turned_off():
    def paths(enable_demo):
        demo_app = FastAPI()
        demo_app.include_router(build_api_router(enable_demo))
        return set(demo_app.openapi()["paths"])

    assert "/api/users" in paths(True) and "/me" in paths(True)
    off = paths(False)
    assert "/me" in off and "/conversations" in off
    assert not [p for p in off if p.startswith("/api/")]


def test_settings_module_keeps_old_names():
    assert config.APP_TITLE == config.settings.APP_TITLE
