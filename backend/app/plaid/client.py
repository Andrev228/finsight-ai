"""Minimal async client for the Plaid Sandbox API."""

import httpx

from app.core.config import PlaidConfig
from app.plaid.exceptions import PlaidApiError, PlaidConfigurationError
from app.plaid.schemas import (
    LinkToken,
    PlaidAccountsResponse,
    PlaidTransactionsSyncResponse,
    PublicTokenExchange,
)


class PlaidClient:
    def __init__(self, config: PlaidConfig) -> None:
        self._client_id = config.client_id
        self._secret = config.secret.get_secret_value()
        self._base_url = f"https://{config.env}.plaid.com"

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

    async def get_accounts(self, access_token: str) -> PlaidAccountsResponse:
        body = await self._post(
            "/accounts/get",
            {"access_token": access_token},
        )
        return PlaidAccountsResponse.model_validate(body)

    async def sync_transactions(
        self,
        access_token: str,
        cursor: str | None,
    ) -> PlaidTransactionsSyncResponse:
        payload: dict[str, object] = {
            "access_token": access_token,
            "count": 500,
        }
        if cursor is not None:
            payload["cursor"] = cursor

        body = await self._post("/transactions/sync", payload)
        return PlaidTransactionsSyncResponse.model_validate(body)

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
