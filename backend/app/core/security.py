from __future__ import annotations

import hashlib
from typing import Any

import jwt

from app.core.config import settings


def hash_password(password: str) -> str:
    return hashlib.sha256(password.strip().encode("utf-8")).hexdigest()


def verify_password(password: str, password_hash: str | None) -> bool:
    return password_hash is not None and hash_password(password) == password_hash


def build_token(user: dict[str, Any]) -> str:
    return jwt.encode({"sub": user["id"], "email": user["email"]}, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
