"""Billing persistence models."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Uuid, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.banking import TimestampMixin


class BillingCustomer(TimestampMixin, Base):
    __tablename__ = "billing_customers"

    user_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    stripe_customer_id: Mapped[str] = mapped_column(String(255), unique=True)


class Subscription(TimestampMixin, Base):
    __tablename__ = "subscriptions"

    id: Mapped[UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("billing_customers.user_id", ondelete="CASCADE"),
        unique=True,
        index=True,
    )
    stripe_customer_id: Mapped[str] = mapped_column(String(255), index=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(
        String(255),
        unique=True,
    )
    status: Mapped[str] = mapped_column(String(32), server_default="inactive")
    price_id: Mapped[str | None] = mapped_column(String(255))
    current_period_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )
    cancel_at_period_end: Mapped[bool] = mapped_column(
        Boolean,
        server_default="false",
    )
    last_event_created: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )


class StripeEvent(Base):
    __tablename__ = "stripe_events"

    event_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(128))
    payload_hash: Mapped[str] = mapped_column(String(64))
    event_created: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
