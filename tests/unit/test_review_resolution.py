from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from app.domain.models import OfferingId, ProductType
from app.domain.monitoring import MonitoringRun, RunCommand, RunStatus, RunTrigger
from app.domain.review import (
    ReviewCandidate,
    ReviewDecision,
    ReviewDecisionInput,
    ReviewDecisionType,
    ReviewReason,
    ReviewStatus,
    ReviewTask,
)
from app.services.review_resolution import (
    ReviewInputRejected,
    ReviewResolutionService,
    build_review_view,
    terminal_review_status,
)

NOW = datetime(2026, 9, 25, tzinfo=UTC)


def _run(
    status: RunStatus = RunStatus.AWAITING_REVIEW, **summary: int
) -> MonitoringRun:
    return MonitoringRun(
        id=uuid4(),
        command=RunCommand(
            product=ProductType.CONSUMER_LOAN,
            offering_id=OfferingId.OVERDRAFT,
            trigger=RunTrigger.ADK,
        ),
        status=status,
        queued_at=NOW,
        started_at=NOW,
        completed_at=NOW if status.is_terminal else None,
        summary={"succeeded": 0, "failed": 0, **summary},
    )


def _review(
    run: MonitoringRun,
    scope: str = "interest_rate",
    *,
    reason: ReviewReason = ReviewReason.OFFICIAL_SOURCE_CONFLICT,
    candidates: tuple[ReviewCandidate, ...] | None = None,
    order: int = 0,
) -> ReviewTask:
    review_id = uuid4()
    return ReviewTask(
        id=review_id,
        idempotency_key=f"review:{review_id}",
        run_id=run.id,
        offering_execution_id=uuid4(),
        snapshot_id=uuid4(),
        product=ProductType.CONSUMER_LOAN,
        offering_id=OfferingId.OVERDRAFT,
        reason=reason,
        issue_scope=scope,
        candidates=(
            candidates
            if candidates is not None
            else (
                ReviewCandidate(
                    candidate_id="candidate-1",
                    field=scope,
                    value="12.5%",
                    evidence_references=("evidence-1",),
                ),
            )
        ),
        evidence={
            "items": [
                {
                    "evidence_id": "evidence-1",
                    "content": "Official rate is 12.5%",
                    "locator": {
                        "source_url": "https://ameriabank.am/rates.pdf",
                        "pdf_page": 2,
                    },
                }
            ]
        },
        created_at=NOW + timedelta(seconds=order),
        updated_at=NOW,
    )


class _Runs:
    def __init__(self, run: MonitoringRun) -> None:
        self.run = run
        self.audits: list[tuple[str, dict]] = []
        self.finished: list[tuple[RunStatus, dict]] = []

    async def get(self, run_id: UUID):
        return self.run if run_id == self.run.id else None

    async def list_by_status(self, status, *, limit=100):
        return (self.run,) if self.run.status is status else ()

    async def finish_after_review(self, run_id, status, *, summary):
        if self.run.status is not RunStatus.AWAITING_REVIEW:
            raise RuntimeError("cannot finish after review")
        self.finished.append((status, summary))
        self.run = self.run.model_copy(
            update={"status": status, "summary": summary, "completed_at": NOW}
        )
        return self.run

    async def record_audit(self, run_id, event_type, **kwargs):
        self.audits.append((event_type, kwargs))


class _Reviews:
    def __init__(self, *tasks: ReviewTask) -> None:
        self.tasks = {task.id: task for task in tasks}

    async def get(self, review_id: UUID):
        return self.tasks.get(review_id)

    async def list(self, *, status=None, run_id=None, limit=100, offset=0, **kwargs):
        return tuple(
            task
            for task in self.tasks.values()
            if (status is None or task.status is status)
            and (run_id is None or task.run_id == run_id)
        )[offset : offset + limit]

    async def supersede(self, review_id: UUID):
        self.tasks[review_id] = self.tasks[review_id].model_copy(
            update={"status": ReviewStatus.SUPERSEDED}
        )
        return self.tasks[review_id]


class _Decisions:
    def __init__(self, reviews: _Reviews, *, fail: Exception | None = None) -> None:
        self.reviews = reviews
        self.calls: list[tuple[UUID, ReviewDecision, str]] = []
        self.fail = fail

    async def apply(self, review_id, decision, *, reviewer):
        self.calls.append((review_id, decision, reviewer))
        if self.fail is not None:
            raise self.fail
        status = (
            ReviewStatus.REJECTED
            if decision.decision_type is ReviewDecisionType.REJECT_ALL
            else ReviewStatus.APPROVED
        )
        self.reviews.tasks[review_id] = self.reviews.tasks[review_id].model_copy(
            update={
                "status": status,
                "reviewer": reviewer,
                "decision": decision,
                "decided_at": NOW,
            }
        )
        return self.reviews.tasks[review_id]


