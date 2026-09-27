"""Regression cases from the end-to-end review (fix/review-and-publication).

Each test names the review finding it covers: P1 quotes, P2 waiting reviews,
P3 reject_all scope, P4 orphaned reviews, P5 vanished answers, P6 nested
history fields, P7 transient linked-document failures.
"""

from __future__ import annotations

import hashlib

import pytest

from app.domain.acquisition import SourceLocator, SourceType
from app.domain.models import ProductType
from app.domain.semantic_extraction import (
    EvidenceItem,
    ExtractionField,
    ExtractionStatus,
    ModelCitation,
    ModelFieldResult,
)
from app.domain.source_discovery import (
    Authority,
    InformationRole,
    ProductAssociation,
    TemporalStatus,
)
from app.services.semantic_extraction import _validate_field_result, source_span
from app.services.structured_projection import StructuredTariffProjector

# --- P1: the stored quote is the source's own text --------------------------------

_ROW = "3. Loan terms > 3.4. Nominal annual interest rate:\n  Currency: AMD → 13.5% (Fixed)"


@pytest.mark.parametrize(
    ("quote", "expected"),
    [
        ("Currency: AMD → 13.5%", "Currency: AMD → 13.5%"),
        (
            "Nominal annual interest rate: Currency: AMD → 13.5%",
            "Nominal annual interest rate:\n  Currency: AMD → 13.5%",
        ),
        ("NOMINAL annual  interest", "Nominal annual interest"),
        ("not in the row", "not in the row"),
    ],
)
def test_p1_source_span_returns_the_matching_source_text(quote, expected) -> None:
    assert source_span(quote, _ROW) == expected


def test_p1_source_span_handles_expanding_case_folds() -> None:
    assert source_span("strasse 5", "Adresse: Straße 5, Yerevan") == "Straße 5"


def _row_evidence() -> EvidenceItem:
    return EvidenceItem(
        evidence_id="ev_" + hashlib.sha256(b"row").hexdigest()[:24],
        document_id="page:abc",
        source_item_id="t1:row:3",
        content=_ROW,
        role=InformationRole.PRICING,
        authority=Authority.OFFICIAL_PRODUCT_CONTENT,
        temporal_status=TemporalStatus.CURRENT,
        precedence=2,
        product_association=ProductAssociation.CURRENT_PRODUCT,
        locator=SourceLocator(
            source_url="https://ameriabank.am/en/personal/loans/consumer-loans/consumer-loans",
            source_type=SourceType.PAGE,
            block_id="t1",
        ),
    )


def test_p1_a_line_joined_quote_is_accepted_and_publishable() -> None:
    item = _row_evidence()
    catalog = {item.evidence_id: item}
    result = ModelFieldResult(
        field=ExtractionField.INTEREST_RATE,
        status=ExtractionStatus.FOUND,
        value_json=(
            '[{"value":{"min":13.5,"max":13.5,"rate_type":"fixed","basis":"annual"},'
            '"conditions":[{"dimension":"currency","value":"AMD"}]}]'
        ),
        evidence=(
            ModelCitation(
                evidence_id=item.evidence_id,
                quote="Nominal annual interest rate: Currency: AMD → 13.5%",
            ),
        ),
    )

    validated = _validate_field_result(
        result, catalog, product=ProductType.CONSUMER_LOAN, batch_id="b1"
    )
    verified = StructuredTariffProjector._evidence(validated.evidence, catalog)

    assert validated.evidence[0].quote in _ROW
    assert len(verified) == 1


# --- P3: reject_all closes one offering's candidate, not the whole run -----------


