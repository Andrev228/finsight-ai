"""Tests for privacy-safe rate-limit keys."""

from pydantic import SecretStr

from app.core import rate_limit
from app.core.rate_limit import _fingerprint


def test_rate_limit_fingerprint_does_not_expose_user_id(monkeypatch):
    monkeypatch.setattr(
        rate_limit.settings,
        "plaid_token_encryption_key",
        SecretStr("test-fingerprint-secret"),
    )

    fingerprint = _fingerprint("local-development-user")

    assert len(fingerprint) == 64
    assert "local-development-user" not in fingerprint
