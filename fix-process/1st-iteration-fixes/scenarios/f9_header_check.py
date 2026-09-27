"""F9 check: which blocks above each page's first heading now reach the classifier.

    uv run python fix-process/1st-iteration-fixes/scenarios/f9_header_check.py

Reads the 13 captured seed pages the source-discovery scenarios use
(`fix-process/normalization/.cache-live-2`), builds the discovery candidates, and
writes, per page, the blocks kept in the rule-decided page header and the blocks
moved to the classified "Page summary". No model is called (the source-discovery
runner's Gemini guard is imported with its loader).
"""

from __future__ import annotations

import asyncio
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RUNNER = ROOT / "fix-process/source_discovery/scenarios/run_scenarios.py"
OUT = Path(__file__).resolve().parent / "results/f9_header_check.json"

spec = importlib.util.spec_from_file_location("sd_runner", RUNNER)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)

from app.domain.source_discovery import CandidateLayout, DiscoveryScope  # noqa: E402
from app.services.discovery_prefilter import build_discovery_candidates  # noqa: E402

SEEDS = sorted(
    path.name.removesuffix(".artifact.json")
    for path in runner.CACHE.glob("*.artifact.json")
)


async def main() -> None:
    report: dict[str, dict] = {}
    for seed in SEEDS:
        _, bundle = await runner._bundle(seed)
        document = bundle.documents[0]
        texts = {
            f"{document.id}::block::{block.id}": block.text for block in document.blocks
        }
        header: list[str] = []
        summary: list[str] = []
        for candidate in build_discovery_candidates(bundle):
            if candidate.scope is not DiscoveryScope.SECTION:
                continue
            members = [texts.get(item, item)[:120] for item in candidate.member_source_ids]
            if candidate.layout is CandidateLayout.PAGE_HEADER:
                header.extend(members)
            elif candidate.title == "Page summary":
                summary.extend(members)
        report[seed] = {"page_header": header, "page_summary": summary}
        print(f"{seed}: header {len(header)}, moved to summary {len(summary)}")
        for text in summary:
            print(f"    + {text!r}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    assert not runner.GEMINI_ATTEMPTS, "a model call was attempted"


if __name__ == "__main__":
    asyncio.run(main())
