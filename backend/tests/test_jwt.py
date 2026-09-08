"""Unit tests for framework-free HS256 verification."""

import base64
import hashlib
import hmac
import json

import pytest

from app.core.jwt import InvalidTokenError, decode_hs256

SECRET = "a" * 32
ISSUER = "finsight-ai"
AUDIENCE = "finsight-ai-api"


def _encode(value: object) -> str:
    return (
        base64.urlsafe_b64encode(json.dumps(value, separators=(",", ":")).encode())
        .rstrip(b"=")
        .decode()
    )


def _token(secret: str = SECRET, **claims: object) -> str:
    header = _encode({"alg": "HS256", "typ": "JWT"})
    payload = _encode(claims)
    signature = hmac.new(
        secret.encode(),
        f"{header}.{payload}".encode(),
        hashlib.sha256,
    ).digest()
    encoded_signature = base64.urlsafe_b64encode(signature).rstrip(b"=").decode()
    return f"{header}.{payload}.{encoded_signature}"


def test_valid_token_with_audience_list_returns_subject():
    token = _token(
        sub="user-1",
        iss=ISSUER,
        aud=["other", AUDIENCE],
        exp=1000,
    )

    subject = decode_hs256(
        token,
        secret=SECRET,
        issuer=ISSUER,
        audience=AUDIENCE,
        now=500,
    )

    assert subject == "user-1"


def test_not_before_in_the_future_is_rejected():
    token = _token(sub="user-1", iss=ISSUER, aud=AUDIENCE, exp=1000, nbf=900)

    with pytest.raises(InvalidTokenError):
        decode_hs256(token, secret=SECRET, issuer=ISSUER, audience=AUDIENCE, now=500)


def test_signature_from_a_different_secret_is_rejected():
    token = _token(secret="b" * 32, sub="user-1", iss=ISSUER, aud=AUDIENCE, exp=1000)

    with pytest.raises(InvalidTokenError):
        decode_hs256(token, secret=SECRET, issuer=ISSUER, audience=AUDIENCE, now=500)
