import uuid
from datetime import time
from typing import Annotated, Literal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, not_, select, update

from app.api.supabase_deps import CurrentUser, Session
from app.core.rate_limit import limiter
from app.integrations import goclaw
from app.models import Agent, Conversation, Message, ScheduledTask
from app.schemas.schedule import ScheduleCreate, ScheduleOut
from app.services.schedule_worker import NOTICE_KIND

router = APIRouter(prefix="/schedules", tags=["schedules"])

NOT_FOUND = HTTPException(status.HTTP_404_NOT_FOUND, "Không tìm thấy lịch hẹn")
ACTIVE = ("scheduled", "retrying")
MAX_ACTIVE_PER_USER = 100  # Chặn đặt lịch gọi AI vô hạn (tốn tiền)
_IS_SCHEDULE = not_(ScheduledTask.payload.has_key("kind"))


def _publish_instruction(content: str, platforms: list[str], when: str, timezone: str) -> str:
    channels = ", ".join(platforms) if platforms else "các nền tảng đã chọn trong lịch"
    return (
        "LỆNH ĐĂNG ĐÃ ĐƯỢC NGƯỜI DÙNG XÁC NHẬN TỪ TRƯỚC. Bây giờ đã đến giờ đăng. Hãy gọi công cụ/tích hợp đăng bài "
        f"thật để đăng ngay nội dung bên dưới lên {channels}: {when} ({timezone}). Không hỏi lại, không xin xác nhận, "
        "không chỉ tạo bản nháp, không viết lại hoặc thêm lời dẫn. Hãy đăng nguyên văn nội dung. "
        "Chỉ báo thành công sau khi nền tảng xác nhận đã đăng; nếu không thể đăng, trả lỗi cụ thể, không giả vờ đã đăng. "
        "Sau khi thực hiện, chỉ trả một câu ngắn báo kết quả, không hỏi thêm.\n\n"
        "--- BẮT ĐẦU NỘI DUNG CẦN ĐĂNG ---\n"
        f"{content}\n"
        "--- KẾT THÚC NỘI DUNG CẦN ĐĂNG ---"
    )


def _schedule_confirmation(platforms: list[str], when: str, timezone: str) -> str:
    channels = ", ".join(platforms) if platforms else "chưa chọn nền tảng"
    return (
        "HỆ THỐNG ĐÃ LƯU LỊCH ĐĂNG THEO XÁC NHẬN CỦA NGƯỜI DÙNG. "
        f"Thời gian: {when} ({timezone}). Nền tảng: {channels}. "
        "Nội dung và ảnh đính kèm (nếu có) đã được lưu. Đến giờ, hệ thống sẽ gửi lại lệnh đăng. "
        "Bây giờ chỉ trả lời đúng một câu xác nhận ngắn, nêu rõ ngày giờ và nền tảng. "
        "Không hỏi người dùng bất kỳ câu nào, không yêu cầu xác nhận thêm, không đăng bài ngay lúc này."
    )


async def _get_owned(session: Session, user_id: uuid.UUID, schedule_id: uuid.UUID) -> ScheduledTask:
    task = await session.scalar(
        select(ScheduledTask).where(ScheduledTask.id == schedule_id, ScheduledTask.user_id == user_id, _IS_SCHEDULE)
    )
    if task is None:
        raise NOT_FOUND
    return task


@router.post("", response_model=ScheduleOut, status_code=status.HTTP_201_CREATED)
async def create_schedule(body: ScheduleCreate, user: CurrentUser, session: Session):
    """Lưu lịch, gửi một yêu cầu xác nhận giờ cho agent và giao lệnh đăng khi tới hạn."""
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
    if (body.content_message_id is not None or body.content is not None) and not body.platforms:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Chọn ít nhất một nền tảng để đăng nội dung đã lên lịch",
        )
    if body.content_message_id is not None:
        content_message = await session.scalar(
            select(Message).where(
                Message.id == body.content_message_id,
                Message.conversation_id == conv.id,
                Message.user_id == user.id,
                Message.role == "assistant",
                Message.status == "completed",
                Message.content.is_not(None),
                func.length(func.btrim(Message.content)) > 0,
            )
        )
        if content_message is None:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                "content_message_id phải là phản hồi assistant đã hoàn tất trong cuộc trò chuyện này",
            )
        scheduled_content = content_message.content
        source_message = None
        if content_message.reply_to_message_id is not None:
            source_message = await session.scalar(
                select(Message).where(
                    Message.id == content_message.reply_to_message_id,
                    Message.conversation_id == conv.id,
                    Message.user_id == user.id,
                    Message.role == "user",
                )
            )
        image_attachments = [
            {
                "file_path": item.file_path,
                "file_name": item.file_name,
                "mime_type": item.mime_type,
            }
            for item in (source_message.attachments if source_message is not None else [])
            if item.mime_type.startswith("image/")
        ]
    else:
        scheduled_content = body.content
        image_attachments = []
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
            _IS_SCHEDULE,
        )
    )
    if active >= MAX_ACTIVE_PER_USER:
        raise HTTPException(status.HTTP_409_CONFLICT, f"Chỉ được có tối đa {MAX_ACTIVE_PER_USER} lịch đang chờ")

    local = body.scheduled_at.astimezone(ZoneInfo(body.timezone))
    when = local.strftime("%d/%m/%Y" if local.time() == time.min else "%d/%m/%Y %H:%M")
    task = ScheduledTask(
        user_id=user.id,
        conversation_id=conv.id,
        content_message_id=body.content_message_id,
        agent_id=conv.agent_id,
        task_name=body.task_name or (scheduled_content.strip()[:60] if scheduled_content else f"Lịch {when}"),
        task_type="send_message",
        payload=(
            {
                "content": scheduled_content,
                "agent_instruction": _publish_instruction(scheduled_content, body.platforms, when, body.timezone),
                "media": image_attachments,
            }
            if scheduled_content
            else {}
        ),
        platforms=body.platforms,
        scheduled_at=body.scheduled_at,
        timezone=body.timezone,
    )
    session.add(task)
    session.add(
        ScheduledTask(
            user_id=user.id,
            conversation_id=conv.id,
            agent_id=conv.agent_id,
            task_name=f"Xác nhận lịch đăng {when}",
            task_type="send_message",
            payload={
                "content": _schedule_confirmation(body.platforms, when, body.timezone),
                "kind": NOTICE_KIND,
            },
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
