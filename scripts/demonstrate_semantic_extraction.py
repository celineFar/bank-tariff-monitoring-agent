from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.config import load_settings
from app.domain.normalization import NormalizedSourceBundle
from app.domain.semantic_extraction import (
    SemanticExtractionPlan,
    SemanticExtractionResult,
)
from app.domain.source_discovery import SourceDiscoveryResult
from app.services.discovery_classifier import is_retryable_api_error
from app.services.model_pricing import enforce_model_price_cap, get_model_price
from app.services.semantic_extraction import (
    AdkSemanticExtractor,
    InMemorySemanticExtractionRepository,
    SemanticExtractionService,
)


SEMANTIC_EXTRACTION_LOGGER = "app.services.semantic_extraction"


class SemanticExtractionRunFailed(RuntimeError):
    def __init__(self, output_directory: Path, error: Exception) -> None:
        super().__init__(str(error))
        self.output_directory = output_directory
        self.error = error


async def demonstrate(
    case_path: Path,
    *,
    source_discovery_result: Path | None = None,
    execute_llm: bool = False,
) -> Path:
    bundle_path, case_directory = _resolve_case(case_path)
    discovery_path = _resolve_discovery_result(
        case_directory, source_discovery_result
    )
    print(f"Loading normalized input from {bundle_path}", flush=True)
    print(f"Loading discovery result from {discovery_path}", flush=True)
    bundle = NormalizedSourceBundle.model_validate_json(
        bundle_path.read_text(encoding="utf-8")
    )
    discovery = SourceDiscoveryResult.model_validate_json(
        discovery_path.read_text(encoding="utf-8")
    )
    settings = load_settings()
    repository = InMemorySemanticExtractionRepository()
    planning_service = SemanticExtractionService(
        extractor=None,
        repository=repository,
        settings=settings.semantic_extraction,
        model_name=settings.models.generation_model,
    )
    plan = await planning_service.plan(bundle, discovery)
    print(
        f"Extraction plan ready: {len(plan.batches)} LLM batch(es), "
        f"{len(plan.cache_hits)} cached batch(es), "
        f"{len(plan.evidence_catalog)} evidence item(s)",
        flush=True,
    )
    if not execute_llm:
        output_directory = case_directory / "semantic_extraction" / "preflight"
        _write_preflight(plan, output_directory, execution_run=False)
        return output_directory

    if settings.models.api_key is None:
        raise RuntimeError("GEMINI_API_KEY is required for --execute-llm")
    models = _model_sequence(
        settings.models.generation_model,
        settings.source_discovery.fallback_model_names,
    )
    enforce_model_price_cap(
        models,
        max_price_per_million_tokens_usd=(
            settings.source_discovery.max_price_per_million_tokens_usd
        ),
    )
    output_directory = _next_run_directory(case_directory / "semantic_extraction")
    _write_preflight(plan, output_directory, execution_run=True)
    print(f"Run artifacts initialized at {output_directory.resolve()}", flush=True)
    attempts: list[dict[str, Any]] = []
    for index, model_name in enumerate(models):
        print(
            f"Semantic extraction model attempt {index + 1}/{len(models)}: "
            f"{model_name}",
            flush=True,
        )
        extractor = AdkSemanticExtractor(
            model_name,
            api_key=settings.models.api_key.get_secret_value(),
            max_attempts=settings.source_discovery.classifier_max_attempts,
            backoff_base_seconds=(
                settings.source_discovery.classifier_backoff_base_seconds
            ),
            max_backoff_seconds=(
                settings.source_discovery.classifier_max_backoff_seconds
            ),
            retry_jitter_ratio=(
                settings.source_discovery.classifier_retry_jitter_ratio
            ),
        )
        service = SemanticExtractionService(
            extractor=extractor,
            repository=InMemorySemanticExtractionRepository(),
            settings=settings.semantic_extraction,
            model_name=model_name,
        )
        try:
            result = await service.extract(
                bundle, discovery, retrieved_at=_retrieved_at(case_directory)
            )
        except Exception as exc:
            attempts.append(_attempt(model_name, extractor, exc))
            _write_json(output_directory / "model_attempts.json", attempts)
            if is_retryable_api_error(exc) and index + 1 < len(models):
                print(
                    f"Model {model_name} exhausted retries; falling back to "
                    f"{models[index + 1]}.",
                    flush=True,
                )
                continue
            _write_failure(output_directory, attempts, exc)
            raise SemanticExtractionRunFailed(output_directory, exc) from None
        attempts.append(_attempt(model_name, extractor, None))
        _write_json(output_directory / "model_attempts.json", attempts)
        _write_result(result, output_directory)
        print(
            f"Model {model_name} completed: "
            f"{extractor.usage.request_attempts} request attempt(s), "
            f"{extractor.usage.total_tokens} total token(s)",
            flush=True,
        )
        return output_directory
    raise AssertionError("semantic extraction model sequence exhausted")


