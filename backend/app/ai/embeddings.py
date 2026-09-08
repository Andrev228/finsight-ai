"""Google Gemini embedding gateway."""

import httpx

from app.ai.exceptions import LLMConfigurationError, LLMProviderError
from app.core.config import GeminiConfig

EMBEDDING_DIMENSIONS = 768


class GeminiEmbeddingGateway:
    def __init__(self, config: GeminiConfig) -> None:
        self._api_key = config.api_key.get_secret_value()
        self._base_url = config.base_url.rstrip("/")
        self._model = config.embedding_model

    async def embed_document(self, content: str, title: str) -> list[float]:
        return await self._embed(content, "RETRIEVAL_DOCUMENT", title)

    async def embed_documents(
        self,
        documents: list[tuple[str, str]],
    ) -> list[list[float]]:
        if not documents:
            return []
        if not self._api_key:
            raise LLMConfigurationError("Gemini API key is not configured")

        model = f"models/{self._model}"
        requests = [
            {
                "model": model,
                "content": {"parts": [{"text": content}]},
                "taskType": "RETRIEVAL_DOCUMENT",
                "title": title,
                "outputDimensionality": EMBEDDING_DIMENSIONS,
            }
            for title, content in documents
        ]
        body = await self._post(
            f"{self._base_url}/models/{self._model}:batchEmbedContents",
            {"requests": requests},
        )
        embeddings = body.get("embeddings")
        if not isinstance(embeddings, list) or len(embeddings) != len(documents):
            raise LLMProviderError("GEMINI_INVALID_EMBEDDING_RESPONSE")
        return [self._extract_values(embedding) for embedding in embeddings]

    async def embed_query(self, query: str) -> list[float]:
        return await self._embed(query, "RETRIEVAL_QUERY")

    async def _embed(
        self,
        content: str,
        task_type: str,
        title: str | None = None,
    ) -> list[float]:
        if not self._api_key:
            raise LLMConfigurationError("Gemini API key is not configured")

        payload: dict[str, object] = {
            "content": {"parts": [{"text": content}]},
            "taskType": task_type,
            "outputDimensionality": EMBEDDING_DIMENSIONS,
        }
        if title is not None:
            payload["title"] = title

        body = await self._post(
            f"{self._base_url}/models/{self._model}:embedContent",
            payload,
        )
        embedding = body.get("embedding")
        return self._extract_values(embedding)

    async def _post(
        self,
        url: str,
        payload: dict[str, object],
    ) -> dict[str, object]:
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    url,
                    headers={
                        "x-goog-api-key": self._api_key,
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
        except httpx.HTTPError as exc:
            raise LLMProviderError("GEMINI_EMBEDDING_UNAVAILABLE") from exc

        try:
            body = response.json()
        except ValueError as exc:
            raise LLMProviderError("GEMINI_INVALID_EMBEDDING_RESPONSE") from exc

        if response.is_error:
            error = body.get("error", {})
            raise LLMProviderError(
                str(
                    error.get("status")
                    or error.get("code")
                    or "GEMINI_EMBEDDING_FAILED",
                ),
                status_code=response.status_code,
            )
        return body

    @staticmethod
    def _extract_values(embedding: object) -> list[float]:
        if not isinstance(embedding, dict):
            raise LLMProviderError("GEMINI_INVALID_EMBEDDING_RESPONSE")
        values = embedding.get("values")
        if not isinstance(values, list) or len(values) != EMBEDDING_DIMENSIONS:
            raise LLMProviderError("GEMINI_INVALID_EMBEDDING_RESPONSE")
        return [float(value) for value in values]
