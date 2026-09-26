"""Regression tests for the source-discovery fix plan.

Each test asserts the *correct* behaviour of one item in
`fix-process/source_discovery/source-discovery-fix-plan.md`. A test marked
`xfail(strict=True)` documents a bug that is not fixed yet; the fix removes the
marker, and `strict` fails the suite if a fix makes a test pass without that.
"""

from __future__ import annotations

from datetime import date

import pytest

from app.config import SourceDiscoverySettings
from app.domain.acquisition import SourceLocator, SourceType
from app.domain.models import OfferingId, ProductType
from app.domain.normalization import (
    NormalizedBlock,
    NormalizedBlockType,
    NormalizedDocument,
    NormalizedSourceBundle,
    SourceReference,
)
from app.domain.pdf_extraction import (
    PdfAdmission,
    PdfAdmissionRelevance,
    PdfAdmissionRole,
    PdfTemporalStatus,
)
from app.domain.source_discovery import (
    Authority,
    DecisionSource,
    DiscoveryBatch,
    DiscoveryBatchResponse,
    DiscoveryScope,
    EffectivePeriod,
    InformationRole,
    ModelSourceAssessment,
    ProductAssociation,
    Relevance,
    TemporalStatus,
)
from app.services.discovery_prefilter import build_discovery_candidates
from app.services.source_discovery import (
    InMemorySourceDiscoveryRepository,
    SourceDiscoveryService,
)

URL = "https://ameriabank.am/en/personal/loans/mortgage/primary"
PDF_URL = "https://ameriabank.am/Content/PDF/web-info-eng.pdf"


def _offering(offering_id: OfferingId = OfferingId.MORTGAGE_PRIMARY):
    from app.domain.source_discovery import OfferingContext

    names = {
        OfferingId.MORTGAGE_PRIMARY: ("Primary Market Mortgage", URL),
        OfferingId.MORTGAGE_EXPRESS: (
            "Express Mortgage",
            "https://ameriabank.am/en/personal/loans/mortgage/express-loan",
        ),
    }
    display_name, seed_url = names[offering_id]
    return OfferingContext(
        offering_id=offering_id.value,
        product=ProductType.MORTGAGE,
        display_name=display_name,
        seed_url=seed_url,
        page_title=display_name,
    )


def _ref(identifier: str, source_type: SourceType = SourceType.PAGE) -> SourceReference:
    return SourceReference(
        source_item_id=identifier,
        locator=SourceLocator(
            source_url=PDF_URL if source_type is SourceType.PDF else URL,
            source_type=source_type,
        ),
    )


def _block(
    identifier: str,
    text: str,
    *,
    heading_path: tuple[str, ...] = (),
    block_type: NormalizedBlockType = NormalizedBlockType.PARAGRAPH,
    parent_id: str | None = None,
    **extra,
) -> NormalizedBlock:
    return NormalizedBlock(
        id=identifier,
        type=block_type,
        raw_text=text,
        text=text,
        heading_path=heading_path,
        parent_id=parent_id,
        source_refs=(_ref(identifier),),
        extraction_method="browser",
        **extra,
    )


def _page(*blocks: NormalizedBlock, content_hash: str = "a" * 64) -> NormalizedDocument:
    return NormalizedDocument(
        id="page:1",
        name="Primary Market Mortgage",
        source_url=URL,
        source_type=SourceType.PAGE,
        mime_type="text/html",
        content_sha256=content_hash,
        extraction_method="browser",
        blocks=blocks,
    )


def _bundle(*documents: NormalizedDocument) -> NormalizedSourceBundle:
    return NormalizedSourceBundle(
        canonical_url=URL,
        acquisition_content_hash="d" * 64,
        documents=documents,
    )


class _Classifier:
    """Accepts everything as current, or answers with the given overrides."""

    def __init__(self, **overrides) -> None:
        self.batches: list[DiscoveryBatch] = []
        self.overrides = overrides

    async def classify(self, batch: DiscoveryBatch) -> DiscoveryBatchResponse:
        self.batches.append(batch)
        values = {
            "product_association": ProductAssociation.CURRENT_PRODUCT,
            "role": InformationRole.PRODUCT_TERMS,
            "relevance": Relevance.RELEVANT,
            "authority": Authority.OFFICIAL_PRODUCT_CONTENT,
            "temporal_status": TemporalStatus.CURRENT,
            "reason": "Fixture classifier accepted the source.",
            **self.overrides,
        }
        return DiscoveryBatchResponse(
            items=tuple(
                ModelSourceAssessment(source_id=item.source_id, **values)
                for item in batch.items
            )
        )


