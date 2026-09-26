"""R04 and R05 on the dev database, read-only.

    uv run python fix-process/reviews/scenarios/run_stored_reviews.py

- **R04.** The Overdraft reviews stored before this fix (`evidence.items`, a copy of
  the snapshot's catalog) still build a pause view and a terminal display, and a
  decision still resolves an evidence reference from `items`. For comparison, the
  view the code before this fix built (commit `be049e5`) is rebuilt from git.
- **R05.** `get_current_tariffs` and `get_tariff_history` payload sizes for the
  accepted Overdraft snapshot, before (`model_dump`) and after.

The connection is opened with `default_transaction_read_only`; nothing is written.
The password is read from the database container's environment, in memory only.
The report goes to `results/R04-R05-stored.json`.
"""

from __future__ import annotations

import asyncio
import importlib.util
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "fix-process" / "semantic_extraction" / "survey"))
sys.path.insert(0, str(ROOT))

import replay  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402

from app.domain.intent import (  # noqa: E402
    FreshnessStatus,
    HistoryQuery,
    HistoryRequestKind,
)
from app.domain.models import OfferingId, ProductType  # noqa: E402
from app.domain.tariff_queries import (  # noqa: E402
    CurrentTariffItem,
    CurrentTariffResult,
    HistoryResultStatus,
    TariffHistoryResult,
)
from app.repositories.monitoring import PostgresSnapshotRepository  # noqa: E402
from app.repositories.reviews import PostgresReviewRepository  # noqa: E402
from app.services.review_decisions import _evidence_items  # noqa: E402
from app.services.review_evidence import (  # noqa: E402
    build_review_display,
    review_passages,
)
from app.services.review_resolution import (  # noqa: E402
    _evidence_excerpt,
    build_review_view,
)
from app.tools.reads import (  # noqa: E402
    current_tariffs_payload,
    tariff_history_payload,
)

RESULTS = Path(__file__).resolve().parent / "results"
BEFORE = "be049e5"


def _old_resolution_module():
    """`review_resolution.py` as it was before this fix, imported from git."""
    source = subprocess.run(
        ["git", "show", f"{BEFORE}:app/services/review_resolution.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    path = RESULTS / "_old_review_resolution.py"
    path.write_text(source)
    spec = importlib.util.spec_from_file_location("old_review_resolution", path)
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    finally:
        path.unlink()
    return module


async def main() -> None:
    password = replay._database_password()
    engine = create_async_engine(
        f"postgresql+asyncpg://tariff:{password}@localhost:5434/tariff_monitor",
        connect_args={"server_settings": {"default_transaction_read_only": "on"}},
    )
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    reviews = PostgresReviewRepository(sessions)
    snapshots = PostgresSnapshotRepository(sessions)
    RESULTS.mkdir(exist_ok=True)
    old = _old_resolution_module()
    report: dict[str, Any] = {
        "as_of": datetime.now(UTC).isoformat(),
        "r04": [],
        "r05": {},
    }
    try:
        async with sessions() as session:
            ids = (
                (
                    await session.execute(
                        text("SELECT id FROM human_reviews ORDER BY created_at")
                    )
                )
                .scalars()
                .all()
            )
        for review_id in ids:
            task = await reviews.get(review_id)
            snapshot = await snapshots.get(task.snapshot_id)
            view = build_review_view(task, snapshot.evidence)
            display = build_review_display(task, snapshot.evidence)
            old_view = old.build_review_view(task)
            passages = review_passages(task, snapshot.evidence)
            some_id = passages[0]["evidence_id"]
            record = {
                "review": str(task.id),
                "reason": task.reason.value,
                "field": task.issue_scope,
                "status": task.status.value,
                "stored_items": len(task.evidence.get("items", [])),
                "new_units": [
                    (unit.kind, unit.title[:60], len(unit.passages), unit.omitted)
                    for unit in display.units
                ],
                "new_seed_passages": [p.content[:100] for p in display.seeds],
                "new_view_excerpts": len(view.evidence),
                "new_view_bytes": len(view.model_dump_json()),
                "old_view_excerpts": len(old_view.evidence),
                "old_view_bytes": len(old_view.model_dump_json()),
                "old_view_first": [e.excerpt[:100] for e in old_view.evidence[:3]],
                "override_reference_resolves": _evidence_excerpt(passages, some_id)
                is not None,
                "decision_passages": len(_evidence_items(task, snapshot)),
            }
            report["r04"].append(record)
            print(json.dumps(record, ensure_ascii=False, indent=1))
        accepted = await snapshots.get_latest_accepted(
            bank="ameria",
            product=ProductType.CONSUMER_LOAN,
            offering_id=OfferingId.OVERDRAFT,
        )
        now = datetime.now(UTC)
        current = CurrentTariffResult(
            as_of=now,
            items=(
                CurrentTariffItem(
                    product=accepted.product,
                    offering_id=accepted.offering_id,
                    freshness=FreshnessStatus.STALE,
                    snapshot_id=accepted.id,
                    accepted_at=accepted.accepted_at,
                    age_seconds=(now - accepted.accepted_at).total_seconds(),
                    normalized_tariff=accepted.normalized_tariff,
                    evidence=accepted.evidence,
                ),
            ),
        )
        history = TariffHistoryResult(
            query=HistoryQuery(
                kind=HistoryRequestKind.SHOW_HISTORY,
                product=ProductType.CONSUMER_LOAN,
            ),
            status=HistoryResultStatus.HISTORY_FOUND,
            window_start=accepted.accepted_at,
            window_end=now,
            snapshots=(accepted,),
        )
        new_current = current_tariffs_payload(current)
        report["r05"] = {
            "current_before_bytes": len(current.model_dump_json()),
            "current_after_bytes": len(json.dumps(new_current)),
            "current_after": new_current,
            "history_before_bytes": len(history.model_dump_json()),
            "history_after_bytes": len(json.dumps(tariff_history_payload(history))),
        }
        print(
            json.dumps({k: v for k, v in report["r05"].items() if k != "current_after"})
        )
        print(json.dumps(new_current["items"][0], indent=1))
    finally:
        await engine.dispose()
    (RESULTS / "R04-R05-stored.json").write_text(
        json.dumps(report, indent=1, ensure_ascii=False, default=str)
    )


if __name__ == "__main__":
    asyncio.run(main())
