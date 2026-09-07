"""Stripe checkout and idempotent subscription synchronization."""

import hashlib
import hmac
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.billing.schemas import SubscriptionStatus
from app.billing.stripe import StripeClient, StripeError
from app.core.config import Settings
from app.db.models import BillingCustomer, StripeEvent, Subscription


class BillingService:
    def __init__(
        self,
        stripe: StripeClient,
        session: AsyncSession,
        settings: Settings,
    ) -> None:
        self._stripe = stripe
        self._session = session
        self._settings = settings

    async def create_checkout(self, user_id: str) -> str:
        if not self._settings.stripe_price_id:
            raise StripeError("Stripe price is not configured")
        customer = await self._get_or_create_customer(user_id)
        subscription = await self._session.scalar(
            select(Subscription).where(Subscription.user_id == user_id),
        )
        if subscription is not None and subscription.status in {
            "active",
            "trialing",
            "past_due",
            "unpaid",
            "incomplete",
            "paused",
        }:
            raise StripeError("An active subscription already exists")
        payload = await self._stripe.post(
            "checkout/sessions",
            [
                ("mode", "subscription"),
                ("customer", customer.stripe_customer_id),
                ("line_items[0][price]", self._settings.stripe_price_id),
                ("line_items[0][quantity]", "1"),
                ("success_url", self._settings.stripe_success_url),
                ("cancel_url", self._settings.stripe_cancel_url),
            ],
            idempotency_key=(
                f"checkout-{self._fingerprint(user_id)}-"
                f"{self._settings.stripe_price_id}"
            ),
        )
        return self._required_string(payload, "url")

    async def create_portal(self, user_id: str) -> str:
        customer = await self._customer(user_id)
        if customer is None:
            raise StripeError("No billing customer exists")
        payload = await self._stripe.post(
            "billing_portal/sessions",
            [
                ("customer", customer.stripe_customer_id),
                ("return_url", self._settings.stripe_success_url),
            ],
        )
        return self._required_string(payload, "url")

    async def status(self, user_id: str) -> SubscriptionStatus:
        subscription = await self._session.scalar(
            select(Subscription).where(Subscription.user_id == user_id),
        )
        if subscription is None:
            return SubscriptionStatus(status="inactive")
        return SubscriptionStatus(
            status=subscription.status,
            price_id=subscription.price_id,
            current_period_end=subscription.current_period_end,
            cancel_at_period_end=subscription.cancel_at_period_end,
        )

    async def process_event(
        self,
        event: dict[str, Any],
        raw_body: bytes,
    ) -> bool:
        event_id = self._required_string(event, "id")
        event_type = self._required_string(event, "type")
        created_timestamp = event.get("created")
        if not isinstance(created_timestamp, int):
            raise StripeError("Stripe event timestamp is missing")
        event_created = datetime.fromtimestamp(created_timestamp, tz=UTC)
        self._session.add(
            StripeEvent(
                event_id=event_id,
                event_type=event_type,
                payload_hash=hashlib.sha256(raw_body).hexdigest(),
                event_created=event_created,
            ),
        )
        try:
            await self._session.flush()
        except IntegrityError as exc:
            await self._session.rollback()
            constraint = getattr(getattr(exc.orig, "diag", None), "constraint_name", "")
            if constraint == "stripe_events_pkey":
                return False
            raise
        data = event.get("data")
        obj = data.get("object") if isinstance(data, dict) else None
        if not isinstance(obj, dict):
            raise StripeError("Stripe event object is missing")
        if event_type.startswith("customer.subscription."):
            await self._sync_subscription(obj, event_created)
        await self._session.commit()
        return True

    async def _sync_subscription(
        self,
        obj: dict[str, Any],
        event_created: datetime,
    ) -> None:
        subscription_id = self._required_string(obj, "id")
        current = await self._stripe.get(f"subscriptions/{subscription_id}")
        customer_id = self._required_string(current, "customer")
        customer = await self._session.scalar(
            select(BillingCustomer)
            .where(BillingCustomer.stripe_customer_id == customer_id)
            .with_for_update(),
        )
        if customer is None:
            raise StripeError("Subscription customer is unknown")
        subscription = await self._session.scalar(
            select(Subscription).where(Subscription.user_id == customer.user_id),
        )
        if subscription is None:
            subscription = Subscription(
                user_id=customer.user_id,
                stripe_customer_id=customer_id,
            )
            self._session.add(subscription)
        items = current.get("items", {}).get("data", [])
        first_item = items[0] if isinstance(items, list) and items else {}
        price = first_item.get("price", {}) if isinstance(first_item, dict) else {}
        period_end = current.get("current_period_end")
        subscription.stripe_subscription_id = subscription_id
        subscription.status = self._required_string(current, "status")
        subscription.price_id = price.get("id") if isinstance(price, dict) else None
        subscription.current_period_end = (
            datetime.fromtimestamp(period_end, tz=UTC)
            if isinstance(period_end, int)
            else None
        )
        subscription.cancel_at_period_end = bool(
            current.get("cancel_at_period_end"),
        )
        if (
            subscription.last_event_created is None
            or event_created > subscription.last_event_created
        ):
            subscription.last_event_created = event_created

    async def _get_or_create_customer(self, user_id: str) -> BillingCustomer:
        customer = await self._customer(user_id)
        if customer is not None:
            return customer
        payload = await self._stripe.post(
            "customers",
            [],
            idempotency_key=f"customer-{self._fingerprint(user_id)}",
        )
        customer = BillingCustomer(
            user_id=user_id,
            stripe_customer_id=self._required_string(payload, "id"),
        )
        self._session.add(customer)
        try:
            await self._session.commit()
        except IntegrityError:
            await self._session.rollback()
            existing = await self._customer(user_id)
            if existing is None:
                raise
            return existing
        return customer

    async def _customer(self, user_id: str) -> BillingCustomer | None:
        return await self._session.get(BillingCustomer, user_id)

    @staticmethod
    def _required_string(payload: dict[str, Any], key: str) -> str:
        value = payload.get(key)
        if not isinstance(value, str) or not value:
            raise StripeError(f"Stripe field {key} is missing")
        return value

    def _fingerprint(self, value: str) -> str:
        secret = (
            self._settings.plaid_token_encryption_key.get_secret_value().encode()
        )
        if not secret:
            raise StripeError("Billing fingerprint secret is not configured")
        return hmac.new(secret, value.encode(), hashlib.sha256).hexdigest()
