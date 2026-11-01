from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.core.security import build_token, hash_password, verify_password
from app.repositories.user_repository import get_user_by_id
from app.services.user_service import create_account, create_user_profile, get_account_by_email, get_user_by_email

__all__ = ["build_token", "hash_password", "login_user", "register_user", "login_google_user", "send_reset_password"]


def login_user(db: Session, email: str, password: str) -> dict[str, Any]:
    normalized_email = email.strip().lower()
    account = get_account_by_email(db, normalized_email, provider="local")
    if account is None or not verify_password(password, account.password_hash):
        raise ValueError("Email hoặc mật khẩu không hợp lệ.")

    user = get_user_by_id(db, account.user_id)
    payload = {"id": user.id, "name": user.full_name, "email": user.email, "role": "admin"}
    return {"message": "Đăng nhập thành công", "token": build_token(payload), "user": payload}


def register_user(db: Session, full_name: str, email: str, password: str, phone: str | None = None) -> dict[str, Any]:
    normalized_email = email.strip().lower()
    if not normalized_email or "@" not in normalized_email or len(password.strip()) < 6:
        raise ValueError("Email hoặc mật khẩu không hợp lệ.")

    user = get_user_by_email(db, normalized_email)
    if user is None:
        user = create_user_profile(db, full_name or "User", normalized_email, phone)

    account = get_account_by_email(db, normalized_email, provider="local")
    if account is None:
        create_account(db, user.id, normalized_email, hash_password(password), provider="local")
    else:
        account.password_hash = hash_password(password)
        db.commit()

    payload = {"id": user.id, "name": user.full_name, "email": user.email, "role": "admin"}
    return {"message": "Tạo tài khoản thành công", "token": build_token(payload), "user": payload}


def login_google_user(db: Session, email: str, name: str | None) -> dict[str, Any]:
    normalized_email = email.strip().lower()
    user = get_user_by_email(db, normalized_email)
    if user is None:
        user = create_user_profile(db, name or "Google User", normalized_email)

    account = get_account_by_email(db, normalized_email, provider="google")
    if account is None:
        create_account(db, user.id, normalized_email, None, provider="google")

    payload = {"id": user.id, "name": user.full_name, "email": user.email, "role": "editor"}
    return {"message": "Đăng nhập Google thành công", "token": build_token(payload), "user": payload}


def send_reset_password(email: str) -> dict[str, Any]:
    return {"message": f"Link đặt lại mật khẩu đã được gửi tới {email}.", "success": True}
