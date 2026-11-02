"""Gọi Supabase Auth (GoTrue) qua REST. Mật khẩu, OTP và việc ký JWT do Supabase xử lý;
backend không lưu mật khẩu và không tự phát hành token."""

import logging
from dataclasses import dataclass
from typing import Any

import httpx

from app.config import get_settings

log = logging.getLogger(__name__)

TIMEOUT_SECONDS = 15
EXPIRED_SESSION = (401, "Phiên đăng nhập đã hết hạn, vui lòng đăng nhập lại")
BAD_OTP = (400, "Mã OTP sai hoặc đã hết hạn")
SMS_UNAVAILABLE = (503, "Chưa gửi được SMS, vui lòng thử lại sau")
PHONE_UNAVAILABLE = (503, "Đăng nhập bằng số điện thoại đang tạm tắt")
TOO_MANY = (429, "Bạn thao tác quá nhanh, vui lòng thử lại sau ít phút")

# error_code của Supabase -> (HTTP status, thông báo cho user). Không trả nguyên văn lỗi của Supabase.
ERRORS: dict[str, tuple[int, str]] = {
    "invalid_credentials": (401, "Sai số điện thoại hoặc mật khẩu"),
    "phone_not_confirmed": (403, "Số điện thoại chưa xác minh, vui lòng nhập mã OTP"),
    "user_banned": (403, "Tài khoản đã bị khóa"),
    "phone_exists": (409, "Số điện thoại này đã được đăng ký"),
    "user_already_exists": (409, "Số điện thoại này đã được đăng ký"),
    "weak_password": (422, "Mật khẩu quá yếu"),
    "validation_failed": (422, "Số điện thoại hoặc mật khẩu không hợp lệ"),
    "otp_expired": BAD_OTP,
    "otp_disabled": PHONE_UNAVAILABLE,
    "refresh_token_not_found": EXPIRED_SESSION,
    "refresh_token_already_used": EXPIRED_SESSION,
    "session_not_found": EXPIRED_SESSION,
    "session_expired": EXPIRED_SESSION,
    "bad_jwt": EXPIRED_SESSION,
    "phone_provider_disabled": PHONE_UNAVAILABLE,
    "signup_disabled": PHONE_UNAVAILABLE,
    "sms_send_failed": SMS_UNAVAILABLE,
    "over_request_rate_limit": TOO_MANY,
    "over_sms_send_rate_limit": TOO_MANY,
}


class AuthError(Exception):
    def __init__(self, status_code: int, message: str, code: str | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.message = message
        self.code = code


@dataclass
class AuthSession:
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    expires_at: int | None
    user_id: str
    phone: str | None


def _parse_session(data: dict[str, Any]) -> AuthSession:
    try:
        user = data["user"]
        return AuthSession(
            access_token=data["access_token"],
            refresh_token=data["refresh_token"],
            token_type=data.get("token_type") or "bearer",
            expires_in=data["expires_in"],
            expires_at=data.get("expires_at"),
            user_id=user["id"],
            phone=user.get("phone"),
        )
    except (KeyError, TypeError) as e:
        log.error("Supabase Auth trả phiên không đúng định dạng: thiếu %s", e)
        raise AuthError(503, "Dịch vụ đăng nhập đang gặp sự cố, vui lòng thử lại")


def _headers(client_ip: str | None) -> dict[str, str]:
    settings = get_settings()
    # Backend gọi Supabase thay cho mọi user nên Supabase thấy chung một IP và dễ chặn theo IP.
    # Có secret key thì báo IP thật của user (phải bật IP Address Forwarding trên Dashboard).
    if settings.supabase_secret_key:
        headers = {"apikey": settings.supabase_secret_key}
        if client_ip:
            headers["Sb-Forwarded-For"] = client_ip
        return headers
    if not settings.supabase_publishable_key:
        log.error("Thiếu SUPABASE_PUBLISHABLE_KEY")
        raise AuthError(503, "Dịch vụ đăng nhập chưa được cấu hình")
    return {"apikey": settings.supabase_publishable_key}


async def _post(
    path: str,
    body: dict[str, Any] | None,
    *,
    client_ip: str | None,
    unknown_error: tuple[int, str],
    params: dict[str, str] | None = None,
    bearer: str | None = None,
) -> dict[str, Any]:
    headers = _headers(client_ip)
    if bearer:
        headers["Authorization"] = f"Bearer {bearer}"
    url = f"{get_settings().supabase_url.rstrip('/')}/auth/v1/{path}"
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
            resp = await client.post(url, json=body, params=params, headers=headers)
    except httpx.HTTPError as e:
        log.warning("Không gọi được Supabase Auth (%s): %s", path, type(e).__name__)
        raise AuthError(503, "Dịch vụ đăng nhập đang gặp sự cố, vui lòng thử lại")

    try:
        data = resp.json() if resp.content else {}
    except ValueError:
        data = {}
    if not isinstance(data, dict):
        data = {}
    if resp.is_success:
        return data

    code = data.get("error_code") or data.get("error")
    log.info("Supabase Auth %s trả %s (%s)", path, resp.status_code, code)
    if code in ERRORS:
        raise AuthError(*ERRORS[code], code=code)
    if resp.status_code == 429:
        raise AuthError(*TOO_MANY, code=code)
    if resp.status_code >= 500:
        raise AuthError(503, "Dịch vụ đăng nhập đang gặp sự cố, vui lòng thử lại", code=code)
    raise AuthError(*unknown_error, code=code)


async def sign_up(phone: str, password: str, full_name: str, *, client_ip: str | None) -> AuthSession | None:
    """Tạo tài khoản. Trả None nếu cần xác minh OTP (Supabase đã gửi SMS)."""
    data = await _post(
        "signup",
        {"phone": phone, "password": password, "data": {"full_name": full_name}},
        client_ip=client_ip,
        unknown_error=(400, "Không đăng ký được, vui lòng kiểm tra lại thông tin"),
    )
    return _parse_session(data) if data.get("access_token") else None


async def verify_otp(phone: str, token: str, *, client_ip: str | None) -> AuthSession:
    data = await _post(
        "verify", {"type": "sms", "phone": phone, "token": token}, client_ip=client_ip, unknown_error=BAD_OTP
    )
    return _parse_session(data)


async def resend_otp(phone: str, *, client_ip: str | None) -> None:
    await _post("resend", {"type": "sms", "phone": phone}, client_ip=client_ip, unknown_error=SMS_UNAVAILABLE)


async def login(phone: str, password: str, *, client_ip: str | None) -> AuthSession:
    data = await _post(
        "token",
        {"phone": phone, "password": password},
        params={"grant_type": "password"},
        client_ip=client_ip,
        unknown_error=ERRORS["invalid_credentials"],
    )
    return _parse_session(data)


async def refresh(refresh_token: str, *, client_ip: str | None) -> AuthSession:
    data = await _post(
        "token",
        {"refresh_token": refresh_token},
        params={"grant_type": "refresh_token"},
        client_ip=client_ip,
        unknown_error=EXPIRED_SESSION,
    )
    return _parse_session(data)


async def logout(access_token: str, *, all_devices: bool = False, client_ip: str | None) -> None:
    """Thu hồi phiên. Phiên đã mất từ trước thì coi như đăng xuất thành công."""
    try:
        await _post(
            "logout",
            None,
            params={"scope": "global" if all_devices else "local"},
            bearer=access_token,
            client_ip=client_ip,
            unknown_error=EXPIRED_SESSION,
        )
    except AuthError as e:
        if e.status_code != EXPIRED_SESSION[0]:
            raise
