import uuid
from datetime import datetime, timedelta
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query, Response, status
from sqlalchemy import DateTime, func, literal, select, tuple_, update
from sqlalchemy.exc import DBAPIError, IntegrityError

from app.integrations import goclaw
from app.api.supabase_deps import CurrentUser, Session
from app.core.config import get_settings
from app.core.errors import pg_error
from app.core.rate_limit import limiter
from app.models import Agent, Conversation, Message
from app.schemas.mobile import (
    ConversationCreate,
    ConversationOut,
    ConversationUpdate,
    MessageOut,
    MessagePage,
    SendMessage,
    SendMessageOut,
)

router = APIRouter(prefix="/conversations", tags=["conversations"])

NOT_FOUND = HTTPException(status.HTTP_404_NOT_FOUND, "Không tìm thấy cuộc trò chuyện")


async def _get_owned(session: Session, user_id: uuid.UUID, conversation_id: uuid.UUID) -> Conversation:
    conv = await session.scalar(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
            Conversation.deleted_at.is_(None),
        )
    )
    if conv is None:
        raise NOT_FOUND
    return conv


@router.get("", response_model=list[ConversationOut])
async def list_conversations(
    user: CurrentUser,
    session: Session,
    status_: Annotated[Literal["active", "archived"], Query(alias="status")] = "active",
    limit: Annotated[int, Query(ge=1, le=100)] = 30,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    """Ghim lên đầu, sau đó theo hoạt động gần nhất (khớp index idx_conversations_user_list)."""
    rows = await session.scalars(
        select(Conversation)
        .where(Conversation.user_id == user.id, Conversation.deleted_at.is_(None), Conversation.status == status_)
        .order_by(
            Conversation.pinned_at.desc().nulls_last(),
            func.coalesce(Conversation.last_message_at, Conversation.created_at).desc(),
            Conversation.id,
        )
        .limit(limit)
        .offset(offset)
    )
    return rows.all()


@router.post("", response_model=ConversationOut, status_code=status.HTTP_201_CREATED)
async def create_conversation(body: ConversationCreate, user: CurrentUser, session: Session):
    limiter.hit(f"conversation-create:{user.id}", 30, 60)
    conv = Conversation(user_id=user.id, agent_id=body.agent_id, title=body.title)
    session.add(conv)
    try:
        await session.commit()
    except DBAPIError as e:
        await session.rollback()
        sqlstate, _ = pg_error(e)
        if sqlstate == "23503":  # agent không tồn tại
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Không tìm thấy agent")
        raise
    await session.refresh(conv)
    return conv


@router.get("/{conversation_id}", response_model=ConversationOut)
async def get_conversation(conversation_id: uuid.UUID, user: CurrentUser, session: Session):
    return await _get_owned(session, user.id, conversation_id)


@router.patch("/{conversation_id}", response_model=ConversationOut)
async def update_conversation(
    conversation_id: uuid.UUID, body: ConversationUpdate, user: CurrentUser, session: Session
):
    conv = await _get_owned(session, user.id, conversation_id)
    if body.title is not None:
        conv.title = body.title
    if body.pinned is not None:
        conv.pinned_at = func.now() if body.pinned else None
    if body.archived is not None:
        conv.status = "archived" if body.archived else "active"
        conv.archived_at = func.now() if body.archived else None
    await session.commit()
    await session.refresh(conv)
    return conv


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(conversation_id: uuid.UUID, user: CurrentUser, session: Session):
    """Xóa mềm: ẩn khỏi app, dữ liệu vẫn nằm trong database (chưa có job xóa hẳn)."""
    conv = await _get_owned(session, user.id, conversation_id)
    conv.status = "deleted"
    conv.deleted_at = func.now()
    conv.pinned_at = None
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{conversation_id}/messages", response_model=MessagePage)
async def list_messages(
    conversation_id: uuid.UUID,
    user: CurrentUser,
    session: Session,
    before: uuid.UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 30,
):
    """Tin mới nhất trước. Trang tiếp theo: gửi before = next_before."""
    await _get_owned(session, user.id, conversation_id)
    await _close_stale_replies(session, conversation_id)
    query = select(Message).where(Message.conversation_id == conversation_id, Message.user_id == user.id)
    if before is not None:
        anchor = await session.scalar(
            select(Message.created_at).where(
                Message.id == before, Message.conversation_id == conversation_id, Message.user_id == user.id
            )
        )
        if anchor is None:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "before không thuộc cuộc trò chuyện này")
        query = query.where(tuple_(Message.created_at, Message.id) < (anchor, before))
    items = (await session.scalars(query.order_by(Message.created_at.desc(), Message.id.desc()).limit(limit))).all()
    return MessagePage(items=items, next_before=items[-1].id if len(items) == limit else None)


