"""Authenticated billing endpoints and Stripe webhook."""

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.billing.schemas import BillingUrl, SubscriptionStatus, WebhookResult
from app.billing.service import BillingService
from app.billing.stripe import StripeClient, StripeError, StripeSignatureError
from app.core.auth import CurrentUser
from app.core.config import settings
from app.db.session import get_session

router = APIRouter(prefix="/api/billing", tags=["billing"])


def get_billing_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> BillingService:
    return BillingService(StripeClient(settings), session, settings)


@router.post("/checkout", response_model=BillingUrl)
async def checkout(
    current_user: CurrentUser,
    service: Annotated[BillingService, Depends(get_billing_service)],
) -> BillingUrl:
    try:
        return BillingUrl(url=await service.create_checkout(current_user.user_id))
    except StripeError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@router.post("/portal", response_model=BillingUrl)
async def portal(
    current_user: CurrentUser,
    service: Annotated[BillingService, Depends(get_billing_service)],
) -> BillingUrl:
    try:
        return BillingUrl(url=await service.create_portal(current_user.user_id))
    except StripeError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@router.get("/subscription", response_model=SubscriptionStatus)
async def subscription(
    current_user: CurrentUser,
    service: Annotated[BillingService, Depends(get_billing_service)],
) -> SubscriptionStatus:
    return await service.status(current_user.user_id)


@router.post("/webhook", response_model=WebhookResult)
async def webhook(
    request: Request,
    stripe_signature: Annotated[str | None, Header(alias="Stripe-Signature")],
    service: Annotated[BillingService, Depends(get_billing_service)],
) -> WebhookResult:
    if not stripe_signature:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Stripe signature is required",
        )
    body = await request.body()
    try:
        event = StripeClient(settings).verify_webhook(body, stripe_signature)
    except StripeSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    try:
        processed = await service.process_event(event, body)
    except StripeError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    return WebhookResult(duplicate=not processed)
