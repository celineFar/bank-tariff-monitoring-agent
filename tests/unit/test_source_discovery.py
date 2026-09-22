import pytest
from google.genai.errors import ClientError, ServerError

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
from app.services.discovery_classifier import AdkSourceDiscoveryClassifier
from app.services.model_pricing import model_sequence
from app.services.source_discovery import (
    FallbackSourceDiscoveryService,
    InMemorySourceDiscoveryRepository,
    SourceDiscoveryService,
)
from scripts.demonstrate_source_discovery import (
    SourceDiscoveryRunFailed,
    _render_classification_results,
    main,
)

URL = "https://ameriabank.am/en/personal/loans/mortgage/primary"


def test_model_sequence_preserves_order_and_removes_duplicates() -> None:
    assert model_sequence(
        "gemini-3.7-flash",
        ("gemini-3.8-flash", "gemini-3.7-flash", "gemini-3.6-flash"),
    ) == ("gemini-3.7-flash", "gemini-3.8-flash", "gemini-3.6-flash")


def test_cli_prints_concise_handled_api_failure_without_traceback(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path,
) -> None:
    error = ServerError(
        503,
        {"error": {"status": "UNAVAILABLE", "message": "high demand"}},
    )

    async def fail(*args, **kwargs):
        raise SourceDiscoveryRunFailed(tmp_path, error)

    monkeypatch.setattr("scripts.demonstrate_source_discovery.demonstrate", fail)
    monkeypatch.setattr(
        "sys.argv",
        [
            "demonstrate_source_discovery.py",
            "case_008",
            "--product",
            "mortgage",
            "--execute-llm",
        ],
    )

    assert main() == 1
    captured = capsys.readouterr()
    assert "HTTP 503 / UNAVAILABLE" in captured.err
    assert "failure.json" in captured.err
    assert "Traceback" not in captured.err


def _ref(identifier: str, source_type: SourceType | None = None) -> SourceReference:
    return SourceReference(
        source_item_id=identifier,
        locator=SourceLocator(
            source_url=URL, source_type=source_type or SourceType.PAGE
        ),
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


def _bundle(
    *, changed_text: str = "Nominal interest rate is 13%"
) -> NormalizedSourceBundle:
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
            _block(
                "nav-3", NormalizedBlockType.LIST, "Investment Loans Cards Accounts"
            ),
            _block(
                "terms",
                NormalizedBlockType.PARAGRAPH,
                changed_text,
                heading_path=("Primary mortgage", "Terms"),
            ),
        ),
        tables=(table,),
        links=(
            NormalizedLink(id="l1", url=URL, text="Terms", source_refs=(_ref("l1"),)),
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
    assert any(item.inherited_from == "document::api:1" for item in first.assessments)
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
        item for batch in plan.batches for item in batch.items if item.title == "Terms"
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


@pytest.mark.asyncio
async def test_classification_markdown_groups_direct_decisions() -> None:
    repository = InMemorySourceDiscoveryRepository()
    service = SourceDiscoveryService(
        _Classifier(),
        repository,
        SourceDiscoverySettings(),
        model_name="configured-model",
    )
    bundle = _bundle()
    plan = await service.plan(bundle, ProductType.MORTGAGE)
    result = await service.discover(bundle, ProductType.MORTGAGE)

    markdown = _render_classification_results(plan, result)

    assert "## Relevant" in markdown
    assert "## Possibly relevant (0)" in markdown
    assert "## Irrelevant" in markdown
    assert "## Deterministic and reused decisions" in markdown
    assert "Decision source: `llm`" in markdown
    assert "Child assessments represented through inheritance" in markdown


@pytest.mark.asyncio
async def test_classifier_retries_transient_server_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    planning = SourceDiscoveryService(
        None,
        InMemorySourceDiscoveryRepository(),
        SourceDiscoverySettings(),
        model_name="configured-model",
    )
    batch = (await planning.plan(_bundle(), ProductType.MORTGAGE)).batches[0]
    classifier = AdkSourceDiscoveryClassifier(
        "configured-model",
        api_key="fixture-key",
        max_attempts=3,
        backoff_base_seconds=0,
        max_backoff_seconds=0,
    )
    expected = DiscoveryBatchResponse(
        items=tuple(
            ModelSourceAssessment(
                source_id=item.source_id,
                product_association=ProductAssociation.CURRENT_PRODUCT,
                role=InformationRole.PRODUCT_TERMS,
                relevance=Relevance.RELEVANT,
                authority=Authority.OFFICIAL_PRODUCT_CONTENT,
                temporal_status=TemporalStatus.CURRENT,
                reason="Recovered after transient errors.",
            )
            for item in batch.items
        )
    )
    calls = 0

    async def classify_once(_: DiscoveryBatch) -> DiscoveryBatchResponse:
        nonlocal calls
        calls += 1
        if calls < 3:
            raise ServerError(
                503,
                {"error": {"status": "UNAVAILABLE", "message": "high demand"}},
            )
        return expected

    monkeypatch.setattr(classifier, "_classify_once", classify_once)

    assert await classifier.classify(batch) == expected
    assert calls == 3
    assert classifier.usage.application_retries == 2
    assert classifier.usage.request_attempts == 3


class _RetiredModelClassifier:
    """Answers the way a model id the provider has retired does: a permanent 404."""

    def __init__(self) -> None:
        self.calls = 0

    async def classify(self, batch: DiscoveryBatch) -> DiscoveryBatchResponse:
        self.calls += 1
        raise ClientError(
            404,
            {
                "error": {
                    "status": "NOT_FOUND",
                    "message": "This model is no longer available to new users.",
                }
            },
        )


def _service(classifier, repository, model_name: str) -> SourceDiscoveryService:
    return SourceDiscoveryService(
        classifier,
        repository,
        SourceDiscoverySettings(),
        model_name=model_name,
    )


@pytest.mark.asyncio
async def test_discovery_falls_back_when_the_primary_model_is_retired() -> None:
    repository = InMemorySourceDiscoveryRepository()
    retired = _RetiredModelClassifier()
    successor = _Classifier()
    service = FallbackSourceDiscoveryService(
        (
            _service(retired, repository, "retired-model"),
            _service(successor, repository, "successor-model"),
        )
    )

    result = await service.discover(_bundle(), ProductType.MORTGAGE)

    assert retired.calls == 1
    assert successor.batches
    # The assessments were produced by the successor, so that is the model the
    # cache namespace and the stored rows must name.
    assert result.model_name == "successor-model"


@pytest.mark.asyncio
async def test_discovery_raises_once_every_configured_model_fails() -> None:
    repository = InMemorySourceDiscoveryRepository()
    service = FallbackSourceDiscoveryService(
        (
            _service(_RetiredModelClassifier(), repository, "retired-model"),
            _service(_RetiredModelClassifier(), repository, "also-retired"),
        )
    )

    with pytest.raises(ClientError):
        await service.discover(_bundle(), ProductType.MORTGAGE)


@pytest.mark.asyncio
async def test_discovery_does_not_fall_back_after_a_deterministic_failure() -> None:
    """A malformed response is the same on the next model, so do not pay twice."""
    repository = InMemorySourceDiscoveryRepository()
    successor = _Classifier()
    service = FallbackSourceDiscoveryService(
        (
            _service(_InvalidClassifier(), repository, "first-model"),
            _service(successor, repository, "successor-model"),
        )
    )

    with pytest.raises(ValueError):
        await service.discover(_bundle(), ProductType.MORTGAGE)
    assert not successor.batches