def _service(classifier, repository=None, **settings) -> SourceDiscoveryService:
    return SourceDiscoveryService(
        classifier,
        repository or InMemorySourceDiscoveryRepository(),
        SourceDiscoverySettings(**settings),
        model_name="configured-model",
    )


def _rates_page(content_hash: str = "a" * 64) -> NormalizedDocument:
    return _page(
        _block("b1", "Primary Market Mortgage", block_type=NormalizedBlockType.HEADING),
        _block("b2", "Nominal interest rate 12.9%", heading_path=("Primary", "Rates")),
        content_hash=content_hash,
    )


# --- SD1 ---------------------------------------------------------------------------


@pytest.mark.xfail(strict=True, reason="SD1 not fixed yet")
@pytest.mark.asyncio
async def test_sd1_batch_carries_the_offering_identity() -> None:
    classifier = _Classifier()

    await _service(classifier).discover(_bundle(_rates_page()), _offering())

    batch = classifier.batches[0]
    assert batch.offering.display_name == "Primary Market Mortgage"
    assert str(batch.offering.seed_url) == URL


@pytest.mark.xfail(strict=True, reason="SD1 not fixed yet")
@pytest.mark.asyncio
async def test_sd1_the_cache_is_scoped_to_the_offering() -> None:
    classifier = _Classifier()
    service = _service(classifier, InMemorySourceDiscoveryRepository())
    bundle = _bundle(_rates_page())

    await service.discover(bundle, _offering(OfferingId.MORTGAGE_PRIMARY))
    calls = len(classifier.batches)
    await service.discover(bundle, _offering(OfferingId.MORTGAGE_EXPRESS))

    assert calls > 0
    assert len(classifier.batches) == 2 * calls


# --- SD4 ---------------------------------------------------------------------------


def _skipped_pdf(relevance: PdfAdmissionRelevance) -> NormalizedDocument:
    return NormalizedDocument(
        id="document:abc",
        name="Terms and Conditions",
        source_url=PDF_URL,
        source_type=SourceType.PDF,
        mime_type="application/pdf",
        content_sha256="e" * 64,
        extraction_method="pdf_skipped",
        quality_score=0,
        pdf_admission=PdfAdmission(
            relevance=relevance,
            role=PdfAdmissionRole.OTHER,
            temporal_status=PdfTemporalStatus.UNKNOWN,
            reason="fixture",
        ),
    )


@pytest.mark.xfail(strict=True, reason="SD4 not fixed yet")
@pytest.mark.asyncio
async def test_sd4_a_pdf_with_no_content_is_decided_by_rule() -> None:
    classifier = _Classifier()
    bundle = _bundle(_rates_page(), _skipped_pdf(PdfAdmissionRelevance.IRRELEVANT))

    result = await _service(classifier).discover(bundle, _offering())

    pdf = next(a for a in result.assessments if a.source_id == "document::document:abc")
    assert pdf.decision_source is DecisionSource.RULE
    assert pdf.relevance is Relevance.IRRELEVANT
    assert all(
        item.source_id != "document::document:abc"
        for batch in classifier.batches
        for item in batch.items
    )


# --- SD5 ---------------------------------------------------------------------------


@pytest.mark.xfail(strict=True, reason="SD5 not fixed yet")
@pytest.mark.asyncio
async def test_sd5_a_dated_campaign_expires_without_a_new_call() -> None:
    classifier = _Classifier(
        temporal_status=TemporalStatus.CURRENT,
        effective_periods=(
            EffectivePeriod(
                raw="valid until 31.10.2026",
                start=date(2026, 4, 15),
                end=date(2026, 10, 31),
            ),
        ),
    )
    service = _service(classifier)
    bundle = _bundle(_rates_page())

    before = await service.discover(bundle, _offering(), as_of=date(2026, 10, 1))
    calls = len(classifier.batches)
    after = await service.discover(bundle, _offering(), as_of=date(2026, 11, 1))

    def rates(result):
        return next(a for a in result.assessments if a.scope is DiscoveryScope.SECTION)

    assert rates(before).temporal_status is TemporalStatus.CURRENT
    assert len(classifier.batches) == calls
    assert rates(after).temporal_status is TemporalStatus.POSSIBLY_STALE


