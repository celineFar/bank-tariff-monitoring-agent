from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from google.genai import errors

from app.domain.knowledge import (
    KnowledgeChunk,
    KnowledgeDocument,
    chunk_id,
    document_version_id,
)
from app.domain.models import ProductType
from app.services.embedding_providers import (
    EmbeddingError,
    GeminiEmbeddingProvider,
    GeminiQueryEmbeddingProvider,
)


def _document(
    *, checksum: str = "a" * 64, section: str = "Interest rate"
) -> KnowledgeDocument:
    return KnowledgeDocument(
        run_id=uuid4(),
        product=ProductType.CONSUMER_LOAN,
        document_key="consumer-loan-information-summary",
        document_name="Consumer Loan Information Summary",
        source_url="https://ameriabank.am/loans/consumer.pdf",
        final_url="https://www.ameriabank.am/loans/consumer.pdf",
        mime_type="application/pdf",
        content_sha256=checksum,
        retrieved_at=datetime(2026, 9, 16, 6, tzinfo=UTC),
        extraction_method="digital_pdf",
        quality_score=0.95,
        chunks=(
            KnowledgeChunk(
                ordinal=0,
                content="Nominal interest rate: 13.5%",
                page_start=3,
                page_end=3,
                section=section,
                language="en",
                extraction_method="digital_pdf",
                quality_score=0.98,
            ),
        ),
    )


def test_document_and_chunk_ids_are_stable_and_version_aware() -> None:
    first = _document()
    repeated = first.model_copy(update={"run_id": uuid4()})
    changed_version = _document(checksum="b" * 64)
    changed_location = _document(section="Fees")

    assert document_version_id(first) == document_version_id(repeated)
    assert chunk_id(first, first.chunks[0]) == chunk_id(repeated, repeated.chunks[0])
    assert document_version_id(first) != document_version_id(changed_version)
    assert chunk_id(first, first.chunks[0]) != chunk_id(
        changed_version, changed_version.chunks[0]
    )
    assert chunk_id(first, first.chunks[0]) != chunk_id(
        changed_location, changed_location.chunks[0]
    )


@pytest.mark.asyncio
async def test_gemini_embedding_adapter_uses_document_task_and_configured_model() -> (
    None
):
    class FakeModels:
        def __init__(self) -> None:
            self.arguments: dict[str, object] = {}

        async def embed_content(self, **arguments: object) -> object:
            self.arguments = arguments
            return SimpleNamespace(embeddings=[SimpleNamespace(values=[0.1, 0.2, 0.3])])

    models = FakeModels()
    client = SimpleNamespace(aio=SimpleNamespace(models=models))
    provider = GeminiEmbeddingProvider(
        client,
        "gemini-embedding-001",
        dimensions=3,
    )

    result = await provider.embed_documents(["tariff evidence"])

    assert result == [[0.1, 0.2, 0.3]]
    assert models.arguments["model"] == "gemini-embedding-001"
    assert models.arguments["contents"] == ["tariff evidence"]
    config = models.arguments["config"]
    assert config.task_type == "RETRIEVAL_DOCUMENT"
    assert config.output_dimensionality == 3


@pytest.mark.asyncio
async def test_gemini_query_embedding_adapter_uses_query_task() -> None:
    class FakeModels:
        def __init__(self) -> None:
            self.arguments: dict[str, object] = {}

        async def embed_content(self, **arguments: object) -> object:
            self.arguments = arguments
            return SimpleNamespace(embeddings=[SimpleNamespace(values=[0.3, 0.2, 0.1])])

    models = FakeModels()
    client = SimpleNamespace(aio=SimpleNamespace(models=models))
    provider = GeminiQueryEmbeddingProvider(
        client,
        "gemini-embedding-001",
        dimensions=3,
    )

    result = await provider.embed_query("mortgage interest rate")

    assert result == [0.3, 0.2, 0.1]
    assert models.arguments["contents"] == "mortgage interest rate"
    config = models.arguments["config"]
    assert config.task_type == "RETRIEVAL_QUERY"
    assert config.output_dimensionality == 3


@pytest.mark.asyncio
async def test_document_embedding_batches_large_chunk_sets() -> None:
    class FakeModels:
        def __init__(self) -> None:
            self.batch_sizes: list[int] = []

        async def embed_content(self, **arguments: object) -> object:
            contents = arguments["contents"]
            assert isinstance(contents, list)
            self.batch_sizes.append(len(contents))
            return SimpleNamespace(
                embeddings=[SimpleNamespace(values=[0.1, 0.2, 0.3]) for _ in contents]
            )

    models = FakeModels()
    provider = GeminiEmbeddingProvider(
        SimpleNamespace(aio=SimpleNamespace(models=models)),
        "gemini-embedding-001",
        dimensions=3,
    )

    result = await provider.embed_documents(["tariff evidence"] * 21)

    assert len(result) == 21
    assert models.batch_sizes == [20, 1]


@pytest.mark.asyncio
async def test_embedding_provider_reports_non_retryable_api_status(caplog) -> None:
    class FakeModels:
        async def embed_content(self, **arguments: object) -> object:
            raise errors.ClientError(
                400, {"error": {"status": "INVALID_ARGUMENT", "message": "bad input"}}
            )

    provider = GeminiEmbeddingProvider(
        SimpleNamespace(aio=SimpleNamespace(models=FakeModels())),
        "gemini-embedding-001",
        dimensions=3,
    )

    with pytest.raises(EmbeddingError, match="400 INVALID_ARGUMENT"):
        await provider.embed_documents(["tariff evidence"])

    assert "code=400 status=INVALID_ARGUMENT" in caplog.text
    assert "tariff evidence" not in caplog.text
