"""User-scoped persistent chat history."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.schemas import (
    ChatResponse,
    ConversationDetail,
    ConversationMessage,
    ConversationSummary,
)
from app.core.encryption import AppCipher
from app.db.models import ChatMessage, Conversation


class ConversationNotFoundError(LookupError):
    pass


class ChatHistoryService:
    def __init__(self, session: AsyncSession, cipher: AppCipher) -> None:
        self._session = session
        self._cipher = cipher

    async def list_conversations(
        self,
        user_id: str,
    ) -> list[ConversationSummary]:
        conversations = (
            await self._session.scalars(
                select(Conversation)
                .where(Conversation.user_id == user_id)
                .order_by(Conversation.updated_at.desc()),
            )
        ).all()
        return [self._summary(conversation) for conversation in conversations]

    async def get_conversation(
        self,
        conversation_id: UUID,
        user_id: str,
    ) -> ConversationDetail:
        conversation = await self._owned_conversation(conversation_id, user_id)
        messages = (
            await self._session.scalars(
                select(ChatMessage)
                .where(ChatMessage.conversation_id == conversation.id)
                .order_by(ChatMessage.created_at, ChatMessage.id),
            )
        ).all()
        return ConversationDetail(
            **self._summary(conversation).model_dump(),
            messages=[
                ConversationMessage(
                    id=message.id,
                    role=message.role,
                    content=self._cipher.decrypt(message.content_encrypted),
                    metadata=message.message_metadata,
                    created_at=message.created_at,
                )
                for message in messages
            ],
        )

    async def add_user_message(
        self,
        user_id: str,
        content: str,
        conversation_id: UUID | None,
    ) -> Conversation:
        if conversation_id is None:
            conversation = Conversation(
                user_id=user_id,
                title_encrypted=self._cipher.encrypt(self._title(content)),
            )
            self._session.add(conversation)
            await self._session.flush()
        else:
            conversation = await self._owned_conversation(
                conversation_id,
                user_id,
            )
        self._session.add(
            ChatMessage(
                conversation_id=conversation.id,
                role="user",
                content_encrypted=self._cipher.encrypt(content),
                message_metadata={},
            ),
        )
        await self._session.commit()
        return conversation

    async def add_assistant_message(
        self,
        conversation: Conversation,
        response: ChatResponse,
    ) -> None:
        self._session.add(
            ChatMessage(
                conversation_id=conversation.id,
                role="assistant",
                content_encrypted=self._cipher.encrypt(response.answer),
                message_metadata={
                    "tools_used": response.tools_used,
                    "sources": [
                        source.model_dump(mode="json")
                        for source in response.sources
                    ],
                    "unsupported": response.unsupported,
                },
            ),
        )
        conversation.updated_at = datetime.now(UTC)
        await self._session.commit()

    async def _owned_conversation(
        self,
        conversation_id: UUID,
        user_id: str,
    ) -> Conversation:
        conversation = await self._session.scalar(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
            ),
        )
        if conversation is None:
            raise ConversationNotFoundError(str(conversation_id))
        return conversation

    def _summary(self, conversation: Conversation) -> ConversationSummary:
        return ConversationSummary(
            id=conversation.id,
            title=self._cipher.decrypt(conversation.title_encrypted),
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
        )

    @staticmethod
    def _title(content: str) -> str:
        normalized = " ".join(content.split())
        return normalized[:117] + "..." if len(normalized) > 120 else normalized
