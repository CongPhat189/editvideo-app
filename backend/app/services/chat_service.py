"""Gửi tin cho agent và ghi kết quả. Dùng chung cho API chat và lịch hẹn."""

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import DateTime, func, literal, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import pg_error
from app.integrations import goclaw
from app.models import Conversation, Message, MessageAttachment


HIDDEN_KEY = "hidden"  # Khóa trong messages.metadata của tin không hiện trong khung chat

CONTENT_ONLY_INSTRUCTION = (
    "\n\n[CHẾ ĐỘ TẠO CONTENT]\n"
    "Chỉ trả về bản content hoàn chỉnh để đăng. Không viết lời dẫn, giải thích, nhận xét, tiêu đề kiểu 'bản nháp', "
    "câu hỏi, lựa chọn tiếp theo hoặc lời mời trao đổi. Không hỏi lại; tự hoàn thiện nội dung hợp lý từ thông tin đã có. "
    "Giữ nguyên ngôn ngữ, emoji và hashtag phù hợp. Response chỉ gồm đúng phần content có thể đăng, không bọc markdown."
)


class ReplyInFlight(Exception):
    """Agent đang trả lời tin trước trong cùng cuộc trò chuyện."""


class DuplicateIdempotencyKey(Exception):
    """Một request khác vừa ghi cùng idempotency_key."""


@dataclass
class SendResult:
    user_message: Message
    reply: Message
    error: goclaw.GoClawError | None = None


async def close_stale_replies(session: AsyncSession, conversation_id: uuid.UUID) -> None:
    """Câu trả lời kẹt quá lâu (server chết giữa chừng) -> đánh dấu lỗi, để app không chờ mãi và chat tiếp được."""
    stale_after = timedelta(seconds=get_settings().goclaw_timeout_seconds + 60)
    result = await session.execute(
        update(Message)
        .where(
            Message.conversation_id == conversation_id,
            Message.role == "assistant",
            Message.status.in_(("pending", "processing")),
            Message.created_at < func.now() - stale_after,
        )
        .values(status="failed", error_message="Hết thời gian chờ agent trả lời")
        .execution_options(synchronize_session=False)
    )
    if result.rowcount:
        await session.commit()


def _created_after(previous: datetime | None):
    """Bảng messages không có cột số thứ tự, nên tin sau phải có created_at lớn hơn hẳn tin trước,
    kể cả khi hai lần ghi rơi vào cùng một tick đồng hồ hoặc đồng hồ các server lệch nhau."""
    if previous is None:
        return func.clock_timestamp()
    return func.greatest(func.clock_timestamp(), literal(previous + timedelta(microseconds=1), DateTime(timezone=True)))


def _usage(result: goclaw.GoClawReply) -> dict:
    usage = {
        "model": result.model,
        "input_tokens": result.input_tokens,
        "output_tokens": result.output_tokens,
        "cost_usd": str(result.cost_usd) if result.cost_usd is not None else None,
    }
    return {k: v for k, v in usage.items() if v is not None}


async def send_to_agent(
    session: AsyncSession,
    conv: Conversation,
    target: goclaw.GoClawTarget,
    *,
    user_id: uuid.UUID,
    content: str | None,
    idempotency_key: uuid.UUID,
    response_mode: str = "chat",
    hidden: bool = False,
    content_type: str = "text",
    attachments: list[dict] | None = None,
    media: list[goclaw.GoClawMedia] | None = None,
    title: str | None = None,
) -> SendResult:
    """Gửi tin và chờ agent trả lời.

    1. Ghi tin của user + chỗ trống cho câu trả lời (status processing) rồi commit.
    2. Gọi GoClaw (không giữ transaction trong lúc chờ).
    3. Ghi câu trả lời (completed) hoặc lỗi (failed). Lỗi GoClaw nằm trong SendResult.error.

    hidden: tin do hệ thống gửi thay user, không hiện trong khung chat. Câu trả lời của agent vẫn hiện.
    attachments: các dòng message_attachments, ghi cùng transaction với tin. media: file gửi cho agent.
    """
    session_key = conv.goclaw_session_id or goclaw.session_key_for(target, conv.id)
    user_msg = Message(
        conversation_id=conv.id,
        user_id=user_id,
        role="user",
        content=content,
        content_type=content_type,
        status="completed",
        idempotency_key=idempotency_key,
        meta={HIDDEN_KEY: True} if hidden else {},
        created_at=_created_after(conv.last_message_at),
    )
    session.add(user_msg)
    try:
        await session.flush()
        for attachment in attachments or []:
            session.add(MessageAttachment(message_id=user_msg.id, **attachment))
        reply = Message(
            conversation_id=conv.id,
            user_id=user_id,
            role="assistant",
            status="processing",
            reply_to_message_id=user_msg.id,
            created_at=_created_after(user_msg.created_at),
        )
        session.add(reply)
        await session.commit()
    except IntegrityError as e:
        await session.rollback()
        _, constraint = pg_error(e)
        if constraint == "uq_messages_one_inflight_reply":
            raise ReplyInFlight from e
        if constraint == "idx_messages_idempotency":  # 2 request cùng key chạy song song
            raise DuplicateIdempotencyKey from e
        raise

    # Lưu id ra biến: sau rollback các object bị hết hạn
    reply_id, user_msg_id, conv_id = reply.id, user_msg.id, conv.id
    finished = (Message.id == reply_id) & (Message.status == "processing")  # chưa bị stale recovery đóng
    error = None
    try:
        extra = {"media": media} if media else {}
        agent_content = (content or "")
        if response_mode == "content_only":
            agent_content += CONTENT_ONLY_INSTRUCTION
        result = await goclaw.send_message(
            target, session_key=session_key, user_id=user_id, content=agent_content, **extra
        )
        await session.execute(
            update(Message)
            .where(finished)
            .values(
                status="completed",
                content=result.content,
                goclaw_message_id=result.message_id,
                meta=_usage(result),
            )
            .execution_options(synchronize_session=False)
        )
        # Ghi có điều kiện ngay trong SQL: không đè tên/session do thiết bị khác vừa đặt
        await session.execute(
            update(Conversation)
            .where(Conversation.id == conv_id)
            .values(goclaw_session_id=func.coalesce(Conversation.goclaw_session_id, result.session_id))
            .execution_options(synchronize_session=False)
        )
        if not hidden:  # tin ẩn không được lộ ra qua tên cuộc trò chuyện
            await session.execute(
                update(Conversation)
                .where(Conversation.id == conv_id, Conversation.title.is_(None))
                .values(title=(title or content or "").strip()[:60])
                .execution_options(synchronize_session=False)
            )
        await session.commit()
    except Exception as e:
        # Lỗi GoClaw, lỗi ghi kết quả hay lỗi ngoài dự kiến: vẫn đóng câu trả lời để user gửi tiếp được
        await session.rollback()
        message = str(e) if isinstance(e, goclaw.GoClawError) else "Lỗi hệ thống khi gọi agent"
        await session.execute(
            update(Message)
            .where(finished)
            .values(status="failed", error_message=message)
            .execution_options(synchronize_session=False)
        )
        await session.commit()
        if not isinstance(e, goclaw.GoClawError):
            raise
        error = e

    user_msg = await session.get(Message, user_msg_id, populate_existing=True)
    reply = await session.get(Message, reply_id, populate_existing=True)
    return SendResult(user_msg, reply, error)
