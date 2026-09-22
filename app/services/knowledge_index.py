from __future__ import annotations

import asyncio
import hashlib
import logging
import math
from collections.abc import Sequence
from typing import Protocol
from uuid import uuid4

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
from app.repositories.embedding_cache import PostgresEmbeddingCache
from app.services.model_call_usage import (
    PostgresModelCallUsageRepository,
    observe_model_call,
    record_model_cache_hit,
)


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
        usage_repository: PostgresModelCallUsageRepository | None = None,
    ) -> None:
        self._usage_repository = usage_repository
        self._client = client
        self._model_name = model_name
        self._dimensions = dimensions

    @property
    def dimensions(self) -> int:
        return self._dimensions

    @property
    def model_name(self) -> str:
        return self._model_name

    async def embed_documents(
        self, contents: Sequence[str]
    ) -> Sequence[Sequence[float]]:
        if not contents:
            return ()
        values: list[Sequence[float]] = []
        for offset in range(0, len(contents), _EMBED_BATCH_SIZE):
            batch = list(contents[offset : offset + _EMBED_BATCH_SIZE])
            call_id = str(uuid4())
            for attempt in range(3):
                try:
                    response = await observe_model_call(
                        lambda batch=batch: self._client.aio.models.embed_content(
                            model=self._model_name,
                            contents=batch,
                            config=types.EmbedContentConfig(
                                task_type="RETRIEVAL_DOCUMENT",
                                output_dimensionality=self._dimensions,
                            ),
                        ),
                        repository=self._usage_repository,
                        stage="indexing.embedding",
                        operation="embed_content",
                        model_id=self._model_name,
                        call_id=call_id,
                        attempt=attempt + 1,
                        input_count=len(batch),
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
        usage_repository: PostgresModelCallUsageRepository | None = None,
    ) -> None:
        self._usage_repository = usage_repository
        self._client = client
        self._model_name = model_name
        self._dimensions = dimensions

    @property
    def dimensions(self) -> int:
        return self._dimensions

    @property
    def model_name(self) -> str:
        return self._model_name

    async def embed_query(self, content: str) -> Sequence[float]:
        response = await observe_model_call(
            lambda: self._client.aio.models.embed_content(
                model=self._model_name,
                contents=content,
                config=types.EmbedContentConfig(
                    task_type="RETRIEVAL_QUERY",
                    output_dimensionality=self._dimensions,
                ),
            ),
            repository=self._usage_repository,
            stage="rag.query_embedding",
            operation="embed_content",
            model_id=self._model_name,
            input_count=1,
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
        embedding_cache: PostgresEmbeddingCache | None = None,
        usage_repository: PostgresModelCallUsageRepository | None = None,
    ) -> None:
        self._usage_repository = usage_repository
        self._embedding_provider = embedding_provider
        self._repository = repository
        self._embedding_cache = embedding_cache

    async def index(self, document: KnowledgeDocument) -> IndexWriteResult:
        embedded_document = await self.embed(document)
        return await self._repository.upsert_document(embedded_document)

    async def embed(self, document: KnowledgeDocument) -> EmbeddedKnowledgeDocument:
        try:
            return await self._embed(document)
        except EmbeddingError:
            raise
        except Exception as exc:
            # A provider error escaping here is not one the batch retry loop saw, so
            # name the document and keep the traceback: the stage failure code alone
            # ("indexing.embedding_failed") does not say which call rejected us.
            logger.warning(
                "embedding failed outside the batch retry loop for document_key=%s "
                "chunks=%s model=%s error=%s: %s",
                document.document_key,
                len(document.chunks),
                getattr(self._embedding_provider, "model_name", "unknown"),
                type(exc).__name__,
                exc,
                exc_info=True,
            )
            raise

    async def _embed(self, document: KnowledgeDocument) -> EmbeddedKnowledgeDocument:
        contents = [chunk.content for chunk in document.chunks]
        if self._embedding_cache is not None:
            model_name = getattr(self._embedding_provider, "model_name", None)
            if not model_name:
                raise EmbeddingError("cache requires a named embedding model")
            hashes = [
                hashlib.sha256(value.encode("utf-8")).hexdigest() for value in contents
            ]
            cached = await self._embedding_cache.get_many(
                model_name,
                self._embedding_provider.dimensions,
                "RETRIEVAL_DOCUMENT",
                hashes,
            )
            await record_model_cache_hit(
                self._usage_repository,
                stage="indexing.embedding",
                operation="embed_content",
                model_id=model_name,
                input_count=sum(checksum in cached for checksum in hashes),
            )
            missing = {
                checksum: content
                for checksum, content in zip(hashes, contents, strict=True)
                if checksum not in cached
            }
            generated = (
                await self._embedding_provider.embed_documents(list(missing.values()))
                if missing
                else ()
            )
            if len(generated) != len(missing):
                raise EmbeddingError("embedding count does not match cache misses")
            fresh = dict(zip(missing, generated, strict=True))
            for embedding in fresh.values():
                if len(embedding) != self._embedding_provider.dimensions or not all(
                    math.isfinite(float(value)) for value in embedding
                ):
                    raise EmbeddingError("embedding cache received an invalid vector")
            await self._embedding_cache.put_many(
                model_name,
                self._embedding_provider.dimensions,
                "RETRIEVAL_DOCUMENT",
                fresh,
            )
            embeddings = [
                cached.get(checksum) or fresh[checksum] for checksum in hashes
            ]
        else:
            embeddings = await self._embedding_provider.embed_documents(contents)

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
