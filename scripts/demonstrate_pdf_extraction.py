from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Any

from app.config import load_settings
from app.domain.acquisition import PageArtifact
from app.repositories.file_pdf_extraction import FileSystemPdfExtractionRepository
from app.services.artifact_store import FileSystemArtifactStore
from app.services.model_pricing import get_model_price
from app.services.normalization import StructuralNormalizationService
from app.services.pdf_extraction import (
    GeminiPdfExtractionService,
    PdfExtractionOutcome,
)
from scripts.demonstrate_normalization import write_normalization_bundle


async def demonstrate(case_path: Path, *, execute_llm: bool = False) -> Path:
    artifact_path, case_directory = _resolve_case(case_path)
    artifact = PageArtifact.model_validate_json(
        artifact_path.read_text(encoding="utf-8")
    )
    settings = load_settings()
    store = FileSystemArtifactStore(artifact_path.parent / "artifacts")
    repository = FileSystemPdfExtractionRepository(
        case_directory / "pdf_extraction" / "cache"
    )
    api_key = (
        settings.models.api_key.get_secret_value()
        if settings.models.api_key is not None
        else None
    )
    service = GeminiPdfExtractionService(
        settings.pdf_extraction,
        repository,
        api_key=api_key if execute_llm else None,
    )
    plans = []
    contents: list[bytes] = []
    for index, document in enumerate(artifact.downloadable_documents):
        content = await store.read(document.artifact)
        contents.append(content)
        plans.append(
            service.plan(
                document,
                content,
                document_id=f"document:{index}:{document.sha256[:12]}",
            )
        )

    if not execute_llm:
        output = case_directory / "pdf_extraction" / "preflight"
        _write_preflight(output, plans)
        return output
    if api_key is None:
        raise RuntimeError("GEMINI_API_KEY is required for --execute-llm")

    output = _next_run_directory(case_directory / "pdf_extraction")
    _write_preflight(output, plans)
    outcomes: list[PdfExtractionOutcome] = []
    for index, (document, content) in enumerate(
        zip(artifact.downloadable_documents, contents, strict=True), start=1
    ):
        print(
            f"Extracting PDF {index}/{len(contents)}: {document.document_name}",
            flush=True,
        )
        outcome = await service.extract(
            document,
            content,
            document_id=f"document:{index - 1}:{document.sha256[:12]}",
        )
        outcomes.append(outcome)
        _write_json(output / f"document_{index - 1:03d}.json", outcome)
        print(
            f"  mode={outcome.plan.input_probe.document_mode.value}, "
            f"admission={outcome.plan.admission.relevance.value}/"
            f"{outcome.plan.admission.temporal_status.value}, "
            f"model={outcome.model_name}, tokens={outcome.usage.total_tokens}",
            flush=True,
        )
    _write_json(output / "results.json", outcomes)
    _write_json(
        output / "normalized_pdf_documents.json",
        [outcome.normalized_document for outcome in outcomes],
    )
    _write_json(
        output / "usage_and_cost.json",
        [_usage_and_cost(outcome) for outcome in outcomes],
    )
    (output / "summary.txt").write_text(_result_summary(outcomes), encoding="utf-8")

    normalizer = StructuralNormalizationService(
        artifact_reader=store,
        pdf_extractor=service,
    )
    bundle = await normalizer.normalize(artifact)
    write_normalization_bundle(
        bundle, output_directory=case_directory / "normalization"
    )
    return output


def _write_preflight(output: Path, plans: list) -> None:
    output.mkdir(parents=True, exist_ok=True)
    _write_json(output / "plans.json", plans)
    estimate = _cost_estimate(plans)
    _write_json(output / "cost_estimate.json", estimate)
    (output / "summary.txt").write_text(
        "\n".join(
            (
                "MODE: PREFLIGHT"
                if output.name == "preflight"
                else "MODE: LLM EXECUTION",
                f"PDF documents: {len(plans)}",
                f"Pages: {sum(plan.input_probe.page_count for plan in plans)}",
                "Machine-readable PDFs: "
                f"{sum(plan.input_probe.document_mode.value == 'machine_readable' for plan in plans)}",
                "Image-only PDFs: "
                f"{sum(plan.input_probe.document_mode.value == 'image_only' for plan in plans)}",
                f"Mixed PDFs: {sum(plan.input_probe.document_mode.value == 'mixed' for plan in plans)}",
                "Metadata-admitted PDFs: "
                f"{sum(plan.admission.relevance.value == 'relevant' for plan in plans)}",
                f"Estimated primary-model cost (USD): {estimate['estimated_cost_usd']:.6f}",
            )
        )
        + "\n",
        encoding="utf-8",
    )


