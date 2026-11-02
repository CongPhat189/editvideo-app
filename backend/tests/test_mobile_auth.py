"""Đăng ký / đăng nhập / JWT do backend tự quản lý, không xác thực số điện thoại."""

import time
import uuid
from unittest import mock

import jwt
import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.core import mobile_security
from app.core.config import SupabaseNotConfigured, get_settings
from app.core.rate_limit import RateLimiter, limiter
from app.schemas.mobile import RegisterIn
from tests.conftest import Client, make_token, new_phone, new_user, sql

PASSWORD = "matkhau-rat-dai"


async def _register(c, phone=None, password=PASSWORD, full_name="Nguyễn Văn A") -> dict:
    r = await c.post("/auth/register", json={"phone": phone or new_phone(), "password": password, "full_name": full_name})
    assert r.status_code == 201, r.text
    return r.json()


# ---------------------------------------------------------------- đầu vào
@pytest.mark.parametrize("raw", ["0912345678", "84912345678", "+84912345678", "+84 912 345 678", "091-234.5678",
                                 "+840912345678"])
def test_vietnam_phone_formats(raw):
    assert RegisterIn(phone=raw, password=PASSWORD, full_name="A").phone == "+84912345678"


@pytest.mark.parametrize("raw", ["", "abc", "091234567", "09123456789", "0212345678", "+8412345", "912345678",
                                 "+84212345678", "+1 23", "0912345678; drop table x", "٠٩١٢٣٤٥٦٧٨", "09１２３４５６７８"])
def test_invalid_phones(raw):
    with pytest.raises(ValidationError):
        RegisterIn(phone=raw, password=PASSWORD, full_name="A")


def test_other_country_phone_only_when_allowed():
    with pytest.raises(ValidationError):
        RegisterIn(phone="+14155552671", password=PASSWORD, full_name="A")
    with mock.patch.object(get_settings(), "allow_international_phones", True):
        assert RegisterIn(phone="+1 415 555 2671", password=PASSWORD, full_name="A").phone == "+14155552671"


async def test_register_input_validation():
    good = {"phone": new_phone(), "password": PASSWORD, "full_name": "A"}
    async with Client() as c:
        for bad in [{"password": "ngan"}, {"password": "a" * 129}, {"full_name": "   "}, {"phone": "123"}]:
            assert (await c.post("/auth/register", json={**good, **bad})).status_code == 422, bad


async def test_validation_error_does_not_echo_password():
    async with Client() as c:
        r = await c.post("/auth/register", json={"phone": "123", "password": "mat-khau-bi-mat", "full_name": "A"})
    assert r.status_code == 422 and "mat-khau-bi-mat" not in r.text
    assert r.json()["detail"][0]["loc"] == ["body", "phone"]


async def test_nul_characters_rejected_not_500():
    user = await new_user()
    async with Client() as c:
        r = await c.post("/auth/register", json={"phone": new_phone(), "password": PASSWORD, "full_name": "A\x00B"})
        assert r.status_code == 422
    async with Client(user) as c:
        assert (await c.patch("/me", json={"full_name": "A\x00"})).status_code == 422
        for body in ({"language": "v\x00"}, {"timezone": "U\x00"}, {"settings_json": {"a": "x\x00"}},
                     {"settings_json": {"a": "x" * 20000}}):
            assert (await c.patch("/me/settings", json=body)).status_code == 422, body
        assert (await c.get("/search", params={"q": "a\x00"})).status_code == 200


# ---------------------------------------------------------------- đăng ký
async def test_register_gives_tokens_immediately_without_otp():
    phone = "0345678912"
    await sql("delete from users where phone = '+84345678912'")
    async with Client() as c:
        body = await _register(c, phone=phone, full_name="  Nguyễn Văn A ")
    assert body["user"]["phone"] == "+84345678912" and body["user"]["full_name"] == "Nguyễn Văn A"
    assert body["access_token"] and body["refresh_token"] and body["expires_in"] == 1800
    assert PASSWORD not in str(body)
    async with Client(token=body["access_token"]) as c:
        me = (await c.get("/me")).json()
    assert me["id"] == body["user"]["id"] and me["settings"]["language"] == "vi"  # có sẵn user_settings


async def test_password_stored_as_argon2id_only():
    async with Client() as c:
        body = await _register(c)
    rows = await sql("select password_hash from users where id = :u", u=body["user"]["id"])
    assert rows[0]["password_hash"].startswith("$argon2id$") and PASSWORD not in rows[0]["password_hash"]


