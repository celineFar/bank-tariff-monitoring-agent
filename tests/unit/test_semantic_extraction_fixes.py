"""Regression cases from the semantic-extraction fix plan.

Each test states the behaviour extraction *should* have for one confirmed or
code-level problem (SE-numbers refer to
fix-process/semantic_extraction/semantic-extraction-fix-plan.md).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest
from google.genai.errors import ClientError

from app.config import SemanticExtractionSettings
from app.domain.acquisition import SourceLocator, SourceType
from app.domain.models import ProductType
from app.domain.normalization import (
    NormalizedBlock,
    NormalizedBlockType,
    NormalizedDocument,
    NormalizedNote,
    NormalizedSourceBundle,
    NormalizedTable,
    NormalizedTableCell,
    NormalizedTableRow,
    SourceReference,
)
from app.domain.semantic_extraction import (
    ExtractionBatchResponse,
    ExtractionField,
    ExtractionStatus,
    LoanCategory,
    ModelCitation,
    ModelFieldResult,
)
from app.domain.source_discovery import (
    Authority,
    DecisionSource,
    DiscoveryScope,
    InformationRole,
    ProductAssociation,
    Relevance,
    SourceAssessment,
    SourceDiscoveryResult,
    TemporalStatus,
)
from app.services import semantic_extraction as extraction_module
from app.services.block_normalizer import normalize_block
from app.services.extraction_evidence import build_evidence_catalog
from app.services.extraction_planner import build_extraction_batches
from app.services.html_parser import HtmlArtifactParser
from app.services.semantic_extraction import (
    FallbackSemanticExtractionService,
    InMemorySemanticExtractionRepository,
    SemanticExtractionService,
    normalize_extraction_field_value,
)
from app.services.table_normalizer import normalize_table

URL = "https://ameriabank.am/en/personal/loans/mortgage/primary"
CONSTRUCTION_URL = (
    "https://ameriabank.am/en/personal/loans/mortgage/construction-mortgage"
)
RETRIEVED_AT = datetime(2026, 9, 26, tzinfo=UTC)


# --- fixtures ------------------------------------------------------------------


def _ref(item_id: str, url: str = URL) -> SourceReference:
    return SourceReference(
        source_item_id=item_id,
        locator=SourceLocator(source_url=url, source_type=SourceType.PAGE),
    )


def _block(
    item_id: str, text: str, heading_path: tuple[str, ...] = ()
) -> NormalizedBlock:
    return NormalizedBlock(
        id=item_id,
        type=NormalizedBlockType.PARAGRAPH,
        raw_text=text,
        text=text,
        heading_path=heading_path,
        source_refs=(_ref(item_id),),
    )


def _cell(text: str, ref: str) -> NormalizedTableCell:
    return NormalizedTableCell(raw_text=text, text=text, source_refs=(_ref(ref),))


def _table(
    table_id: str = "t1",
    rows: tuple[tuple[str, ...], ...] = (
        ("Loan terms ³", "Interest rate", "21%"),
        ("Loan terms ³", "Term (months)", "60"),
    ),
    notes: tuple[tuple[str, str], ...] = (
        ("3", "Other terms can be applied for scoring-based loans."),
    ),
    stub_columns: int = 0,
) -> NormalizedTable:
    return NormalizedTable(
        id=table_id,
        title="Tariffs",
        headers=("Section", "Item", "Terms"),
        stub_columns=stub_columns,
        rows=tuple(
            NormalizedTableRow(
                id=f"{table_id}:row:{index}",
                cells=tuple(
                    _cell(text, f"{table_id}:row:{index}:cell:{column}")
                    for column, text in enumerate(row)
                ),
            )
            for index, row in enumerate(rows)
        ),
        notes=tuple(
            NormalizedNote(
                marker=marker,
                raw_text=text,
                text=text,
                source_refs=(_ref(f"{table_id}:note"),),
            )
            for marker, text in notes
        ),
        source_refs=(_ref(table_id),),
    )


def _assessment(
    item_id: str, scope: DiscoveryScope, document_id: str
) -> SourceAssessment:
    return SourceAssessment(
        source_id=f"{document_id}::{scope.value}::{item_id}",
        document_id=document_id,
        scope=scope,
        product_association=ProductAssociation.CURRENT_PRODUCT,
        role=InformationRole.PRODUCT_TERMS,
        relevance=Relevance.RELEVANT,
        authority=Authority.OFFICIAL_TERMS,
        temporal_status=TemporalStatus.CURRENT,
        reason="test",
        decision_source=DecisionSource.RULE,
        input_fingerprint="c" * 64,
        structural_fingerprint="d" * 64,
        source_refs=(_ref(item_id),),
    )


def _bundle(
    blocks: tuple[NormalizedBlock, ...],
    tables: tuple[NormalizedTable, ...] = (),
    *,
    document_id: str = "page:aaaaaaaaaaaaaaaa",
    product: ProductType = ProductType.MORTGAGE,
    url: str = URL,
) -> tuple[NormalizedSourceBundle, SourceDiscoveryResult]:
    bundle = NormalizedSourceBundle(
        canonical_url=url,
        acquisition_content_hash="a" * 64,
        documents=(
            NormalizedDocument(
                id=document_id,
                name="Mortgage loan",
                source_url=url,
                source_type=SourceType.PAGE,
                mime_type="text/html",
                content_sha256="b" * 64,
                extraction_method="browser",
                blocks=blocks,
                tables=tables,
            ),
        ),
    )
    assessments = tuple(
        _assessment(block.id, DiscoveryScope.BLOCK, document_id) for block in blocks
    ) + tuple(
        _assessment(table.id, DiscoveryScope.TABLE, document_id) for table in tables
    )
    discovery = SourceDiscoveryResult(
        product=product,
        input_content_hash="a" * 64,
        policy_version="1",
        prompt_version="1",
        model_name="test-model",
        assessments=assessments,
        llm_batch_count=0,
        reused_assessment_count=0,
    )
    return bundle, discovery


def _mortgage_bundle(text: str) -> tuple[NormalizedSourceBundle, SourceDiscoveryResult]:
    return _bundle(
        (
            _block("title", "Mortgage loan for primary market"),
            _block("terms", text, ("Loan terms",)),
        )
    )


class ScriptedExtractor:
    """Category and product name found; `answers` for chosen fields; the rest not_stated."""

    def __init__(
        self, answers: dict[ExtractionField, tuple[str, str]] | None = None
    ) -> None:
        self.answers = answers or {}
        self.calls = 0

    async def extract(self, batch):
        self.calls += 1
        by_id = {item.source_item_id: item for item in batch.evidence}
        title = by_id.get("title") or batch.evidence[0]
        results = []
        for field in batch.fields:
            if field is ExtractionField.CATEGORY:
                results.append(
                    self._found(field, '"mortgage"', title, title.content[:10])
                )
            elif field is ExtractionField.PRODUCT_NAME:
                results.append(
                    self._found(field, json.dumps(title.content), title, title.content)
                )
            elif field in self.answers:
                value_json, quote = self.answers[field]
                item = next(
                    (
                        i
                        for i in batch.evidence
                        if quote.casefold() in i.content.casefold()
                    ),
                    by_id.get("terms") or batch.evidence[0],
                )
                results.append(self._found(field, value_json, item, quote))
            else:
                results.append(
                    ModelFieldResult(field=field, status=ExtractionStatus.NOT_STATED)
                )
        return ExtractionBatchResponse(results=tuple(results))

    @staticmethod
    def _found(field, value_json, item, quote):
        return ModelFieldResult(
            field=field,
            status=ExtractionStatus.FOUND,
            value_json=value_json,
            evidence=(ModelCitation(evidence_id=item.evidence_id, quote=quote),),
        )


def _service(extractor, repository=None, *, model_name="model-a", settings=None):
    return SemanticExtractionService(
        extractor,
        repository or InMemorySemanticExtractionRepository(),
        settings or SemanticExtractionSettings(),
        model_name=model_name,
    )


def _reviewed_fields(result) -> set[ExtractionField]:
    return {item.field for item in result.review_items}


def _parse(body: str):
    parsed = HtmlArtifactParser(("ameriabank.am",)).parse(
        f"<html><body>{body}</body></html>", source_url=URL
    )
    return (
        [normalize_block(block, table_id=block.table_id) for block in parsed.blocks],
        [normalize_table(table) for table in parsed.tables],
    )


def _cell_by_text(table: NormalizedTable, text: str) -> NormalizedTableCell:
    return next(cell for row in table.rows for cell in row.cells if cell.text == text)


# --- SE13: raw responses never cross offerings ------------------------------------


@pytest.mark.asyncio
async def test_se13_failing_call_carries_no_other_offerings_raw_response() -> None:
    from app.services.semantic_extraction import (
        AdkSemanticExtractor,
        SemanticExtractionCallError,
    )

    extractor = AdkSemanticExtractor("model-a", api_key="test-key", max_attempts=1)
    assert not hasattr(extractor, "raw_responses")

    async def no_answer(*_args, **_kwargs):
        raise RuntimeError("semantic extractor returned no final response")
        yield  # pragma: no cover

    extractor._runner.run_async = no_answer
    bundle, discovery = _mortgage_bundle("Loan amount AMD 3,000,000")
    batch = (await _service(extractor).plan(bundle, discovery)).batches[0]
    with pytest.raises(SemanticExtractionCallError) as failure:
        await extractor.extract(batch)
    assert failure.value.raw_response is None


# --- SE16: a malformed value is a field review, not a crash -----------------------


@pytest.mark.asyncio
async def test_se16_malformed_term_becomes_a_review_item() -> None:
    bundle, discovery = _mortgage_bundle("Loan term 6 months to 360 months")
    extractor = ScriptedExtractor(
        {ExtractionField.TERM: ('[{"value":{"min_value":"6 months"}}]', "6 months")}
    )
    result = await _service(extractor).extract(
        bundle, discovery, retrieved_at=RETRIEVED_AT
    )
    assert ExtractionField.TERM in _reviewed_fields(result)


# --- SE15: normalizers reshape, never guess ---------------------------------------


def test_se15_age_string_is_not_guessed_into_max_age() -> None:
    value, _ = normalize_extraction_field_value(
        ExtractionField.AGE_REQUIREMENTS, ["from 21 years"]
    )
    assert "max_age" not in json.dumps(value)


def test_se15_rate_currency_becomes_a_condition() -> None:
    value, _ = normalize_extraction_field_value(
        ExtractionField.INTEREST_RATE,
        [
            {"value": {"min": 18, "currency": "AMD"}},
            {"value": {"min": 14, "currency": "USD"}},
        ],
    )
    assert value[0]["conditions"] == [{"dimension": "currency", "value": "AMD"}]
    assert value[1]["conditions"] == [{"dimension": "currency", "value": "USD"}]


def test_se15_bare_collateral_string_is_not_guessed_applicable() -> None:
    value, _ = normalize_extraction_field_value(
        ExtractionField.COLLATERAL, ["not required"]
    )
    assert '"applicable": true' not in json.dumps(value)


# --- SE14: keyword substrings do not reject not_stated ----------------------------


@pytest.mark.asyncio
async def test_se14_mortgage_without_age_limit_accepts_not_stated() -> None:
    bundle, discovery = _mortgage_bundle(
        "Mortgage loan: annual percentage rate 14%, loan amount AMD 3,000,000"
    )
    result = await _service(ScriptedExtractor()).extract(
        bundle, discovery, retrieved_at=RETRIEVED_AT
    )
    assert ExtractionField.AGE_REQUIREMENTS not in _reviewed_fields(result)


# --- SE17: alternatives must differ in their conditions ---------------------------


@pytest.mark.xfail(strict=True, reason="SE17: rate alternatives may be unconditional")
@pytest.mark.asyncio
async def test_se17_unconditional_rate_alternatives_are_rejected() -> None:
    bundle, discovery = _mortgage_bundle("Interest rate 18% for AMD, 14% for USD")
    extractor = ScriptedExtractor(
        {
            ExtractionField.INTEREST_RATE: (
                '[{"value":{"min":18,"max":18},"conditions":[]},'
                '{"value":{"min":14,"max":14},"conditions":[]}]',
                "18% for AMD, 14% for USD",
            )
        }
    )
    result = await _service(extractor).extract(
        bundle, discovery, retrieved_at=RETRIEVED_AT
    )
    assert ExtractionField.INTEREST_RATE in _reviewed_fields(result)


# --- SE18: citations contain the value --------------------------------------------


@pytest.mark.xfail(strict=True, reason="SE18: a citation need not contain the value")
@pytest.mark.asyncio
async def test_se18_value_missing_from_its_citation_is_rejected() -> None:
    bundle, discovery = _mortgage_bundle("Interest rate: 21% per annum")
    extractor = ScriptedExtractor(
        {
            ExtractionField.INTEREST_RATE: (
                '[{"value":{"min":21,"max":21},"conditions":[]}]',
                "Interest rate",
            )
        }
    )
    result = await _service(extractor).extract(
        bundle, discovery, retrieved_at=RETRIEVED_AT
    )
    assert ExtractionField.INTEREST_RATE in _reviewed_fields(result)


@pytest.mark.xfail(
    strict=True, reason="SE18: quotes are compared with exact whitespace"
)
@pytest.mark.asyncio
async def test_se18_quote_differing_only_by_nbsp_is_accepted() -> None:
    bundle, discovery = _mortgage_bundle("Interest rate: 21\u00a0% per annum")
    extractor = ScriptedExtractor(
        {
            ExtractionField.INTEREST_RATE: (
                '[{"value":{"min":21,"max":21},"conditions":[]}]',
                "21 %",
            )
        }
    )
    result = await _service(extractor).extract(
        bundle, discovery, retrieved_at=RETRIEVED_AT
    )
    assert ExtractionField.INTEREST_RATE not in _reviewed_fields(result)


# --- SE10: evidence identity survives unrelated changes ----------------------------


def test_se10_inserting_a_block_keeps_the_tables_evidence_ids() -> None:
    table = _table()
    before = _bundle((_block("b1", "Mortgage loan"),), (table,))
    after = _bundle(
        (_block("b1", "New promotion this month"), _block("b2", "Mortgage loan")),
        (table,),
        document_id="page:bbbbbbbbbbbbbbbb",
    )
    ids = [
        {
            item.evidence_id
            for item in build_evidence_catalog(bundle, discovery)
            if item.source_item_id.startswith("t1:row")
        }
        for bundle, discovery in (before, after)
    ]
    assert ids[0] == ids[1]


# --- SE11: the cache key covers what the model sees, and only that ------------------


async def _fingerprints(bundle, discovery, settings=None) -> set[str]:
    plan = await _service(ScriptedExtractor(), settings=settings).plan(
        bundle, discovery
    )
    return {batch.content_fingerprint for batch in plan.batches}


@pytest.mark.xfail(strict=True, reason="SE11: the instruction is not in the cache key")
@pytest.mark.asyncio
async def test_se11_instruction_change_changes_the_cache_key(monkeypatch) -> None:
    bundle, discovery = _mortgage_bundle("Loan amount AMD 3,000,000-150,000,000")
    before = await _fingerprints(bundle, discovery)
    monkeypatch.setattr(
        extraction_module,
        "SEMANTIC_EXTRACTION_INSTRUCTION",
        extraction_module.SEMANTIC_EXTRACTION_INSTRUCTION + "\nA new rule.",
    )
    assert before.isdisjoint(await _fingerprints(bundle, discovery))


@pytest.mark.asyncio
async def test_se11_heading_rename_changes_the_cache_key() -> None:
    text = "Loan amount AMD 3,000,000-150,000,000"
    before = _bundle(
        (_block("title", "Mortgage loan"), _block("terms", text, ("Unsecured",)))
    )
    after = _bundle(
        (_block("title", "Mortgage loan"), _block("terms", text, ("Secured",)))
    )
    assert (await _fingerprints(*before)).isdisjoint(await _fingerprints(*after))


@pytest.mark.asyncio
async def test_se11_unrelated_unit_does_not_change_budgeted_cache_keys() -> None:
    settings = SemanticExtractionSettings(evidence_mode="budgeted")
    rows = (
        ("Loan terms", "Interest rate", "12%"),
        ("Loan terms", "Term (months)", "60"),
    )
    before = _bundle(
        (
            _block("title", "Mortgage loan"),
            _block("faq", "Can I apply online? Yes.", ("FAQ",)),
        ),
        (_table(rows=rows, notes=()),),
    )
    after = _bundle(
        (
            _block("title", "Mortgage loan"),
            _block("faq", "Can I apply by phone? Yes.", ("FAQ",)),
        ),
        (_table(rows=rows, notes=()),),
    )
    unchanged = (await _fingerprints(*before, settings)) & (
        await _fingerprints(*after, settings)
    )
    assert unchanged, "calls that did not receive the FAQ block keep their cache key"


# --- SE1: table header hierarchy -----------------------------------------------------


def test_se1_card_tier_columns_name_their_cells() -> None:
    _, (table,) = _parse(
        "<table>"
        '<tr><td colspan="2"><strong>Card type</strong></td>'
        '<td colspan="2"><strong>Classic</strong></td>'
        '<td colspan="3"><strong>Gold</strong></td></tr>'
        '<tr><td>Purpose</td><td>Purpose</td><td colspan="5">Payments</td></tr>'
        '<tr><td rowspan="2">Loan terms</td><td>Currency</td><td colspan="5">AMD</td></tr>'
        '<tr><td>Interest rate</td><td colspan="2">AMD: 21%</td><td colspan="3">AMD: 20%</td></tr>'
        "</table>"
    )
    assert _cell_by_text(table, "AMD: 21%").column_path == ("Classic",)
    assert _cell_by_text(table, "AMD: 20%").column_path == ("Gold",)


def test_se1_currency_qualifier_row_names_the_rate_columns() -> None:
    _, (table,) = _parse(
        "<table>"
        '<tr><td colspan="5">Home Purchase Loan (primary market)</td></tr>'
        '<tr><td rowspan="5">3. Loan terms</td><td>3.1. Currency</td><td>3.1.1. AMD</td>'
        "<td>3.1.2. USD</td><td>3.1.3. EUR</td></tr>"
        "<tr><td>3.2. Minimum and maximum loan limits</td><td>AMD 3,000,000 - AMD 150,000,000</td>"
        "<td>USD 5,000 - USD 300,000</td><td>EUR 5,000 - EUR 300,000</td></tr>"
        '<tr><td colspan="4">Term and interest rate</td></tr>'
        '<tr><td rowspan="2">3.4. Nominal annual interest rate</td><td>3.4.1. Fixed</td>'
        "<td>3.4.2. Fixed</td><td>3.4.3. Fixed</td></tr>"
        "<tr><td>13.5%</td><td>11.0%</td><td>8.5%</td></tr>"
        "</table>"
    )
    assert _cell_by_text(table, "13.5%").column_path == ("Currency: AMD",)
    assert _cell_by_text(table, "8.5%").column_path == ("Currency: EUR",)
    value_row = next(r for r in table.rows if any(c.text == "13.5%" for c in r.cells))
    fixed_row = next(
        r for r in table.rows if any(c.text == "3.4.1. Fixed" for c in r.cells)
    )
    assert value_row.continues == fixed_row.id


# --- SE2: headline value and label are one block --------------------------------------


def test_se2_headline_card_is_one_key_value_block() -> None:
    blocks, _ = _parse(
        "<h1>Real estate loan</h1>"
        '<div class="features3-grid__row">'
        '<div class="features3-grid__col"><img src="a.png" alt="Loan amount icon">'
        "<h6>AMD 3-150 million</h6><p>Loan amount</p><div></div></div>"
        '<div class="features3-grid__col"><h6>60-360 months</h6><p>Term</p></div>'
        "</div>"
        "<p>Actual interest rate: 13.67-13.68%</p>"
    )
    pair = next(block for block in blocks if "AMD 3-150 million" in block.text)
    assert pair.type is NormalizedBlockType.KEY_VALUE
    assert pair.text == "Loan amount: AMD 3-150 million"
    after = next(
        block for block in blocks if block.text.startswith("Actual interest rate")
    )
    assert "60-360 months" not in after.heading_path


# --- SE4: a row carries the notes it cites --------------------------------------------


def test_se4_row_record_carries_its_referenced_note() -> None:
    bundle, discovery = _bundle((_block("b1", "Mortgage loan"),), (_table(),))
    rate_row = next(
        item
        for item in build_evidence_catalog(bundle, discovery)
        if item.source_item_id == "t1:row:0"
    )
    assert "Other terms can be applied for scoring-based loans." in rate_row.content


# --- SE21: the field set follows the offering's category --------------------------------


def test_se21_overdraft_offering_requests_no_collateral() -> None:
    bundle, discovery = _bundle(
        (_block("title", "Overdraft"), _block("terms", "Credit limit AMD 100,000")),
        product=ProductType.CONSUMER_LOAN,
    )
    evidence = build_evidence_catalog(bundle, discovery)
    batches = build_extraction_batches(
        ProductType.CONSUMER_LOAN,
        evidence,
        SemanticExtractionSettings(),
        canonical_url=URL,
        category=LoanCategory.OVERDRAFT,
    )
    fields = {field for batch in batches for field in batch.fields}
    assert ExtractionField.COLLATERAL not in fields
    assert ExtractionField.CREDIT_LIMIT in fields


# --- SE20: no URL-gated scope rules ----------------------------------------------------


@pytest.mark.asyncio
async def test_se20_primary_offering_gets_no_url_gated_exclusion() -> None:
    blocks = (
        _block("title", "Mortgage loan"),
        _block("express", "Loan amount AMD 3,000,000", ("Express Home option",)),
    )
    for url in (URL, CONSTRUCTION_URL):
        bundle, discovery = _bundle(blocks, url=url)
        plan = await _service(ScriptedExtractor()).plan(bundle, discovery)
        sent = {
            item.source_item_id for batch in plan.batches for item in batch.evidence
        }
        assert "express" in sent, url


# --- SE25: one failed call falls back alone ----------------------------------------------


class _FailsCoreFinancial(ScriptedExtractor):
    async def extract(self, batch):
        if ExtractionField.INTEREST_RATE in batch.fields:
            self.calls += 1
            raise ClientError(
                404, {"error": {"message": "model retired", "status": "NOT_FOUND"}}
            )
        return await super().extract(batch)


@pytest.mark.xfail(strict=True, reason="SE25: fallback only when every batch fails")
@pytest.mark.asyncio
async def test_se25_one_failing_call_uses_the_fallback_for_that_call_only() -> None:
    bundle, discovery = _mortgage_bundle("Interest rate 14%; loan amount AMD 3,000,000")
    repository = InMemorySemanticExtractionRepository()
    primary, fallback = _FailsCoreFinancial(), ScriptedExtractor()
    service = FallbackSemanticExtractionService(
        (
            _service(primary, repository, model_name="model-a"),
            _service(fallback, repository, model_name="model-b"),
        )
    )
    result = await service.extract(bundle, discovery, retrieved_at=RETRIEVED_AT)
    assert not any(
        item.raw_result is None and item.raw_response is None
        for item in result.review_items
    )
    assert fallback.calls == 1


# --- SE23 / SE24: pinned sampling, one SDK attempt, one retry on an unusable answer ----


def test_se23_extractor_runs_at_temperature_zero_with_one_sdk_attempt() -> None:
    from app.services.semantic_extraction import AdkSemanticExtractor

    extractor = AdkSemanticExtractor(
        "gemini-3.7-flash", api_key="test-key", max_output_tokens=4096
    )
    agent = extractor._runner.agent
    config = agent.generate_content_config
    assert config.temperature == 0
    assert config.max_output_tokens == 4096
    assert agent.model.retry_options.attempts == 1


@pytest.mark.asyncio
async def test_se24_unusable_answer_is_asked_once_more_then_fails() -> None:
    from app.services.semantic_extraction import (
        AdkSemanticExtractor,
        ExtractorOutput,
        SemanticExtractionCallError,
    )

    bundle, discovery = _mortgage_bundle("Loan amount AMD 3,000,000")
    batch = (await _service(ScriptedExtractor()).plan(bundle, discovery)).batches[0]
    good = await ScriptedExtractor().extract(batch)
    extractor = AdkSemanticExtractor("model-a", api_key="test-key")
    answers = iter(
        (
            SemanticExtractionCallError("cut", raw_response="{", retryable=True),
            ExtractorOutput(response=good, raw_response="{...}"),
        )
    )

    async def once(_batch):
        answer = next(answers)
        if isinstance(answer, Exception):
            raise answer
        return answer

    extractor._extract_once = once
    assert (await extractor.extract(batch)).raw_response == "{...}"
    assert extractor.usage.application_retries == 1

    async def always_unusable(_batch):
        raise SemanticExtractionCallError("cut", raw_response="{", retryable=True)

    extractor._extract_once = always_unusable
    with pytest.raises(SemanticExtractionCallError) as failure:
        await extractor.extract(batch)
    assert failure.value.raw_response == "{"


# --- SE6: evidence modes ----------------------------------------------------------------


def test_se6_full_mode_sends_all_evidence_and_fails_loudly_above_the_ceiling() -> None:
    from app.services.extraction_planner import EvidencePacketTooLargeError
    from app.services.failure_mapping import source_failure_code

    bundle, discovery = _mortgage_bundle("Interest rate 14%; loan amount AMD 3,000,000")
    evidence = build_evidence_catalog(bundle, discovery)
    batches = build_extraction_batches(
        ProductType.MORTGAGE, evidence, SemanticExtractionSettings(), canonical_url=URL
    )
    assert len(batches) == 3
    assert all(len(batch.evidence) == len(evidence) for batch in batches)

    huge = _mortgage_bundle("Rate 14%. " + "x" * 12_000)
    with pytest.raises(EvidencePacketTooLargeError) as failure:
        build_extraction_batches(
            ProductType.MORTGAGE,
            build_evidence_catalog(*huge),
            SemanticExtractionSettings(max_packet_chars=10_000, budget_chars=2000),
            canonical_url=URL,
        )
    assert "semantic_extraction.packet_too_large" in str(failure.value)
    assert (
        source_failure_code(failure.value, stage="semantic_extraction").value
        == "source.size_rejected"
    )


@pytest.mark.asyncio
async def test_se6_budgeted_mode_marks_not_stated_fields_it_had_no_room_for() -> None:
    rows = tuple(
        ("Loan terms", f"Fee {index}", "AMD " + "9" * 40) for index in range(80)
    )
    bundle, discovery = _bundle(
        (_block("title", "Mortgage loan"),),
        (
            _table("t1", rows=rows, notes=(), stub_columns=2),
            _table(
                "t2",
                rows=(("Fees", "Service fee", "AMD 5,000"),),
                notes=(),
                stub_columns=2,
            ),
        ),
    )
    settings = SemanticExtractionSettings(evidence_mode="budgeted", budget_chars=2000)
    result = await _service(ScriptedExtractor(), settings=settings).extract(
        bundle, discovery, retrieved_at=RETRIEVED_AT
    )
    fees_batch = next(
        batch
        for batch in (
            await _service(ScriptedExtractor(), settings=settings).plan(
                bundle, discovery
            )
        ).batches
        if ExtractionField.FEES in batch.fields
    )
    assert fees_batch.evidence_mode == "budgeted"
    assert fees_batch.units_left_out
    assert ExtractionField.FEES in fees_batch.budget_limited_fields
    fees = next(
        item for item in result.validated_fields if item.field is ExtractionField.FEES
    )
    assert "not_stated_budget_limited" in (fees.explanation or "")


# --- SE20 / SE21 / SE22: scope from the catalog, fields by category, dimensions ---------


def test_se21_catalog_category_defaults_to_the_family_and_must_belong_to_it() -> None:
    from pydantic import ValidationError as PydanticValidationError

    from app.config.seed_catalog import load_seed_catalog
    from app.domain.catalog import OfferingCategory

    catalog = {
        entry.offering_id.value: entry for entry in load_seed_catalog().offerings
    }
    assert catalog["overdraft"].category is OfferingCategory.OVERDRAFT
    assert catalog["credit_line"].category is OfferingCategory.CREDIT_LINE
    assert catalog["consumer_standard"].category is OfferingCategory.CONSUMER_LOAN
    assert catalog["mortgage_primary"].category is OfferingCategory.MORTGAGE
    with pytest.raises(PydanticValidationError, match="does not belong"):
        catalog["mortgage_primary"].model_validate(
            {**catalog["mortgage_primary"].model_dump(), "category": "overdraft"}
        )


@pytest.mark.asyncio
async def test_se21_a_category_that_disagrees_with_the_catalog_is_a_review() -> None:
    from app.config.seed_catalog import load_seed_catalog
    from app.domain.source_discovery import OfferingContext

    catalog = load_seed_catalog()
    entry = next(e for e in catalog.offerings if e.offering_id.value == "overdraft")
    bundle, discovery = _bundle(
        (_block("title", "Overdraft"), _block("terms", "Credit limit AMD 100,000")),
        product=ProductType.CONSUMER_LOAN,
    )
    offering = OfferingContext.from_catalog_entry(entry, catalog=catalog)

    class SaysConsumerLoan(ScriptedExtractor):
        async def extract(self, batch):
            response = await super().extract(batch)
            return ExtractionBatchResponse(
                results=tuple(
                    item.model_copy(update={"value_json": '"consumer_loan"'})
                    if item.field is ExtractionField.CATEGORY
                    else item
                    for item in response.results
                )
            )

    result = await _service(SaysConsumerLoan()).extract(
        bundle, discovery, retrieved_at=RETRIEVED_AT, offering=offering
    )
    assert ExtractionField.CATEGORY in _reviewed_fields(result)
    plan = await _service(ScriptedExtractor()).plan(bundle, discovery, offering)
    scope = " ".join(plan.batches[0].target_scope)
    assert "offering=Overdraft (overdraft)" in scope and "category=overdraft" in scope
    assert "exclude_as_base" not in scope  # the old URL-gated rule text


def test_se22_condition_dimensions_are_canonical() -> None:
    from app.domain.semantic_extraction import Condition, ConditionDimension

    assert Condition(dimension="card_type", value="Gold").dimension is (
        ConditionDimension.CARD_TIER
    )
    assert Condition(dimension="Currency", value="AMD").dimension is (
        ConditionDimension.CURRENCY
    )
    unknown = Condition(dimension="season", value="summer")
    assert unknown.dimension is ConditionDimension.OTHER
    assert unknown.value == "season: summer"
