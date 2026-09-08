"""Aggregated AI router.

Combines the chat and knowledge sub-routers and re-exports dependency
providers so existing imports (and test overrides) keep working.
"""

from fastapi import APIRouter

from app.ai.dependencies import (
    get_chat_history,
    get_chat_service,
    get_ingestion_service,
    get_llm_gateway,
    get_rag_service,
)
from app.ai.routers.chat import router as chat_router
from app.ai.routers.knowledge import router as knowledge_router

router = APIRouter()
router.include_router(chat_router)
router.include_router(knowledge_router)

__all__ = [
    "get_chat_history",
    "get_chat_service",
    "get_ingestion_service",
    "get_llm_gateway",
    "get_rag_service",
    "router",
]