# --- SD6 ---------------------------------------------------------------------------


class _FlakyClassifier(_Classifier):
    """Answers with a wrong ID for any batch that contains `bad_text`."""

    def __init__(self, bad_text: str, *, failures: int) -> None:
        super().__init__()
        self.bad_text = bad_text
        self.failures = failures

    async def classify(self, batch: DiscoveryBatch) -> DiscoveryBatchResponse:
        if self.failures and any(self.bad_text in item.content for item in batch.items):
            self.failures -= 1
            self.batches.append(batch)
            return DiscoveryBatchResponse(
                items=(
                    ModelSourceAssessment(
                        source_id="invented",
                        product_association=ProductAssociation.UNKNOWN,
                        role=InformationRole.OTHER,
                        relevance=Relevance.IRRELEVANT,
                        authority=Authority.UNKNOWN,
                        temporal_status=TemporalStatus.UNKNOWN,
                        reason="invalid",
                    ),
                )
            )
        return await super().classify(batch)


def _many_sections_page() -> NormalizedDocument:
    return _page(
        *(
            _block(
                f"b{index}", f"Section {index} text", heading_path=(f"Heading {index}",)
            )
            for index in range(1, 7)
        )
    )


@pytest.mark.xfail(strict=True, reason="SD6 not fixed yet")
@pytest.mark.asyncio
async def test_sd6_an_invalid_batch_is_retried_and_split() -> None:
    classifier = _FlakyClassifier("Section 2 text", failures=2)
    service = _service(classifier, max_items_per_batch=3)

    result = await service.discover(_bundle(_many_sections_page()), _offering())

    assert (
        len([a for a in result.assessments if a.scope is DiscoveryScope.SECTION]) == 6
    )


@pytest.mark.xfail(strict=True, reason="SD6 not fixed yet")
@pytest.mark.asyncio
async def test_sd6_good_batches_are_saved_when_one_batch_fails() -> None:
    from app.services.source_discovery import DiscoveryResponseError

    repository = InMemorySourceDiscoveryRepository()
    classifier = _FlakyClassifier("Section 5 text", failures=100)
    service = _service(classifier, repository, max_items_per_batch=3)

    with pytest.raises(DiscoveryResponseError):
        await service.discover(_bundle(_many_sections_page()), _offering())

    assert len(repository._exact) >= 3


# --- SD9 ---------------------------------------------------------------------------


@pytest.mark.xfail(strict=True, reason="SD9 not fixed yet")
@pytest.mark.asyncio
async def test_sd9_site_chrome_is_decided_by_rule_and_kept_apart() -> None:
    classifier = _Classifier()
    page = _page(
        _block("b1", "Personal", block_type=NormalizedBlockType.LIST, site_chrome=True),
        _block("b2", "Primary Market Mortgage", block_type=NormalizedBlockType.HEADING),
        _block("b3", "Rates are 12.9%", heading_path=("Primary", "Construction loan")),
        _block(
            "b4",
            "Down payment from 10%\nNo appraisal fee",
            heading_path=("Primary",),
            block_type=NormalizedBlockType.LIST,
        ),
        _block(
            "b5",
            "Corporate Governance",
            heading_path=("Primary", "Construction loan"),
            block_type=NormalizedBlockType.LIST,
            site_chrome=True,
        ),
    )

    result = await _service(classifier).discover(_bundle(page), _offering())

    sent = [item for batch in classifier.batches for item in batch.items]
    assert not any("Corporate Governance" in item.content for item in sent)
    assert not any("Personal" == item.content for item in sent)
    assert any("Down payment from 10%" in item.content for item in sent)
    chrome = next(
        a for a in result.assessments if a.source_refs[0].source_item_id == "b5"
    )
    assert chrome.relevance is Relevance.IRRELEVANT


