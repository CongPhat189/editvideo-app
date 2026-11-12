import uuid
from datetime import time
from typing import Annotated, Literal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select, update

from app.api.supabase_deps import CurrentUser, Session
from app.core.rate_limit import limiter
from app.integrations import goclaw
from app.models import Agent, Conversation, ScheduledTask
from app.schemas.schedule import ScheduleCreate, ScheduleOut

router = APIRouter(prefix="/schedules", tags=["schedules"])

NOT_FOUND = HTTPException(status.HTTP_404_NOT_FOUND, "Không tìm thấy lịch hẹn")
ACTIVE = ("scheduled", "retrying")
MAX_ACTIVE_PER_USER = 100  # Chặn đặt lịch gọi AI vô hạn (tốn tiền)


async def _get_owned(session: Session, user_id: uuid.UUID, schedule_id: uuid.UUID) -> ScheduledTask:
    task = await session.scalar(
        select(ScheduledTask).where(ScheduledTask.id == schedule_id, ScheduledTask.user_id == user_id)
    )
    if task is None:
        raise NOT_FOUND
    return task


@router.post("", response_model=ScheduleOut, status_code=status.HTTP_201_CREATED)
async def create_schedule(body: ScheduleCreate, user: CurrentUser, session: Session):
    """Lưu content + giờ + nền tảng. Đến giờ worker gửi content đó cho agent để đăng."""
    limiter.hit(f"schedule-create:{user.id}", 30, 60)
    conv = await session.scalar(
        select(Conversation).where(
            Conversation.id == body.conversation_id,
            Conversation.user_id == user.id,
            Conversation.deleted_at.is_(None),
        )
    )
    if conv is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Không tìm thấy cuộc trò chuyện")
    if conv.status != "active":
        raise HTTPException(status.HTTP_409_CONFLICT, "Cuộc trò chuyện đã lưu trữ, bỏ lưu trữ để đặt lịch")
    if body.content is not None and not body.platforms:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Chọn ít nhất một nền tảng để đăng")
    # Báo lỗi cấu hình ngay lúc đặt, không đợi tới giờ gửi
    try:
        goclaw.resolve_target(await session.get(Agent, conv.agent_id))
    except goclaw.GoClawError as e:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(e))
    active = await session.scalar(
        select(func.count())
        .select_from(ScheduledTask)
        .where(
            ScheduledTask.user_id == user.id,
            ScheduledTask.status.in_(ACTIVE),
            ScheduledTask.payload.has_key("content"),
        )
    )
    if active >= MAX_ACTIVE_PER_USER:
        raise HTTPException(status.HTTP_409_CONFLICT, f"Chỉ được có tối đa {MAX_ACTIVE_PER_USER} lịch đang chờ")

    local = body.scheduled_at.astimezone(ZoneInfo(body.timezone))
    when = local.strftime("%d/%m/%Y" if local.time() == time.min else "%d/%m/%Y %H:%M")
    task = ScheduledTask(
        user_id=user.id,
        conversation_id=conv.id,
        agent_id=conv.agent_id,
        task_name=body.task_name or (body.content.strip()[:60] if body.content else f"Lịch {when}"),
        task_type="send_message",
        payload={"content": body.content} if body.content else {},
        platforms=body.platforms,
        scheduled_at=body.scheduled_at,
        timezone=body.timezone,
    )
    session.add(task)
    await session.commit()
    await session.refresh(task)
    return ScheduleOut.from_task(task)


@router.get("", response_model=list[ScheduleOut])
async def list_schedules(
    user: CurrentUser,
    session: Session,
    status_: Annotated[
        Literal["scheduled", "processing", "retrying", "completed", "failed", "cancelled"] | None,
        Query(alias="status"),
    ] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 30,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    """Lịch mới nhất trước."""
    query = select(ScheduledTask).where(ScheduledTask.user_id == user.id)
    if status_ is not None:
        query = query.where(ScheduledTask.status == status_)
    rows = await session.scalars(
        query.order_by(ScheduledTask.scheduled_at.desc(), ScheduledTask.id).limit(limit).offset(offset)
    )
    return [ScheduleOut.from_task(task) for task in rows.all()]


@router.get("/{schedule_id}", response_model=ScheduleOut)
async def get_schedule(schedule_id: uuid.UUID, user: CurrentUser, session: Session):
    return ScheduleOut.from_task(await _get_owned(session, user.id, schedule_id))


@router.delete("/{schedule_id}", response_model=ScheduleOut)
async def cancel_schedule(schedule_id: uuid.UUID, user: CurrentUser, session: Session):
    """Hủy lịch chưa gửi. Lịch đang gửi hoặc đã xong thì không hủy được."""
    user_id = user.id
    task = await _get_owned(session, user_id, schedule_id)
    # Ghi có điều kiện ngay trong SQL: worker có thể vừa nhận lịch này
    result = await session.execute(
        update(ScheduledTask)
        .where(ScheduledTask.id == schedule_id, ScheduledTask.status.in_(ACTIVE))
        .values(status="cancelled", next_retry_at=None)
        .execution_options(synchronize_session=False)
    )
    await session.commit()
    if not result.rowcount:
        raise HTTPException(status.HTTP_409_CONFLICT, "Lịch đang gửi hoặc đã kết thúc, không hủy được")
    await session.refresh(task)
    return ScheduleOut.from_task(task)
