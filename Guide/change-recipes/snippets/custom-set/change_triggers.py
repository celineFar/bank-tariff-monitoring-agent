from uuid import uuid4

from app.domain.models import OfferingId, ProductType
from app.domain.monitoring import SnapshotStatus
from app.domain.review import ReviewReason
from app.services.monitoring_pipeline import _review_tasks
from app.services.snapshot_lifecycle import (
    build_snapshot_attempt,
    detect_fee_changes,
    detect_large_amount_changes,
)
from tests.unit.test_snapshot_lifecycle import _result, _snapshot


def _amount(low, high, currency="AMD"):
    return {
        "loan_amount": {
            "status": "found",
            "value": [
                {
                    "value": {
                        "type": "absolute",
                        "range": {"min": low, "max": high, "currency": currency},
                    },
                    "conditions": [],
                }
            ],
        }
    }


def _fees(*amounts):
    return {
        "fees": {
            "status": "found",
            "value": [
                {
                    "description": f"fee {i}",
                    "scope": "product",
                    "amount": a,
                    "currency": "AMD",
                    "rate_pct": None,
                    "conditions": [],
                }
                for i, a in enumerate(amounts)
            ],
        }
    }


def test_amount_move_above_20_percent_is_flagged() -> None:
    (signal,) = detect_large_amount_changes(
        _amount("300000", "10000000"), _amount("300000", "13000000")
    )
    assert signal["reason"] == "large_amount_change"
    assert "max changed by 30%" in signal["failed_checks"][0]


def test_amount_move_of_20_percent_or_less_is_not() -> None:
    assert (
        detect_large_amount_changes(
            _amount("300000", "10000000"), _amount("300000", "12000000")
        )
        == ()
    )


def test_credit_limit_inside_details_is_checked() -> None:
    before = {
        "details": {
            "type": "overdraft",
            "credit_limit": {
                "status": "found",
                "value": [
                    {
                        "type": "absolute",
                        "range": {"min": "50000", "max": "1000000", "currency": "AMD"},
                    }
                ],
            },
        }
    }
    after = {
        "details": {
            "type": "overdraft",
            "credit_limit": {
                "status": "found",
                "value": [
                    {
                        "type": "absolute",
                        "range": {"min": "50000", "max": "3000000", "currency": "AMD"},
                    }
                ],
            },
        }
    }
    (signal,) = detect_large_amount_changes(before, after)
    assert signal["issue_scope"] == "credit_limit"


def test_any_fee_number_change_is_flagged_but_rewording_is_not() -> None:
    assert detect_fee_changes(_fees("5000"), _fees("5000")) == ()
    reworded = _fees("5000")
    reworded["fees"]["value"][0]["description"] = "Loan processing fee"
    assert detect_fee_changes(_fees("5000"), reworded) == ()
    (signal,) = detect_fee_changes(_fees("5000"), _fees("7000"))
    assert signal["reason"] == "fee_change"


def test_fee_change_becomes_a_pending_review_task() -> None:
    previous = _snapshot(_fees("5000"))
    snapshot = build_snapshot_attempt(
        run_id=uuid4(),
        offering_execution_id=uuid4(),
        product=ProductType.CONSUMER_LOAN,
        offering_id=OfferingId.CONSUMER_STANDARD,
        result=_result(),
        previous_accepted_snapshot_id=previous.id,
        previous_accepted_snapshot=previous,
    )
    assert snapshot.status is SnapshotStatus.REVIEW_REQUIRED
    (task,) = _review_tasks(snapshot)
    assert task.reason is ReviewReason.FEE_CHANGE
