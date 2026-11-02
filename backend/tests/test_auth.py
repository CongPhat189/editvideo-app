"""Luồng đăng ký / đăng nhập / JWT, với một Supabase Auth giả lập cấp token có chữ ký thật."""

import json
import uuid
from contextlib import contextmanager
from unittest import mock

import httpx
import jwt
import pytest
from pydantic import ValidationError

from app import supabase_auth
from app.config import get_settings
from app.schemas import RegisterIn
from tests.conftest import Client, make_token, new_user, sql

PASSWORD = "matkhau-rat-dai"


class FakeGoTrue:
    def __init__(self):
        self.users: dict[str, dict] = {}   # phone (không có +) -> user
        self.refresh_tokens: dict[str, tuple[str, str]] = {}  # token -> (user phone, session id)
        self.requests: list[httpx.Request] = []
        self.autoconfirm = False

    async def _session(self, user, session_id=None) -> httpx.Response:
        if session_id is None:
            rows = await sql("insert into auth.sessions (user_id) values (:u) returning id", u=user["id"])
            session_id = str(rows[0]["id"])
        refresh = uuid.uuid4().hex
        self.refresh_tokens[refresh] = (user["phone"], session_id)
        return httpx.Response(200, json={
            "access_token": make_token(user["id"], session_id=session_id),
            "refresh_token": refresh,
            "token_type": "bearer",
            "expires_in": 3600,
            "expires_at": 1999999999,
            "user": {"id": user["id"], "phone": user["phone"]},
        })

    @staticmethod
    def _error(status, code, msg="lỗi nội bộ của Supabase, http://internal.example/x"):
        return httpx.Response(status, json={"code": status, "error_code": code, "msg": msg})

    async def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        path = request.url.path.removeprefix("/auth/v1/")
        body = json.loads(request.content) if request.content else {}
        phone = body.get("phone", "").removeprefix("+")

        if path == "signup":
            if phone in self.users and self.users[phone]["confirmed"]:
                return self._error(422, "phone_exists")
            rows = await sql(
                "insert into auth.users (phone, raw_user_meta_data) values (:p, cast(:m as jsonb)) returning id",
                p=phone, m=json.dumps(body["data"]),
            )
            user = {"id": str(rows[0]["id"]), "phone": phone, "password": body["password"],
                    "confirmed": self.autoconfirm}
            self.users[phone] = user
            return await self._session(user) if self.autoconfirm else httpx.Response(200, json=dict(id=user["id"]))
        if path == "verify":
            user = self.users.get(phone)
            if user is None or body["token"] != "123456":
                return self._error(403, "otp_expired")
            user["confirmed"] = True
            return await self._session(user)
        if path == "resend":
            return httpx.Response(200, json={})
        if path == "token" and request.url.params["grant_type"] == "password":
            user = self.users.get(phone)
            if user is None or user["password"] != body["password"]:
                return self._error(400, "invalid_credentials")
            if not user["confirmed"]:
                return self._error(400, "phone_not_confirmed")
            return await self._session(user)
        if path == "token":
            found = self.refresh_tokens.pop(body["refresh_token"], None)
            if found is None:
                return self._error(400, "refresh_token_already_used")
            exists = await sql("select 1 from auth.sessions where id = :s", s=found[1])
            if not exists:
                return self._error(400, "session_not_found")
            return await self._session(self.users[found[0]], found[1])
        if path == "logout":
            claims = jwt.decode(request.headers["authorization"].split()[1], options={"verify_signature": False})
            if request.url.params["scope"] == "global":
                await sql("delete from auth.sessions where user_id = :u", u=claims["sub"])
            else:
                rows = await sql("delete from auth.sessions where id = :s returning id", s=claims["session_id"])
                if not rows:
                    return self._error(403, "session_not_found")
            return httpx.Response(204)
        return httpx.Response(404)


