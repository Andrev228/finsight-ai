"""Dependency providers for the AI feature."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.agent import FinancialAgent
from app.ai.embeddings import GeminiEmbeddingGateway
from app.ai.gateway import GeminiGateway
from app.ai.history import ChatHistoryService
from app.ai.ingestion import KnowledgeIngestionService
from app.ai.observability import AiRunRecorder
from app.ai.rag import RagService
from app.analytics.service import AnalyticsService
from app.core.config import settings
from app.core.encryption import AppCipher, get_app_cipher
from app.db.session import get_session


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
    cipher: Annotated[AppCipher, Depends(get_app_cipher)],
) -> ChatHistoryService:
    return ChatHistoryService(session, cipher)
