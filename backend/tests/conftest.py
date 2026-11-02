"""Test chạy trên một Postgres riêng (KHÔNG phải Supabase thật), đã migrate + seed.

    TEST_DATABASE_URL=postgresql://postgres@127.0.0.1:54329/postgres uv run pytest
"""

import os
import time
import uuid

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec

TEST_DB = os.environ.get("TEST_DATABASE_URL")
if not TEST_DB:
    pytest.exit("Đặt TEST_DATABASE_URL tới một database test (đừng dùng Supabase production)", returncode=2)

os.environ.update(
    DATABASE_URL=TEST_DB,
    DB_PASSWORD="",
    SUPABASE_URL="https://test.supabase.co",
    SUPABASE_PUBLISHABLE_KEY="test-publishable",
    SUPABASE_SECRET_KEY="",
    GOCLAW_MODE="mock",
    GOCLAW_TIMEOUT_SECONDS="30",
)

import httpx  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app import auth  # noqa: E402
from app.db import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402

_KEY = ec.generate_private_key(ec.SECP256R1())
ISSUER = "https://test.supabase.co/auth/v1"


@pytest.fixture(autouse=True, scope="session")
def _fake_jwks():
    original = auth._signing_key
    auth._signing_key = lambda token: _KEY.public_key()
    yield
    auth._signing_key = original


def make_token(user_id, *, exp_in=3600, aud="authenticated", iss=ISSUER, key=_KEY, **extra) -> str:
    now = int(time.time())
    claims = {"sub": str(user_id), "aud": aud, "iss": iss, "iat": now, "role": "authenticated", **extra}
    if exp_in is not None:
        claims["exp"] = now + exp_in
    return jwt.encode(claims, key, algorithm="ES256")


async def sql(query: str, **params):
    async with SessionLocal() as s:
        result = await s.execute(text(query), params)
        rows = result.mappings().all() if result.returns_rows else None
        await s.commit()
        return rows


async def new_user(full_name: str | None = "Người Test") -> uuid.UUID:
    meta = '{"full_name": "%s"}' % full_name if full_name else "{}"
    rows = await sql(
        "insert into auth.users (phone, raw_user_meta_data) values (:phone, cast(:meta as jsonb)) returning id",
        phone=f"84{uuid.uuid4().int % 10**9:09d}",
        meta=meta,
    )
    return rows[0]["id"]


class Client(httpx.AsyncClient):
    def __init__(self, user_id=None, token=None, raise_app_exceptions=True):
        headers = {}
        if token or user_id:
            headers["Authorization"] = f"Bearer {token or make_token(user_id)}"
        transport = httpx.ASGITransport(app=app, raise_app_exceptions=raise_app_exceptions)
        super().__init__(transport=transport, base_url="http://test", headers=headers)


@pytest.fixture(scope="session")
async def agents():
    rows = await sql("select id, name, visibility from agents order by sort_order")
    return {r["name"]: r["id"] for r in rows}


@pytest.fixture(autouse=True, scope="session")
async def _dispose():
    yield
    await engine.dispose()
