"""Captures from the 2026-09-27 live run, for the first-iteration regression tests.

The files live in fix-process/1st-iteration-fixes/data/ (see that plan, Phase 0).
Nothing here calls a model.
"""

from __future__ import annotations

import gzip
import json
from datetime import datetime
from functools import cache
from pathlib import Path
from uuid import UUID, uuid4

from app.domain.monitoring import SnapshotAttempt, SnapshotStatus
from app.domain.semantic_extraction import SemanticExtractionResult
from app.services.snapshot_lifecycle import canonical_sha256, canonical_tariff_payload

DATA = Path(__file__).resolve().parents[2] / "fix-process/1st-iteration-fixes/data"


@cache
def _snapshots() -> dict[str, dict]:
    with gzip.open(DATA / "snapshots_2026-09-27.json.gz", "rt") as handle:
        return {item["offering_id"]: item for item in json.load(handle)}


def captured_extraction(offering_id: str) -> SemanticExtractionResult:
    return SemanticExtractionResult.model_validate(
        _snapshots()[offering_id]["semantic_extraction"]
    )


def captured_accepted_snapshot(offering_id: str) -> SnapshotAttempt:
    """A published offering's snapshot as the projector receives it."""
    raw = _snapshots()[offering_id]
    if raw["status"] != "accepted":
        raise ValueError(f"{offering_id} was not accepted on 2026-09-27")
    extraction = captured_extraction(offering_id)
    payload = canonical_tariff_payload(extraction.loan_product)
    accepted_at = datetime.fromisoformat(raw["accepted_at"])
    return SnapshotAttempt(
        id=UUID(raw["snapshot_id"]),
        run_id=uuid4(),
        offering_execution_id=uuid4(),
        product=extraction.product,
        offering_id=offering_id,
        status=SnapshotStatus.ACCEPTED,
        normalized_tariff=payload,
        evidence=tuple(
            item.model_dump(mode="json") for item in extraction.evidence_catalog
        ),
        semantic_extraction=raw["semantic_extraction"],
        validation={"accepted": True},
        canonical_sha256=canonical_sha256(payload),
        created_at=accepted_at,
        accepted_at=accepted_at,
    )


def commercial_raw_answer(attempt: int) -> str:
    """One of the two answers that failed the response schema for Commercial."""
    return (DATA / f"commercial_documents_and_details_raw_{attempt}.json").read_text()


@cache
def captured_reviews() -> tuple[dict, ...]:
    return tuple(json.loads((DATA / "reviews_2026-09-27.json").read_text()))
