"""Validated Plaid API response models."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, SecretStr


class LinkToken(BaseModel):
    link_token: str
    expiration: datetime
    request_id: str


class PublicTokenExchange(BaseModel):
    access_token: SecretStr
    item_id: str
    request_id: str


class PublicTokenRequest(BaseModel):
    public_token: SecretStr = Field(min_length=1)


class ConnectedItem(BaseModel):
    id: UUID
    plaid_item_id: str


class PlaidBalances(BaseModel):
    available: Decimal | None
    current: Decimal | None
    iso_currency_code: str | None


class PlaidAccount(BaseModel):
    account_id: str
    balances: PlaidBalances
    mask: str | None
    name: str
    official_name: str | None
    subtype: str | None
    type: str


class PlaidAccountsResponse(BaseModel):
    accounts: list[PlaidAccount]
    request_id: str


class SyncedAccount(BaseModel):
    id: UUID
    plaid_account_id: str
    name: str
    mask: str | None
    account_type: str
    account_subtype: str | None
    current_balance: Decimal | None
    available_balance: Decimal | None
    iso_currency_code: str | None


class AccountsSyncResult(BaseModel):
    accounts: list[SyncedAccount]


class PlaidPersonalFinanceCategory(BaseModel):
    primary: str
    detailed: str


class PlaidTransaction(BaseModel):
    account_id: str
    transaction_id: str
    amount: Decimal
    iso_currency_code: str | None
    date: date
    authorized_date: date | None
    name: str
    merchant_name: str | None
    pending: bool
    personal_finance_category: PlaidPersonalFinanceCategory | None


class PlaidRemovedTransaction(BaseModel):
    transaction_id: str


class PlaidTransactionsSyncResponse(BaseModel):
    accounts: list[PlaidAccount]
    added: list[PlaidTransaction]
    modified: list[PlaidTransaction]
    removed: list[PlaidRemovedTransaction]
    next_cursor: str
    has_more: bool
    request_id: str


class TransactionsSyncResult(BaseModel):
    added: int
    modified: int
    removed: int
