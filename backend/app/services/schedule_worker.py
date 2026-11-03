"""Worker nền: đến giờ thì gửi tin của scheduled_tasks cho agent, chạy cùng tiến trình API.

Chạy nhiều tiến trình vẫn an toàn: FOR UPDATE SKIP LOCKED bảo đảm mỗi lịch chỉ một worker nhận.

Chỉ tự gửi lại khi chắc chắn GoClaw chưa nhận tin (GoClawError.retryable) hoặc cuộc trò chuyện đang bận.
Agent có thể đăng bài thật, nên hết giờ chờ hay worker chết giữa chừng đều báo failed, không gửi lại.
"""

import asyncio
import os
import socket
import uuid
from datetime import timedelta

from sqlalchemy import and_, func, or_, select, update

from app.core.config import get_settings
from app.core.logging import logger
from app.db.supabase import get_sessionmaker
from app.integrations import goclaw
from app.models import Agent, AppUser, Conversation, ScheduledTask, ScheduledTaskLog
from app.services import chat_service

WORKER_ID = f"{socket.gethostname()}:{os.getpid()}"[:100]
MAX_CONCURRENT = 5
RETRY_DELAY_SECONDS = 60
NOTICE_KIND = "schedule_notice"  # Tin báo gửi ngầm cho agent, không phải lịch của người dùng, không hiện trong khung chat
# Mỗi lần thử có idempotency_key riêng nhưng cố định, sinh từ id của lịch
_KEY_NAMESPACE = uuid.UUID("6f1d3c52-8a57-4c1e-9b1f-2f6a4d7e9c10")


