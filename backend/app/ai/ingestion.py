"""Allowlisted web-document ingestion for RAG."""

import hashlib
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from html.parser import HTMLParser

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.embeddings import GeminiEmbeddingGateway
from app.ai.schemas import IngestionResult
from app.ai.rag import RagService

MAX_DOCUMENT_BYTES = 2_000_000
MAX_CHUNK_CHARS = 1800
CHUNK_OVERLAP_CHARS = 200


@dataclass(frozen=True)
class SourceDefinition:
    id: str
    url: str


@dataclass(frozen=True)
class TextBlock:
    tag: str
    text: str


@dataclass(frozen=True)
class DocumentChunk:
    heading: str
    content: str


SOURCES = {
    "cfpb-emergency-fund": SourceDefinition(
        id="cfpb-emergency-fund",
        url=(
            "https://www.consumerfinance.gov/"
            "an-essential-guide-to-building-an-emergency-fund/"
        ),
    ),
}


class MainContentParser(HTMLParser):
    CONTENT_TAGS = {"h1", "h2", "h3", "p", "li"}
    SKIP_TAGS = {"script", "style", "nav", "footer", "form"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.blocks: list[TextBlock] = []
        self._main_depth = 0
        self._skip_depth = 0
        self._active_tag: str | None = None
        self._active_depth = 0
        self._fragments: list[str] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        if tag == "main":
            self._main_depth += 1
            return
        if not self._main_depth:
            return
        if tag in self.SKIP_TAGS:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        if self._active_tag is not None:
            self._active_depth += 1
        elif tag in self.CONTENT_TAGS:
            self._active_tag = tag
            self._active_depth = 1
            self._fragments = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "main":
            self._main_depth = max(0, self._main_depth - 1)
            return
        if not self._main_depth:
            return
        if tag in self.SKIP_TAGS and self._skip_depth:
            self._skip_depth -= 1
            return
        if self._skip_depth or self._active_tag is None:
            return
        self._active_depth -= 1
        if self._active_depth == 0:
            content = re.sub(r"\s+", " ", " ".join(self._fragments)).strip()
            if content:
                self.blocks.append(TextBlock(self._active_tag, content))
            self._active_tag = None
            self._fragments = []

    def handle_data(self, data: str) -> None:
        if self._main_depth and not self._skip_depth and self._active_tag:
            self._fragments.append(data)


class KnowledgeIngestionService:
    def __init__(
        self,
        embeddings: GeminiEmbeddingGateway,
        session: AsyncSession,
    ) -> None:
        self._embeddings = embeddings
        self._session = session

    async def ingest(self, source_id: str) -> IngestionResult:
        source = SOURCES[source_id]
        title, chunks, document_hash = await self._fetch_and_chunk(source)
        existing_count = await self._existing_chunk_count(
            source.url,
            document_hash,
        )
        if existing_count is not None:
            return IngestionResult(
                source_id=source.id,
                title=title,
                chunks=existing_count,
                changed=False,
            )

        embeddings = await self._embeddings.embed_documents(
            [(f"{title}: {chunk.heading}", chunk.content) for chunk in chunks],
        )
        await self._session.execute(
            text(
                """
                DELETE FROM knowledge_chunks
                WHERE source = :source AND document_hash IS NOT NULL
                """,
            ),
            {"source": source.url},
        )
        fetched_at = datetime.now(UTC)
        for index, (chunk, embedding) in enumerate(zip(chunks, embeddings, strict=True)):
            await self._session.execute(
                text(
                    """
                    INSERT INTO knowledge_chunks (
                        source,
                        title,
                        content,
                        embedding,
                        document_hash,
                        chunk_index,
                        heading,
                        fetched_at
                    )
                    VALUES (
                        :source,
                        :title,
                        :content,
                        CAST(:embedding AS vector),
                        :document_hash,
                        :chunk_index,
                        :heading,
                        :fetched_at
                    )
                    """,
                ),
                {
                    "source": source.url,
                    "title": title,
                    "content": chunk.content,
                    "embedding": RagService._format_vector(embedding),
                    "document_hash": document_hash,
                    "chunk_index": index,
                    "heading": chunk.heading,
                    "fetched_at": fetched_at,
                },
            )
        await self._session.commit()
        return IngestionResult(
            source_id=source.id,
            title=title,
            chunks=len(chunks),
            changed=True,
        )

    async def _existing_chunk_count(
        self,
        source: str,
        document_hash: str,
    ) -> int | None:
        result = await self._session.execute(
            text(
                """
                SELECT count(*)
                FROM knowledge_chunks
                WHERE source = :source AND document_hash = :document_hash
                """,
            ),
            {"source": source, "document_hash": document_hash},
        )
        count = int(result.scalar_one())
        return count if count else None

    async def _fetch_and_chunk(
        self,
        source: SourceDefinition,
    ) -> tuple[str, list[DocumentChunk], str]:
        async with httpx.AsyncClient(
            timeout=30,
            follow_redirects=True,
            headers={"User-Agent": "curl/8.7.1 finsight-ai/0.0.1"},
        ) as client:
            response = await client.get(source.url)
        response.raise_for_status()
        content_type = response.headers.get("content-type", "")
        if "text/html" not in content_type:
            raise ValueError(f"Unsupported content type: {content_type}")
        if len(response.content) > MAX_DOCUMENT_BYTES:
            raise ValueError("Source document is too large")

        parser = MainContentParser()
        parser.feed(response.text)
        title = next(
            (block.text for block in parser.blocks if block.tag == "h1"),
            source.id,
        )
        chunks = self._build_chunks(parser.blocks)
        if not chunks:
            raise ValueError("Source document did not contain usable text")
        canonical_text = "\n\n".join(chunk.content for chunk in chunks)
        document_hash = hashlib.sha256(canonical_text.encode()).hexdigest()
        return title, chunks, document_hash

    @classmethod
    def _build_chunks(cls, blocks: list[TextBlock]) -> list[DocumentChunk]:
        sections: list[tuple[str, list[str]]] = []
        heading = "Overview"
        paragraphs: list[str] = []
        started = False

        for block in blocks:
            if block.tag == "h1":
                started = True
                continue
            if not started:
                continue
            if block.tag in {"h2", "h3"}:
                if paragraphs:
                    sections.append((heading, paragraphs))
                heading = block.text
                paragraphs = []
            else:
                paragraphs.append(block.text)
        if paragraphs:
            sections.append((heading, paragraphs))

        chunks: list[DocumentChunk] = []
        for section_heading, section_paragraphs in sections:
            section_text = "\n\n".join(section_paragraphs)
            for content in cls._split_text(section_text):
                chunks.append(DocumentChunk(section_heading, content))
        return chunks

    @staticmethod
    def _split_text(content: str) -> list[str]:
        if len(content) <= MAX_CHUNK_CHARS:
            return [content]

        chunks: list[str] = []
        start = 0
        while start < len(content):
            end = min(start + MAX_CHUNK_CHARS, len(content))
            if end < len(content):
                paragraph_end = content.rfind("\n\n", start, end)
                sentence_end = content.rfind(". ", start, end)
                boundary = max(paragraph_end, sentence_end)
                if boundary > start + MAX_CHUNK_CHARS // 2:
                    end = boundary + 1
            chunks.append(content[start:end].strip())
            if end == len(content):
                break
            start = max(end - CHUNK_OVERLAP_CHARS, start + 1)
        return chunks
