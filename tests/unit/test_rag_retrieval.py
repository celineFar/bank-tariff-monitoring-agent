from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest

from app.config.models import RagSettings
from app.domain.models import ProductType
from app.domain.retrieval import (
    RetrievalCandidate,
    RetrievalRequest,
    RetrievalStatus,
    TariffField,
)
from app.repositories.rag_retrieval import HYBRID_SEARCH_SQL
from app.services.rag_retrieval import RagRetriever

_DEFAULT_DOCUMENT_ID = UUID("11111111-1111-1111-1111-111111111111")


class FakeQueryEmbeddingProvider:
    dimensions = 3

    def __init__(self) -> None:
        self.query: str | None = None

    async def embed_query(self, content: str) -> tuple[float, ...]:
        self.query = content
        return (0.1, 0.2, 0.3)


class FakeRetrievalRepository:
    def __init__(self, candidates: tuple[RetrievalCandidate, ...]) -> None:
        self.candidates = candidates
        self.arguments: dict[str, object] = {}

    async def search_candidates(
        self, **arguments: object
    ) -> tuple[RetrievalCandidate, ...]:
        self.arguments = arguments
        return self.candidates


def _candidate(
    suffix: str,
    *,
    content: str = "Nominal interest rate: 13.5%",
    lexical_score: float = 0.9,
    vector_score: float = 0.9,
    lexical_rank: int | None = 1,
    vector_rank: int | None = 1,
    document_id: UUID = _DEFAULT_DOCUMENT_ID,
) -> RetrievalCandidate:
    return RetrievalCandidate(
        chunk_id=suffix * 64,
        content=content,
        lexical_score=lexical_score,
        vector_score=vector_score,
        lexical_rank=lexical_rank,
        vector_rank=vector_rank,
        document_id=document_id,
        document_checksum="f" * 64,
        document_name="Official tariff summary",
        source_url="https://ameriabank.am/loans/tariff.pdf",
        final_url="https://www.ameriabank.am/loans/tariff.pdf",
        page_start=3,
        page_end=3,
        section="Rates",
        language="en",
        retrieved_at=datetime(2026, 9, 16, 6, tzinfo=UTC),
        extraction_method="digital_pdf",
        quality_score=0.98,
    )


def _request(
    *,
    query: str = "interest rate",
    product: ProductType = ProductType.CONSUMER_LOAN,
    fields: tuple[TariffField, ...] = (TariffField.NOMINAL_RATE,),
) -> RetrievalRequest:
    return RetrievalRequest(
        query=query,
        bank="Ameria",
        product=product,
        fields=fields,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("query", "product", "field", "expected_term"),
    [
        (
            "What is the consumer loan amount?",
            ProductType.CONSUMER_LOAN,
            TariffField.AMOUNT,
            "loan amount",
        ),
        (
            "Որքա՞ն է հիփոթեքային վարկի ժամկետը",
            ProductType.MORTGAGE,
            TariffField.TERM,
            "ժամկետ",
        ),
    ],
)
async def test_field_queries_support_languages_products_and_mandatory_filters(
    query: str,
    product: ProductType,
    field: TariffField,
    expected_term: str,
) -> None:
    repository = FakeRetrievalRepository((_candidate("a"),))
    provider = FakeQueryEmbeddingProvider()

    result = await RagRetriever(provider, repository, RagSettings()).retrieve(
        _request(query=query, product=product, fields=(field,))
    )

    assert result.status is RetrievalStatus.FOUND
    assert repository.arguments["bank"] == "Ameria"
    assert repository.arguments["product"] is product
    assert expected_term in str(repository.arguments["lexical_query"])
    assert field.value.replace("_", " ") in (provider.query or "")


@pytest.mark.asyncio
async def test_irrelevant_candidates_return_explicit_insufficient_evidence() -> None:
    repository = FakeRetrievalRepository(
        (
            _candidate(
                "a",
                lexical_score=0.0,
                vector_score=0.05,
                lexical_rank=None,
                vector_rank=1,
            ),
        )
    )

    result = await RagRetriever(
        FakeQueryEmbeddingProvider(), repository, RagSettings()
    ).retrieve(_request())

    assert result.status is RetrievalStatus.INSUFFICIENT_EVIDENCE
    assert result.hits == ()
    assert result.reason is not None
    assert "minimum relevance score" in result.reason


@pytest.mark.asyncio
async def test_ordering_is_deterministic_and_provenance_is_complete() -> None:
    repository = FakeRetrievalRepository(
        (
            _candidate(
                "b",
                document_id=UUID("22222222-2222-2222-2222-222222222222"),
            ),
            _candidate("a"),
        )
    )

    result = await RagRetriever(
        FakeQueryEmbeddingProvider(), repository, RagSettings()
    ).retrieve(_request())

    assert [hit.chunk_id for hit in result.hits] == ["a" * 64, "b" * 64]
    hit = result.hits[0]
    assert hit.document_id == UUID("11111111-1111-1111-1111-111111111111")
    assert hit.document_checksum == "f" * 64
    assert hit.page_start == 3
    assert hit.section == "Rates"
    assert str(hit.final_url) == "https://www.ameriabank.am/loans/tariff.pdf"
    assert hit.rank_explanation.lexical_rank == 1
    assert hit.rank_explanation.vector_rank == 1
    assert hit.rank_explanation.formula


@pytest.mark.asyncio
async def test_overlapping_chunks_from_same_document_are_deduplicated() -> None:
    first = _candidate(
        "a",
        content="loan amount up to 20 million AMD term up to 60 months",
    )
    overlapping = _candidate(
        "b",
        content="loan amount up to 20 million AMD term up to 60 months for customers",
        lexical_rank=2,
        vector_rank=2,
    )
    distinct = _candidate(
        "c",
        content="application fee is 5,000 AMD",
        lexical_rank=3,
        vector_rank=3,
    )
    repository = FakeRetrievalRepository((overlapping, distinct, first))

    result = await RagRetriever(
        FakeQueryEmbeddingProvider(), repository, RagSettings(retrieval_top_k=3)
    ).retrieve(_request())

    assert [hit.chunk_id for hit in result.hits] == ["a" * 64, "c" * 64]


@pytest.mark.asyncio
async def test_top_k_limits_the_smallest_relevant_set() -> None:
    repository = FakeRetrievalRepository(
        (
            _candidate("a", content="amount 1"),
            _candidate("b", content="term 2"),
            _candidate("c", content="fee 3"),
        )
    )

    result = await RagRetriever(
        FakeQueryEmbeddingProvider(), repository, RagSettings(retrieval_top_k=2)
    ).retrieve(_request())

    assert len(result.hits) == 2
    assert repository.arguments["limit"] == 20


def test_hybrid_sql_enforces_filters_and_uses_both_indexes() -> None:
    normalized = " ".join(HYBRID_SEARCH_SQL.lower().split())

    assert "d.bank = :bank" in normalized
    assert "d.product = :product" in normalized
    assert "d.is_active is true" in normalized
    assert "c.is_active is true" in normalized
    assert "c.search_vector @@ i.text_query" in normalized
    assert "c.embedding <=> i.query_embedding" in normalized