@contextmanager
def gotrue(handler):
    real = httpx.AsyncClient

    def fake(**kwargs):
        return real(transport=httpx.MockTransport(handler), **kwargs)

    with mock.patch.object(supabase_auth.httpx, "AsyncClient", fake):
        yield handler


@pytest.fixture
def fake():
    server = FakeGoTrue()
    with gotrue(server):
        yield server


def new_phone() -> str:
    return f"09{uuid.uuid4().int % 10**8:08d}"


def e164(phone: str) -> str:
    return f"+84{phone[1:]}"


async def _registered(c, phone, password=PASSWORD, full_name="Nguyễn Văn A") -> dict:
    r = await c.post("/auth/register", json={"phone": phone, "password": password, "full_name": full_name})
    assert r.status_code == 201, r.text
    r = await c.post("/auth/verify-otp", json={"phone": phone, "otp": "123456"})
    assert r.status_code == 200, r.text
    return r.json()


def _authed(token: str) -> Client:
    return Client(token=token)


# ---------------------------------------------------------------- đầu vào
@pytest.mark.parametrize("raw", ["0912345678", "84912345678", "+84912345678", "+84 912 345 678", "091-234.5678",
                                 "+840912345678"])
def test_vietnam_phone_formats(raw):
    assert RegisterIn(phone=raw, password=PASSWORD, full_name="A").phone == "+84912345678"


@pytest.mark.parametrize("raw", ["", "abc", "091234567", "09123456789", "0212345678", "+8412345", "912345678",
                                 "+84212345678", "+1 23", "0912345678; drop table x"])
def test_invalid_phones(raw):
    with pytest.raises(ValidationError):
        RegisterIn(phone=raw, password=PASSWORD, full_name="A")


def test_other_country_phone_kept():
    assert RegisterIn(phone="+1 415 555 2671", password=PASSWORD, full_name="A").phone == "+14155552671"


async def test_register_input_validation(fake):
    good = {"phone": new_phone(), "password": PASSWORD, "full_name": "A"}
    async with Client() as c:
        for bad in [{"password": "ngan"}, {"password": "á" * 40}, {"full_name": "   "}, {"phone": "123"}]:
            assert (await c.post("/auth/register", json={**good, **bad})).status_code == 422, bad
    assert fake.requests == []  # bị chặn trước khi gọi Supabase (không tốn SMS)


# ---------------------------------------------------------------- đăng ký
async def test_register_verify_then_call_api(fake):
    phone = new_phone()
    async with Client() as c:
        r = await c.post("/auth/register", json={"phone": phone, "password": PASSWORD, "full_name": "  Nguyễn Văn A "})
        assert r.status_code == 201
        assert r.json() == {"phone": e164(phone), "otp_required": True, "session": None}
        sent = json.loads(fake.requests[0].content)
        assert sent == {"phone": e164(phone), "password": PASSWORD, "data": {"full_name": "Nguyễn Văn A"}}
        assert fake.requests[0].headers["apikey"] == "test-publishable"

        assert (await c.post("/auth/verify-otp", json={"phone": phone, "otp": "000000"})).status_code == 400
        assert (await c.post("/auth/verify-otp", json={"phone": phone, "otp": "abc"})).status_code == 422
        r = await c.post("/auth/verify-otp", json={"phone": phone, "otp": "123456"})
    assert r.status_code == 200
    body = r.json()
    assert body["user"]["phone"] == e164(phone) and body["user"]["full_name"] == "Nguyễn Văn A"
    assert body["expires_in"] == 3600 and body["refresh_token"]
    assert "password" not in r.text

    async with _authed(body["access_token"]) as c:
        me = (await c.get("/me")).json()
    assert me["id"] == body["user"]["id"] and me["settings"]["language"] == "vi"


async def test_register_with_autoconfirm_returns_tokens(fake):
    fake.autoconfirm = True
    async with Client() as c:
        r = await c.post("/auth/register", json={"phone": new_phone(), "password": PASSWORD, "full_name": "B"})
    assert r.status_code == 201
    assert r.json()["otp_required"] is False and r.json()["session"]["access_token"]


