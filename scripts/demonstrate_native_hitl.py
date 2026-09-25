"""Render deterministic native-HITL request payloads for reviewer training.

This demonstration does not persist reviews or pause a conversation. It builds the
same bounded payload the monitoring node puts on each ``RequestInput`` and the CLI
renders: the reason-specific review view, the entry format and the position.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from uuid import UUID

from app.domain.models import OfferingId, ProductType
from app.domain.review import ReviewCandidate, ReviewReason, ReviewStatus, ReviewTask
from app.services.review_resolution import (
    build_review_view,
    review_input_format,
)

RUN_ID = UUID("10000000-0000-0000-0000-000000000001")
EXECUTION_ID = UUID("20000000-0000-0000-0000-000000000001")
SNAPSHOT_ID = UUID("30000000-0000-0000-0000-000000000001")
NOW = datetime(2026, 9, 21, 12, 0, tzinfo=UTC)


def _evidence(
    evidence_id: str,
    *,
    source_url: str,
    source_type: str,
    content: str,
    document_id: str,
    section: str,
    pdf_page: int | None = None,
) -> dict[str, object]:
    locator: dict[str, object] = {
        "source_url": source_url,
        "source_type": source_type,
    }
    if pdf_page is not None:
        locator["pdf_page"] = pdf_page
    return {
        "evidence_id": evidence_id,
        "document_id": document_id,
        "section": section,
        "content": content,
        "locator": locator,
    }


def large_change_review() -> ReviewTask:
    """Return an evidence-backed rate change over the three-point threshold."""
    evidence_id = "ev_large_change_pdf_page_4"
    return ReviewTask(
        id=UUID("40000000-0000-0000-0000-000000000001"),
        idempotency_key="demo:large-change:mortgage-primary:nominal-rate",
        run_id=RUN_ID,
        offering_execution_id=EXECUTION_ID,
        snapshot_id=SNAPSHOT_ID,
        product=ProductType.MORTGAGE,
        offering_id=OfferingId.MORTGAGE_PRIMARY,
        reason=ReviewReason.LARGE_RATE_CHANGE,
        issue_scope="nominal_interest_rate",
        candidates=(
            ReviewCandidate(
                candidate_id="candidate:new-pdf-rate",
                field="nominal_interest_rate",
                value={"minimum": "13.5", "maximum": "13.5", "unit": "percent"},
                evidence_references=(evidence_id,),
                conditions={"previous_accepted": "9.9", "change_points": "3.6"},
            ),
        ),
        evidence={
            "items": [
                _evidence(
                    evidence_id,
                    source_url="https://ameriabank.am/userfiles/file/Rates/demo-mortgage.pdf",
                    source_type="pdf",
                    content="Nominal annual interest rate: 13.5%.",
                    document_id="demo-mortgage-rates-pdf",
                    section="Interest rates",
                    pdf_page=4,
                )
            ]
        },
        status=ReviewStatus.PENDING,
        created_at=NOW,
        updated_at=NOW,
    )


def source_conflict_review() -> ReviewTask:
    """Return distinct PDF and webpage candidates for the same tariff field."""
    pdf_evidence = "ev_conflict_pdf_page_3"
    web_evidence = "ev_conflict_web_rates"
    return ReviewTask(
        id=UUID("40000000-0000-0000-0000-000000000002"),
        idempotency_key="demo:source-conflict:mortgage-primary:application-fee",
        run_id=RUN_ID,
        offering_execution_id=EXECUTION_ID,
        snapshot_id=SNAPSHOT_ID,
        product=ProductType.MORTGAGE,
        offering_id=OfferingId.MORTGAGE_PRIMARY,
        reason=ReviewReason.OFFICIAL_SOURCE_CONFLICT,
        issue_scope="application_fee",
        candidates=(
            ReviewCandidate(
                candidate_id="candidate:pdf-fee",
                field="application_fee",
                value={"amount": "10000", "currency": "AMD"},
                evidence_references=(pdf_evidence,),
                conditions={"source": "official_pdf"},
            ),
            ReviewCandidate(
                candidate_id="candidate:web-fee",
                field="application_fee",
                value={"amount": "15000", "currency": "AMD"},
                evidence_references=(web_evidence,),
                conditions={"source": "official_webpage"},
            ),
        ),
        evidence={
            "items": [
                _evidence(
                    pdf_evidence,
                    source_url="https://ameriabank.am/userfiles/file/Rates/demo-mortgage.pdf",
                    source_type="pdf",
                    content="Loan application review fee: AMD 10,000.",
                    document_id="demo-mortgage-summary-pdf",
                    section="Fees",
                    pdf_page=3,
                ),
                _evidence(
                    web_evidence,
                    source_url="https://ameriabank.am/en/personal/loans/mortgage/demo",
                    source_type="webpage",
                    content="Application review fee — AMD 15,000.",
                    document_id="demo-mortgage-webpage",
                    section="Tariffs and fees",
                ),
            ]
        },
        status=ReviewStatus.PENDING,
        created_at=NOW,
        updated_at=NOW,
    )


def build_demo_payload(scenario: str) -> str:
    tasks = {
        "large-change": (large_change_review(),),
        "source-conflict": (source_conflict_review(),),
        "all": (large_change_review(), source_conflict_review()),
    }[scenario]
    payloads = [
        {
            "kind": "tariff_review",
            "view": build_review_view(task).model_dump(mode="json"),
            "input_format": review_input_format(task.issue_scope),
            "position": position,
            "total": len(tasks),
            "attempt": 1,
        }
        for position, task in enumerate(tasks, start=1)
    ]
    return json.dumps(payloads, indent=2, ensure_ascii=False)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Render bounded native tariff-review request examples."
    )
    parser.add_argument(
        "--scenario",
        choices=("large-change", "source-conflict", "all"),
        default="all",
    )
    args = parser.parse_args()
    print(build_demo_payload(args.scenario))


if __name__ == "__main__":
    main()
