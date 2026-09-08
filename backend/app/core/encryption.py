"""Symmetric encryption for sensitive application data."""

from functools import lru_cache

from cryptography.fernet import Fernet

from app.core.config import settings


class EncryptionConfigurationError(RuntimeError):
    """Raised when application encryption is not configured."""


class AppCipher:
    def __init__(self, key: str) -> None:
        if not key:
            raise EncryptionConfigurationError("Encryption key is not configured")
        try:
            self._fernet = Fernet(key.encode())
        except ValueError as exc:
            raise EncryptionConfigurationError(
                "Encryption key is invalid",
            ) from exc

    def encrypt(self, value: str) -> bytes:
        return self._fernet.encrypt(value.encode())

    def decrypt(self, value: bytes) -> str:
        return self._fernet.decrypt(value).decode()


@lru_cache(maxsize=1)
def get_app_cipher() -> AppCipher:
    return AppCipher(settings.app_encryption_key.get_secret_value())