async def _close_stale_replies(session: Session, conversation_id: uuid.UUID) -> None:
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


async def _reply_to(session: Session, message: Message) -> Message | None:
    return await session.scalar(
        select(Message)
        .where(Message.reply_to_message_id == message.id, Message.role == "assistant")
        .order_by(Message.created_at.desc(), Message.id.desc())
        .limit(1)
    )


async def _existing_send(session: Session, user_id: uuid.UUID, key: uuid.UUID) -> SendMessageOut | None:
    sent = await session.scalar(select(Message).where(Message.user_id == user_id, Message.idempotency_key == key))
    if sent is None:
        return None
    reply = await _reply_to(session, sent)
    return SendMessageOut(
        user_message=MessageOut.model_validate(sent),
        assistant_message=MessageOut.model_validate(reply) if reply else None,
    )


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


@router.post("/{conversation_id}/messages", response_model=SendMessageOut, status_code=status.HTTP_201_CREATED)
async def send_message(
    conversation_id: uuid.UUID, body: SendMessage, user: CurrentUser, session: Session, response: Response
):
    """Gửi tin và chờ agent trả lời.

    1. Ghi tin của user + chỗ trống cho câu trả lời (status processing) rồi commit.
    2. Gọi GoClaw (không giữ transaction trong lúc chờ).
    3. Ghi câu trả lời (completed) hoặc lỗi (failed).
    Gửi lại cùng idempotency_key -> trả lại kết quả cũ, không gọi GoClaw lần nữa.
    """
    # Giữ id ra biến: sau rollback SQLAlchemy làm hết hạn các object đã load
    user_id = user.id
    conv = await _get_owned(session, user_id, conversation_id)

    async def replay() -> SendMessageOut | None:
        previous = await _existing_send(session, user_id, body.idempotency_key)
        if previous is None:
            return None
        if previous.user_message.conversation_id != conversation_id:
            raise HTTPException(status.HTTP_409_CONFLICT, "idempotency_key đã dùng cho cuộc trò chuyện khác")
        response.status_code = status.HTTP_200_OK
        return previous

    await _close_stale_replies(session, conv.id)
    if (previous := await replay()) is not None:
        return previous

    # Sau bước gửi lại cùng key, để app thử lại không bị tính thêm lượt. Chặn gọi AI vô hạn (tốn tiền).
    limiter.hit(f"send:minute:{user_id}", 20, 60)
    limiter.hit(f"send:hour:{user_id}", 300, 3600)

    if conv.status != "active":
        raise HTTPException(status.HTTP_409_CONFLICT, "Cuộc trò chuyện đã lưu trữ, bỏ lưu trữ để chat tiếp")
    agent = await session.get(Agent, conv.agent_id)
    try:
        target = goclaw.resolve_target(agent)
    except goclaw.GoClawError as e:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(e))
    session_key = conv.goclaw_session_id or str(conv.id)

    user_msg = Message(
        conversation_id=conv.id,
        user_id=user_id,
        role="user",
        content=body.content,
        status="completed",
        idempotency_key=body.idempotency_key,
        created_at=_created_after(conv.last_message_at),
    )
    session.add(user_msg)
    try:
        await session.flush()
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
            raise HTTPException(status.HTTP_409_CONFLICT, "Agent đang trả lời tin trước, đợi xong rồi gửi tiếp")
        if constraint == "idx_messages_idempotency":  # 2 request cùng key chạy song song
            if (previous := await replay()) is not None:
                return previous
        raise

    # Lưu id ra biến: sau rollback các object bị hết hạn
    reply_id, user_msg_id, conv_id = reply.id, user_msg.id, conv.id
    finished = (Message.id == reply_id) & (Message.status == "processing")  # chưa bị stale recovery đóng
    try:
        result = await goclaw.send_message(target, session_key=session_key, user_id=user_id, content=body.content)
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
        await session.execute(
            update(Conversation)
            .where(Conversation.id == conv_id, Conversation.title.is_(None))
            .values(title=body.content.strip()[:60])
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

    user_msg = await session.get(Message, user_msg_id, populate_existing=True)
    reply = await session.get(Message, reply_id, populate_existing=True)
    return SendMessageOut(user_message=user_msg, assistant_message=reply)
