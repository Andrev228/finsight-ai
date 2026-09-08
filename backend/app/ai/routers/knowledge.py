"""Admin-only knowledge base ingestion and search routes."""

from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, status

from app.ai.dependencies import get_ingestion_service, get_rag_service
from app.ai.exceptions import LLMConfigurationError, LLMProviderError
from app.ai.ingestion import SOURCES, KnowledgeIngestionService
from app.ai.rag import RagService
from app.ai.schemas import (
    IngestionResult,
    KnowledgeChunkRequest,
    KnowledgeChunkResponse,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
)
from app.core.auth import AdminAccess

router = APIRouter(prefix="/api/ai", tags=["ai"])


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