def _service(run: MonitoringRun, *tasks: ReviewTask, fail: Exception | None = None):
    runs = _Runs(run)
    reviews = _Reviews(*tasks)
    decisions = _Decisions(reviews, fail=fail)
    return (
        ReviewResolutionService(runs=runs, reviews=reviews, decisions=decisions),
        runs,
        reviews,
        decisions,
    )


# --- validate ----------------------------------------------------------------------


def test_indefinite_term_candidate_is_accepted() -> None:
    run = _run()
    task = _review(
        run,
        "term",
        candidates=(
            ReviewCandidate(
                candidate_id="term-text",
                field="term",
                value="Indefinite term (until requested back)",
                evidence_references=("evidence-1",),
            ),
        ),
    )
    service, *_ = _service(run, task)

    decision = service.validate(
        task,
        ReviewDecisionInput(decision_type="select_candidate", candidate_id="term-text"),
    )

    assert decision.candidate_id == "term-text"


def test_invalid_term_candidate_is_rejected_before_anything_is_written() -> None:
    run = _run()
    task = _review(
        run,
        "term",
        candidates=(
            ReviewCandidate(
                candidate_id="unknown-term",
                field="term",
                value="Some indefinite term",
                evidence_references=("evidence-1",),
            ),
        ),
    )
    service, runs, _, decisions = _service(run, task)

    with pytest.raises(ReviewInputRejected) as rejected:
        service.validate(
            task,
            ReviewDecisionInput(
                decision_type="select_candidate", candidate_id="unknown-term"
            ),
        )

    assert rejected.value.reason_code == "review.candidate_value_invalid"
    assert rejected.value.input_format["field"] == "term"
    assert decisions.calls == []
    assert runs.audits == []


def test_on_demand_text_override_is_parsed_against_the_cited_passage() -> None:
    run = _run()
    task = _review(
        run, "term", reason=ReviewReason.MISSING_REQUIRED_FIELD, candidates=()
    )
    service, *_ = _service(run, task)

    decision = service.validate(
        task,
        ReviewDecisionInput(
            decision_type="override",
            override_value="Indefinite term (until requested back)",
            reason="The official source says the term ends on demand.",
            evidence_reference="evidence-1",
        ),
    )

    assert decision.decision_type is ReviewDecisionType.OVERRIDE
    assert not isinstance(decision.override_value, str)


def test_plain_words_override_becomes_the_structured_value() -> None:
    run = _run()
    task = _review(
        run, "repayment", reason=ReviewReason.MISSING_REQUIRED_FIELD, candidates=()
    )
    service, *_ = _service(run, task)

    decision = service.validate(
        task,
        ReviewDecisionInput(
            decision_type="override",
            override_value="Monthly annuity",
            reason="The official source states monthly annuity payments.",
            evidence_reference="evidence-1",
        ),
    )

    assert decision.override_value == [
        {"value": {"method": "Monthly annuity"}, "conditions": []}
    ]


def test_override_rejection_repeats_the_accepted_format() -> None:
    run = _run()
    task = _review(
        run, "interest_rate", reason=ReviewReason.MISSING_REQUIRED_FIELD, candidates=()
    )
    service, *_ = _service(run, task)

    with pytest.raises(ReviewInputRejected) as rejected:
        service.validate(
            task,
            ReviewDecisionInput(
                decision_type="override",
                override_value="quite high",
                reason="The reviewer typed words instead of a rate.",
                evidence_reference="evidence-1",
            ),
        )

    assert rejected.value.reason_code == "review.override_value_invalid"
    assert "15-21%" in rejected.value.message
    assert rejected.value.as_payload()["input_format"]["field"] == "interest_rate"


def test_candidate_with_conditions_requires_an_override() -> None:
    run = _run()
    task = _review(
        run,
        candidates=(
            ReviewCandidate(
                candidate_id="conditional",
                field="interest_rate",
                value="12.5%",
                evidence_references=("evidence-1",),
                conditions={"conditions": ["for salary clients"]},
            ),
        ),
    )
    service, *_ = _service(run, task)

    with pytest.raises(ReviewInputRejected) as rejected:
        service.validate(
            task,
            ReviewDecisionInput(
                decision_type="select_candidate", candidate_id="conditional"
            ),
        )

    assert rejected.value.reason_code == "review.candidate_requires_override"


