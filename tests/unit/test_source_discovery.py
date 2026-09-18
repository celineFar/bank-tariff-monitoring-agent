import pytest

from app.config import SourceDiscoverySettings
from app.domain.acquisition import SourceLocator, SourceType
from app.domain.models import ProductType
from app.domain.normalization import (
    NormalizedBlock,
    NormalizedBlockType,
    NormalizedDocument,
    NormalizedLink,
    NormalizedSourceBundle,
    NormalizedTable,
    NormalizedTableCell,
    NormalizedTableRow,
    SourceReference,
)
from app.domain.source_discovery import (
    Authority,
    DiscoveryBatch,
    DiscoveryBatchResponse,
    InformationRole,
    ModelSourceAssessment,
    ProductAssociation,
    Relevance,
    TemporalStatus,
)
from app.services.source_discovery import (
    InMemorySourceDiscoveryRepository,
    SourceDiscoveryService,
)

URL = "https://ameriabank.am/en/personal/loans/mortgage/primary"


def _ref(identifier: str, source_type: SourceType = SourceType.PAGE) -> SourceReference:
    return SourceReference(
        source_item_id=identifier,
        locator=SourceLocator(source_url=URL, source_type=source_type),
    )


def _block(
    identifier: str,
    block_type: NormalizedBlockType,
    text: str,
    *,
    heading_path: tuple[str, ...] = (),
) -> NormalizedBlock:
    return NormalizedBlock(
        id=identifier,
        type=block_type,
        raw_text=text,
        text=text,
        heading_path=heading_path,
        source_refs=(_ref(identifier),),
        extraction_method="browser",
    )


def _bundle(*, changed_text: str = "Nominal interest rate is 13%") -> NormalizedSourceBundle:
    table_ref = _ref("t1")
    table = NormalizedTable(
        id="t1",
        title="Tariffs",
        headers=("Item", "Terms"),
        rows=(
            NormalizedTableRow(
                id="t1:row:1",
                cells=(
                    NormalizedTableCell(
                        raw_text="Rate", text="Rate", source_refs=(table_ref,)
                    ),
                    NormalizedTableCell(
                        raw_text="13%", text="13%", source_refs=(table_ref,)
                    ),
                ),
            ),
        ),
        source_refs=(table_ref,),
    )
    page = NormalizedDocument(
        id="page:1",
        name="Primary mortgage",
        source_url=URL,
        source_type=SourceType.PAGE,
        mime_type="text/html",
        content_sha256="a" * 64,
        extraction_method="browser",
        blocks=(
            _block("nav-1", NormalizedBlockType.LIST, "Personal"),
            _block("nav-2", NormalizedBlockType.LIST, "Business"),
            _block("nav-3", NormalizedBlockType.LIST, "Investment Loans Cards Accounts"),
            _block(
                "terms",
                NormalizedBlockType.PARAGRAPH,
                changed_text,
                heading_path=("Primary mortgage", "Terms"),
            ),
        ),
        tables=(table,),
        links=(
            NormalizedLink(
                id="l1", url=URL, text="Terms", source_refs=(_ref("l1"),)
            ),
        ),
    )
    api = NormalizedDocument(
        id="api:1",
        name="https://ameriabank.am/api/product-data",
        source_url="https://ameriabank.am/api/product-data",
        source_type=SourceType.API,
        mime_type="application/json",
        content_sha256="b" * 64,
        extraction_method="json",
        blocks=(
            NormalizedBlock(
                id="api-block",
                type=NormalizedBlockType.KEY_VALUE,
                raw_text="60",
                text="60",
                fields={"path": "$['term']", "value": "60"},
                source_refs=(_ref("api-block", SourceType.API),),
                extraction_method="json",
            ),
        ),
    )
    template = NormalizedDocument(
        id="api:template",
        name="https://ameriabank.am/ContentThemes/HTML/index.html",
        source_url="https://ameriabank.am/ContentThemes/HTML/index.html",
        source_type=SourceType.API,
        mime_type="text/html",
        content_sha256="c" * 64,
        extraction_method="text",
        blocks=(
            NormalizedBlock(
                id="template-block",
                type=NormalizedBlockType.OTHER,
                raw_text="template",
                text="template",
                source_refs=(_ref("template-block", SourceType.API),),
                extraction_method="text",
            ),
        ),
    )
    return NormalizedSourceBundle(
        canonical_url=URL,
        acquisition_content_hash="d" * 64,
        documents=(page, api, template),
    )


