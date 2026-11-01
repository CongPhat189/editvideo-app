from __future__ import annotations

from pydantic import BaseModel


class ConnectorPayload(BaseModel):
    user_id: int | None = None
    provider: str
    name: str
    api_key: str | None = None
    api_secret: str | None = None
    base_url: str | None = None
    project_id: str | None = None
    config_json: dict | None = None
