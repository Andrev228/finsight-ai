"""HTTP routes for AI chat."""

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from typing import Annotated
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.agent import FinancialAgent, InvalidAnalyticsPeriodError
from app.ai.embeddings import GeminiEmbeddingGateway
from app.ai.exceptions import LLMConfigurationError, LLMProviderError
from app.ai.gateway import GeminiGateway
from app.ai.history import ChatHistoryService, ConversationNotFoundError
from app.ai.ingestion import KnowledgeIngestionService, SOURCES
from app.ai.observability import AiRunRecorder
from app.ai.rag import RagService
from app.ai.schemas import (
    ChatRequest,
    ChatResponse,
    ConversationDetail,
    ConversationSummary,
    IngestionResult,
    KnowledgeChunkRequest,
    KnowledgeChunkResponse,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
)
from app.core.auth import AdminAccess, CurrentUser
from app.core.config import settings
from app.core.encryption import TokenCipher, get_token_cipher
from app.core.rate_limit import AiRateLimit
from app.db.session import get_session
from app.analytics.service import AnalyticsService

router = APIRouter(prefix="/api/ai", tags=["ai"])
logger = logging.getLogger(__name__)

STREAM_POLL_SECONDS = 0.5


def get_llm_gateway() -> GeminiGateway:
    return GeminiGateway(settings)


def get_rag_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> RagService:
    return RagService(GeminiEmbeddingGateway(settings), session)


def get_chat_service(
    rag: Annotated[RagService, Depends(get_rag_service)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> FinancialAgent:
    return FinancialAgent(
        get_llm_gateway(),
        rag,
        AnalyticsService(session),
        AiRunRecorder(),
    )


def get_ingestion_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> KnowledgeIngestionService:
    return KnowledgeIngestionService(GeminiEmbeddingGateway(settings), session)


def get_chat_history(
    session: Annotated[AsyncSession, Depends(get_session)],
    cipher: Annotated[TokenCipher, Depends(get_token_cipher)],
) -> ChatHistoryService:
    return ChatHistoryService(session, cipher)


@router.get("/conversations", response_model=list[ConversationSummary])
async def list_conversations(
    current_user: CurrentUser,
    history: Annotated[ChatHistoryService, Depends(get_chat_history)],
) -> list[ConversationSummary]:
    return await history.list_conversations(current_user.user_id)


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationDetail,
)
async def get_conversation(
    conversation_id: UUID,
    current_user: CurrentUser,
    history: Annotated[ChatHistoryService, Depends(get_chat_history)],
) -> ConversationDetail:
    return await history.get_conversation(
        conversation_id,
        current_user.user_id,
    )


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    service: Annotated[FinancialAgent, Depends(get_chat_service)],
    history: Annotated[ChatHistoryService, Depends(get_chat_history)],
    current_user: CurrentUser,
    _: AiRateLimit,
) -> ChatResponse:
    conversation = await history.add_user_message(
        current_user.user_id,
        request.message,
        request.conversation_id,
    )
    response = await service.answer(request.message, current_user.user_id)
    await history.add_assistant_message(conversation, response)
    return response


@router.post("/chat/stream")
async def stream_chat(
    request_body: ChatRequest,
    request: Request,
    service: Annotated[FinancialAgent, Depends(get_chat_service)],
    history: Annotated[ChatHistoryService, Depends(get_chat_history)],
    current_user: CurrentUser,
    _: AiRateLimit,
) -> StreamingResponse:
    async def events() -> AsyncIterator[str]:
        queue: asyncio.Queue[dict[str, object] | None] = asyncio.Queue()

        async def report(progress: str) -> None:
            await queue.put({"type": "status", "status": progress})

        async def run_agent() -> None:
            try:
                conversation = await history.add_user_message(
                    current_user.user_id,
                    request_body.message,
                    request_body.conversation_id,
                )
                result = await service.answer(
                    request_body.message,
                    current_user.user_id,
                    on_progress=report,
                )
                await history.add_assistant_message(conversation, result)
                await queue.put(
                    {
                        "type": "result",
                        "conversation_id": str(conversation.id),
                        "data": result.model_dump(mode="json"),
                    },
                )
            except ConversationNotFoundError:
                await queue.put(
                    {
                        "type": "error",
                        "message": "Conversation was not found.",
                        "code": "CONVERSATION_NOT_FOUND",
                    },
                )
            except InvalidAnalyticsPeriodError as exc:
                await queue.put(
                    {"type": "error", "message": str(exc), "code": "INVALID_PERIOD"},
                )
            except (LLMConfigurationError, LLMProviderError):
                await queue.put(
                    {
                        "type": "error",
                        "message": "The AI service is temporarily unavailable.",
                        "code": "AI_UNAVAILABLE",
                    },
                )
            except Exception:
                logger.exception("Unexpected streamed chat failure")
                await queue.put(
                    {
                        "type": "error",
                        "message": "The chat request failed unexpectedly.",
                        "code": "INTERNAL_ERROR",
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

    return StreamingResponse(
        events(),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache, no-transform"},
    )


@router.post("/knowledge", response_model=KnowledgeChunkResponse)
async def add_knowledge(
    request: KnowledgeChunkRequest,
    rag: Annotated[RagService, Depends(get_rag_service)],
    _: AdminAccess,
) -> KnowledgeChunkResponse:
    try:
        return await rag.add_chunk(
            source=request.source,
            title=request.title,
            content=request.content,
        )
    except (LLMConfigurationError, LLMProviderError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Knowledge embedding failed",
        ) from exc


@router.post("/knowledge/search", response_model=KnowledgeSearchResponse)
async def search_knowledge(
    request: KnowledgeSearchRequest,
    rag: Annotated[RagService, Depends(get_rag_service)],
    _: AdminAccess,
) -> KnowledgeSearchResponse:
    try:
        chunks = await rag.search(request.query, request.limit)
        return KnowledgeSearchResponse(chunks=chunks)
    except (LLMConfigurationError, LLMProviderError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Knowledge search failed",
        ) from exc


@router.post("/knowledge/ingest/{source_id}", response_model=IngestionResult)
async def ingest_knowledge(
    source_id: str,
    service: Annotated[
        KnowledgeIngestionService,
        Depends(get_ingestion_service),
    ],
    _: AdminAccess,
) -> IngestionResult:
    if source_id not in SOURCES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge source was not found",
        )
    try:
        return await service.ingest(source_id)
    except (
        httpx.HTTPError,
        ValueError,
        LLMConfigurationError,
        LLMProviderError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Knowledge ingestion failed",
        ) from exc
