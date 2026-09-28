"""OCR fallback demonstration: Gemini fails, the project's OCR reads the scan.

Runs inside the project's worker image (see run.sh). Each sample PDF goes
through the production `GeminiPdfExtractionService` exactly as a monitoring run
sends it: metadata admission, the input probe, the Gemini model sequence from
settings, then the fallback to the pypdfium2 rasterizer and the tesseract
transcriber.

    --engine ocr     (default) Gemini is made to fail; the service falls back
                     to OCR. The only artificial part: `AdkGeminiPdfExtractor`
                     is swapped for a stand-in that raises the error a Gemini
                     outage raises (`ServerError` 503). Nothing leaves the
                     container.
    --engine gemini  The comparison baseline: the same service with the real
                     Gemini call. Spends a fraction of a cent of credits.

Each run writes `output/<sample>.<engine>.md` for a side-by-side comparison with
the source PDF, and `output/<sample>.<engine>.json` with the run's metadata (and
Gemini's raw response), which `score.py` reads.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import logging
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import ClassVar
from unittest import mock

from google.genai.errors import ServerError

from app.config import Settings, get_settings
from app.domain.acquisition import DocumentArtifact, StoredArtifact
from app.domain.normalization import (
    NormalizedBlockType,
    NormalizedDocument,
    NormalizedTable,
)
from app.domain.pdf_extraction import (
    PdfExtractionPlan,
    PdfExtractionResponse,
    PdfModelUsage,
    PdfTranscriptionSource,
)
from app.services import pdf_extraction
from app.services.model_pricing import get_model_price
from app.services.ocr_transcriber import TesseractOcrTranscriber
from app.services.pdf_extraction import (
    GeminiPdfExtractionService,
    InMemoryPdfExtractionRepository,
    PdfExtractionOutcome,
    is_ocr_method,
)
from app.services.pdf_rasterizer import PdfiumPageRasterizer

HERE = Path(__file__).resolve().parent
SAMPLES = HERE / "samples"
OUTPUT = HERE / "output"
# A reserved `.invalid` host: the demonstration never fetches anything.
SOURCE_URL = "https://demo.invalid/ocr-fallback/{name}"


class SimulatedGeminiOutage:
    """Stands in for `AdkGeminiPdfExtractor`; the only artificial part of the demo.

    It takes the same constructor arguments and fails every call with the error
    type a real outage produces, so the fallback is chosen by production code.
    """

    attempts: ClassVar[list[tuple[str, str]]] = []

    def __init__(self, model_name: str, **_: object) -> None:
        self.model_name = model_name
        self.usage = PdfModelUsage()

    async def extract(self, content: bytes, plan: PdfExtractionPlan) -> None:
        error = ServerError(
            503,
            {
                "error": {
                    "code": 503,
                    "status": "UNAVAILABLE",
                    "message": "The model is overloaded (simulated outage).",
                }
            },
        )
        self.attempts.append((self.model_name, f"{error.code} {error.status}"))
        print(f"    [simulated] {self.model_name} -> {error.code} {error.status}")
        raise error


class RecordingRepository(InMemoryPdfExtractionRepository):
    """The service's own cache, empty at start, keeping Gemini's raw answer."""

    def __init__(self) -> None:
        super().__init__()
        self.response: PdfExtractionResponse | None = None

    async def save(self, *, response: PdfExtractionResponse, **key: str) -> None:
        self.response = response
        await super().save(response=response, **key)


def step(text: str) -> None:
    print(f"\n==> {text}", flush=True)


def build_document(pdf: Path, content: bytes) -> DocumentArtifact:
    """The artifact acquisition would have stored for a downloaded PDF link."""
    sha256 = hashlib.sha256(content).hexdigest()
    url = SOURCE_URL.format(name=pdf.name)
    return DocumentArtifact(
        source_url=url,
        final_url=url,
        document_name=pdf.name,
        mime_type="application/pdf",
        size_bytes=len(content),
        sha256=sha256,
        retrieved_at=datetime.now(UTC),
        artifact=StoredArtifact(
            role="pdf",
            sha256=sha256,
            size_bytes=len(content),
            media_type="application/pdf",
            relative_path=pdf.name,
        ),
        link_text="Loan information sheet",
    )


async def process(pdf: Path, engine: str, settings: Settings) -> bool:
    content = pdf.read_bytes()
    api_key = None
    if engine == "gemini":
        if settings.models.api_key is None:
            print("    GEMINI_API_KEY is not set; the Gemini baseline cannot run.")
            return False
        api_key = settings.models.api_key.get_secret_value()
    repository = RecordingRepository()
    service = GeminiPdfExtractionService(
        settings.pdf_extraction,
        repository,
        # In OCR mode the key is never used: the stand-in replaces the only
        # code that would send it.
        api_key=api_key or "simulated-outage",
        ocr_settings=settings.ocr,
        ocr_transcriber=TesseractOcrTranscriber(settings.ocr),
        rasterizer=PdfiumPageRasterizer(),
    )
    document = build_document(pdf, content)

    step(f"{pdf.name} ({len(content):,} bytes) -> PDF extraction, engine={engine}")
    SimulatedGeminiOutage.attempts.clear()
    started = time.perf_counter()
    if engine == "ocr":
        print("    Every Gemini call is set to fail with 503 UNAVAILABLE.")
        with mock.patch.object(
            pdf_extraction, "AdkGeminiPdfExtractor", SimulatedGeminiOutage
        ):
            outcome = await service.extract(document, content, document_id=pdf.stem)
    else:
        outcome = await service.extract(document, content, document_id=pdf.stem)
    elapsed = time.perf_counter() - started

    run = run_record(pdf, engine, outcome, repository, elapsed)
    print(f"    content produced by {run['produced_by']} in {elapsed:.1f}s")
    if engine == "ocr" and outcome.model_name is not None:
        print("    Unexpected: the outcome did not come from the OCR fallback.")
        return False

    OUTPUT.mkdir(exist_ok=True)
    stem = f"{pdf.stem}.{engine}"
    (OUTPUT / f"{stem}.json").write_text(
        json.dumps(run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (OUTPUT / f"{stem}.md").write_text(
        render_markdown(pdf, engine, outcome, run, settings), encoding="utf-8"
    )
    print(f"    wrote output/{stem}.md and output/{stem}.json")
    return True


def run_record(
    pdf: Path,
    engine: str,
    outcome: PdfExtractionOutcome,
    repository: RecordingRepository,
    elapsed: float,
) -> dict[str, object]:
    usage = outcome.usage
    cost = None
    if outcome.model_name is not None:
        price = get_model_price(outcome.model_name)
        cost = (
            usage.input_tokens * price.input_per_million_tokens_usd
            + (usage.output_tokens + usage.thinking_tokens)
            * price.output_per_million_tokens_usd
        ) / 1_000_000
    return {
        "sample": pdf.name,
        "engine": engine,
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "produced_by": outcome.model_name
        or outcome.normalized_document.extraction_method,
        "elapsed_seconds": round(elapsed, 2),
        "simulated_gemini_failures": [
            {"model": model, "error": error}
            for model, error in SimulatedGeminiOutage.attempts
        ],
        "usage": usage.model_dump(),
        "cost_usd": cost,
        "page_sources": {
            str(page): source.value for page, source in outcome.page_sources
        },
        "ocr_pages": (
            [page.model_dump(exclude={"text"}) for page in outcome.ocr.pages]
            if outcome.ocr
            else []
        ),
        "gemini_response": (
            repository.response.model_dump(mode="json") if repository.response else None
        ),
    }


def render_markdown(
    pdf: Path,
    engine: str,
    outcome: PdfExtractionOutcome,
    run: dict[str, object],
    settings: Settings,
) -> str:
    plan = outcome.plan
    probe = plan.input_probe
    sources = dict(outcome.page_sources)
    ocr_pages = {
        page.page_number: page for page in (outcome.ocr.pages if outcome.ocr else ())
    }

    if engine == "ocr":
        blurb = (
            "Gemini was made to fail on purpose; the text under **Transcription** "
            "was read from the page images by the project's tesseract fallback."
        )
        gemini = "; ".join(
            f"`{item['model']}` failed ({item['error']}, simulated)"
            for item in run["simulated_gemini_failures"]
        )
    else:
        blurb = (
            "The text under **Transcription** is Gemini's transcription of the "
            "page images, as the pipeline normalizes it."
        )
        usage = outcome.usage
        gemini = (
            f"`{outcome.model_name}` succeeded: {usage.input_tokens:,} input and "
            f"{usage.output_tokens:,} output tokens, ${run['cost_usd']:.5f}"
            if outcome.model_name
            else "every model failed; the service fell back to OCR"
        )
    lines = [
        f"# {engine.upper()} output: {pdf.name}",
        "",
        f"Generated {run['generated_at']} by `ocr_fallback_demo.py --engine "
        f"{engine}`. {blurb} The values are synthetic sample data.",
        "",
        "## Run summary",
        "",
        "| | |",
        "|---|---|",
        f"| Source | `samples/{pdf.name}`, sha256 `{plan.document_sha256[:16]}…` |",
        f"| Input probe | `{probe.document_mode.value}`, {probe.page_count} pages, "
        f"{sum(p.native_text_characters for p in probe.pages)} native text "
        "characters |",
        f"| Gemini | {gemini} |",
        f"| Content produced by | `{run['produced_by']}` in "
        f"{run['elapsed_seconds']}s |",
    ]
    if ocr_pages:
        lines.append(
            f"| OCR settings | languages `{settings.ocr.languages}`, "
            f"{settings.ocr.render_dpi} dpi, confidence floor "
            f"{settings.ocr.min_confidence:g} |"
        )
    lines += [
        "",
        "## Pages",
        "",
        "| Page | Probe mode | Content from | OCR outcome | Mean confidence | Words |",
        "|---|---|---|---|---|---|",
    ]
    for page in probe.pages:
        ocr = ocr_pages.get(page.page_number)
        source = sources.get(page.page_number, PdfTranscriptionSource.NONE).value
        lines.append(
            f"| {page.page_number} | `{page.input_mode.value}` | {source} | "
            + (
                f"`{ocr.outcome.value}` | {ocr.mean_confidence:.1f} | "
                f"{ocr.word_count} |"
                if ocr
                else "- | - | - |"
            )
        )

    lines += ["", "## Transcription"]
    for page in probe.pages:
        lines += ["", f"### Page {page.page_number}", ""]
        body = page_body(outcome.normalized_document, page.page_number)
        if not body:
            ocr = ocr_pages.get(page.page_number)
            reason = ocr.detail if ocr and ocr.detail else "no content for this page"
            lines.append(f"_No text emitted: {reason}._")
            continue
        # Invisible when rendered; score.py reads exactly what sits between them.
        lines += [f"<!-- page:{page.page_number} -->", *body, "<!-- /page -->"]
    lines.append("")
    return "\n".join(lines)


def page_body(document: NormalizedDocument, page_number: int) -> list[str]:
    def on_page(refs) -> bool:
        return any(ref.locator.pdf_page == page_number for ref in refs)

    body: list[str] = []
    for block in document.blocks:
        if not on_page(block.source_refs):
            continue
        if is_ocr_method(block.extraction_method):
            body += ["```text", block.text, "```", ""]
        elif block.type is NormalizedBlockType.HEADING:
            body += [f"**{block.text}**", ""]
        else:
            body += ["  \n".join(block.text.splitlines()), ""]
    for table in document.tables:
        if on_page(table.source_refs):
            body += [*table_markdown(table), ""]
    while body and not body[-1]:
        body.pop()
    return body


def table_markdown(table: NormalizedTable) -> list[str]:
    """A normalized table as GFM; a merged header cell is written once."""

    def cell(text: str) -> str:
        return " ".join(text.split()).replace("|", "\\|")

    width = len(table.rows[0].cells) if table.rows else len(table.headers)
    paths = list(table.column_paths) or [(header,) for header in table.headers]
    paths = (paths + [()] * width)[:width]
    header_rows: list[list[str]] = []
    for level in range(max((len(path) for path in paths), default=0)):
        row: list[str] = []
        previous: tuple[str, ...] | None = None
        for path in paths:
            prefix = path[: level + 1]
            row.append(path[level] if level < len(path) and prefix != previous else "")
            previous = prefix
        header_rows.append(row)
    header_rows = header_rows or [[""] * width]

    lines = [f"**{cell(table.title)}**", ""] if table.title else []
    lines.append("| " + " | ".join(cell(text) for text in header_rows[0]) + " |")
    lines.append("|" + "---|" * width)
    for row in header_rows[1:]:
        lines.append(
            "| " + " | ".join(f"**{cell(t)}**" if t else "" for t in row) + " |"
        )
    section = None
    for table_row in table.rows:
        if table_row.section and table_row.section != section:
            section = table_row.section
            lines.append(f"| **{cell(section)}** |" + " |" * (width - 1))
        lines.append("| " + " | ".join(cell(c.text) for c in table_row.cells) + " |")
    lines += [note.text for note in table.notes]
    return lines


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--engine", choices=("ocr", "gemini"), default="ocr")
    parser.add_argument(
        "--sample", action="append", help="sample name (default: every sample)"
    )
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.INFO, format="    [%(name)s] %(message)s", stream=sys.stdout
    )
    settings = get_settings()

    step("Checking the OCR engine this image ships")
    transcriber = TesseractOcrTranscriber(settings.ocr)
    if not (transcriber.available and PdfiumPageRasterizer().available):
        print(
            f"    OCR is not available: {transcriber.unavailable_reason}. "
            "Nothing was written; run this through ./run.sh."
        )
        return 2
    print(
        f"    tesseract {transcriber.engine_version}, languages "
        f"{settings.ocr.languages}, {settings.ocr.render_dpi} dpi, "
        f"confidence floor {settings.ocr.min_confidence:g}"
    )

    names = args.sample or sorted(path.stem for path in SAMPLES.glob("*.pdf"))
    results = [
        await process(SAMPLES / f"{name}.pdf", args.engine, settings) for name in names
    ]
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
