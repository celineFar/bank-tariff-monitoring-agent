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
