from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Account, User


def get_user_by_id(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.execute(select(User).where(User.email == email.strip().lower())).scalar_one_or_none()


def get_account_by_email(db: Session, email: str, provider: str = "local") -> Account | None:
    return db.execute(
        select(Account).where(Account.provider == provider, Account.email == email.strip().lower())
    ).scalar_one_or_none()


def get_all_users(db: Session) -> list[User]:
    return list(db.execute(select(User)).scalars().all())


def add(db: Session, obj):
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj
