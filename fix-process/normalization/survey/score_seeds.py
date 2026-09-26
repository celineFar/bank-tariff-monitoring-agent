"""Normalize every captured seed with the full service, no Gemini, and score it.

    uv run python fix-process/normalization/survey/score_seeds.py [label] [--stored]

Runs `StructuralNormalizationService` exactly as production does, with the
shipped baseline, except that PDFs go to `NoPdfExtractor` (no Gemini tokens) and
are read from the capture. By default each page is re-parsed from its rendered
HTML with the current parser, as acquisition would today; `--stored` scores the
blocks and cells stored at capture time instead (the parser of that day).
Prints, per seed, the page quality score and the warning codes; with a label,
writes `data/seed-scores-<label>.json`.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config import load_settings  # noqa: E402
from app.domain.acquisition import PageArtifact, StoredArtifact  # noqa: E402
from app.services.html_parser import HtmlArtifactParser  # noqa: E402
from app.services.normalization import (  # noqa: E402
    NoPdfExtractor,
    StructuralNormalizationService,
)
from app.services.normalization_baseline import (  # noqa: E402
    load_normalization_baseline,
)


class _CapturedPdfs:
    def __init__(self, cache: Path) -> None:
        self._cache = cache

    async def read(self, artifact: StoredArtifact) -> bytes:
        return (self._cache / "pdfs" / f"{artifact.sha256}.pdf").read_bytes()


def _reparsed(artifact: PageArtifact) -> PageArtifact:
    parsed = HtmlArtifactParser(load_settings().http.allowed_source_hosts).parse(
        artifact.rendered_html or artifact.raw_html or "",
        source_url=str(artifact.final_url),
    )
    return artifact.model_copy(
        update={"blocks": parsed.blocks, "tables": parsed.tables, "links": parsed.links}
    )


async def run(cache: Path, *, stored: bool) -> dict[str, Any]:
    service = StructuralNormalizationService(
        artifact_reader=_CapturedPdfs(cache),
        pdf_extractor=NoPdfExtractor(),
        baseline=load_normalization_baseline(),
    )
    result: dict[str, Any] = {}
    for path in sorted(cache.glob("*.artifact.json")):
        artifact = PageArtifact.model_validate_json(path.read_text())
        if not stored:
            artifact = _reparsed(artifact)
        bundle = await service.normalize(artifact)
        page = bundle.documents[0]
        result[path.name.removesuffix(".artifact.json")] = {
            "page_id": page.id,
            "quality_score": page.quality_score,
            "warning_codes": dict(Counter(w.code.value for w in bundle.warnings)),
            "baseline_failures": [
                w.message
                for w in bundle.warnings
                if w.code.value == "BASELINE_MISMATCH"
            ],
            "evidence_items": sum(len(t.rows) + len(t.notes) for t in page.tables)
            + len(page.blocks),
        }
    return result


def main() -> None:
    args = [arg for arg in sys.argv[1:] if not arg.startswith("--")]
    label = args[0] if args else None
    result = asyncio.run(
        run(
            Path(os.environ.get("SURVEY_CACHE", BASE / ".cache")),
            stored="--stored" in sys.argv,
        )
    )
    for seed, row in result.items():
        print(f"{seed:34} score={row['quality_score']}  {row['warning_codes']}")
        for failure in row["baseline_failures"]:
            print("    ", failure[:300])
    if label:
        (BASE / "data" / f"seed-scores-{label}.json").write_text(
            json.dumps(result, indent=1, ensure_ascii=False) + "\n"
        )


if __name__ == "__main__":
    main()
