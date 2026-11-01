from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.services.user_service import list_users

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("")
def get_users(db: Session = Depends(get_db)) -> dict:
    return {"items": list_users(db)}
