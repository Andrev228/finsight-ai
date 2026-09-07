"""Tests for the AI chat endpoint."""

from fastapi.testclient import TestClient

from app.ai.exceptions import LLMProviderError
from app.ai.router import get_chat_service
from app.ai.schemas import ChatResponse
from app.main import app

client = TestClient(app)


class SuccessfulChatService:
    async def answer(self, message: str, user_id: str) -> ChatResponse:
        assert message == "How does budgeting work?"
        assert user_id == "local-development-user"
        return ChatResponse(
            answer="A budget compares planned income and spending.",
            model="test-model",
            input_tokens=8,
            output_tokens=9,
            sources=[],
            tools_used=["knowledge_search"],
            unsupported=False,
        )


class FailingChatService:
    async def answer(self, message: str, user_id: str) -> ChatResponse:
        raise LLMProviderError(
            "credit_balance_exhausted",
            status_code=429,
            request_id="request-test",
        )


def test_chat_returns_gateway_response():
    app.dependency_overrides[get_chat_service] = SuccessfulChatService

    response = client.post(
        "/api/ai/chat",
        json={"message": "How does budgeting work?"},
    )

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json() == {
        "answer": "A budget compares planned income and spending.",
        "model": "test-model",
        "input_tokens": 8,
        "output_tokens": 9,
        "sources": [],
        "tools_used": ["knowledge_search"],
        "analytics": None,
        "unsupported": False,
    }


def test_chat_maps_provider_errors():
    app.dependency_overrides[get_chat_service] = FailingChatService

    response = client.post("/api/ai/chat", json={"message": "Hello"})

    app.dependency_overrides.clear()
    assert response.status_code == 502
    assert response.json()["detail"]["error_code"] == "credit_balance_exhausted"