def _family_review(run_id, offering, scope, snapshot_id, order):
    from datetime import UTC, datetime, timedelta
    from uuid import uuid4

    from app.domain.review import ReviewCandidate, ReviewReason, ReviewTask

    review_id = uuid4()
    return ReviewTask(
        id=review_id,
        idempotency_key=f"review:{review_id}",
        run_id=run_id,
        offering_execution_id=uuid4(),
        snapshot_id=snapshot_id,
        product=offering.product,
        offering_id=offering,
        reason=ReviewReason.OFFICIAL_SOURCE_CONFLICT,
        issue_scope=scope,
        candidates=(
            ReviewCandidate(
                candidate_id="candidate-1",
                field=scope,
                value="12.5%",
                evidence_references=("evidence-1",),
            ),
        ),
        evidence={"items": [{"evidence_id": "evidence-1", "content": "12.5%"}]},
        created_at=datetime(2026, 9, 25, tzinfo=UTC) + timedelta(seconds=order),
        updated_at=datetime(2026, 9, 25, tzinfo=UTC),
    )


@pytest.mark.asyncio
async def test_p3_reject_all_leaves_other_offerings_reviews_pending() -> None:
    from uuid import uuid4

    from app.domain.models import OfferingId
    from app.domain.review import ReviewDecision, ReviewDecisionType, ReviewStatus
    from app.services.review_resolution import ReviewResolutionService
    from tests.fixtures.monitoring_node import Decisions, Reviews, Runs

    run_id, overdraft, credit_line = uuid4(), uuid4(), uuid4()
    rate = _family_review(run_id, OfferingId.OVERDRAFT, "interest_rate", overdraft, 0)
    fees = _family_review(run_id, OfferingId.OVERDRAFT, "fees", overdraft, 1)
    other = _family_review(run_id, OfferingId.CREDIT_LINE, "fees", credit_line, 2)
    reviews = Reviews()
    reviews.tasks = {task.id: task for task in (rate, fees, other)}
    runs = Runs()
    service = ReviewResolutionService(
        runs=runs, reviews=reviews, decisions=Decisions(reviews)
    )

    await service.apply(
        rate,
        ReviewDecision(decision_type=ReviewDecisionType.REJECT_ALL),
        reviewer="cli-user",
    )

    assert reviews.tasks[rate.id].status is ReviewStatus.REJECTED
    assert reviews.tasks[fees.id].status is ReviewStatus.SUPERSEDED
    assert reviews.tasks[other.id].status is ReviewStatus.PENDING


@pytest.mark.asyncio
async def test_p3_after_a_rejection_the_node_asks_the_next_offerings_review() -> None:
    from app.domain.models import OfferingId
    from app.domain.review import ReviewStatus
    from tests.fixtures.monitoring_node import (
        OFFERING,
        PRODUCT,
        build,
        call,
        function_responses,
        interrupts,
        reply,
        text,
    )

    harness = await build(
        review_scopes=("interest_rate", "fees"),
        other_reviews=((OfferingId.CREDIT_LINE, "interest_rate"),),
    )
    harness.model.play(
        call("run_tariff_monitoring", product=PRODUCT, offering_id=OFFERING)
    )
    ((first, _),) = interrupts(await harness.turn(text("monitor")))

    events = await harness.turn(reply(first, {"decision_type": "reject_all"}))
    ((second, payload),) = interrupts(events)
    assert payload["view"]["offering_id"] == OfferingId.CREDIT_LINE.value

    events = await harness.turn(
        reply(
            second, {"decision_type": "select_candidate", "candidate_id": "candidate-1"}
        )
    )

    result = function_responses(events, "run_tariff_monitoring")[0]
    statuses = sorted(task.status.value for task in harness.reviews.tasks.values())
    assert statuses == ["approved", "rejected", "superseded"]
    assert result["status"] in {"succeeded", "partial_success"}
    assert all(
        task.status is not ReviewStatus.PENDING
        for task in harness.reviews.tasks.values()
    )


# --- P2: reviewing picks the newest waiting run and closes empty ones -------------


