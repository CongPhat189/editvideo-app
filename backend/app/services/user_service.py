from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models import Account, User
from app.repositories import user_repository
from app.repositories.user_repository import get_account_by_email, get_user_by_email

__all__ = ["create_user_profile", "create_account", "get_user_by_email", "get_account_by_email", "list_users"]


def create_user_profile(db: Session, full_name: str, email: str, phone: str | None = None) -> User:
    email = email.strip().lower()
    user = get_user_by_email(db, email)
    if user is None:
        user = user_repository.add(db, User(full_name=full_name.strip(), email=email, phone=phone, is_active=True))
    return user


def create_account(db: Session, user_id: int, email: str, password_hash: str | None = None, provider: str = "local") -> Account:
    email = email.strip().lower()
    account = get_account_by_email(db, email, provider=provider)
    if account is None:
        account = user_repository.add(
            db, Account(user_id=user_id, provider=provider, email=email, password_hash=password_hash, is_active=True)
        )
    return account


def list_users(db: Session) -> list[dict[str, Any]]:
    return [
        {
            "id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "phone": user.phone,
            "avatar_url": user.avatar_url,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat(),
        }
        for user in user_repository.get_all_users(db)
    ]
