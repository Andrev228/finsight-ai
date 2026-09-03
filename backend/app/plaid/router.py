"""HTTP routes for Plaid Link."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.config import settings
from app.plaid.client import (
    LinkToken,
    PlaidApiError,
    PlaidClient,
    PlaidConfigurationError,
)

router = APIRouter(prefix="/api/plaid", tags=["plaid"])


def get_plaid_client() -> PlaidClient:
    return PlaidClient(settings)


@router.post("/link-token", response_model=LinkToken)
async def create_link_token(
    plaid: Annotated[PlaidClient, Depends(get_plaid_client)],
) -> LinkToken:
    try:
        return await plaid.create_link_token(settings.plaid_client_user_id)
    except PlaidConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Plaid Sandbox is not configured",
        ) from exc
    except PlaidApiError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "message": "Plaid request failed",
                "error_code": exc.error_code,
                "request_id": exc.request_id,
            },
        ) from exc
