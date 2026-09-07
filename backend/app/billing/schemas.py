"""Billing API contracts."""

from datetime import datetime

from pydantic import BaseModel


class BillingUrl(BaseModel):
    url: str


class SubscriptionStatus(BaseModel):
    status: str
    price_id: str | None = None
    current_period_end: datetime | None = None
    cancel_at_period_end: bool = False


class WebhookResult(BaseModel):
    received: bool = True
    duplicate: bool = False
