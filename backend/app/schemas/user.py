from __future__ import annotations

from pydantic import BaseModel


class UserOut(BaseModel):
    id: int
    full_name: str
    email: str
    phone: str | None = None
    avatar_url: str | None = None
    is_active: bool
    created_at: str
