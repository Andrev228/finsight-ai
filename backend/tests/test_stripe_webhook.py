"""Stripe webhook signature tests."""

import hashlib
import hmac
import json
import time

import pytest

from app.billing.stripe import StripeClient, StripeError
from app.core.config import settings


def test_stripe_webhook_signature(monkeypatch):
    secret = "whsec_test"
    monkeypatch.setattr(
        settings.stripe_webhook_secret,
        "_secret_value",
        secret,
    )
    body = json.dumps({"id": "evt_1", "type": "test"}).encode()
    timestamp = int(time.time())
    signature = hmac.new(
        secret.encode(),
        f"{timestamp}.".encode() + body,
        hashlib.sha256,
    ).hexdigest()

    event = StripeClient(settings).verify_webhook(
        body,
        f"t={timestamp},v1={signature}",
    )

    assert event["id"] == "evt_1"


def test_expired_stripe_webhook_is_rejected(monkeypatch):
    monkeypatch.setattr(
        settings.stripe_webhook_secret,
        "_secret_value",
        "whsec_test",
    )

    with pytest.raises(StripeError, match="Expired"):
        StripeClient(settings).verify_webhook(
            b"{}",
            "t=1,v1=invalid",
        )
