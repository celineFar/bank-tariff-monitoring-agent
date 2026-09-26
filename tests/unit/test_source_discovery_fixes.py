"""Regression tests for the source-discovery fix plan.

Each test asserts the *correct* behaviour of one item in
`fix-process/source_discovery/source-discovery-fix-plan.md`. A test marked
`xfail(strict=True)` documents a bug that is not fixed yet; the fix removes the
marker, and `strict` fails the suite if a fix makes a test pass without that.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

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


def _offering(offering_id: OfferingId | None = None):
    from app.domain.source_discovery import OfferingContext

    offering_id = offering_id or OfferingId.MORTGAGE_PRIMARY

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


def _ref(identifier: str, source_type: SourceType | None = None) -> SourceReference:
    source_type = source_type or SourceType.PAGE
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
    block_type: NormalizedBlockType | None = None,
    parent_id: str | None = None,
    **extra,
) -> NormalizedBlock:
    return NormalizedBlock(
        id=identifier,
        type=block_type or NormalizedBlockType.PARAGRAPH,
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


def _item_text(item) -> str:
    """What the classifier sees of one prompt item: its content and members."""
    return "\n".join((item.content, *(member.text for member in item.members)))


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


@pytest.mark.asyncio
async def test_sd1_batch_carries_the_offering_identity() -> None:
    classifier = _Classifier()

    await _service(classifier).discover(_bundle(_rates_page()), _offering())

    batch = classifier.batches[0]
    assert batch.offering.display_name == "Primary Market Mortgage"
    assert str(batch.offering.seed_url) == URL


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
        if self.failures and any(
            self.bad_text in _item_text(item) for item in batch.items
        ):
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


@pytest.mark.asyncio
async def test_sd6_an_invalid_batch_is_retried_and_split() -> None:
    classifier = _FlakyClassifier("Section 2 text", failures=2)
    service = _service(classifier, max_items_per_batch=3)

    result = await service.discover(_bundle(_many_sections_page()), _offering())

    assert (
        len([a for a in result.assessments if a.scope is DiscoveryScope.SECTION]) == 6
    )


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
    assert not any("Corporate Governance" in _item_text(item) for item in sent)
    assert not any("Personal" == _item_text(item) for item in sent)
    assert any("Down payment from 10%" in _item_text(item) for item in sent)
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


# --- Phase 3: members are classified, not silently inherited (SD3) ------------------


def test_sd3_every_member_of_a_long_section_reaches_a_prompt_item() -> None:
    paragraphs = [f"Clause {index}: " + "terms text " * 60 for index in range(1, 21)]
    page = _page(
        _block("b0", "Primary Market Mortgage", block_type=NormalizedBlockType.HEADING),
        *(
            _block(f"b{index}", text, heading_path=("Primary", "Terms and conditions"))
            for index, text in enumerate(paragraphs, start=1)
        ),
    )

    parts = [
        candidate
        for candidate in build_discovery_candidates(_bundle(page), item_chars=3000)
        if candidate.title.startswith("Terms and conditions")
    ]

    shown = [member.text for part in parts for member in part.members]
    assert len(parts) > 1
    assert shown == paragraphs
    assert all(sum(len(m.text) for m in part.members) <= 3000 for part in parts)
    assert parts[0].title == f"Terms and conditions (part 1 of {len(parts)})"


class _ExceptionClassifier(_Classifier):
    """Accepts sections as current but calls member m2 a related product."""

    def __init__(self, member_id: str = "m2") -> None:
        super().__init__()
        self.member_id = member_id

    async def classify(self, batch: DiscoveryBatch) -> DiscoveryBatchResponse:
        response = await super().classify(batch)
        from app.domain.source_discovery import MemberException

        items = []
        for item, answer in zip(batch.items, response.items, strict=True):
            if len(item.members) > 1:
                answer = answer.model_copy(
                    update={
                        "member_exceptions": (
                            MemberException(
                                member_id=self.member_id,
                                product_association=ProductAssociation.RELATED_PRODUCT,
                                role=InformationRole.RELATED_PRODUCT,
                                relevance=Relevance.POSSIBLY_RELEVANT,
                                reason="Cross-sell card for the construction loan.",
                            ),
                        )
                    }
                )
            items.append(answer)
        return DiscoveryBatchResponse(items=tuple(items))


def _cross_sell_page() -> NormalizedDocument:
    return _page(
        _block("b0", "Primary Market Mortgage", block_type=NormalizedBlockType.HEADING),
        _block("b1", "Nominal rate 12.9%", heading_path=("Primary", "Terms")),
        _block(
            "b2",
            "Our construction loan offers... Learn more",
            heading_path=("Primary", "Terms"),
        ),
    )


@pytest.mark.asyncio
async def test_sd3_a_member_exception_overrides_inheritance_and_selection() -> None:
    from app.services.source_selection import selected_assessments_by_source_item

    repository = InMemorySourceDiscoveryRepository()
    classifier = _ExceptionClassifier()
    service = _service(classifier, repository)
    bundle = _bundle(_cross_sell_page())

    first = await service.discover(bundle, _offering())
    calls = len(classifier.batches)
    second = await service.discover(bundle, _offering())

    for result in (first, second):
        by_block = {
            a.source_refs[0].source_item_id: a
            for a in result.assessments
            if a.scope is DiscoveryScope.BLOCK
        }
        assert by_block["b1"].product_association is ProductAssociation.CURRENT_PRODUCT
        assert by_block["b1"].decision_source is DecisionSource.INHERITED
        assert by_block["b2"].product_association is ProductAssociation.RELATED_PRODUCT
        assert by_block["b2"].inherited_from is not None
        selected = selected_assessments_by_source_item(result.assessments)
        assert selected["b2"].product_association is ProductAssociation.RELATED_PRODUCT
    assert len(classifier.batches) == calls  # the second run is a cache hit


@pytest.mark.asyncio
async def test_sd3_an_exception_naming_a_foreign_member_is_rejected() -> None:
    service = _service(_ExceptionClassifier(member_id="m9"))

    from app.services.source_discovery import DiscoveryResponseError

    with pytest.raises(DiscoveryResponseError) as raised:
        await service.discover(_bundle(_cross_sell_page()), _offering())
    assert "unknown or repeated members" in str(raised.value.__cause__)


def test_sd3_a_table_item_shows_every_row_label() -> None:
    from app.domain.normalization import (
        NormalizedTable,
        NormalizedTableCell,
        NormalizedTableRow,
    )

    def cell(text: str) -> NormalizedTableCell:
        return NormalizedTableCell(raw_text=text, text=text, source_refs=(_ref("t1"),))

    rows = tuple(
        NormalizedTableRow(
            id=f"r{index}", cells=(cell(f"Label {index}"), cell("x" * 400))
        )
        for index in range(1, 41)
    )
    table = NormalizedTable(
        id="t1",
        title="Express Home Mortgage Loan",
        headers=("Item", "Terms"),
        rows=rows,
        source_refs=(_ref("t1"),),
    )
    page = _rates_page().model_copy(update={"tables": (table,)})

    candidate = next(
        c
        for c in build_discovery_candidates(_bundle(page), item_chars=3000)
        if c.scope is DiscoveryScope.TABLE
    )

    assert "Label 40" in candidate.context_text
    assert len(candidate.context_text) <= 3000 + 10


# --- Phase 5: reliability (SD5, SD18, SD6, SD8, SD13, SD14) -------------------------


def test_sd5_period_status_handles_open_ended_periods() -> None:
    from app.domain.effective_periods import PeriodStatus, period_status

    def period(start=None, end=None):
        return EffectivePeriod(raw="x", start=start, end=end)

    today = date(2026, 10, 1)
    assert period_status((), today) is None
    assert period_status((period(),), today) is None
    assert (
        period_status((period(end=date(2026, 10, 31)),), today) is PeriodStatus.CURRENT
    )
    assert (
        period_status((period(start=date(2026, 7, 14)),), today) is PeriodStatus.CURRENT
    )
    assert (
        period_status((period(end=date(2026, 9, 30)),), today)
        is PeriodStatus.HISTORICAL
    )
    assert (
        period_status((period(start=date(2026, 11, 1)),), today) is PeriodStatus.FUTURE
    )
    assert (
        period_status(
            (period(end=date(2026, 9, 1)), period(start=date(2026, 12, 1))), today
        )
        is PeriodStatus.TIME_BOUNDED
    )


@pytest.mark.asyncio
async def test_sd18_temporal_evidence_must_be_quoted_from_the_item() -> None:
    page = _page(
        _block("b1", "Primary Market Mortgage", block_type=NormalizedBlockType.HEADING),
        _block(
            "b2",
            "Previous terms of the loan, archived in 2024",
            heading_path=("Primary", "Old Terms"),
        ),
    )

    async def status(evidence: str | None) -> TemporalStatus:
        classifier = _Classifier(
            temporal_status=TemporalStatus.POSSIBLY_STALE, temporal_evidence=evidence
        )
        result = await _service(classifier).discover(_bundle(page), _offering())
        return next(
            a
            for a in result.assessments
            if a.scope is DiscoveryScope.SECTION
            and a.source_refs[0].source_item_id == "b2"
        ).temporal_status

    assert await status("previous terms of the loan") is TemporalStatus.POSSIBLY_STALE
    assert await status("valid until 01.01.2020") is TemporalStatus.UNKNOWN
    assert await status(None) is TemporalStatus.UNKNOWN


class _SlowFirstClassifier(_Classifier):
    """The first batch answers last."""

    async def classify(self, batch: DiscoveryBatch) -> DiscoveryBatchResponse:
        import asyncio

        if batch.id == "batch_000":
            await asyncio.sleep(0.05)
        return await super().classify(batch)


@pytest.mark.asyncio
async def test_sd6_concurrent_batches_keep_batch_order() -> None:
    classifier = _SlowFirstClassifier()
    service = _service(classifier, max_items_per_batch=2, max_concurrent_batches=3)

    result = await service.discover(_bundle(_many_sections_page()), _offering())

    order = [
        a.source_refs[0].source_item_id
        for a in result.assessments
        if a.scope is DiscoveryScope.SECTION
    ]
    assert order == [f"b{index}" for index in range(1, 7)]


def test_sd8_the_default_discovery_models_pass_the_price_cap() -> None:
    from app.config import load_settings
    from app.services.model_pricing import enforce_model_price_cap, model_sequence

    settings = load_settings().source_discovery

    models = model_sequence(settings.model_name, settings.fallback_model_names)

    assert models == ("gemini-3.1-flash-lite", "gemini-3.5-flash-lite")
    enforce_model_price_cap(
        models,
        max_price_per_million_tokens_usd=settings.max_price_per_million_tokens_usd,
    )


def test_sd13_sd14_the_sdk_makes_one_attempt_and_temperature_is_per_model() -> None:
    from app.services.discovery_classifier import AdkSourceDiscoveryClassifier
    from app.services.pdf_link_selection import AdkPdfLinkClassifier

    primary = AdkSourceDiscoveryClassifier("gemini-3.1-flash-lite", api_key="k")
    fallback = AdkPdfLinkClassifier("gemini-3.5-flash-lite", api_key="k")

    for classifier in (primary, fallback):
        model = classifier._runner.agent.model
        assert model.retry_options.attempts == 1
    # Both run at temperature 0; each switches thinking off the way it accepts.
    assert primary.temperature == 0 and fallback.temperature == 0
    assert primary.thinking.thinking_budget == 0
    assert fallback.thinking.thinking_level == "MINIMAL"
    assert fallback.thinking.thinking_budget is None


def test_sd6_a_link_selector_that_cannot_answer_hands_over() -> None:
    from app.services.discovery_classifier import is_model_fallback_error
    from app.services.pdf_link_selection import PdfLinkResponseError
    from app.services.source_discovery import DiscoveryResponseError

    assert is_model_fallback_error(PdfLinkResponseError("ids"))
    assert is_model_fallback_error(DiscoveryResponseError("ids"))
    assert not is_model_fallback_error(ValueError("bug"))


# --- Phase 6: one selection path (SD7) ----------------------------------------------


def _labelled_bundle_and_discovery():
    """A page with the offering's rate, a menu, and a sibling's tariff table."""
    from app.domain.normalization import (
        NormalizedTable,
        NormalizedTableCell,
        NormalizedTableRow,
    )
    from app.domain.source_discovery import SourceAssessment, SourceDiscoveryResult

    cell = lambda text: NormalizedTableCell(  # noqa: E731
        raw_text=text, text=text, source_refs=(_ref("t-express"),)
    )
    sibling = NormalizedTable(
        id="t-express",
        title="Express Home Mortgage Loan",
        headers=("Item", "Terms"),
        rows=(NormalizedTableRow(id="r1", cells=(cell("Rate"), cell("12.5%"))),),
        source_refs=(_ref("t-express"),),
    )
    page = _page(
        _block(
            "rate", "Nominal interest rate 12.9%", heading_path=("Primary", "Rates")
        ),
        _block("menu", "Cards Deposits Transfers", block_type=NormalizedBlockType.LIST),
        _block("fees", "Loan service fee 0.5%", heading_path=("Primary", "Fees")),
    ).model_copy(update={"tables": (sibling,)})

    def assessment(item, association, relevance, scope=DiscoveryScope.BLOCK):
        return SourceAssessment(
            source_id=f"page:1::block::{item}",
            document_id="page:1",
            scope=scope,
            product_association=association,
            role=InformationRole.PRICING,
            relevance=relevance,
            authority=Authority.OFFICIAL_PRODUCT_CONTENT,
            temporal_status=TemporalStatus.CURRENT,
            reason="fixture",
            decision_source=DecisionSource.LLM,
            input_fingerprint="a" * 64,
            structural_fingerprint="b" * 64,
            source_refs=(_ref(item),),
        )

    discovery = SourceDiscoveryResult(
        product=ProductType.MORTGAGE,
        input_content_hash="d" * 64,
        policy_version="2",
        prompt_version="2",
        model_name="m",
        assessments=(
            assessment("rate", ProductAssociation.CURRENT_PRODUCT, Relevance.RELEVANT),
            assessment(
                "fees",
                ProductAssociation.GENERIC_BANK_INFORMATION,
                Relevance.POSSIBLY_RELEVANT,
            ),
            assessment(
                "menu", ProductAssociation.GLOBAL_NAVIGATION, Relevance.IRRELEVANT
            ),
            assessment(
                "t-express",
                ProductAssociation.RELATED_PRODUCT,
                Relevance.POSSIBLY_RELEVANT,
                DiscoveryScope.TABLE,
            ),
        ),
        llm_batch_count=1,
        reused_assessment_count=0,
    )
    return _bundle(page), discovery


def test_sd7_projection_indexes_the_selection_with_its_labels() -> None:
    from uuid import uuid4

    from app.services.knowledge_projection import KnowledgeProjectionService
    from app.services.source_selection import (
        build_selected_source_bundle,
        select_sources,
    )

    bundle, discovery = _labelled_bundle_and_discovery()
    selection = select_sources(discovery)

    documents = KnowledgeProjectionService().project_sources(
        run_id=uuid4(),
        product=ProductType.MORTGAGE,
        offering_id=OfferingId.MORTGAGE_PRIMARY,
        bundle=build_selected_source_bundle(bundle, discovery),
        retrieved_at=datetime.now(UTC),
        language="en",
        labels=selection.items,
    )

    chunks = [chunk for document in documents for chunk in document.chunks]
    text = "\n".join(chunk.content for chunk in chunks)
    assert "Nominal interest rate 12.9%" in text
    assert "Cards Deposits Transfers" not in text  # not selected
    assert "Express Home Mortgage Loan" not in text  # selected, but a sibling's
    assert selection.document_ids == ("page:1",)
    # Own content and generic bank material never share a chunk.
    assert [chunk.metadata["product_associations"] for chunk in chunks] == [
        ["current_product"],
        ["generic_bank_information"],
    ]
    assert chunks[0].metadata["precedence"] == 3


def test_sd3_the_response_schema_stays_within_what_gemini_accepts() -> None:
    """Gemini answers 400 when the nested exception adds constraints (Phase 7)."""
    schema = DiscoveryBatchResponse.model_json_schema()
    exception = schema["$defs"]["MemberException"]
    item = schema["$defs"]["ModelSourceAssessment"]["properties"]["member_exceptions"]

    assert not any(
        key in field
        for field in exception["properties"].values()
        for key in ("pattern", "minLength", "maxLength")
    )
    assert "maxItems" not in item


def test_sd3_an_exception_without_a_reason_is_rejected() -> None:
    from app.domain.source_discovery import (
        DiscoveryPromptItem,
        MemberException,
        PromptMember,
    )
    from app.services.source_discovery import _check_response

    batch = DiscoveryBatch(
        id="b",
        product=ProductType.MORTGAGE,
        offering=_offering(),
        items=(
            DiscoveryPromptItem(
                source_id="s1",
                scope=DiscoveryScope.SECTION,
                source_type=SourceType.PAGE,
                title="Terms",
                heading_path=(),
                content="",
                members=(
                    PromptMember(id="m1", text="a"),
                    PromptMember(id="m2", text="b"),
                ),
                mime_type="text/html",
                extraction_method="browser",
                quality_score=None,
            ),
        ),
    )
    answer = ModelSourceAssessment(
        source_id="s1",
        product_association=ProductAssociation.CURRENT_PRODUCT,
        role=InformationRole.PRODUCT_TERMS,
        relevance=Relevance.RELEVANT,
        authority=Authority.OFFICIAL_PRODUCT_CONTENT,
        temporal_status=TemporalStatus.CURRENT,
        reason="ok",
        member_exceptions=(
            MemberException(
                member_id="m2",
                product_association=ProductAssociation.RELATED_PRODUCT,
                role=InformationRole.RELATED_PRODUCT,
                relevance=Relevance.POSSIBLY_RELEVANT,
                reason=" ",
            ),
        ),
    )

    with pytest.raises(ValueError, match="need a reason"):
        _check_response(batch, DiscoveryBatchResponse(items=(answer,)))


def test_sd1_the_offering_carries_what_its_page_says_it_covers() -> None:
    from app.domain.source_discovery import page_scope

    page = _page(
        _block("b0", "Personal", block_type=NormalizedBlockType.LIST, site_chrome=True),
        _block("b1", "Quick mortgage loan", block_type=NormalizedBlockType.HEADING),
        _block(
            "b2",
            "For you to purchase, construct and renovate your home",
            heading_path=("Quick mortgage loan",),
        ),
    )

    heading, summary = page_scope(page.blocks)

    assert heading == "Quick mortgage loan"
    assert summary == "For you to purchase, construct and renovate your home"


@pytest.mark.asyncio
async def test_sd18_a_quoted_date_that_contradicts_the_status_is_ignored() -> None:
    def page(text: str) -> NormalizedDocument:
        return _page(
            _block(
                "b1", "Primary Market Mortgage", block_type=NormalizedBlockType.HEADING
            ),
            _block("b2", text, heading_path=("Primary", "Fees")),
        )

    async def status(document, evidence: str) -> TemporalStatus:
        classifier = _Classifier(
            temporal_status=TemporalStatus.FUTURE, temporal_evidence=evidence
        )
        result = await _service(classifier).discover(
            _bundle(document), _offering(), as_of=date(2026, 9, 26)
        )
        return next(
            a
            for a in result.assessments
            if a.scope is DiscoveryScope.SECTION
            and a.source_refs[0].source_item_id == "b2"
        ).temporal_status

    past = page("Loan service fees (effective from 14.07.2026)")
    later = page("Loan service fees (effective from 14.12.2026)")

    assert await status(past, "effective from 14.07.2026") is TemporalStatus.UNKNOWN
    assert await status(later, "effective from 14.12.2026") is TemporalStatus.FUTURE


# --- Phase 8: follow-ups after review ------------------------------------------------


def _with_links(
    document: NormalizedDocument, links: dict[str, str]
) -> NormalizedDocument:
    from app.domain.normalization import NormalizedLink

    return document.model_copy(
        update={
            "links": tuple(
                NormalizedLink(
                    id=link_id, url=url, text="Learn more", source_refs=(_ref(link_id),)
                )
                for link_id, url in links.items()
            )
        }
    )


def _catalog_offering():
    from app.domain.source_discovery import OtherOffering

    return _offering().model_copy(
        update={
            "other_offerings": (
                OtherOffering(
                    offering_id="mortgage_construction",
                    display_name="Construction Mortgage",
                    seed_url="https://ameriabank.am/en/personal/loans/mortgage/construction-mortgage",
                ),
            )
        }
    )


@pytest.mark.asyncio
async def test_cross_sell_cards_linking_to_another_offering_are_decided_by_rule() -> (
    None
):
    construction = (
        "https://ameriabank.am/en/personal/loans/mortgage/construction-mortgage/"
    )
    page = _with_links(
        _page(
            _block(
                "b0", "Primary Market Mortgage", block_type=NormalizedBlockType.HEADING
            ),
            _block("b1", "Nominal rate 12.9%", heading_path=("Primary", "Rates")),
            _block(
                "b2",
                "Our construction loan offers are designed to help you build.",
                heading_path=("Primary", "Construction loan"),
                link_ids=("l1",),
            ),
            _block(
                "b3",
                "Apply for this mortgage online.",
                heading_path=("Primary", "Apply"),
                link_ids=("l2",),
            ),
            _block(
                "b4",
                "Long terms text. " * 60,
                heading_path=("Primary", "Terms"),
                link_ids=("l1",),
            ),
        ),
        {"l1": construction, "l2": URL},
    )
    classifier = _Classifier()

    result = await _service(classifier).discover(_bundle(page), _catalog_offering())

    by_block = {
        a.source_refs[0].source_item_id: a
        for a in result.assessments
        if a.scope is DiscoveryScope.BLOCK
    }
    card = by_block["b2"]
    assert card.product_association is ProductAssociation.RELATED_PRODUCT
    assert card.decision_source is DecisionSource.INHERITED
    assert "Construction Mortgage" in card.reason
    sent = {
        text
        for batch in classifier.batches
        for item in batch.items
        for text in [_item_text(item)]
    }
    assert not any("Our construction loan offers" in text for text in sent)
    # A card linking to the offering's own page, and a long section, go to Gemini.
    assert any("Apply for this mortgage online." in text for text in sent)
    assert any("Long terms text." in text for text in sent)


@pytest.mark.asyncio
async def test_without_the_catalog_there_is_no_cross_sell_rule() -> None:
    page = _with_links(
        _page(
            _block(
                "b0", "Primary Market Mortgage", block_type=NormalizedBlockType.HEADING
            ),
            _block(
                "b2",
                "Our construction loan offers.",
                heading_path=("Primary", "Construction loan"),
                link_ids=("l1",),
            ),
        ),
        {
            "l1": "https://ameriabank.am/en/personal/loans/mortgage/construction-mortgage"
        },
    )
    classifier = _Classifier()

    await _service(classifier).discover(_bundle(page), _offering())

    assert any(
        "Our construction loan offers." in _item_text(item)
        for batch in classifier.batches
        for item in batch.items
    )


@pytest.mark.asyncio
async def test_every_batch_tells_the_model_what_day_it_is() -> None:
    classifier = _Classifier()

    await _service(classifier).discover(
        _bundle(_rates_page()), _offering(), as_of=date(2026, 9, 26)
    )

    assert {batch.as_of for batch in classifier.batches} == {date(2026, 9, 26)}
    from app.services.discovery_classifier import build_classifier_prompt

    assert '"as_of": "2026-09-26"' in build_classifier_prompt(classifier.batches[0])