class _TaskFailed(Exception):
    def __init__(self, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.retryable = retryable


async def recover_stuck() -> None:
    """Worker chết giữa chừng -> báo lỗi. Không gửi lại vì agent có thể đã nhận và làm xong."""
    stale_after = timedelta(seconds=get_settings().goclaw_timeout_seconds + 120)
    message = "Worker dừng giữa chừng, không rõ agent đã nhận tin hay chưa"
    async with get_sessionmaker()() as session:
        stuck = (
            await session.scalars(
                update(ScheduledTask)
                .where(ScheduledTask.status == "processing", ScheduledTask.locked_at < func.now() - stale_after)
                .values(status="failed", last_error=message, locked_by=None, locked_at=None)
                .returning(ScheduledTask.id)
                .execution_options(synchronize_session=False)
            )
        ).all()
        if stuck:
            await session.execute(
                update(ScheduledTaskLog)
                .where(ScheduledTaskLog.task_id.in_(stuck), ScheduledTaskLog.status == "processing")
                .values(status="failed", error_message=message, finished_at=func.now())
                .execution_options(synchronize_session=False)
            )
            logger.warning("Lịch bị kẹt, đã đánh dấu lỗi: %s", stuck)
        await session.commit()


async def claim_due(limit: int) -> list[uuid.UUID]:
    """Nhận các lịch đã đến giờ, chuyển sang processing trong cùng một câu lệnh."""
    now = func.now()
    due = (
        select(ScheduledTask.id)
        .where(
            ScheduledTask.task_type == "send_message",
            ScheduledTask.payload.has_key("content"),  # lịch chỉ lưu ngày thì không có gì để gửi
            or_(
                and_(ScheduledTask.status == "scheduled", ScheduledTask.scheduled_at <= now),
                and_(ScheduledTask.status == "retrying", ScheduledTask.next_retry_at <= now),
            ),
        )
        .order_by(func.coalesce(ScheduledTask.next_retry_at, ScheduledTask.scheduled_at))
        .limit(limit)
        .with_for_update(skip_locked=True)
    )
    async with get_sessionmaker()() as session:
        ids = (
            await session.scalars(
                update(ScheduledTask)
                .where(ScheduledTask.id.in_(due))
                .values(
                    status="processing",
                    locked_by=WORKER_ID,
                    locked_at=now,
                    attempts=ScheduledTask.attempts + 1,
                    next_retry_at=None,
                    executed_at=func.coalesce(ScheduledTask.executed_at, now),
                )
                .returning(ScheduledTask.id)
                .execution_options(synchronize_session=False)
            )
        ).all()
        await session.commit()
    return list(ids)


async def _deliver(session, *, conversation_id, user_id, content, key, hidden) -> dict:
    conv = None
    if conversation_id is not None:
        conv = await session.scalar(
            select(Conversation).where(
                Conversation.id == conversation_id, Conversation.user_id == user_id, Conversation.deleted_at.is_(None)
            )
        )
    if conv is None:
        raise _TaskFailed("Cuộc trò chuyện không còn tồn tại")
    if conv.status != "active":
        raise _TaskFailed("Cuộc trò chuyện đã lưu trữ")
    user = await session.get(AppUser, user_id)
    if user is None or user.status != "active":
        raise _TaskFailed("Tài khoản không còn hoạt động")
    agent = await session.get(Agent, conv.agent_id)
    target = goclaw.resolve_target(agent)

    await chat_service.close_stale_replies(session, conv.id)
    try:
        sent = await chat_service.send_to_agent(
            session, conv, target, user_id=user_id, content=content, idempotency_key=key, hidden=hidden
        )
    except chat_service.ReplyInFlight:
        raise _TaskFailed("Agent đang trả lời tin trước trong cuộc trò chuyện", retryable=True)
    if sent.error is not None:
        raise sent.error
    if sent.reply.status != "completed":
        raise _TaskFailed(sent.reply.error_message or "Agent không trả lời được")
    return {"user_message_id": str(sent.user_message.id), "assistant_message_id": str(sent.reply.id)}


async def run_task(task_id: uuid.UUID) -> None:
    async with get_sessionmaker()() as session:
        task = await session.get(ScheduledTask, task_id)
        # Lưu ra biến: sau rollback các object bị hết hạn
        attempt, max_attempts = task.attempts, task.max_attempts
        conversation_id, user_id = task.conversation_id, task.user_id
        content = task.payload.get("content")
        hidden = task.payload.get("kind") == NOTICE_KIND
        session.add(
            ScheduledTaskLog(
                task_id=task_id,
                attempt_number=attempt,
                status="processing",
                request_payload={"conversation_id": str(conversation_id) if conversation_id else None},
                started_at=func.now(),
            )
        )
        await session.commit()

        response, error, retryable = None, None, False
        try:
            if not content:
                raise _TaskFailed("Lịch không có nội dung tin nhắn")
            response = await _deliver(
                session,
                conversation_id=conversation_id,
                user_id=user_id,
                content=content,
                key=uuid.uuid5(_KEY_NAMESPACE, f"{task_id}:{attempt}"),
                hidden=hidden,
            )
        except (_TaskFailed, goclaw.GoClawError) as e:
            error, retryable = str(e), getattr(e, "retryable", False)
        except Exception:
            logger.exception("Lỗi khi chạy lịch %s", task_id)
            error = "Lỗi hệ thống khi gửi tin"
        await session.rollback()

        finished = {"locked_by": None, "locked_at": None}
        if error is None:
            values = {"status": "completed", "completed_at": func.now(), "last_error": None, **finished}
        elif retryable and attempt < max_attempts:
            delay = timedelta(seconds=RETRY_DELAY_SECONDS * attempt)
            values = {"status": "retrying", "next_retry_at": func.now() + delay, "last_error": error, **finished}
        else:
            values = {"status": "failed", "last_error": error, **finished}
        await session.execute(
            update(ScheduledTask)
            .where(ScheduledTask.id == task_id, ScheduledTask.status == "processing")
            .values(**values)
            .execution_options(synchronize_session=False)
        )
        await session.execute(
            update(ScheduledTaskLog)
            .where(ScheduledTaskLog.task_id == task_id, ScheduledTaskLog.attempt_number == attempt)
            .values(
                status="completed" if error is None else "failed",
                response_payload=response,
                error_message=error,
                finished_at=func.now(),
            )
            .execution_options(synchronize_session=False)
        )
        await session.commit()


async def run_forever() -> None:
    try:
        config = get_settings()
    except Exception:
        logger.warning("Chưa cấu hình Supabase, không chạy worker lịch hẹn")
        return
    if not config.schedule_worker_enabled:
        return

    running: set[asyncio.Task] = set()
    try:
        while True:
            try:
                await recover_stuck()
                free = MAX_CONCURRENT - len(running)
                if free > 0:
                    for task_id in await claim_due(free):
                        job = asyncio.create_task(run_task(task_id))
                        running.add(job)
                        job.add_done_callback(_job_done(running))
            except Exception:
                logger.exception("Worker lịch hẹn gặp lỗi, sẽ thử lại")
            await asyncio.sleep(config.schedule_poll_seconds)
    finally:
        for job in running:
            job.cancel()


def _job_done(running: set[asyncio.Task]):
    def done(job: asyncio.Task) -> None:
        running.discard(job)
        if not job.cancelled() and job.exception() is not None:
            logger.error("Lịch hẹn lỗi ngoài dự kiến: %r", job.exception())

    return done