@pytest.mark.asyncio
async def test_p2_review_them_asks_the_newest_waiting_run_first() -> None:
    from datetime import timedelta

    from app.domain.models import OfferingId
    from app.domain.monitoring import RunStatus
    from app.services.monitoring_node import parse_review_interrupt_id
    from tests.fixtures.monitoring_node import (
        NOW,
        PRODUCT,
        build,
        call,
        interrupts,
        queued_run,
        review_task,
        text,
    )

    harness = await build()
    empty = harness.runs.add(
        queued_run(status=RunStatus.AWAITING_REVIEW, queued_at=NOW + timedelta(hours=2))
    )
    older = harness.runs.add(queued_run(status=RunStatus.AWAITING_REVIEW))
    newer = harness.runs.add(
        queued_run(status=RunStatus.AWAITING_REVIEW, queued_at=NOW + timedelta(hours=1))
    )
    for run in (older, newer):
        task = review_task(run, OfferingId.OVERDRAFT, "interest_rate")
        harness.reviews.tasks[task.id] = task
    harness.model.play(call("run_tariff_monitoring", product=PRODUCT, review_only=True))

    ((interrupt_id, _),) = interrupts(await harness.turn(text("review them")))

    assert parse_review_interrupt_id(interrupt_id)[0] == newer.id
    # The paused run with nothing pending was closed on the way.
    assert harness.runs.runs[empty.id].status.is_terminal


@pytest.mark.asyncio
async def test_p2_the_worker_keeps_closing_reviewed_runs_and_survives_errors() -> None:
    import asyncio
    from datetime import timedelta

    from app.worker import MonitoringWorker

    class Runs:
        async def recover_abandoned(self, *, before):
            return 0

    class Resolution:
        calls = 0

        async def close_orphaned_reviews(self, *, limit=500):
            return 0

        async def complete_runs_without_pending_reviews(self, *, limit=100):
            self.calls += 1
            if self.calls == 1:
                raise RuntimeError("database away")
            return 1

    resolution = Resolution()
    worker = MonitoringWorker(
        runs=Runs(),
        pipeline=None,
        resolution=resolution,
        worker_id="worker-1",
        abandoned_after=timedelta(minutes=2),
        recovery_interval_seconds=0.01,
    )
    stop = asyncio.Event()
    loop = asyncio.create_task(worker._recover_forever(stop))
    for _ in range(500):
        if resolution.calls >= 2:
            break
        await asyncio.sleep(0.01)
    stop.set()
    await loop

    assert resolution.calls >= 2


# --- P2: pauses that could not end ------------------------------------------------


def _ocr_result(batch_id: str):
    """The accepted fixture's rate, cited from an OCR-read page."""
    from app.domain.pdf_extraction import OCR_SOURCE_ITEM_MARKER
    from app.domain.semantic_extraction import SemanticExtractionResult
    from tests.fixtures.structured_tariffs import accepted_snapshot

    result = SemanticExtractionResult.model_validate(
        accepted_snapshot("consumer").semantic_extraction
    )
    field = result.validated_fields[0]
    citation = field.evidence[0].model_copy(
        update={"source_item_id": f"pdf{OCR_SOURCE_ITEM_MARKER}p1"}
    )
    return result.model_copy(
        update={
            "validated_fields": (
                field.model_copy(
                    update={"evidence": (citation,), "batch_id": batch_id}
                ),
            )
        }
    )


def test_p2_a_confirmed_ocr_reading_is_not_asked_again() -> None:
    from app.services.snapshot_lifecycle import detect_review_signals

    fresh = detect_review_signals(_ocr_result("batch-1"))
    confirmed = detect_review_signals(_ocr_result("memory:review-1"))

    assert [signal["reason"] for signal in fresh] == ["ocr_evidence"]
    assert confirmed == ()


