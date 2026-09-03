"""Persistence models for Plaid connections and transaction data."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    LargeBinary,
    Numeric,
    String,
    Text,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class PlaidItem(TimestampMixin, Base):
    __tablename__ = "plaid_items"

    id: Mapped[UUID] = mapped_column(
        Uuid,
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[str] = mapped_column(String(255), index=True)
    plaid_item_id: Mapped[str] = mapped_column(String(255), unique=True)
    access_token_encrypted: Mapped[bytes] = mapped_column(LargeBinary)
    institution_id: Mapped[str | None] = mapped_column(String(255))
    sync_cursor: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), server_default="active")


class Account(TimestampMixin, Base):
    __tablename__ = "accounts"

    id: Mapped[UUID] = mapped_column(
        Uuid,
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    plaid_item_id: Mapped[UUID] = mapped_column(
        ForeignKey("plaid_items.id", ondelete="CASCADE"),
        index=True,
    )
    plaid_account_id: Mapped[str] = mapped_column(String(255), unique=True)
    name: Mapped[str] = mapped_column(String(255))
    official_name: Mapped[str | None] = mapped_column(String(255))
    mask: Mapped[str | None] = mapped_column(String(16))
    account_type: Mapped[str] = mapped_column(String(64))
    account_subtype: Mapped[str | None] = mapped_column(String(64))
    iso_currency_code: Mapped[str | None] = mapped_column(String(3))
    current_balance: Mapped[Decimal | None] = mapped_column(Numeric(19, 4))
    available_balance: Mapped[Decimal | None] = mapped_column(Numeric(19, 4))


class Transaction(TimestampMixin, Base):
    __tablename__ = "transactions"
    __table_args__ = (
        Index("ix_transactions_account_date", "account_id", "transaction_date"),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid,
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    account_id: Mapped[UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"),
        index=True,
    )
    plaid_transaction_id: Mapped[str] = mapped_column(String(255), unique=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(19, 4))
    iso_currency_code: Mapped[str | None] = mapped_column(String(3))
    transaction_date: Mapped[date] = mapped_column(Date)
    authorized_date: Mapped[date | None] = mapped_column(Date)
    name: Mapped[str] = mapped_column(String(512))
    merchant_name: Mapped[str | None] = mapped_column(String(512))
    pending: Mapped[bool] = mapped_column(Boolean, server_default="false")
    category_primary: Mapped[str | None] = mapped_column(String(128))
    category_detailed: Mapped[str | None] = mapped_column(String(128))
    is_removed: Mapped[bool] = mapped_column(Boolean, server_default="false")
