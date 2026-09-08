"""NDJSON streaming plumbing for the chat endpoint."""

import asyncio
import json
import logging
from collections.abc import AsyncIterator

from starlette.requests import Request

from app.ai.agent import FinancialAgent, InvalidAnalyticsPeriodError
from app.ai.exceptions import LLMConfigurationError, LLMProviderError
from app.ai.history import ChatHistoryService, ConversationNotFoundError
from app.ai.schemas import ChatRequest

logger = logging.getLogger(__name__)

STREAM_POLL_SECONDS = 0.5


def stream_chat_events(
    request_body: ChatRequest,
    request: Request,
    service: FinancialAgent,
    history: ChatHistoryService,
    user_id: str,
) -> AsyncIterator[str]:
    """Run the agent in the background and yield NDJSON progress events."""

    async def events() -> AsyncIterator[str]:
        queue: asyncio.Queue[dict[str, object] | None] = asyncio.Queue()

        async def report(progress: str) -> None:
            await queue.put({"type": "status", "status": progress})

        async def run_agent() -> None:
            try:
                turns = await history.recent_turns(
                    request_body.conversation_id,
                    user_id,
                )
                conversation = await history.add_user_message(
                    user_id,
                    request_body.message,
                    request_body.conversation_id,
                )
            except ConversationNotFoundError:
                await queue.put(
                    {
                        "type": "error",
                        "message": "Conversation was not found.",
                        "code": "CONVERSATION_NOT_FOUND",
                    },
                )
                await queue.put(None)
                return

            conversation_id = str(conversation.id)
            try:
                result = await service.answer(
                    request_body.message,
                    user_id,
                    on_progress=report,
                    history=turns,
                )
                await history.add_assistant_message(conversation, result)
                await queue.put(
                    {
                        "type": "result",
                        "conversation_id": conversation_id,
                        "data": result.model_dump(mode="json"),
                    },
                )
            except InvalidAnalyticsPeriodError as exc:
                await queue.put(
                    {
                        "type": "error",
                        "message": str(exc),
                        "code": "INVALID_PERIOD",
                        "conversation_id": conversation_id,
                    },
                )
            except (LLMConfigurationError, LLMProviderError):
                await queue.put(
                    {
                        "type": "error",
                        "message": "The AI service is temporarily unavailable.",
                        "code": "AI_UNAVAILABLE",
                        "conversation_id": conversation_id,
                    },
                )
            except Exception:
                logger.exception("Unexpected streamed chat failure")
                await queue.put(
                    {
                        "type": "error",
                        "message": "The chat request failed unexpectedly.",
                        "code": "INTERNAL_ERROR",
                        "conversation_id": conversation_id,
                    },
                )
            finally:
                await queue.put(None)

        task = asyncio.create_task(run_agent())
        try:
            while True:
                if await request.is_disconnected():
                    task.cancel()
                    break
                try:
                    event = await asyncio.wait_for(
                        queue.get(),
                        timeout=STREAM_POLL_SECONDS,
                    )
                except TimeoutError:
                    continue
                if event is None:
                    break
                yield json.dumps(event, separators=(",", ":")) + "\n"
        finally:
            if not task.done():
                task.cancel()
            await asyncio.gather(task, return_exceptions=True)

    return events()