async def test_register_existing_phone_conflict():
    phone = new_phone()
    async with Client() as c:
        await _register(c, phone=phone)
        r = await c.post("/auth/register", json={"phone": phone, "password": "mat-khau-khac-123", "full_name": "B"})
        assert r.status_code == 409
        # không bị đổi mật khẩu của chủ tài khoản
        assert (await c.post("/auth/login", json={"phone": phone, "password": PASSWORD})).status_code == 200
        assert (await c.post("/auth/login", json={"phone": phone, "password": "mat-khau-khac-123"})).status_code == 401


# ---------------------------------------------------------------- đăng nhập
async def test_login_rules():
    phone = new_phone()
    async with Client() as c:
        created = await _register(c, phone=phone)
        wrong = await c.post("/auth/login", json={"phone": phone, "password": "sai-mat-khau"})
        unknown = await c.post("/auth/login", json={"phone": new_phone(), "password": PASSWORD})
        assert wrong.status_code == unknown.status_code == 401
        assert wrong.json() == unknown.json()  # không lộ số nào đã đăng ký
        r = await c.post("/auth/login", json={"phone": phone.replace("+84", "0"), "password": PASSWORD})
    assert r.status_code == 200
    rows = await sql("select last_login_at from users where id = :u", u=created["user"]["id"])
    assert rows[0]["last_login_at"] is not None
    async with Client(token=r.json()["access_token"]) as c:
        assert (await c.get("/me")).status_code == 200


async def test_unknown_phone_still_hashes():
    with mock.patch.object(mobile_security, "verify_password", wraps=mobile_security.verify_password) as verify:
        async with Client() as c:
            await c.post("/auth/login", json={"phone": new_phone(), "password": PASSWORD})
    assert verify.called


async def test_suspended_and_deleted_accounts():
    phone = new_phone()
    async with Client() as c:
        first = await _register(c, phone=phone)
        uid = first["user"]["id"]
        await sql("update users set status = 'suspended' where id = :u", u=uid)
        r = await c.post("/auth/login", json={"phone": phone, "password": PASSWORD})
        assert r.status_code == 403 and "access_token" not in r.text
        # sai mật khẩu thì không tiết lộ tài khoản bị khóa
        assert (await c.post("/auth/login", json={"phone": phone, "password": "sai-mat-khau"})).status_code == 401
        assert (await c.post("/auth/refresh", json={"refresh_token": first["refresh_token"]})).status_code == 403

        await sql("update users set status = 'deleted', deleted_at = now() where id = :u", u=uid)
        assert (await c.post("/auth/login", json={"phone": phone, "password": PASSWORD})).status_code == 401
        assert (await c.post("/auth/refresh", json={"refresh_token": first["refresh_token"]})).status_code == 401


# ---------------------------------------------------------------- token
async def test_refresh_gives_working_tokens_and_types_not_interchangeable():
    async with Client() as c:
        first = await _register(c)
        r = await c.post("/auth/refresh", json={"refresh_token": first["refresh_token"]})
        assert r.status_code == 200
        assert r.json()["refresh_token"] != first["refresh_token"]
        assert (await c.post("/auth/refresh", json={"refresh_token": first["access_token"]})).status_code == 401
        assert (await c.post("/auth/refresh", json={"refresh_token": "rac"})).status_code == 401
    async with Client(token=r.json()["access_token"]) as c:
        assert (await c.get("/me")).status_code == 200
    async with Client(token=first["refresh_token"]) as c:
        assert (await c.get("/me")).status_code == 401


async def test_token_claims_and_lifetimes():
    async with Client() as c:
        body = await _register(c)
    secret = get_settings().auth_jwt_secret
    decode = lambda t: jwt.decode(t, secret, algorithms=["HS256"], audience=mobile_security.AUDIENCE)  # noqa: E731
    access, refresh = decode(body["access_token"]), decode(body["refresh_token"])
    assert access["typ"] == "access" and refresh["typ"] == "refresh"
    assert access["exp"] - access["iat"] == 30 * 60 and refresh["exp"] - refresh["iat"] == 30 * 86400
    assert access["sub"] == body["user"]["id"]
    assert not {"password", "password_hash", "phone"} & set(access)
    assert abs(body["expires_at"] - (time.time() + 1800)) < 5


