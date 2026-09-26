"""Regression cases from the review fix plan.

Each test states the behaviour reviews *should* have for one item (RV-numbers
refer to fix-process/reviews/review-fix-plan.md). The extraction results they
start from are real `SemanticExtractionService` results over scripted answers.
"""

from __future__ import annotations

import json
from uuid import uuid4

import pytest

from app.domain.models import OfferingId, ProductType
from app.domain.review import ReviewDecision, ReviewDecisionType, ReviewReason
from app.domain.semantic_extraction import (
    ExtractionBatchResponse,
    ExtractionField,
    ExtractionStatus,
    ModelCitation,
    ModelFieldResult,
)
from app.services.snapshot_lifecycle import (
    build_snapshot_attempt,
    detect_review_signals,
)
from tests.unit.test_semantic_extraction_fixes import (
    RETRIEVED_AT,
    ScriptedExtractor,
    _block,
    _bundle,
    _service,
    _table,
)


def _long_page(rows=None):
    """25 unrelated paragraphs, then the tariff table: the rate row is not among
    the first 20 catalog entries."""
    blocks = tuple(
        _block(f"b{index}", f"Paragraph {index} about the bank's history.", ("About",))
        for index in range(25)
    )
    rows = rows or (
        ("Loan terms", "Annual interest rate", "14%"),
        ("Loan terms", "Term (months)", "60"),
    )
    return _bundle(
        (_block("title", "Mortgage loan for primary market"), *blocks),
        (_table(rows=rows, notes=(), stub_columns=2),),
    )


async def _result(bundle_and_discovery, extractor=None):
    bundle, discovery = bundle_and_discovery
    discovery = discovery.model_copy(update={"offering_id": "mortgage_primary"})
    return await _service(extractor or ScriptedExtractor()).extract(
        bundle, discovery, retrieved_at=RETRIEVED_AT
    )


def _row(result, label: str):
    return next(item for item in result.evidence_catalog if label in item.content)


class _CitesUnknownEvidence(ScriptedExtractor):
    """A rate with one real citation whose quote lacks the value, and one ID that
    does not exist."""

    async def extract(self, batch):
        response = await super().extract(batch)
        rate = next(item for item in batch.evidence if "interest rate" in item.content)
        return ExtractionBatchResponse(
            results=tuple(
                ModelFieldResult(
                    field=item.field,
                    status=ExtractionStatus.FOUND,
                    value_json='[{"value":{"min":14,"max":14},"conditions":[]}]',
                    evidence=(
                        ModelCitation(
                            evidence_id=rate.evidence_id, quote="Annual interest rate"
                        ),
                        ModelCitation(evidence_id="ev_" + "f" * 24, quote="14%"),
                    ),
                )
                if item.field is ExtractionField.INTEREST_RATE
                else item
                for item in response.results
            )
        )


def _signal(result, field: str):
    return next(s for s in detect_review_signals(result) if s.get("field") == field)


# --- RV1 / RV2: the set is decided at signal time, from the field's call ------------------


@pytest.mark.asyncio
async def test_rv1_not_stated_signal_is_seeded_from_the_fields_call() -> None:
    result = await _result(_long_page())
    assert result.call_evidence, "each call's evidence is kept (RV2)"
    signal = _signal(result, "interest_rate")
    rate_row = _row(result, "Annual interest rate")
    units = signal["evidence_set"]["units"]
    assert any(rate_row.evidence_id in unit["evidence_ids"] for unit in units)
    assert len(units) <= 2


# --- RV3 / RV5: unknown IDs apart; a failed value is extraction_invalid ---------------------


@pytest.mark.asyncio
async def test_rv5_failed_value_is_extraction_invalid_with_its_candidate() -> None:
    result = await _result(_long_page(), _CitesUnknownEvidence())
    signal = _signal(result, "interest_rate")
    assert signal["reason"] == ReviewReason.EXTRACTION_INVALID.value
    assert signal["candidates"][0]["value"] == [
        {"value": {"min": 14, "max": 14}, "conditions": []}
    ]
    assert signal["failed_checks"]
    assert signal["evidence_set"]["unknown_ids"] == ["ev_" + "f" * 24]
    assert all(
        "ev_" + "f" * 24 not in unit["evidence_ids"]
        for unit in signal["evidence_set"]["units"]
    )


# --- RV4 / RV7: the set reaches the review, as references ----------------------------------


