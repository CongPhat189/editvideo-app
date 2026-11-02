from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.integration import ConnectorPayload
from app.services.integration_service import list_integrations, save_integration

router = APIRouter(tags=["platforms"])



@router.get("/api/platforms")
def platforms(db: Session = Depends(get_db)) -> dict:
    user_id = 1
    return {
        "channels": [
            {"name": "Facebook", "description": "Fanpage", "icon": "f", "color": "#1877F2", "status": "Đã kết nối", "type": "connected"},
            {"name": "YouTube", "description": "Kênh demo", "icon": "▶", "color": "#FF0000", "status": "Đã kết nối", "type": "connected"},
            {"name": "TikTok", "description": "@demo", "icon": "♪", "color": "#101827", "status": "Hết hạn", "type": "expired"},
            {"name": "Instagram", "description": "Chưa kết nối", "icon": "IG", "color": "#E1306C", "status": "Kết nối", "type": "disconnected"},
            {"name": "Website", "description": "example.com/blog", "icon": "W", "color": "#526783", "status": "Đã kết nối", "type": "connected"},
        ],
        "notifications": [
            {"name": "Thông báo trên app", "icon": "♧", "enabled": True},
            {"name": "Zalo", "icon": "◉", "enabled": True},
            {"name": "Telegram", "icon": "➤", "enabled": False},
        ],
        "connectors": list_integrations(db, user_id),
    }


@router.post("/api/connectors/{provider}")
def save_connector(provider: str, payload: ConnectorPayload, db: Session = Depends(get_db)) -> dict:
    user_id = payload.user_id or 1
    record = save_integration(
        db,
        user_id=user_id,
        provider=provider.lower(),
        name=payload.name,
        api_key=payload.api_key,
        api_secret=payload.api_secret,
        base_url=payload.base_url,
        project_id=payload.project_id,
        config_json=payload.config_json,
    )
    return {"message": "Kết nối đã được lưu.", "item": {
        "id": record.id,
        "provider": record.provider,
        "name": record.name,
        "base_url": record.base_url,
        "project_id": record.project_id,
        "is_active": record.is_active,
    }}


@router.get("/api/connectors")
def list_connectors(db: Session = Depends(get_db), user_id: int | None = None) -> dict:
    return {"items": list_integrations(db, user_id)}
