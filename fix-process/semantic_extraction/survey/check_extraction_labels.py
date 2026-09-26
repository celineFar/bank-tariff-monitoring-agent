"""Check semantic extraction against the field labels in `data/seed-extraction-labels.json`.

    uv run python fix-process/semantic_extraction/survey/check_extraction_labels.py \
        --extractor fake|gemini [--seed S ...] [--pdfs] [--max-usd 1.5] [--label after]

Sources are replayed (see `replay.py`): no discovery or transcription call is made.
The extractor is:

- `fake`: answers every requested field `not_stated`, except the category, which it
  answers from the catalog. It checks the plumbing and costs nothing.
- `gemini`: the real `AdkSemanticExtractor`, with `GEMINI_API_KEY` from the environment,
  behind a spend guard. Before each call the guard estimates the call's cost from the
  prompt size; it refuses the call if the running spend plus the estimate would pass
  `--max-usd`. Actual token use and cost are reported.

Each labelled field is scored:

- `match`: the status agrees and every expected number (or substring, or enum value) is in
  the extracted value;
- `wrong_value`: found, but an expected number, substring or value is missing;
- `missing`: labelled found, extracted not_stated (or absent);
- `spurious`: labelled not_stated, extracted found;
- `review`: the field went to human review;
- `ambiguous`: extracted ambiguous or conflicting.

Numbers in the value not in the label's `numbers` or `may` are reported as
`extra_numbers` (informational). With `--label`, the report goes to
`data/extraction-check-<label>.json`.
"""

from __future__ import annotations

import argparse
import asyncio
import inspect
import json
import os
import sys
from collections import Counter
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import replay

from app.config import load_settings
from app.domain.semantic_extraction import (
    ExtractionBatch,
    ExtractionBatchResponse,
    ExtractionField,
    ExtractionStatus,
    ModelCitation,
    ModelFieldResult,
)
from app.services.html_parser import HtmlArtifactParser
from app.services.model_pricing import get_model_price
from app.services.semantic_extraction import (
    InMemorySemanticExtractionRepository,
    SemanticExtractionService,
    build_extraction_prompt,
)

BASE = Path(__file__).resolve().parents[1]
LABELS = json.loads((BASE / "data" / "seed-extraction-labels.json").read_text())
CHARS_PER_TOKEN = 3.5
ESTIMATED_OUTPUT_TOKENS = 2500


class FakeExtractor:
    """Plumbing only: `not_stated` everywhere, the category from the catalog."""

    def __init__(self, categories: dict[str, str]) -> None:
        self.categories = categories
        self.seed = ""
        self.calls = 0

    async def extract(self, batch: ExtractionBatch) -> ExtractionBatchResponse:
        self.calls += 1
        results = []
        for field in batch.fields:
            if field is ExtractionField.CATEGORY:
                item = batch.evidence[0]
                results.append(
                    ModelFieldResult(
                        field=field,
                        status=ExtractionStatus.FOUND,
                        value_json=json.dumps(self.categories[self.seed]),
                        evidence=(
                            ModelCitation(
                                evidence_id=item.evidence_id,
                                quote=item.content[:12],
                            ),
                        ),
                    )
                )
            else:
                results.append(
                    ModelFieldResult(field=field, status=ExtractionStatus.NOT_STATED)
                )
        return ExtractionBatchResponse(results=tuple(results))


class GuardedExtractor:
    """Refuses a call once the running spend plus its estimate passes the budget."""

    def __init__(self, inner: Any, price: Any, max_usd: float) -> None:
        self.inner = inner
        self.price = price
        self.max_usd = max_usd
        self.calls = 0
        self.refused = 0

    def spent_usd(self) -> float:
        usage = self.inner.usage
        return (
            usage.input_tokens * self.price.input_per_million_tokens_usd
            + (usage.output_tokens + usage.thinking_tokens)
            * self.price.output_per_million_tokens_usd
        ) / 1_000_000

    def estimate_usd(self, batch: ExtractionBatch) -> float:
        tokens = len(build_extraction_prompt(batch)) / CHARS_PER_TOKEN
        return (
            tokens * self.price.input_per_million_tokens_usd
            + ESTIMATED_OUTPUT_TOKENS * self.price.output_per_million_tokens_usd
        ) / 1_000_000

    async def extract(self, batch: ExtractionBatch) -> Any:
        if self.spent_usd() + self.estimate_usd(batch) > self.max_usd:
            self.refused += 1
            raise RuntimeError(
                f"spend guard: ${self.spent_usd():.4f} of ${self.max_usd}"
            )
        self.calls += 1
        return await self.inner.extract(batch)

    def __getattr__(self, name: str) -> Any:
        return getattr(self.inner, name)


def _numbers(value: Any) -> set[Decimal]:
    """Every number in a value, ignoring condition and free-text strings."""
    found: set[Decimal] = set()

    def walk(node: Any, key: str | None = None) -> None:
        if isinstance(node, bool) or node is None:
            return
        if isinstance(node, (int, float, Decimal)):
            found.add(Decimal(str(node)).normalize())
        elif isinstance(node, str):
            if key in {"conditions", "value", "formula", "description", "name"}:
                return
            try:
                found.add(Decimal(node).normalize())
            except InvalidOperation:
                return
        elif isinstance(node, dict):
            for child_key, child in node.items():
                if child_key == "conditions":
                    continue
                walk(child, child_key)
        elif isinstance(node, (list, tuple)):
            for child in node:
                walk(child, key)

    walk(value)
    return found


def _jsonable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, Decimal):
        return str(value)
    return value


