from __future__ import annotations

from typing import Any

import jwt
from fastapi import Header, HTTPException

from app.core.security import decode_token
from app.db.session import get_db

__all__ = ["get_db", "get_current_user"]


def get_current_user(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    """Đọc JWT từ header `Authorization: Bearer <token>`. Gắn vào route nào cần đăng nhập."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail={"message": "Chưa đăng nhập."})
    try:
        return decode_token(authorization.split(" ", 1)[1])
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail={"message": "Token không hợp lệ."}) from exc
