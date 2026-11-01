from __future__ import annotations

from pydantic import BaseModel


class SchedulePayload(BaseModel):
    user_id: int | None = None
    title: str | None = None
    description: str | None = None
    scheduled_at: str | None = None
    platform: str = "facebook"
    payload: dict | None = None
