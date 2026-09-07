"""HTTP routes for deterministic financial analytics."""

from datetime import date, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.schemas import FinancialOverview
from app.analytics.service import AnalyticsService
from app.core.auth import CurrentUser
from app.db.session import get_session

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


def get_analytics_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AnalyticsService:
    return AnalyticsService(session)


@router.get("/overview", response_model=FinancialOverview)
async def get_overview(
    service: Annotated[AnalyticsService, Depends(get_analytics_service)],
    current_user: CurrentUser,
    start: date | None = None,
    end_exclusive: date | None = None,
    currency: str = Query(default="USD", min_length=3, max_length=3),
    category_limit: int = Query(default=5, ge=1, le=20),
) -> FinancialOverview:
    resolved_end = end_exclusive or (date.today() + timedelta(days=1))
    resolved_start = start or (resolved_end - timedelta(days=90))
    if resolved_start >= resolved_end:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="start must be before end",
        )

    return await service.get_overview(
        user_id=current_user.user_id,
        start=resolved_start,
        end_exclusive=resolved_end,
        currency=currency.upper(),
        category_limit=category_limit,
    )
