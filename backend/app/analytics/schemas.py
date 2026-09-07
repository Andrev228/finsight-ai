"""Validated financial analytics responses."""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class AnalyticsPeriod(BaseModel):
    start: date
    end_exclusive: date


class CategorySpending(BaseModel):
    category: str
    amount: Decimal
    transaction_count: int


class MonthlyCashFlow(BaseModel):
    month: date
    spending: Decimal
    income: Decimal
    net_cash_flow: Decimal


class FinancialOverview(BaseModel):
    period: AnalyticsPeriod
    currency: str
    total_spending: Decimal
    total_income: Decimal
    net_cash_flow: Decimal
    transaction_count: int
    top_categories: list[CategorySpending]
    monthly_cash_flow: list[MonthlyCashFlow]
    generated_at: datetime
    warnings: list[str] = Field(default_factory=list)
