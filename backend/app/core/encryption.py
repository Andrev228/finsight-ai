"""Encryption for sensitive application credentials."""

from cryptography.fernet import Fernet

from app.core.config import settings


class EncryptionConfigurationError(RuntimeError):
    """Raised when token encryption is not configured."""


class TokenCipher:
    def __init__(self, key: str) -> None:
        if not key:
            raise EncryptionConfigurationError("Token encryption key is not configured")
        try:
            self._fernet = Fernet(key.encode())
        except ValueError as exc:
            raise EncryptionConfigurationError(
                "Token encryption key is invalid",
            ) from exc

    def encrypt(self, value: str) -> bytes:
        return self._fernet.encrypt(value.encode())


def get_token_cipher() -> TokenCipher:
    return TokenCipher(settings.plaid_token_encryption_key.get_secret_value())