def test_p2_an_ocr_approval_is_remembered_as_read() -> None:
    from uuid import uuid4

    from app.domain.monitoring import SnapshotStatus
    from app.domain.review import ReviewReason
    from app.services.review_decisions import _remembered_approval
    from tests.fixtures.structured_tariffs import accepted_snapshot

    result = _ocr_result("batch-1")
    field = result.validated_fields[0]
    result = result.model_copy(
        update={
            "validated_fields": (
                field.model_copy(update={"result_fingerprint": "f" * 64}),
            )
        }
    )
    snapshot = accepted_snapshot("consumer").model_copy(
        update={
            "status": SnapshotStatus.REVIEW_REQUIRED,
            "semantic_extraction": result.model_dump(mode="json"),
        }
    )
    task = _family_review(
        uuid4(), snapshot.offering_id, "interest_rate", snapshot.id, 0
    ).model_copy(update={"reason": ReviewReason.OCR_EVIDENCE})

    remembered = _remembered_approval(task, snapshot)
    large_change = _remembered_approval(
        task.model_copy(update={"reason": ReviewReason.LARGE_RATE_CHANGE}), snapshot
    )

    assert remembered is not None
    assert remembered.result_fingerprint == "f" * 64
    assert remembered.decision.value == field.value
    assert remembered.decision.batch_id == f"memory:{task.id}"
    assert large_change is None


@pytest.mark.asyncio
async def test_p2_a_remembered_citation_takes_the_passages_current_labels() -> None:
    from app.domain.semantic_extraction import (
        RememberedReviewDecision,
        ValidatedFieldResult,
    )
    from app.repositories.review_memory import InMemoryReviewDecisionMemory
    from app.services.semantic_extraction import (
        SemanticExtractionService,
        _hydrate_citation,
        validate_review_field_value,
    )
    from tests.unit.test_semantic_extraction_fixes import (
        RETRIEVED_AT,
        InMemorySemanticExtractionRepository,
        ScriptedExtractor,
        SemanticExtractionSettings,
        _mortgage_bundle,
    )

    extractor = ScriptedExtractor(
        {
            ExtractionField.INTEREST_RATE: (
                '[{"value":{"min":21,"max":21},"conditions":[]}]',
                "Interest rate",
            )
        }
    )
    memory = InMemoryReviewDecisionMemory()
    service = SemanticExtractionService(
        extractor,
        InMemorySemanticExtractionRepository(),
        SemanticExtractionSettings(),
        model_name="model-a",
        review_memory=memory,
    )
    bundle, discovery = _mortgage_bundle("Interest rate: 21% per annum")
    discovery = discovery.model_copy(update={"offering_id": "mortgage_primary"})
    first = await service.extract(bundle, discovery, retrieved_at=RETRIEVED_AT)
    review = next(
        item
        for item in first.review_items
        if item.field is ExtractionField.INTEREST_RATE
    )
    terms = next(
        item for item in first.evidence_catalog if item.source_item_id == "terms"
    )
    catalog = {item.evidence_id: item for item in first.evidence_catalog}
    # Stored when discovery labelled the passage differently.
    stale = _hydrate_citation(terms.evidence_id, "21%", catalog).model_copy(
        update={
            "authority": (
                Authority.OFFICIAL_TERMS
                if terms.authority is not Authority.OFFICIAL_TERMS
                else Authority.OFFICIAL_PRODUCT_CONTENT
            )
        }
    )
    await memory.remember(
        RememberedReviewDecision(
            offering_id="mortgage_primary",
            field=ExtractionField.INTEREST_RATE,
            prompt_fingerprint=review.prompt_fingerprint,
            result_fingerprint=review.result_fingerprint,
            decision=ValidatedFieldResult(
                field=ExtractionField.INTEREST_RATE,
                status=ExtractionStatus.FOUND,
                value=validate_review_field_value(
                    ExtractionField.INTEREST_RATE, [{"value": {"min": 21, "max": 21}}]
                ),
                evidence=(stale,),
                batch_id="memory:review-1",
            ),
        )
    )

    second = await service.extract(bundle, discovery, retrieved_at=RETRIEVED_AT)

    reused = next(
        item
        for item in second.validated_fields
        if item.field is ExtractionField.INTEREST_RATE
    )
    assert reused.batch_id == "memory:review-1"
    assert reused.evidence[0].authority is terms.authority