class _Classifier:
    def __init__(self) -> None:
        self.batches: list[DiscoveryBatch] = []

    async def classify(self, batch: DiscoveryBatch) -> DiscoveryBatchResponse:
        self.batches.append(batch)
        return DiscoveryBatchResponse(
            items=tuple(
                ModelSourceAssessment(
                    source_id=item.source_id,
                    product_association=ProductAssociation.CURRENT_PRODUCT,
                    role=InformationRole.PRODUCT_TERMS,
                    relevance=Relevance.RELEVANT,
                    authority=Authority.OFFICIAL_PRODUCT_CONTENT,
                    temporal_status=TemporalStatus.CURRENT,
                    reason="Fixture classifier accepted the source.",
                )
                for item in batch.items
            )
        )


class _InvalidClassifier:
    async def classify(self, batch: DiscoveryBatch) -> DiscoveryBatchResponse:
        return DiscoveryBatchResponse(
            items=(
                ModelSourceAssessment(
                    source_id="invented-source-id",
                    product_association=ProductAssociation.UNKNOWN,
                    role=InformationRole.OTHER,
                    relevance=Relevance.IRRELEVANT,
                    authority=Authority.UNKNOWN,
                    temporal_status=TemporalStatus.UNKNOWN,
                    reason="Invalid fixture response.",
                ),
            )
        )


@pytest.mark.asyncio
async def test_discovery_prefilters_inherits_and_reuses_exact_assessments() -> None:
    repository = InMemorySourceDiscoveryRepository()
    classifier = _Classifier()
    service = SourceDiscoveryService(
        classifier,
        repository,
        SourceDiscoverySettings(
            max_items_per_batch=2,
            max_chars_per_item=500,
            max_chars_per_batch=1000,
        ),
        model_name="configured-model",
    )

    first = await service.discover(_bundle(), ProductType.MORTGAGE)
    first_call_count = len(classifier.batches)
    second = await service.discover(_bundle(), ProductType.MORTGAGE)

    assert first_call_count > 0
    assert len(classifier.batches) == first_call_count
    assert second.llm_batch_count == 0
    assert second.reused_assessment_count > 0
    assert any(
        item.inherited_from == "document::api:1" for item in first.assessments
    )
    assert all(
        item.role is not InformationRole.NAVIGATION
        for item in first.extraction_context.items
    )


@pytest.mark.asyncio
async def test_changed_content_gets_prior_hint_but_is_reassessed() -> None:
    repository = InMemorySourceDiscoveryRepository()
    classifier = _Classifier()
    service = SourceDiscoveryService(
        classifier,
        repository,
        SourceDiscoverySettings(),
        model_name="configured-model",
    )
    await service.discover(_bundle(), ProductType.MORTGAGE)

    plan = await service.plan(
        _bundle(changed_text="Nominal interest rate is 14%"), ProductType.MORTGAGE
    )

    changed = next(
        item
        for batch in plan.batches
        for item in batch.items
        if item.title == "Terms"
    )
    assert changed.prior_assessment is not None


@pytest.mark.asyncio
async def test_discovery_rejects_missing_or_invented_classifier_ids() -> None:
    service = SourceDiscoveryService(
        _InvalidClassifier(),
        InMemorySourceDiscoveryRepository(),
        SourceDiscoverySettings(),
        model_name="configured-model",
    )

    with pytest.raises(ValueError, match="response IDs"):
        await service.discover(_bundle(), ProductType.MORTGAGE)
