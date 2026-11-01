from __future__ import annotations

from typing import Any

from app.core.config import settings
from app.integrations.external_api import request_json


class GoClawClient:
    """Client kết nối GoClaw API. Bổ sung endpoint thật khi có tài liệu API."""

    def __init__(self, base_url: str | None = None, api_key: str | None = None) -> None:
        self.base_url = (base_url or settings.GOCLAW_BASE_URL).rstrip("/")
        self.api_key = api_key or settings.GOCLAW_API_KEY

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}

    def get(self, path: str) -> dict[str, Any]:
        return request_json("GET", f"{self.base_url}/{path.lstrip('/')}", headers=self._headers())

    def post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        return request_json("POST", f"{self.base_url}/{path.lstrip('/')}", payload, headers=self._headers())
