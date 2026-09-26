"""Capture every seed once, live, so the normalization survey can run offline.

    uv run python fix-process/normalization/survey/capture_seeds.py

For each enabled seed this acquires the page with the production composition
(browser render, PDF downloads on, cap 40) and writes, under
`fix-process/normalization/.cache/` (git-ignored):

- `<offering>.artifact.json`: the whole `PageArtifact`, rendered HTML included;
- `pdfs/<sha256>.pdf`: every linked PDF that was downloaded.

Acquisition makes no model calls. As in the acquisition scenarios, the Gemini key
is removed and any attempt to create a Gemini client raises.
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
# SURVEY_CACHE picks another capture folder (a live re-check keeps its own).
CACHE = Path(
    os.environ.get("SURVEY_CACHE", Path(__file__).resolve().parents[1] / ".cache")
)
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

os.environ["GEMINI_API_KEY"] = ""
os.environ.pop("GOOGLE_API_KEY", None)

import google.genai  # noqa: E402
import google.genai.client  # noqa: E402


def _refuse_gemini(*args: Any, **kwargs: Any) -> None:
    raise RuntimeError("Gemini is disabled in the normalization survey")


google.genai.Client.__init__ = _refuse_gemini  # type: ignore[method-assign]
google.genai.client.Client.__init__ = _refuse_gemini  # type: ignore[method-assign]

import httpx  # noqa: E402

from app.config import load_settings  # noqa: E402
from app.config.seed_catalog import load_seed_catalog  # noqa: E402
from app.services.acquisition import build_acquisition_service  # noqa: E402


async def main(selected: list[str]) -> None:
    settings = load_settings()
    artifact_dir = Path(tempfile.mkdtemp(prefix="norm-survey-"))
    settings = settings.model_copy(
        update={
            "acquisition": settings.acquisition.model_copy(
                update={"max_linked_documents": 40}
            ),
            "application": settings.application.model_copy(
                update={"artifact_temp_dir": artifact_dir}
            ),
        }
    )
    seeds = {
        entry.offering_id.value: str(entry.seed_url)
        for entry in load_seed_catalog().offerings
    }
    (CACHE / "pdfs").mkdir(parents=True, exist_ok=True)
    summary: dict[str, Any] = {}
    async with httpx.AsyncClient(timeout=30, follow_redirects=False) as client:
        service = build_acquisition_service(client, settings)
        for offering, url in seeds.items():
            if selected and offering not in selected:
                continue
            started = time.monotonic()
            try:
                artifact = await service.acquire(url)
            except Exception as exc:  # recorded, not fatal for the survey
                summary[offering] = {"error": f"{type(exc).__name__}: {exc}"[:500]}
                print(offering, "FAILED", exc)
                continue
            (CACHE / f"{offering}.artifact.json").write_text(
                artifact.model_dump_json(indent=None)
            )
            for document in artifact.downloadable_documents:
                source = artifact_dir / document.artifact.relative_path
                target = CACHE / "pdfs" / f"{document.sha256}.pdf"
                if source.exists() and not target.exists():
                    shutil.copyfile(source, target)
            summary[offering] = {
                "url": url,
                "mode": artifact.acquisition_mode.value,
                "tables": len(artifact.tables),
                "blocks": len(artifact.blocks),
                "pdfs": len(artifact.downloadable_documents),
                "warnings": [w.code.value for w in artifact.warnings],
                "seconds": round(time.monotonic() - started, 1),
            }
            print(offering, summary[offering])
    (CACHE / "capture-summary.json").write_text(json.dumps(summary, indent=1))


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1:]))
