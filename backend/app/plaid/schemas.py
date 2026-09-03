"""Validated Plaid API response models."""

from datetime import datetime
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
