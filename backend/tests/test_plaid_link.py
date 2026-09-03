"""Tests for the Plaid Link token endpoint."""

from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.main import app
from app.plaid.exceptions import PlaidApiError
from app.plaid.router import get_plaid_client, get_plaid_service
from app.plaid.schemas import ConnectedItem, LinkToken

client = TestClient(app)


class SuccessfulPlaidClient:
    async def create_link_token(self, client_user_id: str) -> LinkToken:
        assert client_user_id == "local-development-user"
        return LinkToken(
            link_token="link-sandbox-test",
            expiration=datetime(2026, 9, 3, 15, tzinfo=UTC),
            request_id="request-test",
        )


class FailingPlaidClient:
    async def create_link_token(self, client_user_id: str) -> LinkToken:
        raise PlaidApiError("INVALID_REQUEST", "request-failed")


class SuccessfulPlaidService:
    async def connect_item(self, public_token: str, user_id: str) -> ConnectedItem:
        assert public_token == "public-sandbox-test"
        assert user_id == "local-development-user"
        return ConnectedItem(
            id="8eb7fc6f-d05d-45b6-9599-44f2288b17ea",
            plaid_item_id="item-sandbox-test",
        )


def test_create_link_token_returns_plaid_response():
    app.dependency_overrides[get_plaid_client] = SuccessfulPlaidClient

    response = client.post("/api/plaid/link-token")

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["link_token"] == "link-sandbox-test"


def test_create_link_token_maps_plaid_errors():
    app.dependency_overrides[get_plaid_client] = FailingPlaidClient

    response = client.post("/api/plaid/link-token")

    app.dependency_overrides.clear()
    assert response.status_code == 502
    assert response.json()["detail"]["error_code"] == "INVALID_REQUEST"


def test_exchange_public_token_persists_item():
    app.dependency_overrides[get_plaid_service] = SuccessfulPlaidService

    response = client.post(
        "/api/plaid/exchange-token",
        json={"public_token": "public-sandbox-test"},
    )

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json() == {
        "id": "8eb7fc6f-d05d-45b6-9599-44f2288b17ea",
        "plaid_item_id": "item-sandbox-test",
    }
