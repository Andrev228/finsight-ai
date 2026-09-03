"""Validated Plaid API response models."""

from datetime import datetime

from pydantic import BaseModel


class LinkToken(BaseModel):
    link_token: str
    expiration: datetime
    request_id: str
