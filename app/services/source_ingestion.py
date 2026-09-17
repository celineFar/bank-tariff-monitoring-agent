from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.domain.crawl import PageResource, PageSourceType
from app.domain.discovery import (
    IngestedProduct,
    IngestedSource,
    OfficialSourceDiscoveryRun,
    SourceCandidateType,
    SourceIngestionResult,
)
from app.repositories.contracts import SourceIngestionRepository
from app.services.contracts import ArtifactStore

Clock = Callable[[], datetime]
IdFactory = Callable[[], UUID]


class SourceIngestionService:
    """Persist validated discovery bytes and a provenance-only run manifest."""

    def __init__(
        self,
        artifact_store: ArtifactStore,
        *,
        metadata_repository: SourceIngestionRepository | None = None,
        clock: Clock | None = None,
        id_factory: IdFactory = uuid4,
    ) -> None:
        self._artifact_store = artifact_store
        self._metadata_repository = metadata_repository
        self._clock = clock or (lambda: datetime.now(UTC))
        self._id_factory = id_factory

    async def ingest(
        self,
        discovery: OfficialSourceDiscoveryRun,
        *,
        monitoring_run_id: UUID | None = None,
    ) -> SourceIngestionResult:
        run_id = self._id_factory()
        started_at = self._clock()
        sources: list[IngestedSource] = []

        for product in discovery.products:
            inventory = product.inventory
            pages = (
                *((inventory.product_page_en,) if inventory.product_page_en else ()),
                *((inventory.product_page_hy,) if inventory.product_page_hy else ()),
                *inventory.supporting_pages,
            )
            for page in pages:
                sources.append(await self._store_page(product.product_id, page))
            for document in inventory.documents:
                artifact = await self._artifact_store.put(
                    content=document.content,
                    sha256=document.sha256,
                    mime_type=document.content_type,
                )
                for source_url in document.urls:
                    sources.append(
                        IngestedSource(
                            product_id=product.product_id,
                            candidate_type=SourceCandidateType.DOCUMENT,
                            source_url=source_url,
                            final_url=document.final_url,
                            language=(
                                document.language_hints[0]
                                if len(document.language_hints) == 1
                                else None
                            ),
                            referrer_urls=document.referrer_urls,
                            retrieved_at=document.retrieved_at,
                            artifact=artifact,
                        )
                    )

        completed_at = self._clock()
        candidates = tuple(
            candidate
            for product in discovery.products
            for candidate in product.candidates
        )
        warnings = (
            *discovery.warnings,
            *(
                issue
                for product in discovery.products
                for issue in (*product.warnings, *product.errors)
            ),
        )
        products = tuple(
            IngestedProduct(
                product_id=product.product_id,
                product_name=product.product_name,
                category=product.category,
                crawl_status=product.inventory.status.value,
                candidate_count=len(product.candidates),
                stored_source_count=sum(
                    source.product_id == product.product_id for source in sources
                ),
                warnings=product.warnings,
                errors=product.errors,
            )
            for product in discovery.products
        )
        manifest_key = f"manifests/{run_id}.json"
        result = SourceIngestionResult(
            run_id=run_id,
            monitoring_run_id=monitoring_run_id,
            started_at=started_at,
            completed_at=completed_at,
            manifest_key=manifest_key,
            products=products,
            sources=tuple(sources),
            candidates=candidates,
            warnings=warnings,
        )
        written_key = await self._artifact_store.write_manifest(
            str(run_id),
            result.model_dump(mode="json"),
        )
        if written_key != manifest_key:
            result = result.model_copy(update={"manifest_key": written_key})
        if self._metadata_repository is not None:
            await self._metadata_repository.save_ingestion(result)
        return result

    async def _store_page(self, product_id: str, page: PageResource) -> IngestedSource:
        artifact = await self._artifact_store.put(
            content=page.content,
            sha256=page.sha256,
            mime_type="text/html",
        )
        return IngestedSource(
            product_id=product_id,
            candidate_type=(
                SourceCandidateType.PRODUCT_PAGE
                if page.source_type is PageSourceType.PRODUCT_PAGE
                else SourceCandidateType.SUPPORTING_PAGE
            ),
            source_url=page.source_url,
            final_url=page.final_url,
            language=page.language,
            referrer_urls=((page.referrer_url,) if page.referrer_url else ()),
            retrieved_at=page.retrieved_at,
            artifact=artifact,
        )
