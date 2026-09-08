"""Authenticated user and administrative boundaries."""

import base64
import binascii
import hashlib
import hmac
import json
import secrets
import time
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings

MIN_JWT_SECRET_BYTES = 32
MAX_JWT_TOKEN_LENGTH = 8192


@dataclass(frozen=True)
class UserPrincipal:
    user_id: str


bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
) -> UserPrincipal:
    if settings.app_env == "local" and settings.allow_insecure_local_auth:
        return UserPrincipal(user_id=settings.plaid_client_user_id)
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _unauthorized()
    return UserPrincipal(user_id=_verify_token(credentials.credentials))


CurrentUser = Annotated[UserPrincipal, Depends(get_current_user)]


def require_admin(
    x_admin_key: Annotated[str | None, Header()] = None,
) -> None:
    configured_key = settings.admin_api_key.get_secret_value()
    if settings.app_env == "local" and settings.allow_insecure_local_admin:
        return
    if not configured_key or not x_admin_key or not secrets.compare_digest(
        configured_key,
        x_admin_key,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access is required",
        )


AdminAccess = Annotated[None, Depends(require_admin)]


def _verify_token(token: str) -> str:
    secret = settings.auth_jwt_secret.get_secret_value()
    if len(secret) < MIN_JWT_SECRET_BYTES or len(token) > MAX_JWT_TOKEN_LENGTH:
        raise _unauthorized()
    parts = token.split(".")
    if len(parts) != 3:
        raise _unauthorized()
    encoded_header, encoded_payload, encoded_signature = parts
    try:
        header = json.loads(_decode_segment(encoded_header))
        payload = json.loads(_decode_segment(encoded_payload))
        signature = _decode_bytes(encoded_signature)
    except (ValueError, binascii.Error, json.JSONDecodeError, UnicodeDecodeError):
        raise _unauthorized() from None

    if not isinstance(header, dict) or not isinstance(payload, dict):
        raise _unauthorized()
    if header.get("alg") != "HS256" or header.get("typ") not in (None, "JWT"):
        raise _unauthorized()
    expected_signature = hmac.new(
        secret.encode(),
        f"{encoded_header}.{encoded_payload}".encode(),
        hashlib.sha256,
    ).digest()
    if not hmac.compare_digest(signature, expected_signature):
        raise _unauthorized()

    now = int(time.time())
    subject = payload.get("sub")
    audience = payload.get("aud")
    expires_at = payload.get("exp")
    not_before = payload.get("nbf")
    valid_audience = (
        settings.auth_jwt_audience in audience
        if isinstance(audience, list)
        else audience == settings.auth_jwt_audience
    )
    if (
        not isinstance(subject, str)
        or not subject
        or payload.get("iss") != settings.auth_jwt_issuer
        or not valid_audience
        or isinstance(expires_at, bool)
        or not isinstance(expires_at, (int, float))
        or expires_at <= now
        or (
            not_before is not None
            and (
                isinstance(not_before, bool)
                or not isinstance(not_before, (int, float))
                or not_before > now
            )
        )
    ):
        raise _unauthorized()
    return subject


def _decode_segment(value: str) -> str:
    return _decode_bytes(value).decode()


def _decode_bytes(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication is required",
        headers={"WWW-Authenticate": "Bearer"},
    )
