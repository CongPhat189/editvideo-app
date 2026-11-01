from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import IntegrationConfig


def get_by_user_and_provider(db: Session, user_id: int, provider: str) -> IntegrationConfig | None:
    return db.execute(
        select(IntegrationConfig).where(IntegrationConfig.user_id == user_id, IntegrationConfig.provider == provider)
    ).scalar_one_or_none()


def get_integrations(db: Session, user_id: int | None = None) -> list[IntegrationConfig]:
    query = select(IntegrationConfig)
    if user_id is not None:
        query = query.where(IntegrationConfig.user_id == user_id)
    return list(db.execute(query).scalars().all())
