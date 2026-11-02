"""Xác thực API mobile: `Authorization: Bearer <access_token>` do chính backend cấp (app/core/mobile_security.py).

Lưu ý: backend kết nối DB bằng user postgres nên KHÔNG bị RLS chặn.
Mọi truy vấn phải tự lọc theo user.id lấy từ token.
"""

import uuid
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.mobile_security import decode_token, fingerprint_matches
from app.db.supabase import get_session
from app.models import AppUser

_bearer = HTTPBearer(auto_error=False)


def unauthorized() -> HTTPException:
    return HTTPException(
        status.HTTP_401_UNAUTHORIZED, "Chưa đăng nhập hoặc phiên đã hết hạn", {"WWW-Authenticate": "Bearer"}
    )


async def load_token_user(session: AsyncSession, token: str, token_type) -> AppUser:
    """Token hợp lệ và tài khoản còn dùng được. Kiểm tra lại DB mỗi lần nên khóa tài khoản có hiệu lực ngay."""
    try:
        claims = decode_token(token, token_type)
        user_id = uuid.UUID(claims["sub"])
    except (jwt.PyJWTError, TypeError, ValueError):
        raise unauthorized()
    user = await session.get(AppUser, user_id)
    if (
        user is None
        or user.status == "deleted"
        or not fingerprint_matches(claims, user.password_hash)
        or claims["ver"] != user.token_version
    ):
        raise unauthorized()
    if user.status != "active":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Tài khoản đã bị khóa")
    return user


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AppUser:
    if credentials is None:
        raise unauthorized()
    return await load_token_user(session, credentials.credentials, "access")


CurrentUser = Annotated[AppUser, Depends(get_current_user)]
Session = Annotated[AsyncSession, Depends(get_session)]