@pytest.mark.parametrize(
    ("reply", "message"),
    [
        (
            ReviewDecisionInput(decision_type="approve"),
            "not allowed for this review",
        ),
        (
            ReviewDecisionInput(decision_type="select_candidate", candidate_id="nope"),
            "not part of this review",
        ),
        (
            ReviewDecisionInput(
                decision_type="override",
                override_value="13%",
                reason="typed",
                evidence_reference="evidence-elsewhere",
            ),
            "cited evidence is not part of this review",
        ),
        (
            ReviewDecisionInput(decision_type="override", override_value="13%"),
            "override requires value, reason, and evidence reference",
        ),
    ],
)
def test_out_of_scope_or_incoherent_replies_are_rejected(reply, message) -> None:
    run = _run()
    task = _review(run)  # official_source_conflict: approve is not allowed
    service, *_ = _service(run, task)

    with pytest.raises(ReviewInputRejected) as rejected:
        service.validate(task, reply)

    assert rejected.value.reason_code == "review.invalid_input"
    assert message in rejected.value.message


def test_decision_input_ignores_extra_keys_and_blank_optional_values() -> None:
    reply = ReviewDecisionInput.model_validate(
        {"review_id": "ignored", "decision_type": "reject_all", "candidate_id": ""}
    )

    assert reply.to_decision() == ReviewDecision(
        decision_type=ReviewDecisionType.REJECT_ALL
    )


# --- apply ---------------------------------------------------------------------


@pytest.mark.asyncio
async def test_apply_records_attempt_and_is_idempotent() -> None:
    run = _run()
    task = _review(run)
    service, runs, _, decisions = _service(run, task)
    decision = ReviewDecision(
        decision_type=ReviewDecisionType.SELECT_CANDIDATE, candidate_id="candidate-1"
    )

    first = await service.apply(task, decision, reviewer="cli-user")
    second = await service.apply(task, decision, reviewer="cli-user")

    assert first.status is ReviewStatus.APPROVED
    assert second.status is ReviewStatus.APPROVED
    assert len(decisions.calls) == 1
    assert decisions.calls[0][2] == "cli-user"
    assert [event for event, _ in runs.audits] == ["review.resume_attempt"]


@pytest.mark.asyncio
async def test_reject_all_supersedes_the_other_pending_reviews_of_the_run() -> None:
    run = _run()
    first, second = _review(run), _review(run, "fees", order=1)
    service, _, reviews, _ = _service(run, first, second)

    await service.apply(
        first,
        ReviewDecision(decision_type=ReviewDecisionType.REJECT_ALL),
        reviewer="cli-user",
    )

    assert reviews.tasks[first.id].status is ReviewStatus.REJECTED
    assert reviews.tasks[second.id].status is ReviewStatus.SUPERSEDED
    assert await service.pending(run.id) == ()


@pytest.mark.asyncio
async def test_decision_service_rejection_becomes_a_reask_and_is_audited() -> None:
    run = _run()
    task = _review(run)
    service, runs, reviews, _ = _service(
        run, task, fail=ValueError("candidate snapshot is no longer reviewable")
    )

    with pytest.raises(ReviewInputRejected) as rejected:
        await service.apply(
            task,
            ReviewDecision(
                decision_type=ReviewDecisionType.SELECT_CANDIDATE,
                candidate_id="candidate-1",
            ),
            reviewer="cli-user",
        )

    assert rejected.value.reason_code == "review.decision_failed"
    assert "no longer reviewable" in rejected.value.message
    assert reviews.tasks[task.id].status is ReviewStatus.PENDING
    assert [event for event, _ in runs.audits] == [
        "review.resume_attempt",
        "review.resume_failed",
    ]


@pytest.mark.asyncio
async def test_pending_is_ordered_by_creation() -> None:
    run = _run()
    later, earlier = _review(run, "fees", order=5), _review(run, order=1)
    service, *_ = _service(run, later, earlier)

    assert [task.id for task in await service.pending(run.id)] == [
        earlier.id,
        later.id,
    ]


# --- complete_run ----------------------------------------------------------------


@pytest.mark.asyncio
async def test_approved_review_completes_the_run_as_succeeded() -> None:
    run = _run()
    task = _review(run)
    service, runs, *_ = _service(run, task)
    await service.apply(
        task,
        ReviewDecision(
            decision_type=ReviewDecisionType.SELECT_CANDIDATE,
            candidate_id="candidate-1",
        ),
        reviewer="cli-user",
    )

    completed = await service.complete_run(run.id)

    assert completed.status is RunStatus.SUCCEEDED
    assert completed.summary["reviews_approved"] == 1
    assert completed.summary["reviews_rejected"] == 0
    assert runs.audits[-1][0] == "review.approved"


