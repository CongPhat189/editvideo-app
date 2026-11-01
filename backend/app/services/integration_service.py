from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models import IntegrationConfig
from app.repositories import integration_repository


def save_integration(db: Session, user_id: int, provider: str, name: str, api_key: str | None = None, api_secret: str | None = None, base_url: str | None = None, project_id: str | None = None, config_json: dict | None = None) -> IntegrationConfig:
    record = integration_repository.get_by_user_and_provider(db, user_id, provider)

    if record is None:
        record = IntegrationConfig(
            user_id=user_id,
            provider=provider,
            name=name,
            api_key=api_key,
            api_secret=api_secret,
            base_url=base_url,
            project_id=project_id,
            config_json=config_json or {},
            is_active=True,
        )
        db.add(record)
    else:
        record.name = name
        record.api_key = api_key
        record.api_secret = api_secret
        record.base_url = base_url
        record.project_id = project_id
        record.config_json = config_json or {}
        record.is_active = True

    db.commit()
    db.refresh(record)
    return record


def list_integrations(db: Session, user_id: int | None = None) -> list[dict[str, Any]]:
    return [
        {
            "id": item.id,
            "user_id": item.user_id,
            "provider": item.provider,
            "name": item.name,
            "base_url": item.base_url,
            "project_id": item.project_id,
            "is_active": item.is_active,
            "config_json": item.config_json,
        }
        for item in integration_repository.get_integrations(db, user_id)
    ]
