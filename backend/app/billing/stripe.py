"""Minimal Stripe API and webhook client."""

import hashlib
import hmac
import json
import time
from typing import Any
from urllib.parse import urlencode

import httpx

from app.core.config import StripeConfig


class StripeError(RuntimeError):
    pass


class StripeSignatureError(StripeError):
    pass


class StripeClient:
    def __init__(self, config: StripeConfig) -> None:
        self._key = config.secret_key.get_secret_value()
        self._webhook_secret = config.webhook_secret.get_secret_value()
        self._base_url = "https://api.stripe.com/v1"

    async def post(
        self,
        path: str,
        values: list[tuple[str, str]],
        *,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        if not self._key:
            raise StripeError("Stripe is not configured")
        async with httpx.AsyncClient(timeout=15) as client:
            headers = {
                "Authorization": f"Bearer {self._key}",
                "Content-Type": "application/x-www-form-urlencoded",
            }
            if idempotency_key:
                headers["Idempotency-Key"] = idempotency_key
            response = await client.post(
                f"{self._base_url}/{path.lstrip('/')}",
                headers=headers,
                content=urlencode(values),
            )
        if response.status_code >= 400:
            raise StripeError("Stripe request failed")
        payload = response.json()
        if not isinstance(payload, dict):
            raise StripeError("Stripe returned an invalid response")
        return payload

    async def get(self, path: str) -> dict[str, Any]:
        if not self._key:
            raise StripeError("Stripe is not configured")
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(
                f"{self._base_url}/{path.lstrip('/')}",
                headers={"Authorization": f"Bearer {self._key}"},
            )
        if response.status_code >= 400:
            raise StripeError("Stripe request failed")
        payload = response.json()
        if not isinstance(payload, dict):
            raise StripeError("Stripe returned an invalid response")
        return payload

    def verify_webhook(
        self,
        body: bytes,
        signature_header: str,
        *,
        tolerance_seconds: int = 300,
    ) -> dict[str, Any]:
        if not self._webhook_secret:
            raise StripeSignatureError("Stripe webhook is not configured")
        values: dict[str, list[str]] = {}
        for part in signature_header.split(","):
            key, separator, value = part.partition("=")
            if separator:
                values.setdefault(key, []).append(value)
        try:
            timestamp = int(values["t"][0])
        except (KeyError, ValueError):
            raise StripeSignatureError("Invalid Stripe signature") from None
        if abs(int(time.time()) - timestamp) > tolerance_seconds:
            raise StripeSignatureError("Expired Stripe signature")
        signed = f"{timestamp}.".encode() + body
        expected = hmac.new(
            self._webhook_secret.encode(),
            signed,
            hashlib.sha256,
        ).hexdigest()
        if not any(
            hmac.compare_digest(expected, candidate)
            for candidate in values.get("v1", [])
        ):
            raise StripeSignatureError("Invalid Stripe signature")
        try:
            event = json.loads(body)
        except json.JSONDecodeError:
            raise StripeSignatureError("Invalid Stripe payload") from None
        if not isinstance(event, dict):
            raise StripeSignatureError("Invalid Stripe payload")
        return event
