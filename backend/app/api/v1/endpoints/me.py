from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import selectinload

from app.api.supabase_deps import CurrentUser, Session
from app.core.errors import pg_error
from app.models import AppUser, UserSetting
from app.schemas.mobile import MeOut, MeUpdate, SettingsOut, SettingsUpdate

router = APIRouter(prefix="/me", tags=["me"])


async def _load_me(session: Session, user_id) -> AppUser:
    return await session.scalar(
        select(AppUser)
        .where(AppUser.id == user_id)
        .options(selectinload(AppUser.settings))
        .execution_options(populate_existing=True)
    )


@router.get("", response_model=MeOut)
async def get_me(user: CurrentUser, session: Session):
    return await _load_me(session, user.id)


@router.patch("", response_model=MeOut)
async def update_me(body: MeUpdate, user: CurrentUser, session: Session):
    data = body.model_dump(exclude_unset=True)
    if "full_name" in data:
        if data["full_name"] is None:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Tên không được để trống")
        user.full_name = data["full_name"]
    if "avatar_url" in data:
        user.avatar_url = data["avatar_url"]
    await session.commit()
    return await _load_me(session, user.id)


@router.patch("/settings", response_model=SettingsOut)
async def update_settings(body: SettingsUpdate, user: CurrentUser, session: Session):
    settings = await session.scalar(select(UserSetting).where(UserSetting.user_id == user.id))
    if settings is None:
        settings = UserSetting(user_id=user.id)
        session.add(settings)
    for field, value in body.model_dump(exclude_unset=True, exclude_none=True).items():
        setattr(settings, field, value)
    try:
        await session.commit()
    except DBAPIError as e:
        await session.rollback()
        sqlstate, _ = pg_error(e)
        if sqlstate == "22023":  # trigger validate_timezone
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Múi giờ không hợp lệ")
        raise
    await session.refresh(settings)
    return settings
