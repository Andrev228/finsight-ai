"""Validated chat request and response models."""

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.ai.constants import ToolName
from app.analytics.schemas import FinancialOverview

ALLOWED_TOOLS = frozenset(ToolName)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    conversation_id: UUID | None = None


class LLMResponse(BaseModel):
    answer: str
    model: str
    input_tokens: int
    output_tokens: int


class ChatSource(BaseModel):
    id: UUID
    source: str
    title: str
    heading: str | None
    similarity: float


class ChatResponse(LLMResponse):
    sources: list[ChatSource]
    tools_used: list[str]
    analytics: FinancialOverview | None = None
    unsupported: bool = False


class ConversationSummary(BaseModel):
    id: UUID
    title: str
    created_at: datetime
    updated_at: datetime


class ConversationMessage(BaseModel):
    id: UUID
    role: Literal["user", "assistant"]
    content: str
    metadata: dict[str, object]
    created_at: datetime


class ConversationDetail(ConversationSummary):
    messages: list[ConversationMessage]


class AgentPlan(BaseModel):
    tools: list[ToolName]
    unsupported: bool = False
    unsupported_reason: str | None = None
    start: date | None = None
    end_exclusive: date | None = None
    currency: str = Field(default="USD", min_length=3, max_length=3)


class GroundedAnswerDraft(BaseModel):
    answer_markdown: str = Field(min_length=1, max_length=5000)
    citations: list[str] = Field(default_factory=list)
    unsupported: bool = False


class KnowledgeChunkRequest(BaseModel):
    source: str = Field(min_length=1, max_length=512)
    title: str = Field(min_length=1, max_length=255)
    content: str = Field(min_length=1, max_length=10000)


class KnowledgeChunkResponse(KnowledgeChunkRequest):
    id: UUID


class KnowledgeSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    limit: int = Field(default=5, ge=1, le=20)


class RetrievedChunk(KnowledgeChunkResponse):
    heading: str | None = None
    similarity: float


class KnowledgeSearchResponse(BaseModel):
    chunks: list[RetrievedChunk]


class IngestionResult(BaseModel):
    source_id: str
    title: str
    chunks: int
    changed: bool
