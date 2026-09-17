from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from app.domain.discovery import (
    IngestionRunSummary,
    IngestionWriteResult,
    PersistedArtifact,
    PersistedSourceOrigin,
    SourceIngestionResult,
)
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


class SourceIngestionRepository(Protocol):
    async def save_ingestion(
        self, ingestion: SourceIngestionResult
    ) -> IngestionWriteResult: ...

    async def get_run(self, run_id: UUID) -> IngestionRunSummary | None: ...

    async def get_artifact(self, content_sha256: str) -> PersistedArtifact | None: ...

    async def list_product_sources(
        self,
        product_id: str,
        *,
        ingestion_run_id: UUID | None = None,
    ) -> tuple[PersistedSourceOrigin, ...]: ...
