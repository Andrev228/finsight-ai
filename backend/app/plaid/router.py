"""HTTP routes for Plaid Link."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser
from app.core.config import settings
from app.core.encryption import EncryptionConfigurationError, get_app_cipher
from app.db.session import get_session
from app.plaid.client import PlaidClient
from app.plaid.exceptions import (
    PlaidApiError,
    PlaidConfigurationError,
    PlaidItemAlreadyExistsError,
    PlaidItemNotFoundError,
)
from app.plaid.schemas import (
    AccountsSyncResult,
    ConnectedItem,
    LinkToken,
    PublicTokenRequest,
    TransactionsSyncResult,
)
from app.plaid.service import PlaidService

router = APIRouter(prefix="/api/plaid", tags=["plaid"])


def get_plaid_client() -> PlaidClient:
    return PlaidClient(settings)


def get_plaid_service(
    plaid: Annotated[PlaidClient, Depends(get_plaid_client)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PlaidService:
    try:
        token_cipher = get_app_cipher()
    except EncryptionConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Token encryption is not configured",
        ) from exc
    return PlaidService(plaid, session, token_cipher)


@router.post("/link-token", response_model=LinkToken)
async def create_link_token(
    plaid: Annotated[PlaidClient, Depends(get_plaid_client)],
    current_user: CurrentUser,
) -> LinkToken:
    try:
        return await plaid.create_link_token(current_user.user_id)
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
    current_user: CurrentUser,
) -> ConnectedItem:
    try:
        return await service.connect_item(
            public_token=request.public_token.get_secret_value(),
            user_id=current_user.user_id,
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


@router.post(
    "/items/{item_id}/accounts/sync",
    response_model=AccountsSyncResult,
)
async def sync_accounts(
    item_id: UUID,
    service: Annotated[PlaidService, Depends(get_plaid_service)],
    current_user: CurrentUser,
) -> AccountsSyncResult:
    try:
        return await service.sync_accounts(
            item_id=item_id,
            user_id=current_user.user_id,
        )
    except PlaidItemNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plaid Item was not found",
        ) from exc
    except PlaidApiError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "message": "Plaid accounts request failed",
                "error_code": exc.error_code,
                "request_id": exc.request_id,
            },
        ) from exc


@router.post(
    "/items/{item_id}/transactions/sync",
    response_model=TransactionsSyncResult,
)
async def sync_transactions(
    item_id: UUID,
    service: Annotated[PlaidService, Depends(get_plaid_service)],
    current_user: CurrentUser,
) -> TransactionsSyncResult:
    try:
        return await service.sync_transactions(
            item_id=item_id,
            user_id=current_user.user_id,
        )
    except PlaidItemNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plaid Item was not found",
        ) from exc
    except PlaidApiError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "message": "Plaid transactions request failed",
                "error_code": exc.error_code,
                "request_id": exc.request_id,
            },
        ) from exc