def _snapshot(result, previous=None):
    return build_snapshot_attempt(
        run_id=uuid4(),
        offering_execution_id=uuid4(),
        product=ProductType.MORTGAGE,
        offering_id=OfferingId("mortgage_primary"),
        result=result,
        previous_accepted_snapshot_id=previous.id if previous else None,
        previous_accepted_snapshot=previous,
    )


@pytest.mark.asyncio
async def test_rv4_review_stores_the_signals_evidence_set_not_the_catalog() -> None:
    from app.services.monitoring_pipeline import _review_tasks

    result = await _result(_long_page())
    snapshot = _snapshot(result)
    task = next(t for t in _review_tasks(snapshot) if t.issue_scope == "interest_rate")
    assert "items" not in task.evidence
    signal = next(
        s
        for s in snapshot.validation["review_signals"]
        if s["field"] == "interest_rate"
    )
    assert task.evidence["set"] == signal["evidence_set"]


@pytest.mark.asyncio
async def test_rv4_rate_change_review_links_the_new_values_citations() -> None:
    def rate(value: str):
        return ScriptedExtractor(
            {
                ExtractionField.INTEREST_RATE: (
                    json.dumps(
                        [{"value": {"min": value, "max": value}, "conditions": []}]
                    ),
                    f"{value}%",
                )
            }
        )

    old = await _result(
        _long_page((("Loan terms", "Annual interest rate", "10%"),)), rate("10")
    )
    new = await _result(
        _long_page((("Loan terms", "Annual interest rate", "14%"),)), rate("14")
    )
    signal = next(
        s
        for s in _snapshot(new, _snapshot(old)).validation["review_signals"]
        if s["reason"] == "large_rate_change"
    )
    seeds = {i for unit in signal["evidence_set"]["units"] for i in unit["seed_ids"]}
    assert _row(new, "14%").evidence_id in seeds


# --- RV6: a decision removes only its own signal ----------------------------------------------


def test_rv6_resolving_the_ocr_review_keeps_the_rate_signal() -> None:
    from app.services.review_decisions import _without_review_signal

    validation = {
        "review_signals": [
            {"reason": "ocr_evidence", "issue_scope": "interest_rate"},
            {"reason": "large_rate_change", "issue_scope": "interest_rate"},
        ]
    }
    left = _without_review_signal(
        validation, "interest_rate", ReviewReason.OCR_EVIDENCE
    )
    assert [s["reason"] for s in left["review_signals"]] == ["large_rate_change"]


# --- RV8: the model gets freshness, not the catalog -------------------------------------------


@pytest.mark.xfail(
    strict=True, reason="RV8: get_current_tariffs returns the whole catalog"
)
def test_rv8_current_tariffs_payload_has_no_evidence_or_values() -> None:
    from datetime import UTC, datetime

    from app.domain.tariff_queries import (
        CurrentTariffItem,
        CurrentTariffResult,
        FreshnessStatus,
    )
    from app.tools.reads import current_tariffs_payload

    result = CurrentTariffResult(
        as_of=datetime(2026, 9, 26, tzinfo=UTC),
        items=(
            CurrentTariffItem(
                product=ProductType.CONSUMER_LOAN,
                offering_id=OfferingId.OVERDRAFT,
                freshness=FreshnessStatus.FRESH,
                snapshot_id=uuid4(),
                accepted_at=datetime(2026, 9, 25, tzinfo=UTC),
                age_seconds=86400,
                normalized_tariff={"interest_rate": {"status": "found", "value": [1]}},
                evidence=({"evidence_id": "ev_" + "a" * 24, "content": "x" * 5000},),
            ),
        ),
    )
    payload = current_tariffs_payload(result)
    text = json.dumps(payload)
    assert "evidence" not in text and "x" * 100 not in text
    assert payload["items"][0]["fields"] == {"interest_rate": "found"}


# --- RV9: bounded units; the model gets only the seeds -----------------------------------------


@pytest.mark.asyncio
async def test_rv9_large_table_is_windowed_and_the_model_view_is_trimmed() -> None:
    from app.services.monitoring_pipeline import _review_tasks
    from app.services.review_resolution import build_review_view

    rows = tuple(
        ("Loan terms", f"Fee item {index}", f"AMD {index},000") for index in range(40)
    )
    rows = (*rows[:20], ("Loan terms", "Annual interest rate", "14%"), *rows[20:])
    result = await _result(_long_page(rows))
    snapshot = _snapshot(result)
    task = next(t for t in _review_tasks(snapshot) if t.issue_scope == "interest_rate")
    unit = task.evidence["set"]["units"][0]
    assert unit["kind"] == "table"
    assert len(unit["evidence_ids"]) <= 7 and unit["omitted"] >= 30
    view = build_review_view(task, snapshot.evidence)
    assert 1 <= len(view.evidence) <= 5
    assert all(len(item.excerpt) <= 600 for item in view.evidence)