# --- SD10 --------------------------------------------------------------------------


def test_sd10_inserting_a_block_leaves_other_section_fingerprints_alone() -> None:
    before = _page(
        _block("b1", "Primary Market Mortgage", block_type=NormalizedBlockType.HEADING),
        _block("b2", "Nominal interest rate 12.9%", heading_path=("Primary", "Rates")),
        _block("b3", "Required documents: ID", heading_path=("Primary", "Documents")),
    )
    after = _page(
        _block("b1", "New banner", block_type=NormalizedBlockType.PARAGRAPH),
        _block("b2", "Primary Market Mortgage", block_type=NormalizedBlockType.HEADING),
        _block("b3", "Nominal interest rate 12.9%", heading_path=("Primary", "Rates")),
        _block("b4", "Required documents: ID", heading_path=("Primary", "Documents")),
    )

    def fingerprints(document: NormalizedDocument) -> dict[str, str]:
        return {
            candidate.title: candidate.content_fingerprint
            for candidate in build_discovery_candidates(_bundle(document))
            if candidate.scope is DiscoveryScope.SECTION and candidate.heading_path
        }

    assert fingerprints(before) == fingerprints(after)


# --- SD11 --------------------------------------------------------------------------


def test_sd11_same_heading_under_different_parents_is_structurally_distinct() -> None:
    page = _page(
        _block("p1", "Fees", heading_path=("Primary", "Terms")),
        _block("c1", "Fee is 0%", heading_path=("Primary", "Terms"), parent_id="p1"),
        _block("p2", "Documents", heading_path=("Primary", "Terms")),
        _block("c2", "Passport", heading_path=("Primary", "Terms"), parent_id="p2"),
    )

    children = [
        candidate
        for candidate in build_discovery_candidates(_bundle(page))
        if candidate.scope is DiscoveryScope.SECTION
        and any(
            member.endswith(("::c1", "::c2")) for member in candidate.member_source_ids
        )
    ]

    assert len(children) == 2
    assert children[0].structural_fingerprint != children[1].structural_fingerprint


# --- SD18 --------------------------------------------------------------------------


@pytest.mark.xfail(strict=True, reason="SD18 not fixed yet")
@pytest.mark.asyncio
async def test_sd18_undated_content_is_not_stale_without_evidence() -> None:
    classifier = _Classifier(temporal_status=TemporalStatus.POSSIBLY_STALE)

    result = await _service(classifier).discover(
        _bundle(_rates_page()), _offering(), as_of=date(2026, 9, 26)
    )

    section = next(a for a in result.assessments if a.scope is DiscoveryScope.SECTION)
    assert section.temporal_status is TemporalStatus.UNKNOWN


# --- Phase 1: candidates and rules, independent of the discovery signature --------


def _rule(candidate):
    from app.services.source_discovery import _rule_assessment

    return _rule_assessment(candidate)


def test_sd9_chrome_and_page_header_are_their_own_rule_decided_groups() -> None:
    from app.domain.source_discovery import CandidateLayout

    page = _page(
        _block("b1", "Personal", block_type=NormalizedBlockType.LIST, site_chrome=True),
        _block("b2", "EN • ՀԱՅ", block_type=NormalizedBlockType.LIST),
        _block("b3", "Primary Market Mortgage", block_type=NormalizedBlockType.HEADING),
        _block("b4", "Rates are 12.9%", heading_path=("Primary", "Construction loan")),
        _block(
            "b5",
            "Down payment from 10%\nNo appraisal fee",
            block_type=NormalizedBlockType.LIST,
        ),
        _block(
            "b6",
            "Corporate Governance",
            heading_path=("Primary", "Construction loan"),
            block_type=NormalizedBlockType.LIST,
            site_chrome=True,
        ),
    )

    sections = {
        candidate.layout: candidate
        for candidate in build_discovery_candidates(_bundle(page))
        if candidate.scope is DiscoveryScope.SECTION
        and candidate.layout is not CandidateLayout.CONTENT
    }
    content = [
        candidate
        for candidate in build_discovery_candidates(_bundle(page))
        if candidate.scope is DiscoveryScope.SECTION
        and candidate.layout is CandidateLayout.CONTENT
    ]

    chrome = sections[CandidateLayout.SITE_CHROME]
    header = sections[CandidateLayout.PAGE_HEADER]
    assert chrome.member_source_ids == ("page:1::block::b1", "page:1::block::b6")
    assert header.member_source_ids == ("page:1::block::b2",)
    assert _rule(chrome).relevance is Relevance.IRRELEVANT
    assert _rule(header).product_association is ProductAssociation.GLOBAL_NAVIGATION
    # The footer block no longer joins the section whose heading it inherited,
    # and an unheaded list below the first heading is its own item for Gemini.
    construction = next(c for c in content if c.title == "Construction loan")
    assert construction.member_source_ids == ("page:1::block::b4",)
    assert any(
        c.member_source_ids == ("page:1::block::b5",) and _rule(c) is None
        for c in content
    )


