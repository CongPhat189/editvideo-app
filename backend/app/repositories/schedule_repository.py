from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Schedule


def get_schedules(db: Session, user_id: int | None = None) -> list[Schedule]:
    query = select(Schedule)
    if user_id is not None:
        query = query.where(Schedule.user_id == user_id)
    return list(db.execute(query).scalars().all())


def add(db: Session, schedule: Schedule) -> Schedule:
    db.add(schedule)
    db.commit()
    db.refresh(schedule)
    return schedule