@pytest.mark.asyncio
async def test_p2_a_candidate_with_nothing_to_review_fails_instead_of_pausing(
    monkeypatch,
) -> None:
    from uuid import uuid4

    from app.domain.monitoring import SnapshotStatus
    from app.services import monitoring_pipeline
    from app.services.monitoring_pipeline import OfferingPipelineError
    from tests.unit.test_monitoring_pipeline import _indexing, _offering

    build = monitoring_pipeline.build_snapshot_attempt

    def unreviewable(**kwargs):
        snapshot = build(**kwargs)
        return snapshot.model_copy(
            update={
                "status": SnapshotStatus.REVIEW_REQUIRED,
                "accepted_at": None,
                "validation": {**snapshot.validation, "review_signals": []},
            }
        )

    monkeypatch.setattr(monitoring_pipeline, "build_snapshot_attempt", unreviewable)
    service, _, publications = _indexing()

    with pytest.raises(OfferingPipelineError) as captured:
        await service.refresh(_offering(), uuid4(), uuid4())

    assert captured.value.failure_code == "offering.validation_failed"
    assert publications.values == []


@pytest.mark.asyncio
async def test_p2_the_same_result_as_an_approved_one_is_marked_confirmed() -> None:
    from app.domain.semantic_extraction import RememberedReviewDecision
    from app.repositories.review_memory import InMemoryReviewDecisionMemory
    from app.services.semantic_extraction import SemanticExtractionService
    from tests.unit.test_semantic_extraction_fixes import (
        RETRIEVED_AT,
        InMemorySemanticExtractionRepository,
        ScriptedExtractor,
        SemanticExtractionSettings,
        _mortgage_bundle,
    )

    extractor = ScriptedExtractor(
        {
            ExtractionField.INTEREST_RATE: (
                '[{"value":{"min":21,"max":21},"conditions":[]}]',
                "21%",
            )
        }
    )
    memory = InMemoryReviewDecisionMemory()
    service = SemanticExtractionService(
        extractor,
        InMemorySemanticExtractionRepository(),
        SemanticExtractionSettings(),
        model_name="model-a",
        review_memory=memory,
    )
    bundle, discovery = _mortgage_bundle("Interest rate: 21% per annum")
    discovery = discovery.model_copy(update={"offering_id": "mortgage_primary"})
    first = await service.extract(bundle, discovery, retrieved_at=RETRIEVED_AT)
    read = next(
        item
        for item in first.validated_fields
        if item.field is ExtractionField.INTEREST_RATE
    )
    assert not read.batch_id.startswith("memory:")
    await memory.remember(
        RememberedReviewDecision(
            offering_id="mortgage_primary",
            field=ExtractionField.INTEREST_RATE,
            prompt_fingerprint=read.prompt_fingerprint,
            result_fingerprint=read.result_fingerprint,
            decision=read.model_copy(update={"batch_id": "memory:review-7"}),
        )
    )

    second = await service.extract(bundle, discovery, retrieved_at=RETRIEVED_AT)

    confirmed = next(
        item
        for item in second.validated_fields
        if item.field is ExtractionField.INTEREST_RATE
    )
    assert confirmed.batch_id == "memory:review-7"
    assert confirmed.value == read.value
    assert confirmed.evidence == read.evidence


# --- P4: reviews of a run that ended are closed, not announced forever ------------


@pytest.mark.asyncio
async def test_p4_reviews_of_an_ended_run_are_superseded() -> None:
    from app.domain.models import OfferingId
    from app.domain.monitoring import RunFailureCode, RunStatus
    from app.domain.review import ReviewStatus
    from app.services.review_resolution import ReviewResolutionService
    from tests.fixtures.monitoring_node import (
        Decisions,
        Reviews,
        Runs,
        queued_run,
        review_task,
    )

    runs, reviews = Runs(), Reviews()
    cancelled = runs.add(
        queued_run(status=RunStatus.FAILED, failure_code=RunFailureCode.CANCELLED.value)
    )
    waiting = runs.add(queued_run(status=RunStatus.AWAITING_REVIEW))
    orphan = review_task(cancelled, OfferingId.OVERDRAFT, "interest_rate")
    live = review_task(waiting, OfferingId.CREDIT_LINE, "interest_rate")
    reviews.tasks = {orphan.id: orphan, live.id: live}
    service = ReviewResolutionService(
        runs=runs, reviews=reviews, decisions=Decisions(reviews)
    )

    assert await service.close_orphaned_reviews() == 1
    assert reviews.tasks[orphan.id].status is ReviewStatus.SUPERSEDED
    assert reviews.tasks[live.id].status is ReviewStatus.PENDING


