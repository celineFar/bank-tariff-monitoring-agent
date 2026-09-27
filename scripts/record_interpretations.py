"""Run the live request interpreter over the interpretation case set (RRS02).

Records every interpretation into `tests/fixtures/recorded_interpretations.json`
(replayed offline by RRS01), prints the score, and measures tokens and latency
(RRS08). Spends intent-interpretation calls only: one per case turn.

    GEMINI_API_KEY=... uv run python scripts/record_interpretations.py
    ... --cases rr1_bare_offering,rr9_numeric_reply_keeps_question   # a subset
    ... --dry-run                                                     # do not write
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import statistics
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import get_settings
from app.config.seed_catalog import (
    DEFAULT_SEED_CATALOG_PATH,
    load_seed_catalog,
)
from app.services.intent_resolution import (
    AdkRequestInterpreter,
    RequestResolver,
)
from tests.fixtures.interpretation_cases import INTERPRETATION_CASES
from tests.fixtures.interpretation_scoring import run_case
from tests.fixtures.recorded_interpretations import (
    FIXTURE,
    RecordingInterpreter,
    load_recordings,
)


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", default="", help="comma-separated case IDs")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--concurrency", type=int, default=6)
    args = parser.parse_args()

    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("GEMINI_API_KEY is required", file=sys.stderr)
        return 2
    settings = get_settings()
    live = AdkRequestInterpreter(
        settings.models.generation_model,
        api_key=api_key,
        max_attempts=settings.intent_resolution.classifier_max_attempts,
    )
    wanted = {item for item in args.cases.split(",") if item}
    cases = [
        case for case in INTERPRETATION_CASES if not wanted or case.case_id in wanted
    ]
    limit = asyncio.Semaphore(args.concurrency)
    results: dict[str, list] = {}
    recorders: dict[str, RecordingInterpreter] = {}

    async def one(case) -> None:
        async with limit:
            # One recorder per case: the interpreter's `last_call` is per call,
            # and the cases run concurrently.
            recorder = RecordingInterpreter(
                AdkRequestInterpreter(
                    settings.models.generation_model,
                    api_key=api_key,
                    max_attempts=settings.intent_resolution.classifier_max_attempts,
                )
            )
            recorders[case.case_id] = recorder
            resolver = RequestResolver(load_seed_catalog(), interpreter=recorder)
            results[case.case_id] = await run_case(resolver, case)

    await asyncio.gather(*(one(case) for case in cases))

    passed = 0
    checks: Counter[str] = Counter()
    safety: list[str] = []
    for case in cases:
        mismatches = results[case.case_id]
        if not mismatches:
            passed += 1
            continue
        detail = "; ".join(f"t{m.turn} {m.check}: {m.detail}" for m in mismatches)
        print(f"FAIL {case.case_id} [{case.source}]: {detail}")
        for item in mismatches:
            checks[item.check] += 1
            if item.safety:
                safety.append(f"{case.case_id} t{item.turn} {item.check}")
    total = len(cases)
    print(f"\npassed {passed}/{total} cases ({passed / total:.1%})")
    print(f"safety mismatches: {len(safety)} {safety}")
    print("failed checks:", dict(checks.most_common()))

    stats = [item for recorder in recorders.values() for item in recorder.stats]
    tokens_in = [item["input_tokens"] for item in stats if item["input_tokens"]]
    tokens_out = [item["output_tokens"] for item in stats if item["output_tokens"]]
    latency = sorted(item["latency_ms"] for item in stats)
    if stats:
        print(
            f"calls {len(stats)}; input tokens mean {statistics.mean(tokens_in):.0f}"
            f" max {max(tokens_in)}; output tokens mean {statistics.mean(tokens_out):.0f}"
            f" max {max(tokens_out)}; latency p50 {latency[len(latency) // 2]} ms"
            f" p90 {latency[int(len(latency) * 0.9)]} ms"
        )

    if not args.dry_run:
        entries = {} if not wanted else load_recordings()
        for case_id, recorder in recorders.items():
            entries[case_id] = recorder.entries
        FIXTURE.write_text(
            json.dumps(
                {
                    "model": settings.models.generation_model,
                    "recorded_at": datetime.now(UTC).isoformat(timespec="seconds"),
                    "catalog_sha256": hashlib.sha256(
                        DEFAULT_SEED_CATALOG_PATH.read_bytes()
                    ).hexdigest(),
                    "cases": {
                        case_id: dict(sorted(items.items()))
                        for case_id, items in sorted(entries.items())
                    },
                },
                ensure_ascii=False,
                indent=1,
            )
            + "\n",
            encoding="utf-8",
        )
        count = sum(len(items) for items in entries.values())
        print(f"wrote {count} recordings for {len(entries)} cases to {FIXTURE}")
    del live
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
