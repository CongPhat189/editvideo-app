from __future__ import annotations

from fastapi import APIRouter

from app.db.mock_data import state

router = APIRouter(tags=["dashboard"])


@router.get("/api/dashboard")
def dashboard() -> dict:
    return {
        "videos": state["videos"],
        "filters": [
            {"label": "Tất cả", "value": "all", "count": 12},
            {"label": "Show tính năng", "value": "feature", "count": 6},
            {"label": "Quan điểm", "value": "opinion", "count": 4},
        ],
    }
