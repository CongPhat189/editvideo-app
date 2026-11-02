"""Mật khẩu (Argon2id) và JWT của app mobile. Tách khỏi app/core/security.py, vốn chỉ dùng cho API demo /api/*.

Sơ đồ không có bảng phiên nên token không thu hồi riêng lẻ được. Vì vậy mỗi token mang dấu vân tay của
password_hash: đổi mật khẩu thì mọi token cũ, gồm cả refresh token bị lộ, hết tác dụng ngay.
"""

import hashlib
import hmac
import time
import uuid
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Literal

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.core.config import SupabaseNotConfigured, get_settings

ALGORITHM = "HS256"
ISSUER = "goclaw-backend"
AUDIENCE = "goclaw-mobile"
MIN_SECRET_LENGTH = 32

TokenType = Literal["access", "refresh"]

_hasher = PasswordHasher()  # mặc định là Argon2id


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


@lru_cache
def _dummy_hash() -> str:
    return _hasher.hash("mat-khau-gia-de-do-thoi-gian")


def burn_verify_time(password: str) -> None:
    """Số chưa đăng ký cũng tốn thời gian như sai mật khẩu, để không dò được số nào đã có tài khoản."""
    verify_password(password, _dummy_hash())


def _secret() -> str:
    secret = get_settings().auth_jwt_secret
    if not secret or len(secret) < MIN_SECRET_LENGTH:
        raise SupabaseNotConfigured(f"AUTH_JWT_SECRET phải có ít nhất {MIN_SECRET_LENGTH} ký tự")
    return secret


def password_fingerprint(password_hash: str) -> str:
    return hmac.new(_secret().encode(), password_hash.encode(), hashlib.sha256).hexdigest()[:32]


def fingerprint_matches(claims: dict[str, Any], password_hash: str) -> bool:
    return hmac.compare_digest(str(claims.get("pwf", "")), password_fingerprint(password_hash))


def _encode(user_id: uuid.UUID, password_hash: str, token_type: TokenType, lifetime: int, now: int) -> str:
    return jwt.encode(
        {
            "sub": str(user_id),
            "typ": token_type,
            "pwf": password_fingerprint(password_hash),
            "iss": ISSUER,
            "aud": AUDIENCE,
            "iat": now,
            "exp": now + lifetime,
            "jti": uuid.uuid4().hex,
        },
        _secret(),
        algorithm=ALGORITHM,
    )


@dataclass
class TokenPair:
    access_token: str
    refresh_token: str
    expires_in: int
    expires_at: int


def issue_tokens(user_id: uuid.UUID, password_hash: str) -> TokenPair:
    settings = get_settings()
    now = int(time.time())
    access_lifetime = settings.access_token_minutes * 60
    return TokenPair(
        access_token=_encode(user_id, password_hash, "access", access_lifetime, now),
        refresh_token=_encode(user_id, password_hash, "refresh", settings.refresh_token_days * 86400, now),
        expires_in=access_lifetime,
        expires_at=now + access_lifetime,
    )


def decode_token(token: str, expected_type: TokenType) -> dict[str, Any]:
    """Ném jwt.PyJWTError nếu token sai chữ ký, hết hạn hoặc sai loại (refresh token không dùng gọi API được)."""
    claims = jwt.decode(
        token,
        _secret(),
        algorithms=[ALGORITHM],
        audience=AUDIENCE,
        issuer=ISSUER,
        options={"require": ["exp", "iat", "sub", "aud", "iss", "typ", "pwf"]},
    )
    if claims["typ"] != expected_type:
        raise jwt.InvalidTokenError("sai loại token")
    return claims
