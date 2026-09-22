"""Deliverable 9 — normal tariff extraction with evidence.

The scenario replays a recorded live run: the page as it was fetched from the
bank, and the structured output Gemini returned for it. It prints the source
text the extractor was given, the values the model returned from that text, and
checks each quote against the captured source. Everything after extraction —
admission, persistence, projection, intent resolution and the answer — executes
for real against the disposable `_test` database.
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterable, Sequence

from pydantic import BaseModel

from app.config import load_seed_catalog
from app.config.models import IntentResolutionSettings
from app.domain.monitoring import SnapshotStatus
from app.domain.semantic_extraction import (
    EvidenceCitation,
    ExtractedValue,
    ExtractionField,
    ExtractionStatus,
    LoanProduct,
)
from app.domain.structured_tariffs import QueryStatus
from app.repositories.structured_tariff_query import (
    PostgresStructuredTariffQueryRepository,
)
from app.services.intent_resolution import RequestResolver
from app.services.structured_backfill import StructuredProjectionBackfill
from app.services.structured_query_planning import issue_resolution_plan
from app.services.structured_tariff_query import StructuredTariffQueryService
from scripts.demonstrations import ScenarioResult
from scripts.demonstrations.capture import Capture, load_capture
from scripts.demonstrations.support import (
    demonstration_sessions,
    offering_for_url,
    store_extraction,
)

QUESTION = "What is the nominal interest rate of the Overdraft?"
REQUIRED_FIELDS = {"rate.nominal.minimum", "rate.nominal.maximum"}
# The fields walked through on screen. The extraction covers every field in the
# schema; these are the ones the question is about, plus their neighbours.
SHOWN_FIELDS = (
    ExtractionField.INTEREST_RATE,
    ExtractionField.EFFECTIVE_RATE,
    ExtractionField.LOAN_AMOUNT,
    ExtractionField.TERM,
)
QUOTE_WIDTH = 96
SOURCE_WIDTH = 300


async def run() -> ScenarioResult:
    result = ScenarioResult(
        deliverable="Deliverable 9",
        title="Normal tariff extraction, stored with source evidence",
    )
    capture = load_capture(os.getenv("DEMONSTRATION_CAPTURE"))
    offering = offering_for_url(load_seed_catalog(), capture.source_url)
    extraction = capture.extraction
    product = extraction.loan_product

    result.section("Input — the captured bank page")
    _describe_input(result, capture)

    result.section("Extraction — what the model returned from that text")
    unverified = _describe_extraction(result, capture, product)

    result.section("Admission and storage")
    async with demonstration_sessions() as sessions:
        snapshot = await store_extraction(sessions, offering, extraction)
        result.step(
            f"Snapshot admission decided {snapshot.status.value} for "
            f"{offering.offering_id.value} (snapshot {str(snapshot.id)[:8]}, "
            f"payload sha256 {snapshot.canonical_sha256[:12]}): "
            f"{snapshot.validation['validated_field_count']} validated fields, "
            f"{snapshot.validation['review_count']} review items, "
            f"{len(snapshot.validation['review_signals'])} review signals."
        )
        projected = await StructuredProjectionBackfill(sessions).run_scope(
            "ameria",
            offering.product.value,
            offering.offering_id.value,
            apply=True,
        )
        result.step(
            "Projected the stored snapshot into typed facts, verified citations, "
            f"and retrieval units ({projected.published} version published, "
            f"{len(projected.issues)} unprojectable)."
        )

        result.section("Question — asked of the stored data")
        resolver = RequestResolver(load_seed_catalog(), IntentResolutionSettings())
        resolution = (await resolver.resolve_turn(QUESTION)).resolution
        result.step(
            f'Resolved "{QUESTION}" deterministically to '
            f"{resolution.product.value}/{resolution.offering_id.value} "
            f"by {resolution.method.value} match, with no model call."
        )
        plan = issue_resolution_plan(
            QUESTION, resolution, session_id="demo-extraction", turn_id="turn-1"
        )
        result.step(
            f"Issued a per-turn authorization plan: operation={plan.operation.value}, "
            f"fields={len(plan.fields)}, expires {plan.expires_at.isoformat()}."
        )
        service = StructuredTariffQueryService(
            PostgresStructuredTariffQueryRepository(sessions)
        )
        answer = await service.answer(plan, QUESTION)
        result.step(
            f"Answered from the stored typed facts: status={answer.status.value}, "
            f"{len(answer.facts)} facts, as of {answer.as_of}."
        )
        for fact in answer.facts:
            value = (
                f"{fact.value} {fact.currency}" if fact.currency else str(fact.value)
            )
            conditions = _conditions(fact.conditions)
            result.detail(
                f"{fact.field_path.value} = {value}"
                + (f"  when {conditions}" if conditions else "")
            )
            for citation in fact.evidence:
                result.detail(
                    f'    cited to "{_clip(citation.quote, QUOTE_WIDTH)}" '
                    f"[{citation.locator.get('block_id', 'n/a')}] {citation.authority}"
                )

    returned_fields = {fact.field_path.value for fact in answer.facts}
    uncited = [fact for fact in answer.facts if not fact.evidence]
    unlocated = [
        item
        for fact in answer.facts
        for item in fact.evidence
        if not item.quote or not item.locator
    ]

    result.check(
        "quotes come from the captured page",
        "every quote the model cited appears verbatim in the captured source text",
        not unverified,
        f"{len(unverified)} of the shown citations could not be matched"
        if unverified
        else "all shown citations matched their captured block",
    )
    result.check(
        "admitted without human review",
        "the extraction clears deterministic admission on its own",
        snapshot.status is SnapshotStatus.ACCEPTED,
        f"status={snapshot.status.value}, "
        f"signals={len(snapshot.validation['review_signals'])}",
    )
    result.check(
        "answered",
        "the query is answered from accepted data, not abstained",
        answer.status is QueryStatus.ANSWERED,
        f"status={answer.status.value}",
    )
    result.check(
        "requested fields returned",
        "both the minimum and maximum nominal rate come back",
        REQUIRED_FIELDS <= returned_fields,
        f"returned {sorted(returned_fields)}",
    )
    result.check(
        "every value is cited",
        "no returned fact lacks source evidence",
        not uncited,
        f"{len(answer.facts)} facts, {len(uncited)} without evidence",
    )
    result.check(
        "evidence is verifiable",
        "each citation carries an exact quote and a source locator",
        not unlocated,
        f"{sum(len(fact.evidence) for fact in answer.facts)} citations, "
        f"{len(unlocated)} missing quote or locator",
    )
    result.check(
        "freshness is reported",
        "the answer carries the stored snapshot's as-of time",
        answer.as_of is not None,
        f"as_of={answer.as_of}",
    )
    result.note(
        f"Acquisition and the Gemini calls happened in {capture.name}; this run "
        "replays their recorded output. Record a new one with "
        "`scripts/demonstrate_end_to_end.py <url>`, or replay a specific one by "
        "setting DEMONSTRATION_CAPTURE."
    )
    result.note(
        f"The full evidence overlay for this capture, with each cited quote "
        f"highlighted inside the source document, is in "
        f"{capture.directory}/semantic-extraction/extraction.md."
    )
    return result


def _describe_input(result: ScenarioResult, capture: Capture) -> None:
    artifact = capture.artifact
    pages = sum(
        1 for item in capture.bundle.documents if item.source_type.value == "page"
    )
    result.step(
        f"Fetched {capture.source_url} on "
        f"{artifact.retrieved_at:%Y-%m-%d %H:%M} UTC in "
        f"{artifact.acquisition_mode.value} mode: {len(artifact.blocks)} content "
        f"blocks, {len(artifact.tables)} tables, "
        f"{len(artifact.downloadable_documents)} linked documents."
    )
    result.step(
        f"Normalized into {len(capture.bundle.documents)} documents "
        f"({pages} page, {len(capture.bundle.documents) - pages} from PDFs) "
        f"with {sum(len(item.blocks) for item in capture.bundle.documents)} blocks."
    )
    result.step(
        f"Source discovery assessed {len(capture.discovery.assessments)} items and "
        f"admitted {len(capture.discovery.extraction_context.items)} as evidence."
    )
    plan = capture.plan
    # A cached batch was packeted and answered by an earlier identical run, so
    # its evidence was sent even though the recording reuses the stored answer.
    batches = (*plan.batches, *plan.cached_batches)
    result.step(
        f"The extractor was given {sum(len(batch.evidence) for batch in batches)} "
        f"evidence items in {len(batches)} bounded batch(es), schema "
        f"{plan.schema_version} / prompt {plan.prompt_version}, model "
        f"{capture.extraction.model_name}."
    )


def _describe_extraction(
    result: ScenarioResult, capture: Capture, product: LoanProduct | None
) -> list[str]:
    """Print each shown field beside its source text; return unmatched quotes."""
    if product is None:
        result.step(
            "The model returned no complete product; "
            f"{len(capture.extraction.review_items)} item(s) went to review."
        )
        return []
    unverified: list[str] = []
    for field in SHOWN_FIELDS:
        extracted = getattr(product, field.value, None)
        if not isinstance(extracted, ExtractedValue):
            continue
        if extracted.status is not ExtractionStatus.FOUND:
            result.step(f"{field.value}: {extracted.status.value}")
            continue
        _describe_value(result, field, extracted.value)
        for citation in extracted.evidence:
            unverified.extend(_describe_citation(result, capture, field, citation))
    return unverified


def _describe_value(
    result: ScenarioResult, field: ExtractionField, value: object
) -> None:
    """Print one field, one line per conditional variant the model returned."""
    variants = (
        value if isinstance(value, Sequence) and not isinstance(value, str) else ()
    )
    if variants and all(hasattr(item, "conditions") for item in variants):
        result.step(f"{field.value} — {len(variants)} variant(s) returned")
        for variant in variants:
            conditions = _conditions(
                [item.model_dump(mode="json") for item in variant.conditions]
            )
            result.detail(
                _render_scalar(variant.value)
                + (f"  when {conditions}" if conditions else "  (unconditional)")
            )
        return
    result.step(f"{field.value} = {_render(value)}")


def _describe_citation(
    result: ScenarioResult,
    capture: Capture,
    field: ExtractionField,
    citation: EvidenceCitation,
) -> Iterable[str]:
    source = capture.source_text(citation.source_item_id)
    result.detail(
        f'cited "{_clip(citation.quote, QUOTE_WIDTH)}" '
        f"[{citation.source_item_id}] {citation.authority.value}"
    )
    if source is None:
        result.detail(
            f"    source text for {citation.source_item_id} is not in the capture"
        )
        return (f"{field.value}:{citation.source_item_id}",)
    result.detail(
        f"    from {source.kind} in {_clip(source.document, 60)} ({source.locator})"
    )
    result.detail(f'    "{_excerpt(source.text, citation.quote, SOURCE_WIDTH)}"')
    if _normalize(citation.quote) in _normalize(source.text):
        result.detail("    quote matches the captured source text")
        return ()
    result.detail("    QUOTE NOT FOUND in the captured source text")
    return (f"{field.value}:{citation.source_item_id}",)


def _render_scalar(value: object) -> str:
    """Render one extracted value as a readable line, inventing no units."""
    if isinstance(value, BaseModel):
        data = value.model_dump(mode="json")
    elif isinstance(value, dict):
        data = dict(value)
    else:
        return str(value)
    data = {key: item for key, item in data.items() if item is not None}
    nested = data.pop("range", None)
    if isinstance(nested, dict):
        data.update({key: item for key, item in nested.items() if item is not None})
    parts: list[str] = []
    for low_key, high_key in (("min", "max"), ("min_months", "max_months")):
        low, high = data.pop(low_key, None), data.pop(high_key, None)
        if low is None and high is None:
            continue
        span = str(low) if low == high else f"{low} to {high}"
        parts.append(span if low_key == "min" else f"{span} months")
    parts.extend(f"{key}={item}" for key, item in data.items())
    return _clip(" ".join(parts), 160)


def _render(value: object) -> str:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    elif isinstance(value, Sequence) and not isinstance(value, str):
        value = [
            item.model_dump(mode="json") if isinstance(item, BaseModel) else item
            for item in value
        ]
    return _clip(json.dumps(value, ensure_ascii=False, default=str), 160)


def _conditions(conditions: Sequence[dict[str, object]]) -> str:
    """Render the variant a fact applies to, such as a card type or currency."""
    parts = [
        f"{item.get('dimension')}={item.get('value')}"
        for item in conditions
        if item.get("value") is not None
    ]
    return _clip("; ".join(parts), 120)


def _excerpt(text: str, quote: str, width: int) -> str:
    """Show the captured text around the quote, so the value can be read in place."""
    collapsed = " ".join(text.split())
    position = _normalize(collapsed).find(_normalize(quote))
    if position < 0 or len(collapsed) <= width:
        return _clip(collapsed, width)
    start = max(0, position - width // 4)
    end = min(len(collapsed), start + width)
    return (
        ("…" if start else "")
        + collapsed[start:end]
        + ("…" if end < len(collapsed) else "")
    )


def _normalize(value: str) -> str:
    return " ".join(value.split()).casefold()


def _clip(value: str, width: int) -> str:
    collapsed = " ".join(value.split())
    if len(collapsed) <= width:
        return collapsed
    return collapsed[: width - 1] + "…"
