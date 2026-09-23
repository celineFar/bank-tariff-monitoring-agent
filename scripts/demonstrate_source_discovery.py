from __future__ import annotations

import argparse
import asyncio
import json
import math
import sys
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from app.config import SourceDiscoverySettings, load_settings
from app.domain.models import ProductType
from app.domain.normalization import NormalizedSourceBundle
from app.domain.source_discovery import (
    DiscoveryCandidate,
    SourceAssessment,
    SourceDiscoveryPlan,
    SourceDiscoveryResult,
)
from app.services.discovery_classifier import (
    SOURCE_DISCOVERY_INSTRUCTION,
    AdkSourceDiscoveryClassifier,
    ClassifierUsage,
    build_classifier_prompt,
    is_model_fallback_error,
    is_retryable_api_error,
)
from app.services.model_pricing import (
    ModelPrice,
    enforce_model_price_cap,
    get_model_price,
    model_sequence,
)
from app.services.source_discovery import (
    InMemorySourceDiscoveryRepository,
    SourceDiscoveryService,
)


class SourceDiscoveryRunFailed(RuntimeError):
    def __init__(self, output_directory: Path, error: Exception) -> None:
        super().__init__(str(error))
        self.output_directory = output_directory
        self.error_type = type(error).__name__
        self.http_status_code = getattr(error, "code", None)
        self.api_status = getattr(error, "status", None)


async def demonstrate(
    case_path: Path, product: ProductType, *, execute_llm: bool = False
) -> Path:
    bundle_path, case_directory = _resolve_case(case_path)
    bundle = NormalizedSourceBundle.model_validate_json(
        bundle_path.read_text(encoding="utf-8")
    )
    settings = load_settings()
    repository = InMemorySourceDiscoveryRepository()
    planning_service = SourceDiscoveryService(
        classifier=None,
        repository=repository,
        settings=settings.source_discovery,
        model_name=settings.models.generation_model,
    )
    plan = await planning_service.plan(bundle, product)
    if not execute_llm:
        return write_preflight_bundle(
            plan,
            settings=settings.source_discovery,
            output_directory=case_directory / "source_discovery" / "preflight",
        )

    if settings.models.api_key is None:
        raise RuntimeError(
            "GEMINI_API_KEY is required for --execute-llm; set it in .env or the process environment"
        )
    models = model_sequence(
        settings.models.generation_model,
        settings.source_discovery.fallback_model_names,
    )
    enforce_model_price_cap(
        models,
        max_price_per_million_tokens_usd=(
            settings.source_discovery.max_price_per_million_tokens_usd
        ),
    )
    output_directory = _next_run_directory(case_directory / "source_discovery")
    write_preflight_bundle(
        plan,
        settings=settings.source_discovery,
        output_directory=output_directory,
        execution_run=True,
    )
    attempts: list[dict[str, Any]] = []
    for model_index, model_name in enumerate(models):
        print(
            f"Source discovery model attempt {model_index + 1}/{len(models)}: "
            f"{model_name}",
            flush=True,
        )
        attempt_repository = InMemorySourceDiscoveryRepository()
        classifier = _build_classifier(
            model_name,
            settings.models.api_key.get_secret_value(),
            settings.source_discovery,
        )
        service = SourceDiscoveryService(
            classifier=classifier,
            repository=attempt_repository,
            settings=settings.source_discovery,
            model_name=model_name,
        )
        model_plan = await service.plan(bundle, product)
        try:
            result = await service.discover(bundle, product)
        except Exception as exc:
            attempts.append(_model_attempt(model_name, classifier.usage, exc))
            _write_model_attempts(output_directory, attempts)
            has_fallback = model_index + 1 < len(models)
            if is_model_fallback_error(exc) and has_fallback:
                next_model = models[model_index + 1]
                print(
                    f"Model {model_name} exhausted retries with HTTP "
                    f"{getattr(exc, 'code', None)}; falling back to {next_model}.",
                    flush=True,
                )
                continue
            _write_failed_run(output_directory, attempts, exc)
            raise SourceDiscoveryRunFailed(output_directory, exc) from None

        attempts.append(_model_attempt(model_name, classifier.usage, None))
        _write_model_attempts(output_directory, attempts)
        write_preflight_bundle(
            model_plan,
            settings=settings.source_discovery,
            output_directory=output_directory,
            execution_run=True,
        )
        write_live_bundle(
            model_plan,
            result,
            attempts,
            settings=settings.source_discovery,
            output_directory=output_directory,
        )
        if model_index:
            print(
                f"Source discovery completed with fallback model {model_name}.",
                flush=True,
            )
        return output_directory
    raise AssertionError("source discovery model sequence exhausted unexpectedly")


