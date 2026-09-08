"""Chat and conversation-history routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from app.ai.agent import FinancialAgent
from app.ai.dependencies import get_chat_history, get_chat_service
from app.ai.history import ChatHistoryService
from app.ai.schemas import (
    ChatRequest,
    ChatResponse,
    ConversationDetail,
    ConversationSummary,
)
from app.ai.streaming import stream_chat_events
from app.core.auth import CurrentUser
from app.core.rate_limit import AiRateLimit

router = APIRouter(prefix="/api/ai", tags=["ai"])


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
    turns = await history.recent_turns(
        request.conversation_id,
        current_user.user_id,
    )
    conversation = await history.add_user_message(
        current_user.user_id,
        request.message,
        request.conversation_id,
    )
    response = await service.answer(
        request.message,
        current_user.user_id,
        history=turns,
    )
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
    return StreamingResponse(
        stream_chat_events(
            request_body,
            request,
            service,
            history,
            current_user.user_id,
        ),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache, no-transform"},
    )
