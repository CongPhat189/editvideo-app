import uuid
from datetime import timedelta
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query, Response, status
from sqlalchemy import func, select, text, update
from sqlalchemy.exc import DBAPIError, IntegrityError

from app import goclaw
from app.auth import CurrentUser, Session
from app.config import get_settings
from app.errors import pg_error
from app.models import Agent, Conversation, GoclawWorkspace, Message
from app.schemas import (
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
    conv = Conversation(user_id=user.id, agent_id=body.agent_id, title=body.title)
    if body.title:
        conv.title_source = "user"
    session.add(conv)
    try:
        await session.commit()
    except DBAPIError as e:
        await session.rollback()
        sqlstate, _ = pg_error(e)
        if sqlstate in ("42501", "23503"):  # trigger enforce_agent_access / agent không tồn tại
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Bạn không dùng được agent này")
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
        conv.title_source = "user"  # AI không tự đổi tên nữa
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
    """Xóa mềm: ẩn ngay khỏi app, job purge xóa hẳn sau N ngày."""
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
    before_seq: Annotated[int | None, Query(ge=1)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 30,
):
    """Tin mới nhất trước. Trang tiếp theo: gửi before_seq = next_before_seq."""
    await _get_owned(session, user.id, conversation_id)
    query = select(Message).where(Message.conversation_id == conversation_id, Message.user_id == user.id)
    if before_seq is not None:
        query = query.where(Message.seq < before_seq)
    items = (await session.scalars(query.order_by(Message.seq.desc()).limit(limit))).all()
    return MessagePage(items=items, next_before_seq=items[-1].seq if len(items) == limit else None)


async def _reply_to(session: Session, message: Message) -> Message | None:
    return await session.scalar(
        select(Message)
        .where(Message.reply_to_message_id == message.id, Message.role == "assistant")
        .order_by(Message.seq.desc())
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


@router.post("/{conversation_id}/messages", response_model=SendMessageOut, status_code=status.HTTP_201_CREATED)
async def send_message(
    conversation_id: uuid.UUID, body: SendMessage, user: CurrentUser, session: Session, response: Response
):
    """Gửi tin và chờ agent trả lời.

    1. Ghi tin của user + chỗ trống cho câu trả lời (status processing) rồi commit,
       để app khác của cùng user thấy ngay qua Realtime.
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

    if (previous := await replay()) is not None:
        return previous

    if conv.status != "active":
        raise HTTPException(status.HTTP_409_CONFLICT, "Cuộc trò chuyện đã lưu trữ, bỏ lưu trữ để chat tiếp")
    can_use = await session.scalar(
        text("select public.can_use_agent(:user_id, :agent_id)"), {"user_id": user_id, "agent_id": conv.agent_id}
    )
    if not can_use:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Agent này hiện không dùng được")
    agent = await session.get(Agent, conv.agent_id)
    workspace = await session.get(GoclawWorkspace, agent.workspace_id)
    # Đọc API key (Vault) ngay trong transaction này, để lúc chờ agent không giữ kết nối DB nào
    try:
        target = await goclaw.resolve_target(session, agent=agent, workspace=workspace)
    except goclaw.GoClawError as e:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(e))
    session_key = conv.goclaw_session_id or str(conv.id)

    # Câu trả lời kẹt ở processing quá lâu (server chết giữa chừng) -> đánh dấu lỗi để chat tiếp được
    stale_after = timedelta(seconds=get_settings().goclaw_timeout_seconds + 60)
    await session.execute(
        update(Message)
        .where(
            Message.conversation_id == conv.id,
            Message.role == "assistant",
            Message.status.in_(("pending", "processing")),
            Message.created_at < func.now() - stale_after,
        )
        .values(status="failed", error_message="Hết thời gian chờ agent trả lời")
    )

    user_msg = Message(
        conversation_id=conv.id,
        user_id=user_id,
        role="user",
        content=body.content,
        status="completed",
        idempotency_key=body.idempotency_key,
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
    except Exception as e:
        # Lỗi GoClaw (hoặc lỗi ngoài dự kiến): vẫn đóng câu trả lời để user gửi tiếp được
        await session.rollback()
        message = str(e) if isinstance(e, goclaw.GoClawError) else "Lỗi hệ thống khi gọi agent"
        await session.execute(update(Message).where(finished).values(status="failed", error_message=message))
        await session.commit()
        if not isinstance(e, goclaw.GoClawError):
            raise
    else:
        await session.execute(
            update(Message)
            .where(finished)
            .values(
                status="completed",
                content=result.content,
                goclaw_message_id=result.message_id,
                model=result.model,
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
                cost_usd=result.cost_usd,
            )
        )
        # Ghi có điều kiện ngay trong SQL: không đè tên/session do thiết bị khác vừa đặt
        await session.execute(
            update(Conversation)
            .where(Conversation.id == conv_id)
            .values(goclaw_session_id=func.coalesce(Conversation.goclaw_session_id, result.session_id))
        )
        await session.execute(
            update(Conversation)
            .where(Conversation.id == conv_id, Conversation.title.is_(None), Conversation.title_source == "auto")
            .values(title=body.content.strip()[:60])
        )
        await session.commit()

    user_msg = await session.get(Message, user_msg_id, populate_existing=True)
    reply = await session.get(Message, reply_id, populate_existing=True)
    return SendMessageOut(user_message=user_msg, assistant_message=reply)
