"""Shared authentication overrides for isolated API tests."""

from types import SimpleNamespace
from uuid import UUID

import pytest

from app.ai.router import get_chat_history
from app.core.auth import UserPrincipal, get_current_user
from app.core.rate_limit import enforce_ai_rate_limit
from app.main import app


class StubChatHistory:
    async def add_user_message(self, user_id, content, conversation_id):
        return SimpleNamespace(
            id=conversation_id
            or UUID("4a68e30e-586d-49d9-a932-9b8f4ee641b1"),
        )

    async def add_assistant_message(self, conversation, response):
        return None


@pytest.fixture(autouse=True)
def authenticated_test_user():
    app.dependency_overrides[get_current_user] = lambda: UserPrincipal(
        user_id="local-development-user",
    )
    app.dependency_overrides[enforce_ai_rate_limit] = lambda: None
    app.dependency_overrides[get_chat_history] = StubChatHistory
    yield
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(enforce_ai_rate_limit, None)
    app.dependency_overrides.pop(get_chat_history, None)
