from __future__ import annotations

import asyncio
import logging
import math
from collections.abc import Sequence
from typing import Protocol

from google import genai
from google.genai import errors, types

from app.domain.knowledge import (
    EMBEDDING_DIMENSIONS,
    EmbeddedKnowledgeChunk,
    EmbeddedKnowledgeDocument,
    IndexWriteResult,
    KnowledgeDocument,
)
from app.repositories.contracts import KnowledgeStoreRepository


class EmbeddingError(RuntimeError):
    pass


logger = logging.getLogger(__name__)
_EMBED_BATCH_SIZE = 20
_RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})


class EmbeddingProvider(Protocol):
    @property
    def dimensions(self) -> int: ...

    async def embed_documents(
        self, contents: Sequence[str]
    ) -> Sequence[Sequence[float]]: ...


class QueryEmbeddingProvider(Protocol):
    @property
    def dimensions(self) -> int: ...

    async def embed_query(self, content: str) -> Sequence[float]: ...


class GeminiEmbeddingProvider:
    """Gemini embedding adapter used by deterministic ingestion, never as a tool."""

    def __init__(
        self,
        client: genai.Client,
        model_name: str,
        *,
        dimensions: int = EMBEDDING_DIMENSIONS,
    ) -> None:
        self._client = client
        self._model_name = model_name
        self._dimensions = dimensions

    @property
    def dimensions(self) -> int:
        return self._dimensions

    async def embed_documents(
        self, contents: Sequence[str]
    ) -> Sequence[Sequence[float]]:
        if not contents:
            return ()
        values: list[Sequence[float]] = []
        for offset in range(0, len(contents), _EMBED_BATCH_SIZE):
            batch = list(contents[offset : offset + _EMBED_BATCH_SIZE])
            for attempt in range(3):
                try:
                    response = await self._client.aio.models.embed_content(
                        model=self._model_name,
                        contents=batch,
                        config=types.EmbedContentConfig(
                            task_type="RETRIEVAL_DOCUMENT",
                            output_dimensionality=self._dimensions,
                        ),
                    )
                    break
                except errors.APIError as exc:
                    logger.warning(
                        "embedding provider rejected batch code=%s status=%s "
                        "batch_size=%s attempt=%s",
                        exc.code,
                        exc.status,
                        len(batch),
                        attempt + 1,
                    )
                    if exc.code not in _RETRYABLE_STATUS_CODES or attempt == 2:
                        raise EmbeddingError(
                            f"embedding provider error {exc.code} {exc.status}"
                        ) from exc
                    await asyncio.sleep(10 * (attempt + 1))
            embeddings = response.embeddings or []
            if len(embeddings) != len(batch) or any(
                embedding.values is None for embedding in embeddings
            ):
                raise EmbeddingError("Gemini returned incomplete embeddings")
            values.extend(embedding.values for embedding in embeddings)
        return values


class GeminiQueryEmbeddingProvider:
    """Gemini query adapter paired with RETRIEVAL_DOCUMENT ingestion vectors."""

    def __init__(
        self,
        client: genai.Client,
        model_name: str,
        *,
        dimensions: int = EMBEDDING_DIMENSIONS,
    ) -> None:
        self._client = client
        self._model_name = model_name
        self._dimensions = dimensions

    @property
    def dimensions(self) -> int:
        return self._dimensions

    async def embed_query(self, content: str) -> Sequence[float]:
        response = await self._client.aio.models.embed_content(
            model=self._model_name,
            contents=content,
            config=types.EmbedContentConfig(
                task_type="RETRIEVAL_QUERY",
                output_dimensionality=self._dimensions,
            ),
        )
        embeddings = response.embeddings or []
        if len(embeddings) != 1 or embeddings[0].values is None:
            raise EmbeddingError("Gemini did not return exactly one query embedding")
        return embeddings[0].values


class KnowledgeIndexer:
    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        repository: KnowledgeStoreRepository,
    ) -> None:
        self._embedding_provider = embedding_provider
        self._repository = repository

    async def index(self, document: KnowledgeDocument) -> IndexWriteResult:
        embedded_document = await self.embed(document)
        return await self._repository.upsert_document(embedded_document)

    async def embed(self, document: KnowledgeDocument) -> EmbeddedKnowledgeDocument:
        embeddings = await self._embedding_provider.embed_documents(
            [chunk.content for chunk in document.chunks]
        )

        if len(embeddings) != len(document.chunks):
            raise EmbeddingError(
                "embedding count does not match the number of document chunks"
            )

        embedded_chunks: list[EmbeddedKnowledgeChunk] = []
        for chunk, embedding in zip(document.chunks, embeddings, strict=True):
            values = tuple(float(value) for value in embedding)
            if len(values) != self._embedding_provider.dimensions:
                raise EmbeddingError(
                    "embedding dimensions do not match the configured index schema"
                )
            if not all(math.isfinite(value) for value in values):
                raise EmbeddingError("embedding contains a non-finite value")
            embedded_chunks.append(
                EmbeddedKnowledgeChunk(
                    **chunk.model_dump(),
                    embedding=values,
                )
            )

        return EmbeddedKnowledgeDocument(
            **document.model_dump(exclude={"chunks"}),
            chunks=tuple(embedded_chunks),
        )
