"""Tests for streamed agent progress."""

from fastapi.testclient import TestClient

from app.ai.router import get_chat_service
from app.ai.schemas import ChatResponse
from app.main import app

client = TestClient(app)


class StreamingChatService:
    async def answer(self, message, user_id, on_progress=None, history=None):
        assert on_progress is not None
        await on_progress("planning")
        await on_progress("generating")
        return ChatResponse(
            answer="Grounded answer",
            model="test-model",
            input_tokens=1,
            output_tokens=2,
            sources=[],
            tools_used=[],
        )


class BrokenStreamingChatService:
    async def answer(self, message, user_id, on_progress=None, history=None):
        raise RuntimeError("database unavailable")


def test_stream_chat_emits_progress_and_result():
    app.dependency_overrides[get_chat_service] = StreamingChatService

    response = client.post(
        "/api/ai/chat/stream",
        json={"message": "Hello"},
    )

    app.dependency_overrides.clear()
    assert response.status_code == 200
    lines = response.text.strip().splitlines()
    assert '"status":"planning"' in lines[0]
    assert '"status":"generating"' in lines[1]
    assert '"type":"result"' in lines[2]


def test_stream_chat_converts_unexpected_failure_to_terminal_error():
    app.dependency_overrides[get_chat_service] = BrokenStreamingChatService

    response = client.post(
        "/api/ai/chat/stream",
        json={"message": "Hello"},
    )

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert '"type":"error"' in response.text
    assert '"code":"INTERNAL_ERROR"' in response.text
    assert "database unavailable" not in response.text
