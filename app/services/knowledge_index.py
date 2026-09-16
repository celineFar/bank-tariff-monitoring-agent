from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Protocol

from google import genai
from google.genai import types

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


class EmbeddingProvider(Protocol):
    @property
    def dimensions(self) -> int: ...

    async def embed_documents(
        self, contents: Sequence[str]
    ) -> Sequence[Sequence[float]]: ...


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
        response = await self._client.aio.models.embed_content(
            model=self._model_name,
            contents=list(contents),
            config=types.EmbedContentConfig(
                task_type="RETRIEVAL_DOCUMENT",
                output_dimensionality=self._dimensions,
            ),
        )
        embeddings = response.embeddings or []
        values = [embedding.values for embedding in embeddings]
        if any(value is None for value in values):
            raise EmbeddingError("Gemini returned an embedding without values")
        return [value for value in values if value is not None]


class KnowledgeIndexer:
    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        repository: KnowledgeStoreRepository,
    ) -> None:
        self._embedding_provider = embedding_provider
        self._repository = repository

    async def index(self, document: KnowledgeDocument) -> IndexWriteResult:
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

        embedded_document = EmbeddedKnowledgeDocument(
            **document.model_dump(exclude={"chunks"}),
            chunks=tuple(embedded_chunks),
        )
        return await self._repository.upsert_document(embedded_document)
