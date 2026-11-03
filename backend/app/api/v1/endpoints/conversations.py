import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query, Request, Response, status
from sqlalchemy import func, not_, select, tuple_
from sqlalchemy.exc import DBAPIError
from starlette.datastructures import UploadFile

from app.integrations import goclaw, supabase_storage
from app.api.supabase_deps import CurrentUser, Session
from app.core.errors import pg_error
from app.core.rate_limit import limiter
from app.models import Agent, Conversation, Message
from app.services import attachment_service, chat_service
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
    await chat_service.close_stale_replies(session, conversation_id)
    query = select(Message).where(
        Message.conversation_id == conversation_id,
        Message.user_id == user.id,
        not_(Message.meta.has_key(chat_service.HIDDEN_KEY)),
    )
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
    return MessagePage(
        items=await attachment_service.to_out(items), next_before=items[-1].id if len(items) == limit else None
    )


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
    return _send_out(await attachment_service.to_out([sent, reply] if reply else [sent]))


def _send_out(messages: list[MessageOut]) -> SendMessageOut:
    return SendMessageOut(user_message=messages[0], assistant_message=messages[1] if len(messages) > 1 else None)


async def _replay(
    session: Session, response: Response, user_id: uuid.UUID, conversation_id: uuid.UUID, key: uuid.UUID
) -> SendMessageOut | None:
    previous = await _existing_send(session, user_id, key)
    if previous is None:
        return None
    if previous.user_message.conversation_id != conversation_id:
        raise HTTPException(status.HTTP_409_CONFLICT, "idempotency_key đã dùng cho cuộc trò chuyện khác")
    response.status_code = status.HTTP_200_OK
    return previous


@router.post("/{conversation_id}/messages", response_model=SendMessageOut, status_code=status.HTTP_201_CREATED)
async def send_message(
    conversation_id: uuid.UUID, body: SendMessage, user: CurrentUser, session: Session, response: Response
):
    """Gửi tin và chờ agent trả lời. Gửi lại cùng idempotency_key -> trả lại kết quả cũ, không gọi GoClaw lần nữa."""
    # Giữ id ra biến: sau rollback SQLAlchemy làm hết hạn các object đã load
    user_id = user.id
    conv = await _get_owned(session, user_id, conversation_id)

    async def replay() -> SendMessageOut | None:
        return await _replay(session, response, user_id, conversation_id, body.idempotency_key)

    await chat_service.close_stale_replies(session, conv.id)
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
    try:
        sent = await chat_service.send_to_agent(
            session, conv, target, user_id=user_id, content=body.content, idempotency_key=body.idempotency_key
        )
    except chat_service.ReplyInFlight:
        raise HTTPException(status.HTTP_409_CONFLICT, "Agent đang trả lời tin trước, đợi xong rồi gửi tiếp")
    except chat_service.DuplicateIdempotencyKey:
        if (previous := await replay()) is not None:
            return previous
        raise
    return _send_out(await attachment_service.to_out([sent.user_message, sent.reply]))


def _upload_form_fields(form) -> tuple[str | None, uuid.UUID, list[UploadFile]]:
    content = form.get("content")
    if content is not None and not isinstance(content, str):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "content phải là chữ")
    if content is not None and (len(content) > 20000 or "\x00" in content):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "content không hợp lệ")
    raw_key = form.get("idempotency_key")
    try:
        key = uuid.UUID(raw_key) if raw_key else uuid.uuid4()
    except (TypeError, ValueError, AttributeError):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "idempotency_key phải là UUID")
    files = [item for item in form.getlist("files") if isinstance(item, UploadFile)]
    return (content if content and content.strip() else None), key, files


@router.post(
    "/{conversation_id}/messages/upload",
    response_model=SendMessageOut,
    status_code=status.HTTP_201_CREATED,
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "multipart/form-data": {
                    "schema": {
                        "type": "object",
                        "required": ["files"],
                        "properties": {
                            "files": {"type": "array", "items": {"type": "string", "format": "binary"}},
                            "content": {"type": "string"},
                            "idempotency_key": {"type": "string", "format": "uuid"},
                        },
                    }
                }
            },
        }
    },
)
async def send_message_with_files(
    conversation_id: uuid.UUID, request: Request, user: CurrentUser, session: Session, response: Response
):
    """Gửi tin kèm ảnh, video, file (tối đa 5 file, mỗi file 50 MB) và chờ agent trả lời. content có thể bỏ trống."""
    # Tự đọc form sau khi đã xác thực: khai báo File() thì FastAPI nhận cả file trước khi kiểm tra token
    user_id = user.id
    conv = await _get_owned(session, user_id, conversation_id)
    limiter.hit(f"upload:{user_id}", 20, 60)
    length = request.headers.get("content-length", "")
    if not length.isdigit():
        raise HTTPException(status.HTTP_411_LENGTH_REQUIRED, "Thiếu Content-Length")
    if int(length) > attachment_service.MAX_REQUEST_BYTES:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, "Tổng dung lượng file quá lớn")

    async with request.form(max_files=attachment_service.MAX_FILES + 1, max_fields=5) as form:
        content, key, uploads = _upload_form_fields(form)
        files = attachment_service.validate(uploads)

        await chat_service.close_stale_replies(session, conv.id)
        if (previous := await _replay(session, response, user_id, conversation_id, key)) is not None:
            return previous
        limiter.hit(f"send:minute:{user_id}", 20, 60)
        limiter.hit(f"send:hour:{user_id}", 300, 3600)

        if conv.status != "active":
            raise HTTPException(status.HTTP_409_CONFLICT, "Cuộc trò chuyện đã lưu trữ, bỏ lưu trữ để chat tiếp")
        agent = await session.get(Agent, conv.agent_id)
        try:
            target = goclaw.resolve_target(agent)
        except goclaw.GoClawError as e:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(e))
        # Kiểm tra trước để khỏi tải file lên rồi lại phải xóa
        busy = await session.scalar(
            select(Message.id)
            .where(
                Message.conversation_id == conv.id,
                Message.role == "assistant",
                Message.status.in_(("pending", "processing")),
            )
            .limit(1)
        )
        if busy is not None:
            raise HTTPException(status.HTTP_409_CONFLICT, "Agent đang trả lời tin trước, đợi xong rồi gửi tiếp")

        await session.commit()  # Không giữ transaction trong lúc tải file lên
        await attachment_service.store(files, user_id=user_id, conversation_id=conversation_id)
        try:
            sent = await chat_service.send_to_agent(
                session,
                conv,
                target,
                user_id=user_id,
                content=content,
                idempotency_key=key,
                content_type=attachment_service.content_type_of(files),
                attachments=[f.row() for f in files],
                media=[f.media() for f in files],
                title=files[0].file_name,
            )
        except chat_service.ReplyInFlight:
            await supabase_storage.delete([f.file_path for f in files])
            raise HTTPException(status.HTTP_409_CONFLICT, "Agent đang trả lời tin trước, đợi xong rồi gửi tiếp")
        except chat_service.DuplicateIdempotencyKey:
            await supabase_storage.delete([f.file_path for f in files])
            if (previous := await _replay(session, response, user_id, conversation_id, key)) is not None:
                return previous
            raise
        return _send_out(await attachment_service.to_out([sent.user_message, sent.reply]))
