"""Compare two fresh live captures through the production normalization path.

    SURVEY_CACHE=.cache-live-1 uv run python .../capture_seeds.py
    SURVEY_CACHE=.cache-live-2 uv run python .../capture_seeds.py
    uv run python fix-process/normalization/survey/live_check.py .cache-live-1 .cache-live-2

No Gemini: PDFs go to `NoPdfExtractor`. Normalizes each capture exactly as the
pipeline does (the blocks and tables acquisition stored, the shipped baseline)
and reports, per seed: whether the page id, the acquisition content hash and
the normalized page document are identical across the two captures, the
quality score, and the warning codes. Writes `data/live-check-<date>.json`.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import sys
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.domain.acquisition import PageArtifact, StoredArtifact  # noqa: E402
from app.domain.pdf_extraction import (  # noqa: E402
    PdfAdmissionRelevance,
    PdfTemporalStatus,
)
from app.services.normalization import (  # noqa: E402
    NoPdfExtractor,
    StructuralNormalizationService,
)
from app.services.normalization_baseline import (  # noqa: E402
    load_normalization_baseline,
)
from app.services.pdf_admission import assess_pdf_metadata  # noqa: E402


class _CapturedPdfs:
    def __init__(self, cache: Path) -> None:
        self._cache = cache

    async def read(self, artifact: StoredArtifact) -> bytes:
        return (self._cache / "pdfs" / f"{artifact.sha256}.pdf").read_bytes()


async def _run(cache: Path) -> dict[str, dict[str, Any]]:
    service = StructuralNormalizationService(
        artifact_reader=_CapturedPdfs(cache),
        pdf_extractor=NoPdfExtractor(),
        baseline=load_normalization_baseline(),
    )
    labels = json.loads((BASE / "data" / "seed-pdf-labels.json").read_text())["pdfs"]
    as_of = date.fromisoformat(
        json.loads((BASE / "data" / "seed-pdf-labels.json").read_text())["as_of"]
    )
    out: dict[str, dict[str, Any]] = {}
    for path in sorted(cache.glob("*.artifact.json")):
        artifact = PageArtifact.model_validate_json(path.read_text())
        bundle = await service.normalize(artifact)
        page = bundle.documents[0]
        wrongly_skipped, unlabelled = [], 0
        for document in artifact.downloadable_documents:
            label = labels.get(document.sha256)
            if label is None:
                unlabelled += 1
                continue
            admission = assess_pdf_metadata(document, as_of=as_of)
            skipped = admission.relevance is PdfAdmissionRelevance.IRRELEVANT or (
                admission.temporal_status is PdfTemporalStatus.HISTORICAL
            )
            if skipped and label["label"] in {"current", "future"}:
                wrongly_skipped.append(label["file"])
        out[path.name.removesuffix(".artifact.json")] = {
            "mode": artifact.acquisition_mode.value,
            "inventory": artifact.inventory.model_dump(),
            "page_id": page.id,
            "content_hash": artifact.content_hash[:16],
            "page_digest": hashlib.sha256(page.model_dump_json().encode()).hexdigest()[
                :16
            ],
            "quality_score": page.quality_score,
            "warning_codes": dict(Counter(w.code.value for w in bundle.warnings)),
            "baseline_failures": [
                w.message
                for w in bundle.warnings
                if w.code.value == "BASELINE_MISMATCH"
            ],
            "pdfs": len(artifact.downloadable_documents),
            "pdfs_unlabelled": unlabelled,
            "current_pdfs_skipped": wrongly_skipped,
        }
    return out


def main() -> None:
    first, second = (BASE / name for name in sys.argv[1:3])
    one = asyncio.run(_run(first))
    two = asyncio.run(_run(second))
    seeds = sorted(set(one) | set(two))
    report = {}
    for seed in seeds:
        a, b = one.get(seed), two.get(seed)
        if a is None or b is None:
            report[seed] = {"missing_in": "first" if a is None else "second"}
            continue
        report[seed] = {
            **a,
            "same_page_id": a["page_id"] == b["page_id"],
            "same_content_hash": a["content_hash"] == b["content_hash"],
            "same_normalized_page": a["page_digest"] == b["page_digest"],
            "second_quality_score": b["quality_score"],
        }
        print(
            f"{seed:34} {a['mode']:8} score={a['quality_score']}/{b['quality_score']} "
            f"page_id={'=' if a['page_id'] == b['page_id'] else '≠'} "
            f"normalized={'=' if a['page_digest'] == b['page_digest'] else '≠'} "
            f"content={'=' if a['content_hash'] == b['content_hash'] else '≠'} "
            f"pdfs={a['pdfs']} unlabelled={a['pdfs_unlabelled']} "
            f"current_skipped={len(a['current_pdfs_skipped'])} {a['warning_codes']}"
        )
        for failure in a["baseline_failures"]:
            print("    ", failure[:300])
    out = BASE / "data" / f"live-check-{date.today().isoformat()}.json"
    out.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n")
    print("->", out)


if __name__ == "__main__":
    main()
