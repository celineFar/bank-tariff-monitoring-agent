"""Transcribe the labelled PDFs that have no stored transcription (Phase 9).

    GEMINI_API_KEY=… uv run python \
        fix-process/semantic_extraction/survey/transcribe_missing_pdfs.py --max-usd 0.30

For every seed's `current_product` or `shared_terms` PDF (source-discovery hand
labels) with no transcription in `pdf_extraction_cache`, the production
`GeminiPdfExtractionService` transcribes it once. The responses go to
`.cache/pdf-transcriptions.json`, which `replay.py` reads next to the database.
Token use is reported from each outcome; the run stops before a PDF once the
spend reaches `--max-usd`.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import replay

from app.config import PdfExtractionSettings
from app.domain.acquisition import PageArtifact
from app.services.model_pricing import get_model_price
from app.services.pdf_extraction import GeminiPdfExtractionService


class CapturingRepository:
    def __init__(self) -> None:
        self.saved: dict[str, Any] = {}

    async def get_exact(self, **_: Any) -> None:
        return None

    async def save(
        self, *, document_sha256: str, model_name: str, response: Any, **_: Any
    ) -> None:
        self.saved[f"{document_sha256}|{model_name}"] = response.model_dump(mode="json")


async def run(max_usd: float) -> None:
    stored = await replay.stored_transcriptions()
    have = {sha for sha, _ in stored}
    repository = CapturingRepository()
    pdf_settings = PdfExtractionSettings()
    service = GeminiPdfExtractionService(
        pdf_settings, repository, api_key=os.environ["GEMINI_API_KEY"]
    )
    price = get_model_price(pdf_settings.model_name)
    spent = 0.0
    done: set[str] = set()
    for seed in replay.seeds():
        labels = replay.PDF_LABELS["seeds"].get(seed, {}).get("pdfs", {})
        artifact = PageArtifact.model_validate_json(
            (replay.CACHE / f"{seed}.artifact.json").read_text()
        )
        for document in artifact.downloadable_documents:
            name = replay._file_name(document)
            if labels.get(name) not in replay.KEPT_PDF_LABELS:
                continue
            if document.sha256 in have or document.sha256 in done:
                continue
            if spent >= max_usd:
                print(f"stop: ${spent:.4f} spent; {name} left")
                continue
            content = (replay.CACHE / "pdfs" / f"{document.sha256}.pdf").read_bytes()
            outcome = await service.extract(
                document, content, document_id=f"document:{document.sha256[:12]}"
            )
            usage = outcome.usage
            cost = (
                usage.input_tokens * price.input_per_million_tokens_usd
                + (usage.output_tokens + usage.thinking_tokens)
                * price.output_per_million_tokens_usd
            ) / 1_000_000
            spent += cost
            done.add(document.sha256)
            print(
                f"{seed:32} {name:52} in={usage.input_tokens} out={usage.output_tokens} "
                f"${cost:.4f} pages={outcome.plan.input_probe.page_count}"
            )
    existing = (
        json.loads(replay.LOCAL_TRANSCRIPTIONS.read_text())
        if replay.LOCAL_TRANSCRIPTIONS.exists()
        else {}
    )
    existing.update(repository.saved)
    replay.LOCAL_TRANSCRIPTIONS.parent.mkdir(exist_ok=True)
    replay.LOCAL_TRANSCRIPTIONS.write_text(json.dumps(existing))
    print(f"transcribed {len(done)} PDFs, ${spent:.4f}; cache holds {len(existing)}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-usd", type=float, default=0.30)
    asyncio.run(run(parser.parse_args().max_usd))


if __name__ == "__main__":
    main()
