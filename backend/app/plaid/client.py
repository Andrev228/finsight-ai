"""Minimal async client for the Plaid Sandbox API."""

import httpx

from app.core.config import Settings
from app.plaid.exceptions import PlaidApiError, PlaidConfigurationError
from app.plaid.schemas import LinkToken, PublicTokenExchange


class PlaidClient:
    def __init__(self, settings: Settings) -> None:
        self._client_id = settings.plaid_client_id
        self._secret = settings.plaid_secret
        self._base_url = f"https://{settings.plaid_env}.plaid.com"

    async def create_link_token(self, client_user_id: str) -> LinkToken:
        body = await self._post(
            "/link/token/create",
            {
            "client_name": "finsight-ai",
            "language": "en",
            "country_codes": ["US"],
            "products": ["transactions"],
            "user": {"client_user_id": client_user_id},
            },
        )
        return LinkToken.model_validate(body)

    async def exchange_public_token(
        self,
        public_token: str,
    ) -> PublicTokenExchange:
        body = await self._post(
            "/item/public_token/exchange",
            {"public_token": public_token},
        )
        return PublicTokenExchange.model_validate(body)

    async def _post(self, path: str, payload: dict[str, object]) -> dict[str, object]:
        if not self._client_id or not self._secret:
            raise PlaidConfigurationError("Plaid credentials are not configured")

        authenticated_payload = {
            "client_id": self._client_id,
            "secret": self._secret,
            **payload,
        }
        try:
            async with httpx.AsyncClient(
                base_url=self._base_url,
                timeout=10,
            ) as client:
                response = await client.post(path, json=authenticated_payload)
        except httpx.HTTPError as exc:
            raise PlaidApiError("PLAID_UNAVAILABLE") from exc

        body = response.json()
        if response.is_error:
            raise PlaidApiError(
                error_code=str(body.get("error_code", "PLAID_REQUEST_FAILED")),
                request_id=(
                    str(body["request_id"]) if body.get("request_id") else None
                ),
            )
        return body