@pytest.mark.asyncio
async def test_p4_the_chat_announces_only_reviews_it_can_reach() -> None:
    from app.domain.models import OfferingId
    from app.domain.monitoring import RunStatus
    from app.tools._services import configure_services
    from app.tools.resolution import _pending_review_counts
    from tests.fixtures.monitoring_node import Reviews, Runs, queued_run, review_task

    runs, reviews = Runs(), Reviews()
    ended = runs.add(queued_run(status=RunStatus.FAILED))
    waiting = runs.add(queued_run(status=RunStatus.AWAITING_REVIEW))
    for run, offering in (
        (ended, OfferingId.OVERDRAFT),
        (waiting, OfferingId.CREDIT_LINE),
    ):
        task = review_task(run, offering, "interest_rate")
        reviews.tasks[task.id] = task
    configure_services(None, None, runs=runs, reviews=reviews)
    try:
        counts = await _pending_review_counts()
    finally:
        configure_services(None, None)

    assert counts == {"credit_line": 1}


# --- P5: an answer that could not be applied is reported, not dropped -------------


@pytest.mark.asyncio
async def test_p5_an_answer_to_a_superseded_review_is_reported() -> None:
    from app.domain.review import ReviewStatus
    from tests.fixtures.monitoring_node import (
        OFFERING,
        PRODUCT,
        build,
        call,
        function_responses,
        interrupts,
        reply,
        text,
    )

    harness = await build(review_scopes=("interest_rate",))
    harness.model.play(
        call("run_tariff_monitoring", product=PRODUCT, offering_id=OFFERING)
    )
    ((interrupt_id, _),) = interrupts(await harness.turn(text("monitor")))
    # A newer run's candidate replaces this one while the question is open.
    for task in harness.reviews.tasks.values():
        harness.reviews._set(task.id, status=ReviewStatus.SUPERSEDED)

    events = await harness.turn(
        reply(
            interrupt_id,
            {"decision_type": "select_candidate", "candidate_id": "candidate-1"},
        )
    )

    result = function_responses(events, "run_tariff_monitoring")[0]
    assert result["answers_not_applied"] == ["overdraft · interest rate (superseded)"]
    assert "Not applied" in result["message"]
    assert harness.decisions.applied == []


@pytest.mark.asyncio
async def test_p5_a_conflict_while_applying_is_not_a_tool_error() -> None:
    from app.domain.models import OfferingId
    from app.domain.review import ReviewDecision, ReviewDecisionType, ReviewStatus
    from app.repositories.reviews import ReviewConflictError
    from app.services.review_resolution import ReviewResolutionService
    from tests.fixtures.monitoring_node import Reviews, Runs, queued_run, review_task

    runs, reviews = Runs(), Reviews()
    run = runs.add(queued_run())
    task = review_task(run, OfferingId.OVERDRAFT, "interest_rate")
    reviews.tasks[task.id] = task

    class Racing:
        async def apply(self, review_id, decision, *, reviewer):
            reviews._set(review_id, status=ReviewStatus.SUPERSEDED)
            raise ReviewConflictError("review is no longer pending")

    service = ReviewResolutionService(runs=runs, reviews=reviews, decisions=Racing())

    result = await service.apply(
        task,
        ReviewDecision(decision_type=ReviewDecisionType.REJECT_ALL),
        reviewer="cli-user",
    )

    assert result.status is ReviewStatus.SUPERSEDED
