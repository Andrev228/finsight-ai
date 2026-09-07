"""Tests for deterministic analytics routes and arithmetic."""

from datetime import UTC, date, datetime
from decimal import Decimal

from fastapi.testclient import TestClient

from app.analytics.router import get_analytics_service
from app.analytics.schemas import (
    AnalyticsPeriod,
    CategorySpending,
    FinancialOverview,
    MonthlyCashFlow,
)
from app.main import app

client = TestClient(app)


class SuccessfulAnalyticsService:
    async def get_overview(
        self,
        user_id: str,
        start: date,
        end_exclusive: date,
        currency: str,
        category_limit: int,
    ) -> FinancialOverview:
        assert user_id == "local-development-user"
        assert start == date(2026, 8, 1)
        assert end_exclusive == date(2026, 9, 1)
        assert currency == "USD"
        assert category_limit == 5
        return FinancialOverview(
            period=AnalyticsPeriod(
                start=start,
                end_exclusive=end_exclusive,
            ),
            currency=currency,
            total_spending=Decimal("125.50"),
            total_income=Decimal("1000.00"),
            net_cash_flow=Decimal("874.50"),
            transaction_count=4,
            top_categories=[
                CategorySpending(
                    category="FOOD_AND_DRINK",
                    amount=Decimal("75.50"),
                    transaction_count=2,
                ),
            ],
            monthly_cash_flow=[
                MonthlyCashFlow(
                    month=date(2026, 8, 1),
                    spending=Decimal("125.50"),
                    income=Decimal("1000.00"),
                    net_cash_flow=Decimal("874.50"),
                ),
            ],
            generated_at=datetime(2026, 9, 1, tzinfo=UTC),
        )


def test_overview_returns_sql_calculated_facts():
    app.dependency_overrides[get_analytics_service] = SuccessfulAnalyticsService

    response = client.get(
        "/api/analytics/overview",
        params={
            "start": "2026-08-01",
            "end_exclusive": "2026-09-01",
        },
    )

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["net_cash_flow"] == "874.50"
    assert response.json()["top_categories"][0]["category"] == "FOOD_AND_DRINK"


def test_overview_rejects_invalid_period():
    app.dependency_overrides[get_analytics_service] = SuccessfulAnalyticsService

    response = client.get(
        "/api/analytics/overview",
        params={
            "start": "2026-09-01",
            "end_exclusive": "2026-08-01",
        },
    )

    app.dependency_overrides.clear()
    assert response.status_code == 422
    assert response.json()["detail"] == "start must be before end"
