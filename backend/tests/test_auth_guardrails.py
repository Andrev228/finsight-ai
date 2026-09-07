"""Tests for authentication and privacy guardrails."""

import base64
import hashlib
import hmac
import json
import time

import pytest
from fastapi import HTTPException
from pydantic import SecretStr

from app.ai.guardrails import redact_pii
from app.core import auth
from app.core.config import settings


def encode(value: object) -> str:
    return base64.urlsafe_b64encode(
        json.dumps(value, separators=(",", ":")).encode(),
    ).rstrip(b"=").decode()


def token(secret: str, **claims: object) -> str:
    header = encode({"alg": "HS256", "typ": "JWT"})
    payload = encode(claims)
    signature = hmac.new(
        secret.encode(),
        f"{header}.{payload}".encode(),
        hashlib.sha256,
    ).digest()
    encoded_signature = base64.urlsafe_b64encode(signature).rstrip(b"=").decode()
    return f"{header}.{payload}.{encoded_signature}"


def test_valid_jwt_returns_subject(monkeypatch):
    secret = "a" * 32
    monkeypatch.setattr(settings, "auth_jwt_secret", SecretStr(secret))
    value = token(
        secret,
        sub="user-123",
        iss=settings.auth_jwt_issuer,
        aud=settings.auth_jwt_audience,
        exp=int(time.time()) + 60,
    )

    assert auth._verify_token(value) == "user-123"


def test_expired_jwt_is_rejected(monkeypatch):
    secret = "a" * 32
    monkeypatch.setattr(settings, "auth_jwt_secret", SecretStr(secret))
    value = token(
        secret,
        sub="user-123",
        iss=settings.auth_jwt_issuer,
        aud=settings.auth_jwt_audience,
        exp=int(time.time()) - 1,
    )

    with pytest.raises(HTTPException) as exc_info:
        auth._verify_token(value)
    assert exc_info.value.status_code == 401


def test_pii_is_redacted_before_model_use():
    value = (
        "Email alex@example.com, phone 415-555-1212, SSN 123-45-6789, "
        "card 4111 1111 1111 1111, IBAN GB82 WEST 1234 5698 7654 32."
    )

    assert redact_pii(value) == (
        "Email [REDACTED_EMAIL], phone [REDACTED_PHONE], "
        "SSN [REDACTED_GOVERNMENT_ID], card [REDACTED_NUMBER], "
        "IBAN [REDACTED_BANK_ID]."
    )


def test_jwt_json_arrays_are_rejected_without_server_error(monkeypatch):
    secret = "a" * 32
    monkeypatch.setattr(settings, "auth_jwt_secret", SecretStr(secret))
    header = encode([])
    payload = encode([])
    signature = hmac.new(
        secret.encode(),
        f"{header}.{payload}".encode(),
        hashlib.sha256,
    ).digest()
    value = (
        f"{header}.{payload}."
        f"{base64.urlsafe_b64encode(signature).rstrip(b'=').decode()}"
    )

    with pytest.raises(HTTPException) as exc_info:
        auth._verify_token(value)
    assert exc_info.value.status_code == 401
