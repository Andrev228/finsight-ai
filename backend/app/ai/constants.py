"""Shared enumerations for the bounded financial agent."""

from enum import StrEnum


class ToolName(StrEnum):
    """Bounded tools the planner may route a question to."""

    FINANCIAL_OVERVIEW = "financial_overview"
    KNOWLEDGE_SEARCH = "knowledge_search"


class AgentProgress(StrEnum):
    """Lifecycle stages streamed to the client during a chat request."""

    PLANNING = "planning"
    ANALYZING_FINANCES = "analyzing_finances"
    SEARCHING_KNOWLEDGE = "searching_knowledge"
    GENERATING = "generating"
