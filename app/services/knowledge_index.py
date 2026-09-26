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
    KnowledgeDocument,
)
from app.domain.models import OfferingId
from app.repositories.contracts import ChunkEmbeddingRepository
from app.repositories.embedding_cache import PostgresEmbeddingCache
from app.services.model_call_usage import (
    PostgresModelCallUsageRepository,
    observe_model_call,
    record_model_cache_hit,
)


class EmbeddingError(RuntimeError):
    pass


class EmbeddingQuotaExhausted(EmbeddingError):
    """The provider refused the batch for quota, not because anything is wrong.

    Kept distinct from every other embedding failure because only this one is
    safe to defer: the request was well-formed and the model is healthy, so the
    same call will succeed once the quota window moves. A malformed response or
    a dimension mismatch is a defect and must still fail the offering.
    """


logger = logging.getLogger(__name__)
_EMBED_BATCH_SIZE = 20
DOCUMENT_EMBEDDING_STAGE = "indexing.embedding"
# Vectors filled after publication: an approval's documents and quota-deferred
# runs (IX5, IX7).
SWEEP_EMBEDDING_STAGE = "indexing.embedding_sweep"
_QUOTA_STATUS_CODE = 429
_TRANSIENT_STATUS_CODES = frozenset({500, 502, 503, 504})


def _retry_delay(base_seconds: float, attempt: int) -> float:
    """Linear backoff, matching the schedule this loop has always used."""
    return base_seconds * (attempt + 1)


class EmbeddingProvider(Protocol):
    @property
    def dimensions(self) -> int: ...

    async def embed_documents(
        self, contents: Sequence[str], *, stage: str = DOCUMENT_EMBEDDING_STAGE
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
        max_attempts: int = 3,
        backoff_base_seconds: float = 10.0,
        quota_max_attempts: int = 4,
        quota_backoff_base_seconds: float = 30.0,
    ) -> None:
        self._usage_repository = usage_repository
        self._client = client
        self._model_name = model_name
        self._dimensions = dimensions
        self._max_attempts = max_attempts
        self._backoff_base_seconds = backoff_base_seconds
        self._quota_max_attempts = quota_max_attempts
        self._quota_backoff_base_seconds = quota_backoff_base_seconds

    @property
    def dimensions(self) -> int:
        return self._dimensions

    @property
    def model_name(self) -> str:
        return self._model_name

    async def embed_documents(
        self, contents: Sequence[str], *, stage: str = DOCUMENT_EMBEDDING_STAGE
    ) -> Sequence[Sequence[float]]:
        if not contents:
            return ()
        values: list[Sequence[float]] = []
        for offset in range(0, len(contents), _EMBED_BATCH_SIZE):
            batch = list(contents[offset : offset + _EMBED_BATCH_SIZE])
            call_id = str(uuid4())
            attempt = 0
            while True:
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
                        stage=stage,
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
                    quota = exc.code == _QUOTA_STATUS_CODE
                    if quota:
                        attempts = self._quota_max_attempts
                        base = self._quota_backoff_base_seconds
                    elif exc.code in _TRANSIENT_STATUS_CODES:
                        attempts = self._max_attempts
                        base = self._backoff_base_seconds
                    else:
                        attempts = 1
                        base = 0.0
                    if attempt + 1 >= attempts:
                        detail = f"embedding provider error {exc.code} {exc.status}"
                        if quota:
                            raise EmbeddingQuotaExhausted(detail) from exc
                        raise EmbeddingError(detail) from exc
                    await asyncio.sleep(_retry_delay(base, attempt))
                    attempt += 1
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
        embeddings: ChunkEmbeddingRepository | None = None,
        embedding_cache: PostgresEmbeddingCache | None = None,
        usage_repository: PostgresModelCallUsageRepository | None = None,
    ) -> None:
        self._usage_repository = usage_repository
        self._embedding_provider = embedding_provider
        # Only `embed_missing` writes, and only vectors: documents are
        # published by the offering publication repository (IX15).
        self._embeddings = embeddings
        self._embedding_cache = embedding_cache

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

    async def embed_missing(
        self, *, offering_id: OfferingId | None = None, limit: int = 200
    ) -> int:
        """Fill vectors of active chunks stored without one; returns chunks filled.

        Chunks under review are never active, so they are never embedded here
        (IX5). Works in provider batches and stops at a quota refusal, keeping
        what was filled; the next call resumes. Other failures raise.
        """
        if self._embeddings is None:
            raise RuntimeError("embed_missing needs a chunk embedding repository")
        pending = await self._embeddings.list_missing(
            offering_id=offering_id, limit=limit
        )
        filled = 0
        for offset in range(0, len(pending), _EMBED_BATCH_SIZE):
            batch = pending[offset : offset + _EMBED_BATCH_SIZE]
            try:
                vectors = await self._vectors(
                    [content for _, content in batch], stage=SWEEP_EMBEDDING_STAGE
                )
            except EmbeddingQuotaExhausted:
                logger.warning(
                    "embedding sweep stopped for lack of provider quota after "
                    "%s of %s chunks",
                    filled,
                    len(pending),
                )
                break
            filled += await self._embeddings.fill(
                {
                    identifier: vector
                    for (identifier, _), vector in zip(batch, vectors, strict=True)
                }
            )
        return filled

    async def _embed(self, document: KnowledgeDocument) -> EmbeddedKnowledgeDocument:
        embeddings = await self._vectors(
            [chunk.content for chunk in document.chunks],
            stage=DOCUMENT_EMBEDDING_STAGE,
        )
        if len(embeddings) != len(document.chunks):
            raise EmbeddingError(
                "embedding count does not match the number of document chunks"
            )
        return EmbeddedKnowledgeDocument(
            **document.model_dump(exclude={"chunks"}),
            chunks=tuple(
                EmbeddedKnowledgeChunk(**chunk.model_dump(), embedding=embedding)
                for chunk, embedding in zip(document.chunks, embeddings, strict=True)
            ),
        )

    async def _vectors(
        self, contents: Sequence[str], *, stage: str
    ) -> list[tuple[float, ...]]:
        """One validated vector per content, from the cache first."""
        contents = list(contents)
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
                stage=stage,
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
                await self._generate(list(missing.values()), stage=stage)
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
            embeddings = list(await self._generate(contents, stage=stage))

        if len(embeddings) != len(contents):
            raise EmbeddingError("embedding count does not match the contents")
        vectors: list[tuple[float, ...]] = []
        for embedding in embeddings:
            values = tuple(float(value) for value in embedding)
            if len(values) != self._embedding_provider.dimensions:
                raise EmbeddingError(
                    "embedding dimensions do not match the configured index schema"
                )
            if not all(math.isfinite(value) for value in values):
                raise EmbeddingError("embedding contains a non-finite value")
            vectors.append(values)
        return vectors

    async def _generate(
        self, contents: Sequence[str], *, stage: str
    ) -> Sequence[Sequence[float]]:
        # The document path keeps the provider's default stage, so providers
        # (and test fakes) without a `stage` argument still work there.
        if stage == DOCUMENT_EMBEDDING_STAGE:
            return await self._embedding_provider.embed_documents(contents)
        return await self._embedding_provider.embed_documents(contents, stage=stage)
