"""Tests for privacy-safe rate-limit keys."""

from app.core.rate_limit import _fingerprint


def test_rate_limit_fingerprint_does_not_expose_user_id():
    fingerprint = _fingerprint("local-development-user")

    assert len(fingerprint) == 64
    assert "local-development-user" not in fingerprint
