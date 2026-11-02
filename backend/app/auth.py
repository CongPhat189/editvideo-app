"""Xác thực: mobile đăng nhập bằng Supabase Auth rồi gửi access token
qua header `Authorization: Bearer <token>`. Backend kiểm tra chữ ký bằng
khóa công khai (JWKS) của project, không cần gọi Supabase mỗi request.

Lưu ý: backend kết nối DB bằng user postgres nên KHÔNG bị RLS chặn.
Mọi truy vấn phải tự lọc theo user.id lấy từ token.
"""

import uuid
from typing import Annotated, Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.concurrency import run_in_threadpool
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_session
from app.models import Profile

_bearer = HTTPBearer(auto_error=False)
_jwks_client: jwt.PyJWKClient | None = None


def _signing_key(token: str) -> Any:
    global _jwks_client
    settings = get_settings()
    if jwt.get_unverified_header(token).get("alg") == "HS256":
        if not settings.supabase_jwt_secret:
            raise jwt.InvalidTokenError("HS256 token but SUPABASE_JWT_SECRET is not set")
        return settings.supabase_jwt_secret
    if _jwks_client is None:
        _jwks_client = jwt.PyJWKClient(settings.jwks_url, cache_keys=True, lifespan=3600)
    return _jwks_client.get_signing_key_from_jwt(token).key


def decode_token(token: str) -> dict[str, Any]:
    return jwt.decode(
        token,
        _signing_key(token),
        algorithms=["ES256", "RS256", "HS256"],
        audience="authenticated",
        issuer=get_settings().jwt_issuer,
        options={"require": ["exp", "sub", "aud", "iss"]},
    )


def _unauthorized() -> HTTPException:
    return HTTPException(
        status.HTTP_401_UNAUTHORIZED, "Chưa đăng nhập hoặc phiên đã hết hạn", {"WWW-Authenticate": "Bearer"}
    )


async def _claims(credentials: HTTPAuthorizationCredentials | None) -> dict[str, Any]:
    if credentials is None:
        raise _unauthorized()
    try:
        return await run_in_threadpool(decode_token, credentials.credentials)
    except jwt.PyJWTError:
        raise _unauthorized()


async def verified_token(credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)]) -> str:
    """Access token đã kiểm tra chữ ký và hạn dùng (không tra DB). Dùng cho /auth/logout."""
    await _claims(credentials)
    return credentials.credentials


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Profile:
    claims = await _claims(credentials)
    try:
        user_id = uuid.UUID(claims["sub"])
        session_id = uuid.UUID(claims["session_id"]) if "session_id" in claims else None
    except (KeyError, TypeError, ValueError):
        raise _unauthorized()
    if claims.get("is_anonymous"):  # Supabase anonymous sign-in: không cho dùng API
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cần đăng nhập bằng số điện thoại")

    # JWT còn hạn vẫn hợp lệ về chữ ký sau khi đăng xuất, nên phải kiểm tra phiên còn tồn tại
    if session_id is not None:
        active = await session.scalar(
            text("select exists (select 1 from auth.sessions where id = :id and user_id = :user_id)"),
            {"id": session_id, "user_id": user_id},
        )
        if not active:
            raise _unauthorized()

    profile = await session.get(Profile, user_id)
    if profile is None:
        raise _unauthorized()
    if profile.status != "active":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Tài khoản đã bị khóa")
    return profile


CurrentUser = Annotated[Profile, Depends(get_current_user)]
Session = Annotated[AsyncSession, Depends(get_session)]
