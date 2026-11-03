"""Test chạy trên một Postgres riêng (KHÔNG phải Supabase thật), đã migrate + seed, cộng một SQLite tạm.

    sh tests/run.sh    # toàn bộ test, cần Node.js và uv
    pytest             # chỉ test không cần Postgres
"""

import asyncio
import os
import tempfile
import time
import uuid
from pathlib import Path

import jwt
import pytest
from cryptography.fernet import Fernet

TEST_DB = os.environ.get("TEST_DATABASE_URL")
# Không có Postgres test thì bỏ qua các test cần database. Luôn ghi đè DATABASE_URL để không bao giờ chạm Supabase thật.
collect_ignore = [] if TEST_DB else ["test_api.py", "test_mobile_auth.py", "test_review_fixes.py", "test_schedules.py", "test_attachments.py"]

# Dùng DB tạm khi test, không đụng vào connector_screen.db thật
_tmp = Path(tempfile.mkdtemp()) / "test.db"

os.environ.update(
    DATABASE_URL=TEST_DB or "postgresql://unused@127.0.0.1:1/unused",
    LOCAL_DATABASE_URL=f"sqlite:///{_tmp.as_posix()}",
    ALLOW_NON_SQLITE_LOCAL_DB="false",
    ENABLE_DEMO_API="true",
    DB_PASSWORD="",
    AUTH_JWT_SECRET="khoa-ky-jwt-chi-dung-cho-test-1234567890",
    ACCESS_TOKEN_MINUTES="30",
    REFRESH_TOKEN_DAYS="30",
    AGENT_KEY_ENCRYPTION_KEY=Fernet.generate_key().decode(),
    ALLOW_INTERNATIONAL_PHONES="false",
    GOCLAW_MODE="mock",
    GOCLAW_API_KEY="",
    GOCLAW_TIMEOUT_SECONDS="30",
    SCHEDULE_WORKER_ENABLED="false",
    SUPABASE_URL="https://storage.invalid",
    SUPABASE_SECRET_KEY="khoa-test",
)

import httpx  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.core import mobile_security  # noqa: E402
from app.core.rate_limit import limiter  # noqa: E402
from app.db.supabase import get_engine, get_sessionmaker  # noqa: E402
from app.main import app  # noqa: E402

TEST_PASSWORD = "mat-khau-test"
TEST_HASH = mobile_security.hash_password(TEST_PASSWORD)  # băm một lần cho nhanh


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


def make_token(
    user_id,
    *,
    token_type="access",
    exp_in=3600,
    aud=mobile_security.AUDIENCE,
    iss=mobile_security.ISSUER,
    secret=None,
    password_hash=TEST_HASH,
    algorithm="HS256",
    **extra,
) -> str:
    now = int(time.time())
    claims = {
        "sub": str(user_id),
        "typ": token_type,
        "pwf": mobile_security.password_fingerprint(password_hash),
        "ver": 0,
        "aud": aud,
        "iss": iss,
        "iat": now,
        **extra,
    }
    if exp_in is not None:
        claims["exp"] = now + exp_in
    return jwt.encode(claims, secret or os.environ["AUTH_JWT_SECRET"], algorithm=algorithm)


async def sql(query: str, **params):
    async with get_sessionmaker()() as s:
        result = await s.execute(text(query), params)
        rows = result.mappings().all() if result.returns_rows else None
        await s.commit()
        return rows


def new_phone() -> str:
    return f"+849{uuid.uuid4().int % 10**8:08d}"


async def new_user(full_name: str = "Người Test") -> uuid.UUID:
    rows = await sql(
        "insert into users (full_name, phone, password_hash) values (:n, :p, :h) returning id",
        n=full_name, p=new_phone(), h=TEST_HASH,
    )
    await sql("insert into user_settings (user_id) values (:u)", u=rows[0]["id"])
    return rows[0]["id"]


class Client(httpx.AsyncClient):
    def __init__(self, user_id=None, token=None, raise_app_exceptions=True):
        headers = {}
        if token or user_id:
            headers["Authorization"] = f"Bearer {token or make_token(user_id)}"
        transport = httpx.ASGITransport(app=app, raise_app_exceptions=raise_app_exceptions)
        super().__init__(transport=transport, base_url="http://test", headers=headers)


@pytest.fixture(scope="session")
def agents():
    rows = asyncio.run(sql("select id, name from agents"))
    return {r["name"]: r["id"] for r in rows}


@pytest.fixture(autouse=True)
def _reset_rate_limits():
    limiter.reset()


@pytest.fixture(autouse=True, scope="session")
def _dispose():
    yield
    try:
        asyncio.run(get_engine().dispose())
    except Exception:
        pass
