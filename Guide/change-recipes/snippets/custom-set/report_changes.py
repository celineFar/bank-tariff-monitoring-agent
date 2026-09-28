from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.domain.models import OfferingId, ProductType
from app.domain.monitoring import OfferingRunStatus, SnapshotChange, SnapshotChangeSet
from app.services.monitoring_node import _change_lines

NOW = datetime(2026, 9, 28, tzinfo=UTC)
RUN = SimpleNamespace(
    id=uuid4(),
    command=SimpleNamespace(product=ProductType.CONSUMER_LOAN),
    queued_at=NOW,
)


def _set(run_id):
    return SnapshotChangeSet(
        id=uuid4(),
        run_id=run_id,
        product=ProductType.CONSUMER_LOAN,
        offering_id=OfferingId.OVERDRAFT,
        current_snapshot_id=uuid4(),
        created_at=NOW,
        changes=(
            SnapshotChange(
                field="interest_rate", previous_display="21", current_display="23"
            ),
        ),
    )


class _Changes:
    def __init__(self, *sets):
        self.sets = sets

    async def list_changes(self, **kwargs):
        return self.sets


def _execution(status=OfferingRunStatus.SUCCEEDED):
    return SimpleNamespace(status=status, offering_id=OfferingId.OVERDRAFT)


@pytest.mark.asyncio
async def test_this_runs_changes_become_report_lines() -> None:
    lines = await _change_lines(
        _Changes(_set(RUN.id), _set(uuid4())), RUN, _execution()
    )
    assert lines == ("interest_rate: 21 -> 23",)


@pytest.mark.asyncio
async def test_no_lines_without_a_reader_or_for_a_review() -> None:
    assert await _change_lines(None, RUN, _execution()) == ()
    review = _execution(OfferingRunStatus.CANDIDATE_REVIEW)
    assert await _change_lines(_Changes(_set(RUN.id)), RUN, review) == ()