def test_sd4_pdfs_without_content_get_rule_decisions() -> None:
    historical = _skipped_pdf(PdfAdmissionRelevance.RELEVANT).model_copy(
        update={
            "pdf_admission": PdfAdmission(
                relevance=PdfAdmissionRelevance.RELEVANT,
                role=PdfAdmissionRole.PRODUCT_TERMS,
                temporal_status=PdfTemporalStatus.HISTORICAL,
                reason="fixture",
            )
        }
    )
    failed = _skipped_pdf(PdfAdmissionRelevance.AMBIGUOUS).model_copy(
        update={"extraction_method": "gemini_pdf_unavailable", "pdf_admission": None}
    )

    decisions = {
        name: _rule(build_discovery_candidates(_bundle(_rates_page(), document))[-1])
        for name, document in (
            ("irrelevant", _skipped_pdf(PdfAdmissionRelevance.IRRELEVANT)),
            ("ambiguous", _skipped_pdf(PdfAdmissionRelevance.AMBIGUOUS)),
            ("historical", historical),
            ("failed", failed),
        )
    }

    assert all(value is not None for value in decisions.values())
    assert all(value.relevance is Relevance.IRRELEVANT for value in decisions.values())
    assert decisions["historical"].temporal_status is TemporalStatus.POSSIBLY_STALE
    assert "gemini_pdf_unavailable" in decisions["failed"].reason


def test_sd12_pdf_context_keeps_each_page_tables_with_the_page() -> None:
    from app.domain.normalization import (
        NormalizedTable,
        NormalizedTableCell,
        NormalizedTableRow,
    )

    def pdf_ref(identifier: str, page: int) -> SourceReference:
        return SourceReference(
            source_item_id=identifier,
            locator=SourceLocator(
                source_url=PDF_URL, source_type=SourceType.PDF, pdf_page=page
            ),
        )

    long_text = "Clause text. " * 2000
    blocks = tuple(
        NormalizedBlock(
            id=f"d:page:{page}:block:0",
            type=NormalizedBlockType.PARAGRAPH,
            raw_text=long_text if page == 2 else f"Page {page} opening",
            text=long_text if page == 2 else f"Page {page} opening",
            source_refs=(pdf_ref(f"d:page:{page}:block:0", page),),
        )
        for page in (1, 2)
    )
    cell = NormalizedTableCell(
        raw_text="Nominal rate", text="Nominal rate", source_refs=(pdf_ref("c", 1),)
    )
    table = NormalizedTable(
        id="d:page:1:table:0",
        title="Tariffs",
        headers=("Item", "Value"),
        rows=(NormalizedTableRow(id="r", cells=(cell, cell)),),
        source_refs=(pdf_ref("d:page:1:table:0", 1),),
    )
    document = NormalizedDocument(
        id="document:pdf",
        name="Terms",
        source_url=PDF_URL,
        source_type=SourceType.PDF,
        mime_type="application/pdf",
        content_sha256="f" * 64,
        extraction_method="gemini",
        blocks=blocks,
        tables=(table,),
    )

    candidate = build_discovery_candidates(_bundle(_rates_page(), document))[-1]

    text = candidate.context_text
    assert text.index("TABLE: Tariffs") < text.index("Clause text.")
    assert "Rows: Nominal rate" in text
