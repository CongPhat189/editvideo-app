from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.schemas.content import PublishingRequest
from app.db.mock_data import state
from app.utils.helpers import new_id, normalize_platforms

router = APIRouter(tags=["publishing"])


@router.post("/api/publishing")
def publishing(payload: PublishingRequest) -> dict:
    content = (payload.content or "").strip()
    normalized_platforms = normalize_platforms(payload.platforms or [])

    if not content:
        raise HTTPException(status_code=400, detail={"message": "Chưa có nội dung để đăng."})
    if not normalized_platforms:
        raise HTTPException(status_code=400, detail={"message": "Hãy chọn ít nhất một nền tảng để đăng."})

    entry = {
        "id": new_id(),
        "time": "20:00",
        "title": content[:60] or "Video AI",
        "channels": normalized_platforms,
        "status": "Đã lên lịch",
        "type": "scheduled",
    }

    state["schedule"].setdefault(14, [])
    state["schedule"][14] = [entry] + state["schedule"][14]
    return {"message": f"Đã gửi yêu cầu đăng bài lên {', '.join(normalized_platforms)}.", "item": entry}
