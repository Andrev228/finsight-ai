"""Tests for bounded agent orchestration."""

import asyncio
from datetime import date, timedelta

import pytest

from app.ai.agent import (
    DEFAULT_ANALYTICS_DAYS,
    FinancialAgent,
    InvalidAnalyticsPeriodError,
)
from app.ai.exceptions import LLMProviderError


class FailingGateway:
    async def plan(self, message, today):
        raise LLMProviderError("RESOURCE_EXHAUSTED", status_code=429)


class RecordingStub:
    def __init__(self):
        self.values = None

    async def record(self, **values):
        self.values = values


def test_default_period_is_bounded_and_end_exclusive():
    today = date(2026, 9, 5)

    start, end = FinancialAgent._resolve_period(None, None, today)

    assert end == today + timedelta(days=1)
    assert end - start == timedelta(days=DEFAULT_ANALYTICS_DAYS)


def test_model_period_cannot_exceed_maximum():
    today = date(2026, 9, 5)
    requested_end = date(2026, 9, 1)

    with pytest.raises(InvalidAnalyticsPeriodError):
        FinancialAgent._resolve_period(
            date(2020, 1, 1),
            requested_end,
            today,
        )


def test_invalid_model_period_falls_back_safely():
    today = date(2026, 9, 5)
    requested_end = date(2026, 8, 1)

    with pytest.raises(InvalidAnalyticsPeriodError):
        FinancialAgent._resolve_period(
            date(2026, 9, 1),
            requested_end,
            today,
        )


def test_provider_failure_is_recorded_without_masking_original_error():
    recorder = RecordingStub()
    agent = FinancialAgent(FailingGateway(), object(), object(), recorder)

    with pytest.raises(LLMProviderError):
        asyncio.run(agent.answer("question", "user-1"))

    assert recorder.values["success"] is False
    assert recorder.values["error_code"] == "RESOURCE_EXHAUSTED"
