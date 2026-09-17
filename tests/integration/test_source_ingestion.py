import hashlib
from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import UUID

import pytest

from app.domain.crawl import (
    CrawlStatus,
    DocumentResource,
    PageResource,
    PageSourceType,
    ProductCategory,
    ProductSourceInventory,
)
from app.domain.discovery import (
    CandidateRetrievalStatus,
    DiscoveryOrigin,
    OfficialSourceDiscoveryRun,
    ProductDiscoveryResult,
    SourceCandidate,
    SourceCandidateType,
)
from app.services.local_artifact_store import (
    ArtifactIntegrityError,
    LocalArtifactStore,
)
from app.services.source_ingestion import SourceIngestionService

NOW = datetime(2026, 9, 17, tzinfo=UTC)
RUN_ID = UUID("58b1906d-04f5-4514-9643-47a1cd0d21f0")
SECOND_RUN_ID = UUID("6a71ba5d-e76e-47a7-b287-8cb5609567c2")
PAGE_URL = "https://ameriabank.am/en/product"
DOCUMENT_URL = "https://ameriabank.am/files/terms.pdf"
PAGE_BYTES = b"<html><main>Product terms</main></html>"
DOCUMENT_BYTES = b"%PDF-1.7\nterms\n%%EOF"


def _sha(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _discovery() -> OfficialSourceDiscoveryRun:
    page = PageResource(
        source_type=PageSourceType.PRODUCT_PAGE,
        source_url=PAGE_URL,
        final_url=PAGE_URL,
        canonical_url=PAGE_URL,
        title="Product",
        language="en",
        size_bytes=len(PAGE_BYTES),
        sha256=_sha(PAGE_BYTES),
        retrieved_at=NOW,
        content=PAGE_BYTES,
    )
    document = DocumentResource(
        sha256=_sha(DOCUMENT_BYTES),
        original_urls=(DOCUMENT_URL,),
        urls=(DOCUMENT_URL,),
        final_url=DOCUMENT_URL,
        referrer_urls=(PAGE_URL,),
        content_type="application/pdf",
        size_bytes=len(DOCUMENT_BYTES),
        retrieved_at=NOW,
        language_hints=("en",),
        content=DOCUMENT_BYTES,
    )
    inventory = ProductSourceInventory(
        product_id="consumer.test",
        product_name="Test product",
        category=ProductCategory.CONSUMER,
        status=CrawlStatus.SUCCESS,
        product_page_en=page,
        documents=(document,),
    )
    candidates = (
        SourceCandidate(
            product_id="consumer.test",
            candidate_type=SourceCandidateType.PRODUCT_PAGE,
            origin=DiscoveryOrigin.REGISTRY,
            original_url=PAGE_URL,
            normalized_url=PAGE_URL,
            discovery_path=(PAGE_URL,),
            match_signals=("configured_product_seed",),
            retrieval_status=CandidateRetrievalStatus.RETRIEVED,
            status_code=200,
            content_sha256=page.sha256,
            mime_type="text/html",
        ),
        SourceCandidate(
            product_id="consumer.test",
            candidate_type=SourceCandidateType.DOCUMENT,
            origin=DiscoveryOrigin.PAGE_LINK,
            original_url=DOCUMENT_URL,
            normalized_url=DOCUMENT_URL,
            discovery_path=(PAGE_URL, DOCUMENT_URL),
            match_signals=("validated_page_document_link",),
            retrieval_status=CandidateRetrievalStatus.RETRIEVED,
            status_code=200,
            content_sha256=document.sha256,
            mime_type=document.content_type,
        ),
    )
    return OfficialSourceDiscoveryRun(
        started_at=NOW,
        completed_at=NOW,
        products=(
            ProductDiscoveryResult(
                product_id=inventory.product_id,
                product_name=inventory.product_name,
                category=inventory.category,
                candidates=candidates,
                inventory=inventory,
            ),
        ),
    )


@pytest.mark.asyncio
async def test_ingestion_persists_raw_bytes_manifest_and_reuses_artifacts(
    tmp_path,
) -> None:
    store = LocalArtifactStore(tmp_path / "artifacts")
    run_ids = iter((RUN_ID, SECOND_RUN_ID))
    service = SourceIngestionService(
        store,
        clock=lambda: NOW,
        id_factory=lambda: next(run_ids),
    )

    first = await service.ingest(_discovery())
    second = await service.ingest(_discovery())

    assert len(first.sources) == 2
    assert all(item.artifact.created for item in first.sources)
    assert all(not item.artifact.created for item in second.sources)
    assert await store.read(first.sources[0].artifact.storage_key) == PAGE_BYTES
    assert await store.read(first.sources[1].artifact.storage_key) == DOCUMENT_BYTES
    manifest = await store.read_manifest(first.manifest_key)
    assert manifest["run_id"] == str(RUN_ID)
    assert len(manifest["sources"]) == 2
    assert "content" not in manifest["sources"][0]


@pytest.mark.asyncio
async def test_ingestion_persists_metadata_when_repository_is_configured(
    tmp_path,
) -> None:
    repository = AsyncMock()
    service = SourceIngestionService(
        LocalArtifactStore(tmp_path / "artifacts"),
        metadata_repository=repository,
        clock=lambda: NOW,
        id_factory=lambda: RUN_ID,
    )

    result = await service.ingest(_discovery())

    repository.save_ingestion.assert_awaited_once_with(result)


@pytest.mark.asyncio
async def test_local_store_rejects_hash_mismatch_and_path_escape(tmp_path) -> None:
    store = LocalArtifactStore(tmp_path / "artifacts")
    with pytest.raises(ArtifactIntegrityError, match="SHA-256"):
        await store.put(
            content=PAGE_BYTES,
            sha256="0" * 64,
            mime_type="text/html",
        )
    with pytest.raises(ValueError, match="escaped"):
        await store.read("../outside")