# --- RV10: `?` content is saved with the snapshot ----------------------------------------------


@pytest.mark.asyncio
async def test_rv10_snapshot_keeps_the_selected_sources_markdown() -> None:
    result = await _result(_long_page())
    snapshot = build_snapshot_attempt(
        run_id=uuid4(),
        offering_execution_id=uuid4(),
        product=ProductType.MORTGAGE,
        offering_id=OfferingId("mortgage_primary"),
        result=result,
        previous_accepted_snapshot_id=None,
        selected_sources_markdown="# Mortgage loan\n\n| Loan terms | 14% |",
    )
    assert snapshot.selected_sources_markdown.startswith("# Mortgage loan")


# --- RV12: chat model calls carry the run -----------------------------------------------------


@pytest.mark.xfail(strict=True, reason="RV12: ADK model calls record run_id=None")
@pytest.mark.asyncio
async def test_rv12_model_call_during_a_run_records_the_run() -> None:
    from types import SimpleNamespace

    from app.services.model_call_usage import ACTIVE_RUN_STATE_KEY, adk_usage_callbacks

    recorded = []

    class Repository:
        async def record(self, usage):
            recorded.append(usage)

    run_id = uuid4()
    callbacks = adk_usage_callbacks(
        Repository(), stage="adk.cli", model_id="gemini-3.7-flash"
    )
    context = SimpleNamespace(
        invocation_id="inv-1", state={ACTIVE_RUN_STATE_KEY: str(run_id)}
    )
    await callbacks["before_model_callback"](context, None)
    await callbacks["after_model_callback"](
        context, SimpleNamespace(usage_metadata=None)
    )
    assert recorded and recorded[0].run_id == run_id


# --- RV13: a citation outside the shown units is logged ----------------------------------------


@pytest.mark.asyncio
async def test_rv13_override_citing_outside_the_shown_units_is_audited() -> None:
    from app.domain.monitoring import SnapshotStatus
    from app.services.monitoring_pipeline import _review_tasks
    from app.services.review_decisions import ReviewDecisionService
    from tests.unit.test_multi_review_approval import _Reviews, _Snapshots

    result = await _result(_long_page())
    snapshot = _snapshot(result).model_copy(
        update={"status": SnapshotStatus.REVIEW_REQUIRED}
    )
    task = next(t for t in _review_tasks(snapshot) if t.issue_scope == "interest_rate")
    snapshots = _Snapshots(snapshot)
    reviews = _Reviews([task], snapshots)
    far = _row(result, "Paragraph 3 ")
    await ReviewDecisionService(reviews, snapshots).apply(
        task.id,
        ReviewDecision(
            decision_type=ReviewDecisionType.OVERRIDE,
            override_value="14%",
            reason="Read from the page.",
            evidence_reference=far.evidence_id,
        ),
        reviewer="analyst",
    )
    events = reviews.updates[0].audit_events
    assert events[0]["event_type"] == "review_citation_outside_shown_units"


# --- Evidence-set details (RV1, RV3, RV5, RV9) ------------------------------------------------


@pytest.mark.asyncio
async def test_section_unit_is_a_window_around_the_cited_block() -> None:
    from app.services.review_evidence import cited_evidence_set

    result = await _result(_long_page())
    seed = _row(result, "Paragraph 10 ")
    evidence_set = cited_evidence_set(
        result.evidence_catalog, [seed.evidence_id], why="cited"
    )
    (unit,) = evidence_set.units
    shown = [
        next(i for i in result.evidence_catalog if i.evidence_id == e).content
        for e in unit.evidence_ids
    ]
    assert unit.kind == "section"
    assert [text.split()[1] for text in shown] == ["8", "9", "10", "11", "12"]
    assert unit.seed_ids == (seed.evidence_id,)
    assert unit.omitted == 20


@pytest.mark.asyncio
async def test_page_table_and_its_pdf_copy_count_once() -> None:
    from app.services.review_evidence import cited_evidence_set

    result = await _result(_long_page())
    rows = [i for i in result.evidence_catalog if ":row:" in i.source_item_id]
    copies = [
        row.model_copy(
            update={
                "evidence_id": "ev_" + f"{index:024x}",
                "document_id": "pdf:bbbbbbbbbbbbbbbb",
                "order": 1000 + index,
            }
        )
        for index, row in enumerate(rows)
    ]
    catalog = (*result.evidence_catalog, *copies)
    evidence_set = cited_evidence_set(
        catalog,
        [rows[0].evidence_id, copies[0].evidence_id, copies[1].evidence_id],
        why="cited",
    )
    assert [unit.key.split("|")[0] for unit in evidence_set.units] == [
        "pdf:bbbbbbbbbbbbbbbb"
    ]