def score_field(
    label: dict[str, Any], validated: Any, in_review: bool
) -> dict[str, Any]:
    if in_review:
        return {"outcome": "review"}
    status = validated.status.value if validated is not None else "not_stated"
    value = _jsonable(validated.value) if validated is not None else None
    if status in {"ambiguous", "conflicting"}:
        return {"outcome": "ambiguous", "status": status}
    if label["status"] == "not_stated":
        return {
            "outcome": "match" if status == "not_stated" else "spurious",
            "value": value,
        }
    if status != "found":
        return {"outcome": "missing"}
    numbers = _numbers(value)
    expected = {Decimal(str(n)).normalize() for n in label.get("numbers", [])}
    allowed = expected | {Decimal(str(n)).normalize() for n in label.get("may", [])}
    problems = []
    if expected - numbers:
        problems.append(f"missing numbers {sorted(str(n) for n in expected - numbers)}")
    if "contains" in label and not any(
        needle.casefold() in json.dumps(value, ensure_ascii=False).casefold()
        for needle in label["contains"]
    ):
        problems.append(f"none of {label['contains']}")
    if "value" in label and value != label["value"]:
        problems.append(f"value {value!r} != {label['value']!r}")
    return {
        "outcome": "wrong_value" if problems else "match",
        "problems": problems,
        "extra_numbers": sorted(str(n) for n in numbers - allowed),
        "value": value,
    }


async def _extract(service: SemanticExtractionService, replayed: Any) -> Any:
    """Call extraction with whichever signature this branch has."""
    parameters = inspect.signature(service.extract).parameters
    kwargs: dict[str, Any] = {"retrieved_at": datetime.now(UTC)}
    if "offering" in parameters:
        from app.domain.source_discovery import OfferingContext

        kwargs["offering"] = OfferingContext.from_catalog_entry(
            replayed.entry,
            page_title=replayed.bundle.documents[0].name,
            page_blocks=replayed.bundle.documents[0].blocks,
            catalog=replay.cdl._catalog_model(),
        )
    return await service.extract(replayed.bundle, replayed.discovery, **kwargs)


async def run(args: argparse.Namespace) -> dict[str, Any]:
    settings = load_settings()
    model = args.model or settings.models.generation_model
    parser = HtmlArtifactParser(settings.http.allowed_source_hosts)
    catalog = replay.catalog()
    seeds = args.seed or sorted(LABELS["seeds"])
    categories = {seed: LABELS["seeds"][seed]["category"] for seed in seeds}
    guard = None
    if args.extractor == "gemini":
        from app.services.semantic_extraction import AdkSemanticExtractor

        key = os.environ.get("GEMINI_API_KEY")
        if not key:
            raise SystemExit("GEMINI_API_KEY is required for --extractor gemini")
        guard = GuardedExtractor(
            AdkSemanticExtractor(model, api_key=key),
            get_model_price(model),
            args.max_usd,
        )
        extractor: Any = guard
    else:
        replay.forbid_gemini()
        extractor = FakeExtractor(categories)
    stored = await replay.stored_transcriptions() if args.pdfs else None
    report: dict[str, Any] = {"seeds": {}, "extractor": args.extractor, "model": model}
    totals: Counter[str] = Counter()
    for seed in seeds:
        replayed = await replay.load_seed(seed, parser, catalog, stored_pdfs=stored)
        if isinstance(extractor, FakeExtractor):
            extractor.seed = seed
        service = SemanticExtractionService(
            extractor,
            InMemorySemanticExtractionRepository(),
            settings.semantic_extraction,
            model_name=model,
        )
        try:
            result = await _extract(service, replayed)
        except Exception as exc:  # the report records it; the next seed still runs
            report["seeds"][seed] = {"error": f"{type(exc).__name__}: {exc}"[:500]}
            totals["seed_error"] += 1
            continue
        validated = {item.field.value: item for item in result.validated_fields}
        reviewed = {item.field.value for item in result.review_items}
        fields = {}
        for name, label in LABELS["seeds"][seed]["fields"].items():
            outcome = score_field(label, validated.get(name), name in reviewed)
            fields[name] = outcome
            totals[outcome["outcome"]] += 1
        report["seeds"][seed] = {
            "pdfs_added": replayed.pdfs_added,
            "pdfs_missing": replayed.pdfs_missing,
            "review_items": sorted(reviewed),
            "fields": fields,
        }
        print(
            f"{seed:32} "
            + " ".join(
                f"{outcome}={count}"
                for outcome, count in sorted(
                    Counter(v["outcome"] for v in fields.values()).items()
                )
            )
        )
    report["totals"] = dict(totals)
    if guard is not None:
        usage = guard.inner.usage
        report["usage"] = {
            "calls": guard.calls,
            "refused": guard.refused,
            "input_tokens": usage.input_tokens,
            "output_tokens": usage.output_tokens,
            "thinking_tokens": usage.thinking_tokens,
            "spent_usd": round(guard.spent_usd(), 4),
        }
    else:
        report["usage"] = {"calls": extractor.calls, "spent_usd": 0}
    print("totals:", dict(totals), "usage:", report["usage"])
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--extractor", choices=("fake", "gemini"), default="fake")
    parser.add_argument("--model", default=None)
    parser.add_argument("--seed", action="append")
    parser.add_argument("--pdfs", action="store_true")
    parser.add_argument("--max-usd", type=float, default=0.25)
    parser.add_argument("--label", default=None)
    args = parser.parse_args()
    report = asyncio.run(run(args))
    if args.label:
        path = BASE / "data" / f"extraction-check-{args.label}.json"
        path.write_text(json.dumps(report, indent=1, ensure_ascii=False, default=str))
        print("wrote", path)


if __name__ == "__main__":
    main()
