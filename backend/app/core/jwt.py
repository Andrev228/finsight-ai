"""Framework-free HS256 JWT verification.

Kept separate from FastAPI wiring so the security-sensitive crypto can be
unit-tested and reviewed in isolation.
"""

import base64
import binascii
import hashlib
import hmac
import json
import time

MIN_JWT_SECRET_BYTES = 32
MAX_JWT_TOKEN_LENGTH = 8192


class InvalidTokenError(ValueError):
    """Raised when a token fails structural, signature, or claim validation."""


def decode_hs256(
    token: str,
    *,
    secret: str,
    issuer: str,
    audience: str,
    now: int | None = None,
) -> str:
    """Verify an HS256 token and return its subject, or raise InvalidTokenError."""
    if len(secret) < MIN_JWT_SECRET_BYTES or len(token) > MAX_JWT_TOKEN_LENGTH:
        raise InvalidTokenError("Malformed token or secret")
    parts = token.split(".")
    if len(parts) != 3:
        raise InvalidTokenError("Token must have three segments")
    encoded_header, encoded_payload, encoded_signature = parts
    try:
        header = json.loads(_decode_segment(encoded_header))
        payload = json.loads(_decode_segment(encoded_payload))
        signature = _decode_bytes(encoded_signature)
    except (
        ValueError,
        binascii.Error,
        json.JSONDecodeError,
        UnicodeDecodeError,
    ) as exc:
        raise InvalidTokenError("Token segments are not decodable") from exc

    if not isinstance(header, dict) or not isinstance(payload, dict):
        raise InvalidTokenError("Token header and payload must be objects")
    if header.get("alg") != "HS256" or header.get("typ") not in (None, "JWT"):
        raise InvalidTokenError("Unsupported token header")

    expected_signature = hmac.new(
        secret.encode(),
        f"{encoded_header}.{encoded_payload}".encode(),
        hashlib.sha256,
    ).digest()
    if not hmac.compare_digest(signature, expected_signature):
        raise InvalidTokenError("Token signature mismatch")

    current = int(time.time()) if now is None else now
    subject = payload.get("sub")
    audience_claim = payload.get("aud")
    expires_at = payload.get("exp")
    not_before = payload.get("nbf")
    valid_audience = (
        audience in audience_claim
        if isinstance(audience_claim, list)
        else audience_claim == audience
    )
    if (
        not isinstance(subject, str)
        or not subject
        or payload.get("iss") != issuer
        or not valid_audience
        or isinstance(expires_at, bool)
        or not isinstance(expires_at, (int, float))
        or expires_at <= current
        or (
            not_before is not None
            and (
                isinstance(not_before, bool)
                or not isinstance(not_before, (int, float))
                or not_before > current
            )
        )
    ):
        raise InvalidTokenError("Token claims failed validation")
    return subject


def _decode_segment(value: str) -> str:
    return _decode_bytes(value).decode()


def _decode_bytes(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)