class _OmitsField(ScriptedExtractor):
    """Answers every field of the call except `omitted`."""

    def __init__(self, omitted: ExtractionField) -> None:
        super().__init__()
        self.omitted = omitted

    async def extract(self, batch):
        response = await super().extract(batch)
        kept = tuple(r for r in response.results if r.field is not self.omitted)
        # A repair call asks for the omitted field alone; it is omitted there too.
        return ExtractionBatchResponse(
            results=kept
            or (
                ModelFieldResult(
                    field=ExtractionField.PRODUCT_NAME,
                    status=ExtractionStatus.NOT_STATED,
                ),
            )
        )


@pytest.mark.asyncio
async def test_required_field_missing_from_the_answer_stays_missing_required_field() -> (
    None
):
    result = await _result(_long_page(), _OmitsField(ExtractionField.INTEREST_RATE))
    signal = _signal(result, "interest_rate")
    assert signal["reason"] == "missing_required_field"
    assert signal["evidence_set"]["units"][0]["why"] == "batch"
    assert "candidates" not in signal


@pytest.mark.asyncio
async def test_optional_field_missing_from_the_answer_is_extraction_invalid() -> None:
    result = await _result(_long_page(), _OmitsField(ExtractionField.COLLATERAL))
    signal = _signal(result, "collateral")
    assert signal["reason"] == "extraction_invalid"
    assert "candidates" not in signal
    assert signal["failed_checks"]


@pytest.mark.asyncio
async def test_rv5_selecting_geminis_value_resolves_the_field() -> None:
    from app.domain.monitoring import SnapshotStatus
    from app.services.monitoring_pipeline import _review_tasks
    from app.services.review_decisions import ReviewDecisionService
    from app.services.review_resolution import build_review_view, review_policy
    from tests.unit.test_multi_review_approval import _Reviews, _Snapshots

    result = await _result(_long_page(), _CitesUnknownEvidence())
    snapshot = _snapshot(result).model_copy(
        update={"status": SnapshotStatus.REVIEW_REQUIRED}
    )
    task = next(t for t in _review_tasks(snapshot) if t.issue_scope == "interest_rate")
    allowed, _ = review_policy(task.reason)
    view = build_review_view(task, snapshot.evidence)
    assert ReviewDecisionType.SELECT_CANDIDATE in allowed
    assert "Gemini proposed" in view.guidance and "check failed" in view.guidance
    snapshots = _Snapshots(snapshot)
    reviews = _Reviews([task], snapshots)

    await ReviewDecisionService(reviews, snapshots).apply(
        task.id,
        ReviewDecision(
            decision_type=ReviewDecisionType.SELECT_CANDIDATE,
            candidate_id=task.candidates[0].candidate_id,
        ),
        reviewer="analyst",
    )

    (update,) = reviews.updates
    rate = update.normalized_tariff["interest_rate"]
    assert rate["value"][0]["value"]["min"] == "14"
    assert all(
        s["issue_scope"] != "interest_rate" for s in update.validation["review_signals"]
    )


@pytest.mark.asyncio
async def test_rv13_override_citing_a_shown_passage_is_not_audited() -> None:
    from app.domain.monitoring import SnapshotStatus
    from app.services.monitoring_pipeline import _review_tasks
    from app.services.review_decisions import ReviewDecisionService
    from tests.unit.test_multi_review_approval import _Reviews, _Snapshots

    result = await _result(_long_page())
    snapshot = _snapshot(result).model_copy(
        update={"status": SnapshotStatus.REVIEW_REQUIRED}
    )
    task = next(t for t in _review_tasks(snapshot) if t.issue_scope == "interest_rate")
    snapshots = _Snapshots(snapshot)
    reviews = _Reviews([task], snapshots)
    await ReviewDecisionService(reviews, snapshots).apply(
        task.id,
        ReviewDecision(
            decision_type=ReviewDecisionType.OVERRIDE,
            override_value="14%",
            reason="Read from the table.",
            evidence_reference=_row(result, "Annual interest rate").evidence_id,
        ),
        reviewer="analyst",
    )
    assert reviews.updates[0].audit_events == ()
