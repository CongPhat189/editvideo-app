import re

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import selectinload

from app.auth import CurrentUser, Session
from app.errors import pg_error
from app.models import Profile, UserSetting
from app.schemas import MeOut, MeUpdate, SettingsOut, SettingsUpdate

router = APIRouter(prefix="/me", tags=["me"])

AVATAR_FILE = re.compile(r"[A-Za-z0-9_-][A-Za-z0-9._-]{0,199}")


async def _load_me(session: Session, user: Profile) -> Profile:
    return await session.scalar(
        select(Profile)
        .where(Profile.id == user.id)
        .options(selectinload(Profile.settings))
        .execution_options(populate_existing=True)
    )


@router.get("", response_model=MeOut)
async def get_me(user: CurrentUser, session: Session):
    return await _load_me(session, user)


@router.patch("", response_model=MeOut)
async def update_me(body: MeUpdate, user: CurrentUser, session: Session):
    data = body.model_dump(exclude_unset=True)
    if "full_name" in data:
        if data["full_name"] is None:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Tên không được để trống")
        user.full_name = data["full_name"]
    if "avatar_path" in data:
        path = data["avatar_path"]
        # Ảnh phải nằm ngay trong thư mục của chính mình trên bucket avatars: {user_id}/{tên file}
        folder = f"{user.id}/"
        if path is not None and not (path.startswith(folder) and AVATAR_FILE.fullmatch(path[len(folder):])):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "avatar_path phải có dạng {user_id}/{tên file}")
        user.avatar_path = path
    await session.commit()
    return await _load_me(session, user)


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
