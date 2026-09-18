from __future__ import annotations

import argparse
import asyncio
import json
import math
from pathlib import Path
from typing import Any

from app.config import SourceDiscoverySettings, load_settings
from app.domain.models import ProductType
from app.domain.normalization import NormalizedSourceBundle
from app.domain.source_discovery import SourceDiscoveryPlan
from app.services.discovery_classifier import (
    SOURCE_DISCOVERY_INSTRUCTION,
    build_classifier_prompt,
)
from app.services.source_discovery import (
    InMemorySourceDiscoveryRepository,
    SourceDiscoveryService,
)


async def demonstrate(case_path: Path, product: ProductType) -> Path:
    bundle_path, case_directory = _resolve_case(case_path)
    bundle = NormalizedSourceBundle.model_validate_json(
        bundle_path.read_text(encoding="utf-8")
    )
    settings = load_settings()
    service = SourceDiscoveryService(
        classifier=None,
        repository=InMemorySourceDiscoveryRepository(),
        settings=settings.source_discovery,
        model_name=settings.models.generation_model,
    )
    plan = await service.plan(bundle, product)
    return write_preflight_bundle(
        plan,
        settings=settings.source_discovery,
        output_directory=case_directory / "source_discovery" / "preflight",
    )


def write_preflight_bundle(
    plan: SourceDiscoveryPlan,
    *,
    settings: SourceDiscoverySettings,
    output_directory: Path,
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
        _render_selected(plan), encoding="utf-8"
    )
    (output_directory / "summary.txt").write_text(
        _summary(plan, cost_estimate), encoding="utf-8"
    )
    return output_directory


def _resolve_case(path: Path) -> tuple[Path, Path]:
    resolved = path.resolve()
    candidates = (
        resolved,
        resolved / "normalized_bundle.json",
        resolved / "normalization" / "normalized_bundle.json",
    )
    bundle_path = next((candidate for candidate in candidates if candidate.is_file()), None)
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
        value.model_dump(mode="json") if hasattr(value, "model_dump") else value
        for value in values
    ]
    path.write_text(
        json.dumps(serialized, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _render_selected(plan: SourceDiscoveryPlan) -> str:
    parts = [
        "# Source discovery LLM preflight",
        "",
        "This is the exact bounded material selected for semantic classification. ",
        "The demonstration script did not invoke Gemini.",
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
    prompt_characters = sum(
        len(SOURCE_DISCOVERY_INSTRUCTION) + len(build_classifier_prompt(batch))
        for batch in plan.batches
    )
    input_tokens = math.ceil(
        prompt_characters / settings.estimated_chars_per_input_token
    )
    item_count = sum(len(batch.items) for batch in plan.batches)
    output_tokens = item_count * settings.estimated_output_tokens_per_item
    input_cost = (
        input_tokens * settings.input_price_per_million_tokens_usd / 1_000_000
    )
    output_cost = (
        output_tokens * settings.output_price_per_million_tokens_usd / 1_000_000
    )
    return {
        "currency": "USD",
        "model": plan.model_name,
        "pricing_basis": "Gemini Developer API paid tier",
        "pricing_effective_through": settings.pricing_effective_through,
        "pricing_source": "https://ai.google.dev/gemini-api/docs/pricing",
        "input_price_per_million_tokens": (
            settings.input_price_per_million_tokens_usd
        ),
        "output_price_per_million_tokens": (
            settings.output_price_per_million_tokens_usd
        ),
        "estimated_prompt_characters": prompt_characters,
        "estimated_chars_per_input_token": (
            settings.estimated_chars_per_input_token
        ),
        "estimated_input_tokens": input_tokens,
        "assumed_output_tokens_per_item": (
            settings.estimated_output_tokens_per_item
        ),
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


def _summary(plan: SourceDiscoveryPlan, cost: dict[str, Any]) -> str:
    selected_chars = sum(
        len(item.content) for batch in plan.batches for item in batch.items
    )
    prior_hints = sum(
        item.prior_assessment is not None
        for batch in plan.batches
        for item in batch.items
    )
    lines = (
        "MODE: PREFLIGHT ONLY -- Gemini was not called.",
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
        "Cost status: estimate only -- no model call occurred; free-tier billing may be $0",
        f"Changed-layout prior hints: {prior_hints}",
        f"Child items covered by inheritance: {plan.inherited_item_count}",
    )
    return "\n".join(lines) + "\n"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Show the bounded source components selected for Gemini without "
            "performing any model call."
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
        choices=[product.value for product in ProductType],
        help="Canonical product family being assessed",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    output_directory = asyncio.run(
        demonstrate(args.case, ProductType(args.product))
    )
    print(f"Source discovery preflight saved to {output_directory.resolve()}")


if __name__ == "__main__":
    main()
