"""Minimal async client for the Plaid Sandbox API."""

import httpx

from app.core.config import Settings
from app.plaid.exceptions import PlaidApiError, PlaidConfigurationError
from app.plaid.schemas import LinkToken


class PlaidClient:
    def __init__(self, settings: Settings) -> None:
        self._client_id = settings.plaid_client_id
        self._secret = settings.plaid_secret
        self._base_url = f"https://{settings.plaid_env}.plaid.com"

    async def create_link_token(self, client_user_id: str) -> LinkToken:
        if not self._client_id or not self._secret:
            raise PlaidConfigurationError("Plaid credentials are not configured")

        payload = {
            "client_id": self._client_id,
            "secret": self._secret,
            "client_name": "finsight-ai",
            "language": "en",
            "country_codes": ["US"],
            "products": ["transactions"],
            "user": {"client_user_id": client_user_id},
        }

        try:
            async with httpx.AsyncClient(
                base_url=self._base_url,
                timeout=10,
            ) as client:
                response = await client.post("/link/token/create", json=payload)
        except httpx.HTTPError as exc:
            raise PlaidApiError("PLAID_UNAVAILABLE") from exc

        body = response.json()
        if response.is_error:
            raise PlaidApiError(
                error_code=body.get("error_code", "PLAID_REQUEST_FAILED"),
                request_id=body.get("request_id"),
            )

        return LinkToken.model_validate(body)
