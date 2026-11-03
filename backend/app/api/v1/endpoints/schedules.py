import uuid
from datetime import time
from typing import Annotated, Literal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, not_, select, update

from app.api.supabase_deps import CurrentUser, Session
from app.core.rate_limit import limiter
from app.integrations import goclaw
from app.models import Agent, Conversation, ScheduledTask
from app.schemas.schedule import ScheduleCreate, ScheduleOut
from app.services.schedule_worker import NOTICE_KIND

router = APIRouter(prefix="/schedules", tags=["schedules"])

NOT_FOUND = HTTPException(status.HTTP_404_NOT_FOUND, "Không tìm thấy lịch hẹn")
ACTIVE = ("scheduled", "retrying")
MAX_ACTIVE_PER_USER = 100  # Chặn đặt lịch gọi AI vô hạn (tốn tiền)
_IS_SCHEDULE = not_(ScheduledTask.payload.has_key("kind"))


async def _get_owned(session: Session, user_id: uuid.UUID, schedule_id: uuid.UUID) -> ScheduledTask:
    task = await session.scalar(
        select(ScheduledTask).where(ScheduledTask.id == schedule_id, ScheduledTask.user_id == user_id, _IS_SCHEDULE)
    )
    if task is None:
        raise NOT_FOUND
    return task


@router.post("", response_model=ScheduleOut, status_code=status.HTTP_201_CREATED)
async def create_schedule(body: ScheduleCreate, user: CurrentUser, session: Session):
    """Đặt lịch trong cuộc trò chuyện đang mở.

    Không có content: lưu lịch, worker gửi ngay trong nền tin "hẹn lịch đăng vào ..." cho agent.
    Tin này không hiện trong khung chat, câu trả lời của agent thì có.
    Có content: đến giờ worker mới gửi content cho agent.
    """
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
    if body.content is None:
        # Dùng chung cơ chế gửi của worker để có thử lại khi agent bận. Lưu cùng transaction với lịch.
        # Tốn lượt gọi AI như một tin chat thường.
        limiter.hit(f"send:minute:{user.id}", 20, 60)
        limiter.hit(f"send:hour:{user.id}", 300, 3600)
        where_to = f"lên {', '.join(body.platforms)} " if body.platforms else ""
        session.add(
            ScheduledTask(
                user_id=user.id,
                conversation_id=conv.id,
                agent_id=conv.agent_id,
                task_name=f"Báo hẹn lịch {when}",
                task_type="send_message",
                payload={"content": f"hẹn lịch đăng {where_to}vào {when}", "kind": NOTICE_KIND},
                scheduled_at=func.now(),
                timezone=body.timezone,
            )
        )
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
    query = select(ScheduledTask).where(ScheduledTask.user_id == user.id, _IS_SCHEDULE)
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
