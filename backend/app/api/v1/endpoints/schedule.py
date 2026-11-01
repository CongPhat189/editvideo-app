from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.schedule import SchedulePayload
from app.services.schedule_service import create_schedule, list_schedules

router = APIRouter(tags=["schedule"])



@router.get("/api/schedule")
def get_schedule(user_id: int | None = None, db: Session = Depends(get_db)) -> dict:
    return {"data": list_schedules(db, user_id=user_id)}


@router.post("/api/schedule")
def create_schedule_record(payload: SchedulePayload, db: Session = Depends(get_db)) -> dict:
    if not payload.title or not payload.scheduled_at:
        raise HTTPException(status_code=400, detail={"message": "Thiếu thông tin lịch đăng."})

    user_id = payload.user_id or 1
    record = create_schedule(db, user_id, payload.title, payload.scheduled_at, payload.platform, payload.description, payload.payload)
    return {"message": "Lịch đăng đã được tạo.", "item": {
        "id": record.id,
        "user_id": record.user_id,
        "title": record.title,
        "scheduled_at": record.scheduled_at.isoformat(),
        "status": record.status,
        "platform": record.platform,
        "payload": record.payload,
    }}
