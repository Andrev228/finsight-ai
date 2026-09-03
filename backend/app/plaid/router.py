"""HTTP routes for Plaid Link."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.encryption import EncryptionConfigurationError, get_token_cipher
from app.core.config import settings
from app.db.session import get_session
from app.plaid.client import PlaidClient
from app.plaid.exceptions import (
    PlaidApiError,
    PlaidConfigurationError,
    PlaidItemAlreadyExistsError,
)
from app.plaid.schemas import ConnectedItem, LinkToken, PublicTokenRequest
from app.plaid.service import PlaidService

router = APIRouter(prefix="/api/plaid", tags=["plaid"])


def get_plaid_client() -> PlaidClient:
    return PlaidClient(settings)


def get_plaid_service(
    plaid: Annotated[PlaidClient, Depends(get_plaid_client)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PlaidService:
    try:
        token_cipher = get_token_cipher()
    except EncryptionConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Token encryption is not configured",
        ) from exc
    return PlaidService(plaid, session, token_cipher)


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


@router.post("/exchange-token", response_model=ConnectedItem)
async def exchange_public_token(
    request: PublicTokenRequest,
    service: Annotated[PlaidService, Depends(get_plaid_service)],
) -> ConnectedItem:
    try:
        return await service.connect_item(
            public_token=request.public_token.get_secret_value(),
            user_id=settings.plaid_client_user_id,
        )
    except PlaidConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Plaid Sandbox is not configured",
        ) from exc
    except PlaidItemAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This Plaid Item is already connected",
        ) from exc
    except PlaidApiError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "message": "Plaid token exchange failed",
                "error_code": exc.error_code,
                "request_id": exc.request_id,
            },
        ) from exc
