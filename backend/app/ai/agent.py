"""Bounded tool-routing workflow for personal-finance questions."""

import logging
from collections.abc import Awaitable, Callable
from datetime import date, timedelta
from time import perf_counter

from app.ai.constants import AgentProgress, ToolName
from app.ai.exceptions import LLMProviderError
from app.ai.gateway import GeminiGateway
from app.ai.guardrails import redact_pii
from app.ai.observability import AiRunRecorder
from app.ai.rag import RagService
from app.ai.schemas import ChatResponse, ChatSource, ConversationTurn
from app.analytics.schemas import FinancialOverview
from app.analytics.service import AnalyticsService

DEFAULT_ANALYTICS_DAYS = 90
MAX_ANALYTICS_DAYS = 366
TOP_CATEGORY_LIMIT = 5
KNOWLEDGE_SEARCH_LIMIT = 3
logger = logging.getLogger(__name__)


class InvalidAnalyticsPeriodError(ValueError):
    """Raised when the model proposes an unsafe analytics period."""


class FinancialAgent:
    def __init__(
        self,
        gateway: GeminiGateway,
        rag: RagService,
        analytics: AnalyticsService,
        recorder: AiRunRecorder | None = None,
    ) -> None:
        self._gateway = gateway
        self._rag = rag
        self._analytics = analytics
        self._recorder = recorder

    async def answer(
        self,
        message: str,
        user_id: str,
        on_progress: Callable[[str], Awaitable[None]] | None = None,
        history: list[ConversationTurn] | None = None,
    ) -> ChatResponse:
        started_at = perf_counter()
        tools_used: list[str] = []
        try:
            result, planner_tokens = await self._answer(
                message,
                user_id,
                tools_used,
                on_progress,
                history,
            )
        except Exception as exc:
            await self._record(
                user_id=user_id,
                question=message,
                latency_ms=int((perf_counter() - started_at) * 1000),
                success=False,
                tools_used=tools_used,
                error_code=(
                    exc.error_code
                    if isinstance(exc, LLMProviderError)
                    else type(exc).__name__
                ),
            )
            raise
        result.input_tokens += planner_tokens[0]
        result.output_tokens += planner_tokens[1]
        await self._record(
            user_id=user_id,
            question=message,
            latency_ms=int((perf_counter() - started_at) * 1000),
            success=True,
            model=result.model,
            tools_used=result.tools_used,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            unsupported=result.unsupported,
        )
        return result

    async def _answer(
        self,
        message: str,
        user_id: str,
        tools_used: list[str],
        on_progress: Callable[[str], Awaitable[None]] | None,
        history: list[ConversationTurn] | None = None,
    ) -> tuple[ChatResponse, tuple[int, int]]:
        await self._report(on_progress, AgentProgress.PLANNING)
        today = date.today()
        safe_message = redact_pii(message)
        safe_history = [
            ConversationTurn(role=turn.role, content=redact_pii(turn.content))
            for turn in (history or [])
        ]
        planned = await self._gateway.plan(safe_message, today)
        plan = planned.plan
        if plan.unsupported:
            await self._report(on_progress, AgentProgress.GENERATING)
            response = await self._gateway.answer(
                (
                    f"{safe_message}\n\n"
                    "Explain briefly that this request is not supported by the "
                    "available financial tools. Do not invent user data."
                ),
                allowed_citations=set(),
            )
            return ChatResponse(
                **response.model_dump(),
                sources=[],
                tools_used=[],
                analytics=None,
                unsupported=True,
            ), (planned.input_tokens, planned.output_tokens)
        start, end_exclusive = self._resolve_period(
            plan.start,
            plan.end_exclusive,
            today,
        )

        analytics: FinancialOverview | None = None
        chunks = []
        if ToolName.FINANCIAL_OVERVIEW in plan.tools:
            await self._report(on_progress, AgentProgress.ANALYZING_FINANCES)
            analytics = await self._analytics.get_overview(
                user_id=user_id,
                start=start,
                end_exclusive=end_exclusive,
                currency=plan.currency.upper(),
                category_limit=TOP_CATEGORY_LIMIT,
            )
            tools_used.append(ToolName.FINANCIAL_OVERVIEW)
        if ToolName.KNOWLEDGE_SEARCH in plan.tools:
            await self._report(on_progress, AgentProgress.SEARCHING_KNOWLEDGE)
            chunks = await self._rag.search(safe_message, limit=KNOWLEDGE_SEARCH_LIMIT)
            tools_used.append(ToolName.KNOWLEDGE_SEARCH)

        context_parts: list[str] = []
        if analytics is not None:
            context_parts.append(
                "TRUSTED SQL ANALYTICS [analytics]\n"
                + analytics.model_dump_json(),
            )
        if chunks:
            context_parts.append(
                "UNTRUSTED RETRIEVED REFERENCES\n"
                + "\n\n".join(
                    (
                        f"[{index}] {chunk.title}"
                        f"{f' — {chunk.heading}' if chunk.heading else ''}\n"
                        f"Source: {chunk.source}\n"
                        f"{chunk.content}"
                    )
                    for index, chunk in enumerate(chunks, start=1)
                ),
            )

        allowed_citations = {
            *(["analytics"] if analytics is not None else []),
            *(str(index) for index in range(1, len(chunks) + 1)),
        }
        await self._report(on_progress, AgentProgress.GENERATING)
        response = await self._gateway.answer(
            safe_message,
            "\n\n".join(context_parts) or None,
            allowed_citations=allowed_citations,
            history=safe_history,
        )
        return ChatResponse(
            **response.model_dump(),
            sources=[
                ChatSource(
                    id=chunk.id,
                    source=chunk.source,
                    title=chunk.title,
                    heading=chunk.heading,
                    similarity=chunk.similarity,
                )
                for chunk in chunks
            ],
            tools_used=tools_used,
            analytics=analytics,
            unsupported=False,
        ), (planned.input_tokens, planned.output_tokens)

    async def _record(self, **values: object) -> None:
        if self._recorder is not None:
            try:
                await self._recorder.record(**values)
            except Exception:
                logger.exception("AI telemetry write failed")

    @staticmethod
    async def _report(
        callback: Callable[[str], Awaitable[None]] | None,
        status: str,
    ) -> None:
        if callback is not None:
            await callback(status)

    @staticmethod
    def _resolve_period(
        start: date | None,
        end_exclusive: date | None,
        today: date,
    ) -> tuple[date, date]:
        resolved_end = end_exclusive or (today + timedelta(days=1))
        if resolved_end > today + timedelta(days=1):
            raise InvalidAnalyticsPeriodError("Analytics period cannot be in the future")
        resolved_start = start or (
            resolved_end - timedelta(days=DEFAULT_ANALYTICS_DAYS)
        )
        if resolved_start >= resolved_end:
            raise InvalidAnalyticsPeriodError("Analytics period is invalid")
        if resolved_end - resolved_start > timedelta(days=MAX_ANALYTICS_DAYS):
            raise InvalidAnalyticsPeriodError("Analytics period is too large")
        return resolved_start, resolved_end