def _write_preflight(
    plan: SemanticExtractionPlan,
    output_directory: Path,
    *,
    execution_run: bool,
) -> None:
    output_directory.mkdir(parents=True, exist_ok=True)
    (output_directory / "extraction_plan.json").write_text(
        plan.model_dump_json(indent=2), encoding="utf-8"
    )
    _write_json(output_directory / "evidence_catalog.json", plan.evidence_catalog)
    _write_json(output_directory / "field_batches.json", plan.batches)
    (output_directory / "selected_for_llm.md").write_text(
        _render_selected(plan, execution_run=execution_run), encoding="utf-8"
    )
    estimate = _cost_estimate(plan)
    _write_json(output_directory / "cost_estimate.json", estimate)
    mode = "LLM EXECUTION" if execution_run else "PREFLIGHT ONLY"
    (output_directory / "summary.txt").write_text(
        "\n".join(
            (
                f"MODE: {mode}",
                f"Source-discovery product: {plan.product.value}",
                f"Evidence items: {len(plan.evidence_catalog)}",
                f"Uncached LLM batches: {len(plan.batches)}",
                f"Cached batches: {len(plan.cache_hits)}",
                f"Requested fields: {sum(len(batch.fields) for batch in plan.batches)}",
                f"Estimated input tokens: {estimate['estimated_input_tokens']}",
                f"Estimated output tokens: {estimate['estimated_output_tokens']}",
                f"Estimated cost (USD): {estimate['estimated_cost_usd']:.6f}",
                "selected_for_llm.md shows the exact bounded evidence packets.",
            )
        )
        + "\n",
        encoding="utf-8",
    )


def _write_result(
    result: SemanticExtractionResult, output_directory: Path
) -> None:
    (output_directory / "semantic_extraction_result.json").write_text(
        result.model_dump_json(indent=2), encoding="utf-8"
    )
    (output_directory / "loan_product.json").write_text(
        result.loan_product.model_dump_json(indent=2), encoding="utf-8"
    )
    _write_json(output_directory / "batch_results.json", result.batch_results)
    (output_directory / "extraction_results.md").write_text(
        _render_results(result), encoding="utf-8"
    )


def _render_selected(
    plan: SemanticExtractionPlan, *, execution_run: bool
) -> str:
    lines = [
        "# Semantic extraction LLM input",
        "",
        (
            "These packets were selected for this numbered LLM run."
            if execution_run
            else "Preflight only: Gemini was not invoked."
        ),
        "",
    ]
    for batch in plan.batches:
        lines.extend((f"## {batch.id}: {batch.group}", ""))
        lines.append("Fields: " + ", ".join(field.value for field in batch.fields))
        lines.append("")
        for item in batch.evidence:
            lines.extend(
                (
                    f"### `{item.evidence_id}`",
                    "",
                    f"Source item: `{item.source_item_id}`",
                    f"Role / authority: `{item.role.value}` / `{item.authority.value}`",
                    f"Section: {item.section or '(none)'}",
                    "",
                    "```text",
                    item.content,
                    "```",
                    "",
                )
            )
    return "\n".join(lines)


def _render_results(result: SemanticExtractionResult) -> str:
    lines = ["# Semantic extraction results", ""]
    for response in result.batch_results:
        for item in response.results:
            lines.extend(
                (
                    f"## {item.field.value}",
                    "",
                    f"Status: **{item.status.value}**",
                    "",
                    "```json",
                    json.dumps(item.value, ensure_ascii=False, indent=2),
                    "```",
                    "",
                )
            )
            for citation in item.evidence:
                lines.append(f"- `{citation.evidence_id}`: “{citation.quote}”")
            lines.append("")
    return "\n".join(lines)


def _cost_estimate(plan: SemanticExtractionPlan) -> dict[str, Any]:
    input_chars = sum(
        sum(len(item.content) for item in batch.evidence) for batch in plan.batches
    )
    input_tokens = (input_chars + 3) // 4
    output_tokens = sum(len(batch.fields) for batch in plan.batches) * 250
    price = get_model_price(plan.model_name)
    cost = (
        input_tokens * price.input_per_million_tokens_usd
        + output_tokens * price.output_per_million_tokens_usd
    ) / 1_000_000
    return {
        "model": plan.model_name,
        "estimated_input_tokens": input_tokens,
        "estimated_output_tokens": output_tokens,
        "estimated_cost_usd": cost,
        "pricing_source": price.source,
        "assumptions": "4 input characters/token and 250 output tokens/field",
    }


