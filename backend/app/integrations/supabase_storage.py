"""Lưu file đính kèm trên Supabase Storage. Bucket riêng tư: app xem file qua URL có chữ ký, hết hạn sau một giờ."""

import logging

import httpx

from app.core.config import get_settings

log = logging.getLogger(__name__)

SIGNED_URL_SECONDS = 3600
UPLOAD_TIMEOUT_SECONDS = 300


class StorageError(Exception):
    """Nội dung được hiển thị cho user nên KHÔNG chứa URL hay key.

    rejected: Storage từ chối chính file này (sai loại, quá lớn), gửi lại cũng vô ích.
    """

    def __init__(self, message: str, *, rejected: bool = False) -> None:
        super().__init__(message)
        self.rejected = rejected


def _endpoint() -> tuple[str, dict[str, str], str]:
    config = get_settings()
    if not config.supabase_url or not config.supabase_secret_key:
        raise StorageError("Chưa cấu hình nơi lưu file")
    headers = {"apikey": config.supabase_secret_key, "Authorization": f"Bearer {config.supabase_secret_key}"}
    return f"{config.supabase_url.rstrip('/')}/storage/v1", headers, config.attachment_bucket


def _is_rejected(resp: httpx.Response) -> bool:
    codes = {str(resp.status_code)}
    try:
        codes.add(str(resp.json().get("statusCode")))
    except (AttributeError, ValueError):
        pass
    return bool(codes & {"413", "415"})


async def upload(path: str, data: bytes, mime_type: str) -> None:
    base, headers, bucket = _endpoint()
    try:
        async with httpx.AsyncClient(timeout=UPLOAD_TIMEOUT_SECONDS) as client:
            resp = await client.post(
                f"{base}/object/{bucket}/{path}",
                content=data,
                headers={**headers, "Content-Type": mime_type, "x-upsert": "false"},
            )
    except httpx.HTTPError as e:
        log.warning("Không kết nối được Storage: %s", e)
        raise StorageError("Không lưu được file, vui lòng thử lại")
    if resp.is_error:
        log.warning("Storage trả %s khi tải file lên", resp.status_code)
        if _is_rejected(resp):
            raise StorageError("Loại file không được hỗ trợ hoặc file quá lớn", rejected=True)
        raise StorageError("Không lưu được file, vui lòng thử lại")


async def sign(paths: list[str]) -> dict[str, str]:
    """Trả về {path: URL có chữ ký}. Path lỗi thì không có trong kết quả."""
    base, headers, bucket = _endpoint()
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{base}/object/sign/{bucket}",
                json={"expiresIn": SIGNED_URL_SECONDS, "paths": paths},
                headers=headers,
            )
            resp.raise_for_status()
            items = resp.json()
        return {item["path"]: f"{base}{item['signedURL']}" for item in items if item.get("signedURL")}
    except (httpx.HTTPError, AttributeError, KeyError, TypeError, ValueError) as e:
        log.warning("Không tạo được URL xem file: %r", type(e))
        raise StorageError("Không tạo được đường dẫn xem file")


async def delete(paths: list[str]) -> None:
    """Dọn file khi tin không gửi được. Lỗi chỉ ghi log: file thừa không ảnh hưởng tới user."""
    try:
        base, headers, bucket = _endpoint()
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.request("DELETE", f"{base}/object/{bucket}", json={"prefixes": paths}, headers=headers)
            resp.raise_for_status()
    except (StorageError, httpx.HTTPError) as e:
        log.warning("Không xóa được file thừa trên Storage: %r", type(e))
