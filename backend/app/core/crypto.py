"""Mã hóa API key của agent trước khi lưu vào agents.key (Fernet: AES + HMAC)."""

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import SupabaseNotConfigured, get_settings


class SecretDecryptError(Exception):
    pass


def _fernet() -> Fernet:
    key = get_settings().agent_key_encryption_key
    if not key:
        raise SupabaseNotConfigured("Thiếu AGENT_KEY_ENCRYPTION_KEY")
    try:
        return Fernet(key)
    except ValueError as e:
        raise SupabaseNotConfigured("AGENT_KEY_ENCRYPTION_KEY không đúng định dạng Fernet") from e


def encrypt_secret(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode()


def decrypt_secret(value: str) -> str:
    try:
        return _fernet().decrypt(value.encode()).decode()
    except InvalidToken as e:
        raise SecretDecryptError("Không giải mã được, có thể đã đổi AGENT_KEY_ENCRYPTION_KEY") from e
