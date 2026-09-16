from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from app.domain.knowledge import (
    DocumentVersionSummary,
    EmbeddedKnowledgeDocument,
    IndexWriteResult,
)
from app.domain.models import ProductType, TariffSnapshot
from app.domain.retrieval import RetrievalCandidate


class SnapshotRepository(Protocol):
    async def get_latest(self, product: ProductType) -> TariffSnapshot | None: ...
    async def save(self, snapshot: TariffSnapshot) -> UUID: ...


class ReviewRepository(Protocol):
    async def create(self, run_id: UUID, reason: str, evidence: dict) -> UUID: ...
    async def decide(
        self, review_id: UUID, decision: str, reviewer: str, comment: str | None
    ) -> None: ...


class KnowledgeStoreRepository(Protocol):
    async def upsert_document(
        self, document: EmbeddedKnowledgeDocument
    ) -> IndexWriteResult: ...

    async def list_document_versions(
        self, bank: str, product: ProductType, document_key: str
    ) -> tuple[DocumentVersionSummary, ...]: ...


class HybridRetrievalRepository(Protocol):
    async def search_candidates(
        self,
        *,
        bank: str,
        product: ProductType,
        lexical_query: str,
        query_embedding: Sequence[float],
        limit: int,
    ) -> Sequence[RetrievalCandidate]: ...