@pytest.mark.asyncio
async def test_rejection_after_a_prior_success_is_partial() -> None:
    run = _run(succeeded=1)
    task = _review(run)
    service, runs, *_ = _service(run, task)
    await service.apply(
        task,
        ReviewDecision(decision_type=ReviewDecisionType.REJECT_ALL),
        reviewer="cli-user",
    )

    completed = await service.complete_run(run.id)

    assert completed.status is RunStatus.PARTIAL_SUCCESS
    assert runs.audits[-1][0] == "review.rejected"


@pytest.mark.asyncio
async def test_all_rejected_without_prior_success_fails() -> None:
    run = _run()
    first, second = _review(run), _review(run, "fees", order=1)
    service, *_ = _service(run, first, second)
    await service.apply(
        first,
        ReviewDecision(decision_type=ReviewDecisionType.REJECT_ALL),
        reviewer="cli-user",
    )

    completed = await service.complete_run(run.id)

    assert completed.status is RunStatus.FAILED
    # The superseded sibling activated nothing either.
    assert completed.summary["reviews_rejected"] == 2


@pytest.mark.asyncio
async def test_complete_run_waits_while_a_review_is_pending() -> None:
    run = _run()
    service, runs, *_ = _service(run, _review(run))

    unchanged = await service.complete_run(run.id)

    assert unchanged.status is RunStatus.AWAITING_REVIEW
    assert runs.finished == []


@pytest.mark.asyncio
async def test_paused_run_without_any_review_fails_closed() -> None:
    run = _run()
    service, *_ = _service(run)

    completed = await service.complete_run(run.id)

    assert completed.status is RunStatus.FAILED
    assert completed.summary["review_link_missing"] is True


@pytest.mark.asyncio
async def test_complete_run_leaves_a_terminal_run_alone() -> None:
    run = _run(RunStatus.SUCCEEDED)
    service, runs, *_ = _service(run)

    assert (await service.complete_run(run.id)).status is RunStatus.SUCCEEDED
    assert runs.finished == []


@pytest.mark.asyncio
async def test_startup_check_closes_only_fully_decided_runs() -> None:
    run = _run()
    task = _review(run).model_copy(
        update={
            "status": ReviewStatus.APPROVED,
            "reviewer": "cli-user",
            "decision": ReviewDecision(decision_type=ReviewDecisionType.APPROVE),
            "decided_at": NOW,
        }
    )
    service, *_ = _service(run, task)

    assert await service.complete_runs_without_pending_reviews() == 1


# --- reject_all_pending: the API abort route ------------------------------------


@pytest.mark.asyncio
async def test_reject_all_pending_rejects_every_review_and_closes_the_run() -> None:
    run = _run()
    service, _, reviews, decisions = _service(
        run, _review(run), _review(run, "fees", order=1)
    )

    result = await service.reject_all_pending(reviewer="api-admin")

    assert result["aborted_review_count"] == 2
    assert result["aborted_runs"] == [
        {"run_id": str(run.id), "status": "failed", "review_count": 2}
    ]
    assert result["failed_runs"] == []
    assert all(task.status.is_terminal for task in reviews.tasks.values())
    assert decisions.calls[0][2] == "api-admin"


@pytest.mark.asyncio
async def test_reject_all_pending_reports_a_failing_run_and_keeps_going() -> None:
    run = _run()
    service, *_ = _service(run, _review(run), fail=LookupError("snapshot gone"))

    result = await service.reject_all_pending(reviewer="api-admin")

    assert result["aborted_review_count"] == 0
    assert result["failed_runs"] == [{"run_id": str(run.id), "reason": "LookupError"}]