async def test_register_existing_phone_conflict(fake):
    phone = new_phone()
    async with Client() as c:
        await _registered(c, phone)
        r = await c.post("/auth/register", json={"phone": phone, "password": PASSWORD, "full_name": "C"})
    assert r.status_code == 409


async def test_resend_otp(fake):
    async with Client() as c:
        r = await c.post("/auth/resend-otp", json={"phone": "0912345678"})
    assert r.status_code == 202 and r.json()["phone"] == "+84912345678"


# ---------------------------------------------------------------- đăng nhập
async def test_login_rules(fake):
    phone = new_phone()
    async with Client() as c:
        await c.post("/auth/register", json={"phone": phone, "password": PASSWORD, "full_name": "D"})
        r = await c.post("/auth/login", json={"phone": phone, "password": PASSWORD})
        assert r.status_code == 403 and "OTP" in r.json()["detail"]  # chưa xác minh

        await c.post("/auth/verify-otp", json={"phone": phone, "otp": "123456"})
        wrong = await c.post("/auth/login", json={"phone": phone, "password": "sai-mat-khau"})
        unknown = await c.post("/auth/login", json={"phone": new_phone(), "password": PASSWORD})
        assert wrong.status_code == unknown.status_code == 401
        assert wrong.json() == unknown.json()  # không lộ số nào đã đăng ký

        r = await c.post("/auth/login", json={"phone": e164(phone), "password": PASSWORD})
    assert r.status_code == 200
    async with _authed(r.json()["access_token"]) as c:
        assert (await c.get("/me")).status_code == 200


async def test_suspended_account_gets_no_tokens(fake):
    phone = new_phone()
    async with Client() as c:
        first = await _registered(c, phone)
        await sql("update profiles set status = 'suspended' where id = :u", u=first["user"]["id"])
        before = await sql("select count(*) n from auth.sessions where user_id = :u", u=first["user"]["id"])
        r = await c.post("/auth/login", json={"phone": phone, "password": PASSWORD})
        after = await sql("select count(*) n from auth.sessions where user_id = :u", u=first["user"]["id"])
        refreshed = await c.post("/auth/refresh", json={"refresh_token": first["refresh_token"]})
    assert r.status_code == 403 and "access_token" not in r.text
    assert after[0]["n"] == before[0]["n"]  # phiên vừa cấp đã bị thu hồi
    assert refreshed.status_code == 403 and "access_token" not in refreshed.text


# ---------------------------------------------------------------- refresh & đăng xuất
async def test_refresh_rotates_token(fake):
    async with Client() as c:
        first = await _registered(c, new_phone())
        r = await c.post("/auth/refresh", json={"refresh_token": first["refresh_token"]})
        assert r.status_code == 200
        second = r.json()
        assert second["refresh_token"] != first["refresh_token"]
        reused = await c.post("/auth/refresh", json={"refresh_token": first["refresh_token"]})
        assert reused.status_code == 401
    async with _authed(second["access_token"]) as c:
        assert (await c.get("/me")).status_code == 200


async def test_logout_revokes_immediately(fake):
    async with Client() as c:
        session = await _registered(c, new_phone())
    async with _authed(session["access_token"]) as c:
        assert (await c.get("/me")).status_code == 200
        assert (await c.post("/auth/logout")).status_code == 204
        assert (await c.get("/me")).status_code == 401      # token còn hạn nhưng phiên đã mất
        assert (await c.post("/auth/logout")).status_code == 204  # đăng xuất lại vẫn ổn
    async with Client() as c:
        r = await c.post("/auth/refresh", json={"refresh_token": session["refresh_token"]})
        assert r.status_code == 401
        assert (await c.post("/auth/logout")).status_code == 401  # không có token


