"""Vector-backed knowledge ingestion and retrieval."""

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.embeddings import GeminiEmbeddingGateway
from app.ai.schemas import KnowledgeChunkResponse, RetrievedChunk


class RagService:
    def __init__(
        self,
        embeddings: GeminiEmbeddingGateway,
        session: AsyncSession,
    ) -> None:
        self._embeddings = embeddings
        self._session = session

    async def add_chunk(
        self,
        source: str,
        title: str,
        content: str,
    ) -> KnowledgeChunkResponse:
        embedding = await self._embeddings.embed_document(content, title)
        result = await self._session.execute(
            text(
                """
                INSERT INTO knowledge_chunks (source, title, content, embedding)
                VALUES (:source, :title, :content, CAST(:embedding AS vector))
                RETURNING id
                """,
            ),
            {
                "source": source,
                "title": title,
                "content": content,
                "embedding": self._format_vector(embedding),
            },
        )
        chunk_id = result.scalar_one()
        await self._session.commit()
        return KnowledgeChunkResponse(
            id=UUID(str(chunk_id)),
            source=source,
            title=title,
            content=content,
        )

    async def search(self, query: str, limit: int) -> list[RetrievedChunk]:
        embedding = await self._embeddings.embed_query(query)
        result = await self._session.execute(
            text(
                """
                SELECT
                    id,
                    source,
                    title,
                    heading,
                    content,
                    1 - (embedding <=> CAST(:embedding AS vector)) AS similarity
                FROM knowledge_chunks
                ORDER BY embedding <=> CAST(:embedding AS vector)
                LIMIT :limit
                """,
            ),
            {
                "embedding": self._format_vector(embedding),
                "limit": limit,
            },
        )
        return [
            RetrievedChunk(
                id=UUID(str(row.id)),
                source=row.source,
                title=row.title,
                heading=row.heading,
                content=row.content,
                similarity=float(row.similarity),
            )
            for row in result
        ]

    @staticmethod
    def _format_vector(values: list[float]) -> str:
        return "[" + ",".join(str(value) for value in values) + "]"