def _cost_estimate(plans: list) -> dict[str, Any]:
    pages = sum(plan.input_probe.page_count for plan in plans)
    input_tokens = pages * 258
    output_tokens = pages * 1200
    model_name = plans[0].model_names[0] if plans else "gemini-3.1-flash-lite"
    price = get_model_price(model_name)
    cost = (
        input_tokens * price.input_per_million_tokens_usd
        + output_tokens * price.output_per_million_tokens_usd
    ) / 1_000_000
    return {
        "model": model_name,
        "pages": pages,
        "estimated_input_tokens": input_tokens,
        "estimated_output_tokens": output_tokens,
        "estimated_cost_usd": cost,
        "assumptions": "258 PDF input tokens and 1,200 output tokens per page",
        "pricing_source": price.source,
    }


def _result_summary(outcomes: list[PdfExtractionOutcome]) -> str:
    lines = ["MODE: LLM EXECUTION", f"PDF documents: {len(outcomes)}"]
    for outcome in outcomes:
        lines.append(
            f"- {outcome.normalized_document.name}: "
            f"mode={outcome.plan.input_probe.document_mode.value}, "
            f"temporal={outcome.plan.admission.temporal_status.value}, "
            f"model={outcome.model_name}, blocks={len(outcome.normalized_document.blocks)}, "
            f"tables={len(outcome.normalized_document.tables)}, "
            f"tokens={outcome.usage.total_tokens}, "
            f"cost_usd={_usage_and_cost(outcome)['cost_usd']:.6f}"
        )
    return "\n".join(lines) + "\n"


def _usage_and_cost(outcome: PdfExtractionOutcome) -> dict[str, Any]:
    if outcome.model_name is None:
        return {
            "document_id": outcome.plan.document_id,
            "model": None,
            "reused": outcome.reused,
            "usage": outcome.usage.model_dump(mode="json"),
            "cost_usd": 0.0,
        }
    price = get_model_price(outcome.model_name)
    cost = (
        outcome.usage.input_tokens * price.input_per_million_tokens_usd
        + outcome.usage.output_tokens * price.output_per_million_tokens_usd
    ) / 1_000_000
    return {
        "document_id": outcome.plan.document_id,
        "model": outcome.model_name,
        "reused": outcome.reused,
        "usage": outcome.usage.model_dump(mode="json"),
        "input_per_million_tokens_usd": price.input_per_million_tokens_usd,
        "output_per_million_tokens_usd": price.output_per_million_tokens_usd,
        "cost_usd": cost,
        "pricing_source": price.source,
    }


def _resolve_case(path: Path) -> tuple[Path, Path]:
    resolved = path.resolve()
    candidates = (
        resolved,
        resolved / "page_artifact.json",
        resolved / "output" / "page_artifact.json",
    )
    artifact = next((item for item in candidates if item.is_file()), None)
    if artifact is None:
        raise FileNotFoundError(f"No page_artifact.json found at {resolved}")
    case = (
        artifact.parent.parent if artifact.parent.name == "output" else artifact.parent
    )
    return artifact, case


def _next_run_directory(parent: Path) -> Path:
    parent.mkdir(parents=True, exist_ok=True)
    for index in range(100_000):
        candidate = parent / f"llm_run_{index:03d}"
        try:
            candidate.mkdir()
        except FileExistsError:
            continue
        return candidate
    raise RuntimeError(f"No available PDF extraction run directory below {parent}")


def _write_json(path: Path, value: Any) -> None:
    if isinstance(value, list):
        value = [
            item.model_dump(mode="json") if hasattr(item, "model_dump") else item
            for item in value
        ]
    elif hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    parser = argparse.ArgumentParser(description="Inspect or run Gemini PDF extraction")
    parser.add_argument("case", type=Path)
    parser.add_argument("--execute-llm", action="store_true")
    args = parser.parse_args()
    try:
        output = asyncio.run(demonstrate(args.case, execute_llm=args.execute_llm))
    except Exception as exc:
        print(f"PDF extraction failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    print(f"PDF extraction artifacts written to {output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