def _attempt(
    model_name: str, extractor: AdkSemanticExtractor, error: Exception | None
) -> dict[str, Any]:
    usage = extractor.usage
    price = get_model_price(model_name)
    cost = (
        usage.input_tokens * price.input_per_million_tokens_usd
        + usage.output_tokens * price.output_per_million_tokens_usd
    ) / 1_000_000
    return {
        "model": model_name,
        "status": "failed" if error else "succeeded",
        "request_attempts": usage.request_attempts,
        "application_retries": usage.application_retries,
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "thinking_tokens": usage.thinking_tokens,
        "total_tokens": usage.total_tokens,
        "cost_usd": cost,
        "error_type": type(error).__name__ if error else None,
        "http_status_code": getattr(error, "code", None),
        "message": str(error) if error else None,
    }


def _write_failure(
    output_directory: Path,
    attempts: list[dict[str, Any]],
    error: Exception,
) -> None:
    _write_json(
        output_directory / "failure.json",
        {
            "status": "failed",
            "error_type": type(error).__name__,
            "http_status_code": getattr(error, "code", None),
            "message": str(error),
            "model_attempts": attempts,
        },
    )


def _resolve_case(path: Path) -> tuple[Path, Path]:
    resolved = path.resolve()
    candidates = (
        resolved,
        resolved / "normalized_bundle.json",
        resolved / "normalization" / "normalized_bundle.json",
    )
    bundle = next((item for item in candidates if item.is_file()), None)
    if bundle is None:
        raise FileNotFoundError(f"No normalized_bundle.json found at {resolved}")
    case = bundle.parent.parent if bundle.parent.name == "normalization" else bundle.parent
    return bundle, case


def _resolve_discovery_result(case: Path, supplied: Path | None) -> Path:
    if supplied is not None:
        resolved = supplied.resolve()
        if not resolved.is_file():
            raise FileNotFoundError(resolved)
        return resolved
    matches = sorted(
        (case / "source_discovery").glob("llm_run_*/source_discovery_result.json")
    )
    if not matches:
        raise FileNotFoundError(
            "No successful source_discovery_result.json found; pass "
            "--source-discovery-result explicitly"
        )
    return matches[-1]


def _retrieved_at(case: Path) -> datetime:
    artifact_path = case / "output" / "page_artifact.json"
    if artifact_path.is_file():
        value = json.loads(artifact_path.read_text(encoding="utf-8")).get(
            "retrieved_at"
        )
        if value:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
    return datetime.now(UTC)


def _model_sequence(primary: str, fallbacks: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys((primary, *fallbacks)))


def _next_run_directory(parent: Path) -> Path:
    parent.mkdir(parents=True, exist_ok=True)
    for index in range(100_000):
        candidate = parent / f"llm_run_{index:03d}"
        try:
            candidate.mkdir()
        except FileExistsError:
            continue
        return candidate
    raise RuntimeError(f"No available LLM run directory below {parent}")


def _write_json(path: Path, value: Any) -> None:
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    elif isinstance(value, tuple):
        value = [
            item.model_dump(mode="json") if hasattr(item, "model_dump") else item
            for item in value
        ]
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def _configure_terminal_logging() -> None:
    """Show this command's extraction progress without enabling noisy SDK logs."""
    service_logger = logging.getLogger(SEMANTIC_EXTRACTION_LOGGER)
    service_logger.setLevel(logging.INFO)
    service_logger.propagate = False
    if not service_logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
        service_logger.addHandler(handler)


def main() -> int:
    _configure_terminal_logging()
    parser = argparse.ArgumentParser(description="Inspect or run semantic extraction")
    parser.add_argument("case_path", type=Path)
    parser.add_argument("--source-discovery-result", type=Path)
    parser.add_argument("--execute-llm", action="store_true")
    args = parser.parse_args()
    try:
        output = asyncio.run(
            demonstrate(
                args.case_path,
                source_discovery_result=args.source_discovery_result,
                execute_llm=args.execute_llm,
            )
        )
    except SemanticExtractionRunFailed as exc:
        print(
            f"Semantic extraction failed ({type(exc.error).__name__}, HTTP "
            f"{getattr(exc.error, 'code', None)}). See {exc.output_directory / 'failure.json'}",
            file=sys.stderr,
        )
        return 1
    except Exception as exc:
        print(f"Semantic extraction could not start: {exc}", file=sys.stderr)
        return 1
    print(f"Semantic extraction artifacts written to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