async def test_change_password_revokes_all_old_tokens():
    phone = new_phone()
    async with Client() as c:
        device_a = await _register(c, phone=phone)
        device_b = (await c.post("/auth/login", json={"phone": phone, "password": PASSWORD})).json()
    async with Client(token=device_a["access_token"]) as c:
        body = {"current_password": "sai", "new_password": "mat-khau-moi-123"}
        assert (await c.post("/auth/change-password", json=body)).status_code == 403
        assert (await c.post("/auth/change-password", json={**body, "new_password": "ngan"})).status_code == 422
        r = await c.post("/auth/change-password", json={**body, "current_password": PASSWORD})
        assert r.status_code == 200
        new = r.json()
        assert (await c.get("/me")).status_code == 401  # token cũ của máy A
    async with Client(token=device_b["access_token"]) as c:
        assert (await c.get("/me")).status_code == 401
    async with Client() as c:
        assert (await c.post("/auth/refresh", json={"refresh_token": device_b["refresh_token"]})).status_code == 401
        assert (await c.post("/auth/login", json={"phone": phone, "password": PASSWORD})).status_code == 401
        assert (await c.post("/auth/login", json={"phone": phone, "password": "mat-khau-moi-123"})).status_code == 200
    async with Client(token=new["access_token"]) as c:
        assert (await c.get("/me")).status_code == 200


async def test_expired_refresh_token_rejected():
    user = await new_user()
    token = make_token(user, token_type="refresh", exp_in=-1)
    async with Client() as c:
        assert (await c.post("/auth/refresh", json={"refresh_token": token})).status_code == 401


def test_weak_or_missing_jwt_secret_refused():
    for bad in (None, "", "qua-ngan"):
        with mock.patch.object(get_settings(), "auth_jwt_secret", bad):
            with pytest.raises(SupabaseNotConfigured):
                mobile_security.issue_tokens(uuid.uuid4(), "hash")


async def test_missing_secret_is_503_not_crash():
    with mock.patch.object(get_settings(), "auth_jwt_secret", None):
        async with Client(token="abc") as c:
            assert (await c.get("/me")).status_code == 503
        phone = new_phone()
        async with Client() as c:
            r = await c.post("/auth/register", json={"phone": phone, "password": PASSWORD, "full_name": "A"})
            assert r.status_code == 503
    # không để lại tài khoản: sửa cấu hình xong đăng ký lại được
    assert await sql("select id from users where phone = :p", p=phone) == []


# ---------------------------------------------------------------- giới hạn tần suất
async def test_login_rate_limit():
    phone = new_phone()
    async with Client() as c:
        for _ in range(10):
            assert (await c.post("/auth/login", json={"phone": phone, "password": "sai"})).status_code == 401
        blocked = await c.post("/auth/login", json={"phone": phone, "password": "sai"})
        assert blocked.status_code == 429 and int(blocked.headers["retry-after"]) > 0
        # số khác từ cùng IP vẫn thử được, tới giới hạn tổng theo IP (lượt bị chặn ở trên cũng được tính)
        for _ in range(89):
            assert (await c.post("/auth/login", json={"phone": new_phone(), "password": "sai"})).status_code == 401
        assert (await c.post("/auth/login", json={"phone": new_phone(), "password": "sai"})).status_code == 429


async def test_phone_limit_counts_failures_not_successes():
    phone = new_phone()
    async with Client() as c:
        await _register(c, phone=phone)
    key = f"login:phone-failed:{phone}"
    for _ in range(49):
        limiter.record(key)
    async with Client() as c:
        # dưới ngưỡng: đăng nhập đúng vẫn được và không bị tính thêm
        for _ in range(3):
            assert (await c.post("/auth/login", json={"phone": phone, "password": PASSWORD})).status_code == 200
        assert (await c.post("/auth/login", json={"phone": phone, "password": "sai"})).status_code == 401
        assert (await c.post("/auth/login", json={"phone": phone, "password": PASSWORD})).status_code == 429


async def test_register_rate_limit():
    async with Client() as c:
        for _ in range(30):
            await _register(c)
        r = await c.post("/auth/register", json={"phone": new_phone(), "password": PASSWORD, "full_name": "A"})
    assert r.status_code == 429


def test_limiter_window_expires():
    limiter = RateLimiter()
    with mock.patch("app.core.rate_limit.time.monotonic", side_effect=[0.0, 0.0, 1.0, 1.0, 2.0, 11.5, 11.5]):
        limiter.hit("k", 2, 10)
        limiter.hit("k", 2, 10)
        with pytest.raises(HTTPException):
            limiter.hit("k", 2, 10)
        limiter.hit("k", 2, 10)  # lượt đầu đã ra khỏi cửa sổ
