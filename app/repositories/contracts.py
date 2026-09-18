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
from app.domain.source_discovery import SourceAssessment


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


class SourceDiscoveryRepository(Protocol):
    async def get_exact(
        self,
        *,
        product: ProductType,
        policy_version: str,
        prompt_version: str,
        model_name: str,
        content_fingerprints: Sequence[str],
    ) -> dict[str, SourceAssessment]: ...

    async def get_structural_priors(
        self,
        *,
        product: ProductType,
        policy_version: str,
        prompt_version: str,
        model_name: str,
        structural_fingerprints: Sequence[str],
    ) -> dict[str, SourceAssessment]: ...

    async def save(
        self,
        *,
        product: ProductType,
        policy_version: str,
        prompt_version: str,
        model_name: str,
        assessments: Sequence[SourceAssessment],
    ) -> None: ...