# --- views -------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("reason", "expected"),
    [
        (
            ReviewReason.LARGE_RATE_CHANGE,
            {
                ReviewDecisionType.APPROVE,
                ReviewDecisionType.REJECT_ALL,
                ReviewDecisionType.OVERRIDE,
            },
        ),
        (
            ReviewReason.OFFICIAL_SOURCE_CONFLICT,
            {
                ReviewDecisionType.SELECT_CANDIDATE,
                ReviewDecisionType.REJECT_ALL,
                ReviewDecisionType.OVERRIDE,
            },
        ),
        (
            ReviewReason.OCR_EVIDENCE,
            {
                ReviewDecisionType.APPROVE,
                ReviewDecisionType.REJECT_ALL,
                ReviewDecisionType.OVERRIDE,
            },
        ),
        (
            ReviewReason.SOURCE_APPLICABILITY,
            {ReviewDecisionType.REJECT_ALL, ReviewDecisionType.OVERRIDE},
        ),
        (
            ReviewReason.MISSING_REQUIRED_FIELD,
            {ReviewDecisionType.REJECT_ALL, ReviewDecisionType.OVERRIDE},
        ),
    ],
)
def test_review_view_is_bounded_and_reason_specific(reason, expected) -> None:
    run = _run()
    task = _review(run, reason=reason).model_copy(
        update={
            "evidence": {
                "items": [
                    {
                        "evidence_id": "ev_1234567890abcdef12345678",
                        "document_id": "document-1",
                        "section": "Rates",
                        "content": "x" * 2000,
                        "locator": {
                            "source_url": "https://ameriabank.am/rates.pdf",
                            "source_type": "pdf",
                            "pdf_page": 4,
                        },
                    }
                ]
            },
        }
    )

    view = build_review_view(task)

    assert set(view.allowed_decisions) == expected
    assert view.offering_id is OfferingId.OVERDRAFT
    assert view.evidence[0].page == 4
    assert view.evidence[0].section == "Rates"
    assert len(view.evidence[0].excerpt) == 1500


def test_review_view_prioritizes_field_passages_before_the_limit() -> None:
    run = _run()
    context = [
        {
            "evidence_id": f"context-{index}",
            "content": "Nominal interest rate 15%",
            "locator": {"source_url": "https://example.com/r.pdf"},
        }
        for index in range(25)
    ]
    term = {
        "evidence_id": "term-after-context",
        "content": "Row: Term (months) | Indefinite term (until requested back)",
        "locator": {"source_url": "https://example.com/term.pdf"},
    }
    task = _review(
        run, "term", reason=ReviewReason.MISSING_REQUIRED_FIELD, candidates=()
    ).model_copy(update={"evidence": {"items": [*context, term]}})

    view = build_review_view(task)

    assert len(view.evidence) == 20
    assert view.evidence[0].evidence_id == "term-after-context"


@pytest.mark.parametrize(
    ("approved", "rejected", "prior_succeeded", "prior_failed", "expected"),
    [
        (1, 0, 0, 0, RunStatus.SUCCEEDED),
        (1, 0, 0, 1, RunStatus.PARTIAL_SUCCESS),
        (0, 1, 1, 0, RunStatus.PARTIAL_SUCCESS),
        (0, 1, 0, 0, RunStatus.FAILED),
    ],
)
def test_terminal_review_status(
    approved, rejected, prior_succeeded, prior_failed, expected
) -> None:
    assert (
        terminal_review_status(
            approved=approved,
            rejected=rejected,
            prior_succeeded=prior_succeeded,
            prior_failed=prior_failed,
        )
        is expected
    )


@pytest.mark.asyncio
async def test_abort_api_requires_configured_admin_token() -> None:
    from types import SimpleNamespace

    import httpx
    from fastapi import FastAPI
    from pydantic import SecretStr

    from app.api.routes import router
    from app.config.models import HitlSettings

    class _AbortService:
        def __init__(self) -> None:
            self.reviewers = []

        async def reject_all_pending(self, *, reviewer):
            self.reviewers.append(reviewer)
            return {"aborted_runs": [], "failed_runs": [], "aborted_review_count": 0}

    app = FastAPI()
    app.state.review_resolution = _AbortService()
    app.state.settings = SimpleNamespace(
        hitl=HitlSettings(review_admin_token=SecretStr("secret-token"))
    )
    app.include_router(router)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        missing = await client.post("/api/v1/reviews/abort-pending")
        wrong = await client.post(
            "/api/v1/reviews/abort-pending", headers={"X-Review-Admin-Token": "wrong"}
        )
        allowed = await client.post(
            "/api/v1/reviews/abort-pending",
            headers={"X-Review-Admin-Token": "secret-token"},
        )
    assert missing.status_code == 403
    assert wrong.status_code == 403
    assert allowed.status_code == 200
    assert allowed.json()["aborted_review_count"] == 0
    assert app.state.review_resolution.reviewers == ["api-admin"]
    app.state.settings = SimpleNamespace(hitl=HitlSettings())
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        unconfigured = await client.post(
            "/api/v1/reviews/abort-pending",
            headers={"X-Review-Admin-Token": "secret-token"},
        )
    assert unconfigured.status_code == 503
