"""Populate accepted retrieval-unit vectors lazily with content-addressed reuse."""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Protocol

from app.domain.models import OfferingId, ProductType
from app.repositories.embedding_cache import PostgresEmbeddingCache
from app.repositories.structured_tariff_query import UnitEmbeddingInput
from app.services.knowledge_index import (
    GeminiEmbeddingProvider,
    GeminiQueryEmbeddingProvider,
)
from app.services.model_call_usage import (
    PostgresModelCallUsageRepository,
    record_model_cache_hit,
)


class UnitEmbeddingRepository(Protocol):
    async def missing(
        self,
        *,
        bank: str,
        product: ProductType,
        offering_ids: Sequence[OfferingId],
        model_id: str,
        limit: int,
    ) -> tuple[UnitEmbeddingInput, ...]: ...

    async def save(
        self,
        *,
        model_id: str,
        vectors: Sequence[tuple[UnitEmbeddingInput, Sequence[float]]],
    ) -> int: ...


class StructuredUnitEmbeddingService:
    def __init__(
        self,
        repository: UnitEmbeddingRepository,
        cache: PostgresEmbeddingCache,
        document_provider: GeminiEmbeddingProvider,
        query_provider: GeminiQueryEmbeddingProvider,
        usage_repository: PostgresModelCallUsageRepository | None = None,
    ) -> None:
        if document_provider.model_name != query_provider.model_name:
            raise ValueError("document and query embedding models must match")
        if document_provider.dimensions != query_provider.dimensions:
            raise ValueError("document and query embedding dimensions must match")
        self._repository = repository
        self._cache = cache
        self._document_provider = document_provider
        self._query_provider = query_provider
        self._usage_repository = usage_repository
        self.model_name = document_provider.model_name

    async def ensure(
        self,
        *,
        bank: str,
        product: ProductType,
        offering_ids: Sequence[OfferingId],
        limit: int = 100,
    ) -> int:
        missing = await self._repository.missing(
            bank=bank,
            product=product,
            offering_ids=offering_ids,
            model_id=self.model_name,
            limit=limit,
        )
        if not missing:
            return 0
        hashes = [unit.content_sha256 for unit in missing]
        cached = await self._cache.get_many(
            self.model_name,
            self._document_provider.dimensions,
            "RETRIEVAL_DOCUMENT",
            hashes,
        )
        await record_model_cache_hit(
            self._usage_repository,
            stage="retrieval_unit.embedding",
            operation="embed_content",
            model_id=self.model_name,
            input_count=sum(checksum in cached for checksum in hashes),
        )
        unique_missing = {
            unit.content_sha256: unit.content
            for unit in missing
            if unit.content_sha256 not in cached
        }
        generated = (
            await self._document_provider.embed_documents(list(unique_missing.values()))
            if unique_missing
            else ()
        )
        if len(generated) != len(unique_missing):
            raise ValueError("incomplete retrieval-unit embeddings")
        fresh = dict(zip(unique_missing, generated, strict=True))
        for vector in fresh.values():
            if len(vector) != self._document_provider.dimensions or not all(
                math.isfinite(value) for value in vector
            ):
                raise ValueError("invalid retrieval-unit embedding")
        await self._cache.put_many(
            self.model_name,
            self._document_provider.dimensions,
            "RETRIEVAL_DOCUMENT",
            fresh,
        )
        return await self._repository.save(
            model_id=self.model_name,
            vectors=tuple(
                (unit, cached.get(unit.content_sha256) or fresh[unit.content_sha256])
                for unit in missing
            ),
        )

    async def embed_query(self, question: str) -> Sequence[float]:
        return await self._query_provider.embed_query(question)