async def test_logout_one_device_or_all(fake):
    phone = new_phone()
    async with Client() as c:
        phone_a = await _registered(c, phone)
        phone_b = (await c.post("/auth/login", json={"phone": phone, "password": PASSWORD})).json()
        tablet = (await c.post("/auth/login", json={"phone": phone, "password": PASSWORD})).json()
    async with _authed(phone_a["access_token"]) as c:
        await c.post("/auth/logout")
    async with _authed(phone_b["access_token"]) as c:
        assert (await c.get("/me")).status_code == 200  # máy khác vẫn đăng nhập
        assert (await c.post("/auth/logout", params={"all_devices": True})).status_code == 204
    async with _authed(tablet["access_token"]) as c:
        assert (await c.get("/me")).status_code == 401


async def test_token_session_checks():
    user = await new_user()
    other = await new_user()
    rows = await sql("insert into auth.sessions (user_id) values (:u) returning id", u=other)
    cases = {
        "phiên không tồn tại": make_token(user, session_id=str(uuid.uuid4())),
        "phiên của người khác": make_token(user, session_id=str(rows[0]["id"])),
        "session_id sai định dạng": make_token(user, session_id="khong-phai-uuid"),
        "session_id null": make_token(user, session_id=None),
    }
    for name, token in cases.items():
        async with _authed(token) as c:
            assert (await c.get("/me")).status_code == 401, name


# ---------------------------------------------------------------- lỗi từ Supabase
@pytest.mark.parametrize(
    "response, expected",
    [
        (httpx.Response(400, json={"error_code": "phone_provider_disabled", "msg": "x"}), 503),
        (httpx.Response(429, json={"error_code": "over_request_rate_limit", "msg": "x"}), 429),
        (httpx.Response(429, json={"msg": "x"}), 429),
        (httpx.Response(500, json={"msg": "x"}), 503),
        (httpx.Response(502, text="<html>bad gateway http://internal</html>"), 503),
        (httpx.Response(400, json={"error": "invalid_grant", "error_description": "x"}), 401),
        (httpx.Response(400, json=["không phải object"]), 401),
    ],
)
async def test_login_error_mapping(response, expected):
    with gotrue(lambda request: response):
        async with Client() as c:
            r = await c.post("/auth/login", json={"phone": "0912345678", "password": PASSWORD})
    assert r.status_code == expected, r.text
    assert "internal" not in r.text and "invalid_grant" not in r.text


async def test_network_error_and_malformed_session():
    def down(request):
        raise httpx.ConnectError("không kết nối được http://internal.example")

    for handler in (down, lambda request: httpx.Response(200, json={"access_token": "x"})):
        with gotrue(handler):
            async with Client() as c:
                r = await c.post("/auth/login", json={"phone": "0912345678", "password": PASSWORD})
        assert r.status_code == 503 and "internal" not in r.text


async def test_refresh_with_unknown_error_is_expired_session():
    with gotrue(lambda request: httpx.Response(400, json={"error_code": "something_new", "msg": "x"})):
        async with Client() as c:
            assert (await c.post("/auth/refresh", json={"refresh_token": "abc"})).status_code == 401


# ---------------------------------------------------------------- cấu hình key
async def test_missing_key_is_clear_error(fake):
    with mock.patch.object(get_settings(), "supabase_publishable_key", None):
        async with Client() as c:
            r = await c.post("/auth/login", json={"phone": "0912345678", "password": PASSWORD})
    assert r.status_code == 503 and fake.requests == []


async def test_secret_key_forwards_client_ip(fake):
    with mock.patch.object(get_settings(), "supabase_secret_key", "test-secret"):
        async with Client() as c:
            await c.post("/auth/login", json={"phone": "0912345678", "password": PASSWORD})
    sent = fake.requests[0].headers
    assert sent["apikey"] == "test-secret" and sent["sb-forwarded-for"] == "127.0.0.1"


async def test_publishable_key_does_not_forward_ip(fake):
    async with Client() as c:
        await c.post("/auth/login", json={"phone": "0912345678", "password": PASSWORD})
    assert "sb-forwarded-for" not in fake.requests[0].headers
