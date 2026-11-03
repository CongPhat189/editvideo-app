"""Kiểm tra file đính kèm, lưu lên Storage và tạo URL xem file."""

import logging
import mimetypes
import re
import uuid
from dataclasses import dataclass

from fastapi import HTTPException, status
from starlette.datastructures import UploadFile

from app.integrations import goclaw, supabase_storage
from app.models import Message
from app.schemas.mobile import MessageOut

log = logging.getLogger(__name__)

MAX_FILES = 5
MAX_FILE_BYTES = 50 * 1024 * 1024  # Bằng giới hạn của bucket chat-attachments và của GoClaw /v1/media/upload
MAX_REQUEST_BYTES = MAX_FILES * MAX_FILE_BYTES + 1024 * 1024


@dataclass
class StoredFile:
    upload: UploadFile
    file_name: str
    mime_type: str
    file_size: int
    file_path: str = ""

    def row(self) -> dict:
        return {
            "file_name": self.file_name,
            "file_path": self.file_path,
            "mime_type": self.mime_type,
            "file_size": self.file_size,
        }

    def media(self) -> goclaw.GoClawMedia:
        return goclaw.GoClawMedia(self.file_name, self.mime_type, self.upload.file)


def _safe_name(name: str | None) -> str:
    base = (name or "").replace("\\", "/").rsplit("/", 1)[-1]
    base = "".join(c for c in base if c.isprintable()).replace("..", ".").strip()
    return base[-255:] or "file"


def _mime_type(upload: UploadFile, file_name: str) -> str:
    declared = (upload.content_type or "").split(";")[0].strip().lower()
    if declared and declared != "application/octet-stream":
        return declared[:100]
    return mimetypes.guess_type(file_name)[0] or "application/octet-stream"


def validate(uploads: list[UploadFile]) -> list[StoredFile]:
    if not uploads:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Cần ít nhất một file trong trường files")
    if len(uploads) > MAX_FILES:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"Tối đa {MAX_FILES} file mỗi tin")
    files = []
    for upload in uploads:
        name = _safe_name(upload.filename)
        size = upload.size or 0
        if size == 0:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"File {name} đang trống")
        if size > MAX_FILE_BYTES:
            raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, f"File {name} vượt quá 50 MB")
        files.append(StoredFile(upload, name, _mime_type(upload, name), size))
    return files


def content_type_of(files: list[StoredFile]) -> str:
    """Cả tin cùng một loại thì ghi loại đó, lẫn lộn thì ghi file."""
    kinds = {f.mime_type.split("/")[0] for f in files}
    kind = kinds.pop() if len(kinds) == 1 else "file"
    return kind if kind in ("image", "video", "audio") else "file"


async def store(files: list[StoredFile], *, user_id: uuid.UUID, conversation_id: uuid.UUID) -> None:
    """Lưu lần lượt, lỗi giữa chừng thì dọn các file đã lưu. Tên file của user không nằm trong đường dẫn."""
    stored: list[str] = []
    try:
        for f in files:
            match = re.search(r"\.[A-Za-z0-9]{1,10}$", f.file_name)
            f.file_path = f"{user_id}/{conversation_id}/{uuid.uuid4()}{match.group().lower() if match else ''}"
            await f.upload.seek(0)
            await supabase_storage.upload(f.file_path, await f.upload.read(), f.mime_type)
            stored.append(f.file_path)
    except supabase_storage.StorageError as e:
        if stored:
            await supabase_storage.delete(stored)
        code = status.HTTP_415_UNSUPPORTED_MEDIA_TYPE if e.rejected else status.HTTP_503_SERVICE_UNAVAILABLE
        raise HTTPException(code, str(e))


async def to_out(messages: list[Message]) -> list[MessageOut]:
    """Kèm URL xem file. Storage lỗi thì url để trống, vẫn đọc được tin nhắn."""
    paths = [a.file_path for m in messages for a in m.attachments]
    urls: dict[str, str] = {}
    if paths:
        try:
            urls = await supabase_storage.sign(paths)
        except supabase_storage.StorageError as e:
            log.warning("%s", e)
    result = []
    for message in messages:
        out = MessageOut.model_validate(message)
        for item, attachment in zip(out.attachments, message.attachments):
            item.url = urls.get(attachment.file_path)
        result.append(out)
    return result