def _build_classifier(
    model_name: str, api_key: str, settings: SourceDiscoverySettings
) -> AdkSourceDiscoveryClassifier:
    return AdkSourceDiscoveryClassifier(
        model_name,
        api_key=api_key,
        max_attempts=settings.classifier_max_attempts,
        backoff_base_seconds=settings.classifier_backoff_base_seconds,
        max_backoff_seconds=settings.classifier_max_backoff_seconds,
        retry_jitter_ratio=settings.classifier_retry_jitter_ratio,
    )


def _write_failed_run(
    output_directory: Path,
    attempts: list[dict[str, Any]],
    error: Exception,
) -> None:
    failure = {
        "status": "failed",
        "error_type": type(error).__name__,
        "http_status_code": getattr(error, "code", None),
        "api_status": getattr(error, "status", None),
        "message": str(error),
        "model_attempts": attempts,
    }
    (output_directory / "failure.json").write_text(
        json.dumps(failure, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output_directory / "summary.txt").write_text(
        "\n".join(
            (
                "MODE: LLM EXECUTION FAILED",
                f"Error type: {failure['error_type']}",
                f"HTTP status: {failure['http_status_code']}",
                f"API status: {failure['api_status']}",
                f"Models attempted: {', '.join(item['model'] for item in attempts)}",
                "Application request attempts: "
                f"{sum(item['request_attempts'] for item in attempts)}",
                "Application-level retries: "
                f"{sum(item['application_retries'] for item in attempts)}",
                "See failure.json for details. The preflight directory was not modified.",
                "Rerunning will create a new llm_run_NNN directory.",
            )
        )
        + "\n",
        encoding="utf-8",
    )


def _model_attempt(
    model_name: str, usage: ClassifierUsage, error: Exception | None
) -> dict[str, Any]:
    cost = _actual_cost(usage, get_model_price(model_name))
    return {
        "model": model_name,
        "status": "failed" if error else "succeeded",
        "retryable_failure": is_retryable_api_error(error) if error else False,
        "error_type": type(error).__name__ if error else None,
        "http_status_code": getattr(error, "code", None),
        "api_status": getattr(error, "status", None),
        "message": str(error) if error else None,
        **cost,
    }


def _write_model_attempts(
    output_directory: Path, attempts: list[dict[str, Any]]
) -> None:
    (output_directory / "model_attempts.json").write_text(
        json.dumps(attempts, ensure_ascii=False, indent=2), encoding="utf-8"
    )


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


def write_preflight_bundle(
    plan: SourceDiscoveryPlan,
    *,
    settings: SourceDiscoverySettings,
    output_directory: Path,
    execution_run: bool = False,
) -> Path:
    output_directory.mkdir(parents=True, exist_ok=True)
    cost_estimate = _cost_estimate(plan, settings)
    (output_directory / "discovery_plan.json").write_text(
        plan.model_dump_json(indent=2), encoding="utf-8"
    )
    _write_json(
        output_directory / "deterministic_assessments.json",
        plan.deterministic_assessments,
    )
    _write_json(output_directory / "cache_hits.json", plan.cache_hits)
    _write_json(output_directory / "llm_candidates.json", plan.llm_candidates)
    _write_json(output_directory / "llm_batches.json", plan.batches)
    (output_directory / "cost_estimate.json").write_text(
        json.dumps(cost_estimate, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output_directory / "selected_for_llm.md").write_text(
        _render_selected(plan, execution_run=execution_run), encoding="utf-8"
    )
    (output_directory / "summary.txt").write_text(
        _summary(plan, cost_estimate), encoding="utf-8"
    )
    return output_directory


def write_live_bundle(
    plan: SourceDiscoveryPlan,
    result: SourceDiscoveryResult,
    model_attempts: list[dict[str, Any]],
    *,
    settings: SourceDiscoverySettings,
    output_directory: Path,
) -> None:
    estimated_cost = _cost_estimate(plan, settings)
    actual_cost = _combined_actual_cost(model_attempts, plan.model_name)
    (output_directory / "source_discovery_result.json").write_text(
        result.model_dump_json(indent=2), encoding="utf-8"
    )
    _write_json(output_directory / "assessments.json", result.assessments)
    (output_directory / "extraction_context.json").write_text(
        result.extraction_context.model_dump_json(indent=2), encoding="utf-8"
    )
    (output_directory / "actual_usage_and_cost.json").write_text(
        json.dumps(actual_cost, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output_directory / "classification_results.md").write_text(
        _render_classification_results(plan, result), encoding="utf-8"
    )
    (output_directory / "summary.txt").write_text(
        _summary(plan, estimated_cost, actual=actual_cost), encoding="utf-8"
    )


def _render_classification_results(
    plan: SourceDiscoveryPlan, result: SourceDiscoveryResult
) -> str:
    candidates = {item.source_id: item for item in plan.llm_candidates}
    direct = [item for item in result.assessments if item.inherited_from is None]
    model_decisions = [item for item in direct if item.source_id in candidates]
    other_decisions = [item for item in direct if item.source_id not in candidates]
    inherited_count = sum(
        item.inherited_from is not None for item in result.assessments
    )

    parts = [
        "# Source discovery classification results",
        "",
        f"- Product: `{result.product.value}`",
        f"- Model: `{result.model_name}`",
        f"- Direct LLM/cache classification units: {len(model_decisions)}",
        f"- Deterministic decisions: {len(other_decisions)}",
        f"- Child assessments represented through inheritance: {inherited_count}",
        "",
        "This report shows direct classification units only. Inherited child records ",
        "remain available in `assessments.json`.",
        "",
    ]
    groups = (
        ("Relevant", "relevant"),
        ("Possibly relevant", "possibly_relevant"),
        ("Irrelevant", "irrelevant"),
    )
    for heading, relevance in groups:
        selected = [
            item for item in model_decisions if item.relevance.value == relevance
        ]
        parts.extend((f"## {heading} ({len(selected)})", ""))
        if not selected:
            parts.extend(("No items.", ""))
            continue
        for assessment in selected:
            parts.extend(
                _render_assessment(
                    assessment,
                    candidate=candidates.get(assessment.source_id),
                )
            )

    parts.extend(
        (f"## Deterministic and reused decisions ({len(other_decisions)})", "")
    )
    if not other_decisions:
        parts.extend(("No items.", ""))
    else:
        for assessment in other_decisions:
            parts.extend(_render_assessment(assessment, candidate=None))
    return "\n".join(parts).rstrip() + "\n"


def _render_assessment(
    assessment: SourceAssessment, *, candidate: DiscoveryCandidate | None
) -> list[str]:
    title = candidate.title if candidate is not None else assessment.source_id
    inherited_members = len(candidate.member_source_ids) if candidate is not None else 0
    lines = [
        f"### {title}",
        "",
        f"- Source ID: `{assessment.source_id}`",
        f"- Decision source: `{assessment.decision_source.value}`",
        f"- Product association: `{assessment.product_association.value}`",
        f"- Relevance: `{assessment.relevance.value}`",
        f"- Role: `{assessment.role.value}`",
        f"- Authority: `{assessment.authority.value}`",
        f"- Temporal status: `{assessment.temporal_status.value}`",
        f"- Child items inheriting this decision: {inherited_members}",
        f"- Reason: {assessment.reason}",
    ]
    if candidate is not None:
        lines.extend(
            (
                f"- Scope: `{candidate.scope.value}`",
                f"- Heading path: {' > '.join(candidate.heading_path) or '(none)'}",
                f"- Source type: `{candidate.source_type.value}`",
            )
        )
    if assessment.conditions:
        lines.append(f"- Conditions: {'; '.join(assessment.conditions)}")
    if assessment.effective_periods:
        periods = "; ".join(period.raw for period in assessment.effective_periods)
        lines.append(f"- Effective periods: {periods}")
    if candidate is not None:
        excerpt = candidate.context_text[:1000]
        if len(candidate.context_text) > len(excerpt):
            excerpt += "\n[excerpt truncated]"
        lines.extend(("", "```text", excerpt, "```"))
    lines.append("")
    return lines


def _resolve_case(path: Path) -> tuple[Path, Path]:
    resolved = path.resolve()
    candidates = (
        resolved,
        resolved / "normalized_bundle.json",
        resolved / "normalization" / "normalized_bundle.json",
    )
    bundle_path = next(
        (candidate for candidate in candidates if candidate.is_file()), None
    )
    if bundle_path is None:
        raise FileNotFoundError(
            f"No normalized_bundle.json found at or below {resolved}"
        )
    case_directory = (
        bundle_path.parent.parent
        if bundle_path.parent.name == "normalization"
        else bundle_path.parent
    )
    return bundle_path, case_directory


def _write_json(path: Path, values: tuple[object, ...]) -> None:
    serialized = [
        value.model_dump(mode="json") if isinstance(value, BaseModel) else value
        for value in values
    ]
    path.write_text(
        json.dumps(serialized, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _render_selected(plan: SourceDiscoveryPlan, *, execution_run: bool = False) -> str:
    parts = [
        "# Source discovery LLM preflight",
        "",
        "This is the exact bounded material selected for semantic classification. ",
        (
            "This material was sent to Gemini during this numbered execution run."
            if execution_run
            else "The demonstration script did not invoke Gemini."
        ),
        "",
    ]
    for batch in plan.batches:
        parts.extend((f"## {batch.id}", ""))
        for item in batch.items:
            parts.extend(
                (
                    f"### `{item.source_id}`",
                    "",
                    f"- Scope: `{item.scope.value}`",
                    f"- Source type: `{item.source_type.value}`",
                    f"- Title: {item.title}",
                    f"- Heading path: {' > '.join(item.heading_path) or '(none)'}",
                    f"- MIME: `{item.mime_type}`",
                    f"- Extraction method: `{item.extraction_method}`",
                    f"- Prior structural assessment: {'yes' if item.prior_assessment else 'no'}",
                    "",
                    "```text",
                    item.content,
                    "```",
                    "",
                )
            )
    return "\n".join(parts).rstrip() + "\n"


def _cost_estimate(
    plan: SourceDiscoveryPlan, settings: SourceDiscoverySettings
) -> dict[str, Any]:
    price = get_model_price(plan.model_name)
    prompt_characters = sum(
        len(SOURCE_DISCOVERY_INSTRUCTION) + len(build_classifier_prompt(batch))
        for batch in plan.batches
    )
    input_tokens = math.ceil(
        prompt_characters / settings.estimated_chars_per_input_token
    )
    item_count = sum(len(batch.items) for batch in plan.batches)
    output_tokens = item_count * settings.estimated_output_tokens_per_item
    input_cost = input_tokens * price.input_per_million_tokens_usd / 1_000_000
    output_cost = output_tokens * price.output_per_million_tokens_usd / 1_000_000
    return {
        "currency": "USD",
        "model": plan.model_name,
        "pricing_basis": price.basis,
        "pricing_starts_on": price.starts_on.isoformat(),
        "pricing_effective_through": (
            price.ends_on.isoformat() if price.ends_on else None
        ),
        "pricing_source": price.source,
        "input_price_per_million_tokens": price.input_per_million_tokens_usd,
        "output_price_per_million_tokens": price.output_per_million_tokens_usd,
        "estimated_prompt_characters": prompt_characters,
        "estimated_chars_per_input_token": (settings.estimated_chars_per_input_token),
        "estimated_input_tokens": input_tokens,
        "assumed_output_tokens_per_item": (settings.estimated_output_tokens_per_item),
        "candidate_item_count": item_count,
        "estimated_output_tokens": output_tokens,
        "estimated_input_cost_usd": round(input_cost, 8),
        "estimated_output_cost_usd": round(output_cost, 8),
        "estimated_total_cost_usd": round(input_cost + output_cost, 8),
        "actual_cost": None,
        "notes": [
            "No model call occurred; all token and cost values are estimates.",
            "Input tokens use a configurable characters-per-token approximation.",
            "Provider-added schema and transport overhead are not included.",
            "Output tokens include a configurable per-item assumption; actual output and thinking tokens may differ.",
            "Free-tier usage may have zero billed cost.",
        ],
    }


def _actual_cost(usage: ClassifierUsage, price: ModelPrice) -> dict[str, Any]:
    billed_output_tokens = usage.output_tokens + usage.thinking_tokens
    input_cost = usage.input_tokens * price.input_per_million_tokens_usd / 1_000_000
    output_cost = billed_output_tokens * price.output_per_million_tokens_usd / 1_000_000
    return {
        "currency": "USD",
        "model": price.model,
        "pricing_basis": price.basis,
        "pricing_source": price.source,
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "thinking_tokens": usage.thinking_tokens,
        "billed_output_tokens": billed_output_tokens,
        "total_tokens_reported": usage.total_tokens,
        "request_attempts": usage.request_attempts,
        "application_retries": usage.application_retries,
        "input_cost_usd": round(input_cost, 8),
        "output_cost_usd": round(output_cost, 8),
        "total_cost_usd": round(input_cost + output_cost, 8),
        "note": "Calculated from API-reported usage; provider billing remains authoritative.",
    }


def _combined_actual_cost(
    attempts: list[dict[str, Any]], selected_model: str
) -> dict[str, Any]:
    return {
        "currency": "USD",
        "selected_model": selected_model,
        "fallback_transitions": max(0, len(attempts) - 1),
        "models_attempted": [item["model"] for item in attempts],
        "input_tokens": sum(item["input_tokens"] for item in attempts),
        "output_tokens": sum(item["output_tokens"] for item in attempts),
        "thinking_tokens": sum(item["thinking_tokens"] for item in attempts),
        "billed_output_tokens": sum(item["billed_output_tokens"] for item in attempts),
        "total_tokens_reported": sum(
            item["total_tokens_reported"] for item in attempts
        ),
        "request_attempts": sum(item["request_attempts"] for item in attempts),
        "application_retries": sum(item["application_retries"] for item in attempts),
        "input_cost_usd": round(sum(item["input_cost_usd"] for item in attempts), 8),
        "output_cost_usd": round(sum(item["output_cost_usd"] for item in attempts), 8),
        "total_cost_usd": round(sum(item["total_cost_usd"] for item in attempts), 8),
        "attempts": attempts,
        "note": "Includes all reported usage from failed and successful model attempts; provider billing remains authoritative.",
    }


def _summary(
    plan: SourceDiscoveryPlan,
    cost: dict[str, Any],
    *,
    actual: dict[str, Any] | None = None,
) -> str:
    selected_chars = sum(
        len(item.content) for batch in plan.batches for item in batch.items
    )
    prior_hints = sum(
        item.prior_assessment is not None
        for batch in plan.batches
        for item in batch.items
    )
    lines = [
        (
            "MODE: LLM EXECUTION -- Gemini was called."
            if actual
            else "MODE: PREFLIGHT ONLY -- Gemini was not called."
        ),
        f"Product: {plan.product.value}",
        f"Canonical URL: {plan.canonical_url}",
        f"Input acquisition hash: {plan.input_content_hash}",
        f"Policy version: {plan.policy_version}",
        f"Prompt version: {plan.prompt_version}",
        f"Configured model: {plan.model_name}",
        f"Deterministic assessments: {len(plan.deterministic_assessments)}",
        f"Exact cache hits: {len(plan.cache_hits)}",
        f"Candidates selected for LLM: {len(plan.llm_candidates)}",
        f"LLM batches that would be sent: {len(plan.batches)}",
        f"Characters selected for LLM: {selected_chars}",
        f"Estimated prompt characters (including instructions): {cost['estimated_prompt_characters']}",
        f"Estimated input tokens: {cost['estimated_input_tokens']}",
        f"Assumed output tokens: {cost['estimated_output_tokens']}",
        "Stored paid-tier price: "
        f"${cost['input_price_per_million_tokens']:.2f}/1M input tokens; "
        f"${cost['output_price_per_million_tokens']:.2f}/1M output tokens",
        f"Pricing effective through: {cost['pricing_effective_through']}",
        f"Estimated input cost (USD): ${cost['estimated_input_cost_usd']:.8f}",
        f"Estimated output cost (USD): ${cost['estimated_output_cost_usd']:.8f}",
        f"Estimated total cost (USD): ${cost['estimated_total_cost_usd']:.8f}",
        (
            "Cost status: API usage captured; provider billing remains authoritative"
            if actual
            else "Cost status: estimate only -- no model call occurred; free-tier billing may be $0"
        ),
        f"Changed-layout prior hints: {prior_hints}",
        f"Child items covered by inheritance: {plan.inherited_item_count}",
    ]
    if actual:
        lines.extend(
            (
                f"Actual API input tokens: {actual['input_tokens']}",
                f"Actual API output tokens: {actual['output_tokens']}",
                f"Actual API thinking tokens: {actual['thinking_tokens']}",
                f"Models attempted: {', '.join(actual['models_attempted'])}",
                f"Selected model: {actual['selected_model']}",
                f"Fallback transitions: {actual['fallback_transitions']}",
                f"Application-level retries: {actual['application_retries']}",
                f"Calculated actual cost (USD): ${actual['total_cost_usd']:.8f}",
            )
        )
    return "\n".join(lines) + "\n"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Preview source-discovery inputs, or explicitly execute the bounded "
            "Gemini classifier in a separate incrementing run directory."
        )
    )
    parser.add_argument(
        "case",
        type=Path,
        help=(
            "A case_NNN directory, its normalization directory, or "
            "normalized_bundle.json"
        ),
    )
    parser.add_argument(
        "--product",
        required=True,
        choices=[product.value for product in ProductType.__members__.values()],
        help="Canonical product family being assessed",
    )
    parser.add_argument(
        "--execute-llm",
        action="store_true",
        help=(
            "Call Gemini and write llm_run_NNN; without this flag the script only "
            "updates the preflight directory"
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    try:
        output_directory = asyncio.run(
            demonstrate(
                args.case,
                ProductType(args.product),
                execute_llm=args.execute_llm,
            )
        )
    except SourceDiscoveryRunFailed as exc:
        status = (
            f"HTTP {exc.http_status_code} / {exc.api_status}"
            if exc.http_status_code
            else exc.error_type
        )
        print(f"Source discovery failed: {status}.", file=sys.stderr)
        print(
            f"Failure details: {(exc.output_directory / 'failure.json').resolve()}",
            file=sys.stderr,
        )
        print(
            "No Python traceback is shown because this was a handled provider/API failure.",
            file=sys.stderr,
        )
        return 1
    mode = "LLM run" if args.execute_llm else "preflight"
    print(f"Source discovery {mode} saved to {output_directory.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
