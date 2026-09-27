"""RRS01: the interpretation case set, replayed from recorded interpretations.

The recordings come from the live interpreter (`scripts/record_interpretations.py`);
this test checks that code - validation, state, clarification options - turns
them into the expected resolutions, offline.
"""

from __future__ import annotations

import pytest

from app.config import load_seed_catalog
from app.services.intent_resolution import RequestResolver
from tests.fixtures.interpretation_cases import INTERPRETATION_CASES
from tests.fixtures.interpretation_scoring import run_case
from tests.fixtures.recorded_interpretations import RecordedInterpreter

# Cases the live interpreter answered wrongly in the last recording, with why.
KNOWN_LIVE_MISSES: dict[str, str] = {}


@pytest.mark.parametrize(
    "case", INTERPRETATION_CASES, ids=[case.case_id for case in INTERPRETATION_CASES]
)
@pytest.mark.asyncio
async def test_recorded_case_resolves_as_expected(case, request) -> None:
    if case.case_id in KNOWN_LIVE_MISSES:
        request.applymarker(
            pytest.mark.xfail(strict=True, reason=KNOWN_LIVE_MISSES[case.case_id])
        )
    resolver = RequestResolver(
        load_seed_catalog(), interpreter=RecordedInterpreter(case_id=case.case_id)
    )
    mismatches = await run_case(resolver, case)
    assert not mismatches, [f"t{m.turn} {m.check}: {m.detail}" for m in mismatches]
