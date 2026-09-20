from __future__ import annotations

import hashlib
import json
import re
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, JsonValue

from app.domain.models import OfferingId, ProductType
from app.domain.monitoring import (
    SnapshotAttempt,
    SnapshotChange,
    SnapshotChangeSet,
    SnapshotStatus,
)
from app.domain.semantic_extraction import (
    EvidenceItem,
    ExtractionField,
    ExtractionStatus,
    LoanProduct,
    SemanticExtractionResult,
    SemanticExtractionRunStatus,
)

_REQUIRED_TARIFF_FIELDS = frozenset(
    {
        ExtractionField.PRODUCT_NAME,
        ExtractionField.LOAN_AMOUNT,
        ExtractionField.INTEREST_RATE,
        ExtractionField.EFFECTIVE_RATE,
        ExtractionField.TERM,
        ExtractionField.FEES,
        ExtractionField.REPAYMENT,
        ExtractionField.ELIGIBILITY,
        ExtractionField.REQUIRED_DOCUMENTS,
    }
)
_RATE_FIELDS = frozenset(
    {ExtractionField.INTEREST_RATE.value, ExtractionField.EFFECTIVE_RATE.value}
)
_PERCENTAGE = re.compile(r"(?<!\d)(\d{1,3}(?:[.,]\d+)?)\s*%")

_PROVENANCE_KEYS = frozenset(
    {
        "accepted_at",
        "canonical_url",
        "created_at",
        "evidence",
        "evidence_id",
        "explanation",
        "locator",
        "quote",
        "retrieved_at",
        "section",
        "source_item_id",
        "source_type",
        "source_url",
    }
)


def canonical_tariff_payload(
    value: LoanProduct | dict[str, Any],
) -> dict[str, JsonValue]:
    raw = (
        value.model_dump(mode="json", exclude_none=False)
        if isinstance(value, BaseModel)
        else value
    )
    canonical = _canonicalize(raw)
    if not isinstance(canonical, dict):
        raise ValueError("canonical tariff payload must be an object")
    return canonical


def canonical_sha256(payload: dict[str, JsonValue]) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def build_snapshot_attempt(
    *,
    run_id: UUID,
    offering_execution_id: UUID,
    product: ProductType,
    offering_id: OfferingId,
    result: SemanticExtractionResult,
    previous_accepted_snapshot_id: UUID | None,
    previous_accepted_snapshot: SnapshotAttempt | None = None,
    large_rate_change_percentage_points: Decimal = Decimal("3"),
) -> SnapshotAttempt:
    review_signals = detect_review_signals(result)
    accepted = extraction_is_acceptable(result)
    source_value: LoanProduct | dict[str, Any]
    if result.loan_product is not None:
        source_value = result.loan_product
    elif result.partial_product is not None:
        source_value = {
            item.field.value: {
                "status": item.status.value,
                "value": item.value,
            }
            for item in result.partial_product.fields
        }
    else:
        source_value = {}
    payload = canonical_tariff_payload(source_value)
    if accepted and previous_accepted_snapshot is not None:
        rate_signals = detect_large_rate_changes(
            previous_accepted_snapshot.normalized_tariff,
            payload,
            threshold=large_rate_change_percentage_points,
        )
        review_signals = (*review_signals, *rate_signals)
        accepted = not review_signals
    created_at = (
        result.loan_product.retrieved_at
        if result.loan_product is not None
        else result.partial_product.retrieved_at
        if result.partial_product is not None
        else _result_timestamp_error()
    )
    status = SnapshotStatus.ACCEPTED if accepted else SnapshotStatus.REVIEW_REQUIRED
    return SnapshotAttempt(
        id=uuid4(),
        run_id=run_id,
        offering_execution_id=offering_execution_id,
        product=product,
        offering_id=offering_id,
        status=status,
        normalized_tariff=payload,
        evidence=tuple(
            item.model_dump(mode="json") for item in result.evidence_catalog
        ),
        semantic_extraction=result.model_dump(mode="json"),
        validation={
            "accepted": accepted,
            "review_count": len(result.review_items),
            "validated_field_count": len(result.validated_fields),
            "review_signals": list(review_signals),
        },
        canonical_sha256=canonical_sha256(payload),
        previous_accepted_snapshot_id=previous_accepted_snapshot_id,
        created_at=created_at,
        accepted_at=created_at if accepted else None,
    )


def extraction_is_acceptable(result: SemanticExtractionResult) -> bool:
    if (
        result.status is not SemanticExtractionRunStatus.COMPLETED
        or result.loan_product is None
        or result.review_items
    ):
        return False
    available_ids = {item.evidence_id for item in result.evidence_catalog}
    for field in result.validated_fields:
        if field.status in {ExtractionStatus.AMBIGUOUS, ExtractionStatus.CONFLICTING}:
            return False
        if (
            field.field in _REQUIRED_TARIFF_FIELDS
            and field.status is ExtractionStatus.NOT_STATED
        ):
            return False
        if field.status is ExtractionStatus.FOUND:
            if field.value is None or not field.evidence:
                return False
            if any(item.evidence_id not in available_ids for item in field.evidence):
                return False
    return True


def non_reviewable_extraction_failure(
    result: SemanticExtractionResult,
) -> str | None:
    """Return a safe failure code for execution failures that humans cannot repair."""
    if any(
        item.raw_result is None and item.raw_response is None
        for item in result.review_items
    ):
        return "semantic_extraction.execution_failed"
    if not result.evidence_catalog and result.review_items:
        return "semantic_extraction.no_usable_evidence"
    return None


def detect_review_signals(
    result: SemanticExtractionResult,
) -> tuple[dict[str, JsonValue], ...]:
    evidence_by_id = {item.evidence_id: item for item in result.evidence_catalog}
    signals: list[dict[str, JsonValue]] = []
    for field in result.validated_fields:
        if field.status is ExtractionStatus.CONFLICTING:
            candidates = _conflict_candidates(field, evidence_by_id)
            signals.append(
                {
                    "reason": "official_source_conflict",
                    "issue_scope": field.field.value,
                    "field": field.field.value,
                    "candidates": candidates,
                }
            )
        elif field.status is ExtractionStatus.AMBIGUOUS:
            signals.append(
                {
                    "reason": "source_applicability",
                    "issue_scope": field.field.value,
                    "field": field.field.value,
                    "evidence_references": [
                        item.evidence_id for item in field.evidence
                    ],
                }
            )
        elif (
            field.field in _REQUIRED_TARIFF_FIELDS
            and field.status is ExtractionStatus.NOT_STATED
        ):
            signals.append(
                {
                    "reason": "missing_required_field",
                    "issue_scope": field.field.value,
                    "field": field.field.value,
                    "evidence_references": [
                        item.evidence_id for item in result.evidence_catalog[:20]
                    ],
                }
            )
    existing_scopes = {
        str(signal["issue_scope"]) for signal in signals if "issue_scope" in signal
    }
    for item in result.review_items:
        if item.field.value in existing_scopes:
            continue
        if item.raw_result is None and item.raw_response is None:
            continue
        signals.append(
            {
                "reason": "missing_required_field",
                "issue_scope": item.field.value,
                "field": item.field.value,
                "evidence_references": list(item.evidence_ids),
            }
        )
    return tuple(signals)


def detect_large_rate_changes(
    previous: dict[str, JsonValue],
    current: dict[str, JsonValue],
    *,
    threshold: Decimal = Decimal("3"),
) -> tuple[dict[str, JsonValue], ...]:
    if threshold <= 0:
        raise ValueError("large rate change threshold must be positive")
    signals: list[dict[str, JsonValue]] = []
    for field in sorted(_RATE_FIELDS):
        prior_values = dict(_rate_values(previous.get(field)))
        current_values = dict(_rate_values(current.get(field)))
        common_paths = prior_values.keys() & current_values.keys()
        if not common_paths:
            continue
        largest = max(
            (
                (
                    abs(current_values[path] - prior_values[path]),
                    prior_values[path],
                    current_values[path],
                )
                for path in common_paths
            ),
            key=lambda item: item[0],
        )
        if largest[0] >= threshold:
            signals.append(
                {
                    "reason": "large_rate_change",
                    "issue_scope": field,
                    "field": field,
                    "previous": str(largest[1]),
                    "current": str(largest[2]),
                    "absolute_percentage_point_change": str(largest[0]),
                }
            )
    return tuple(signals)


def _conflict_candidates(field, evidence_by_id: dict[str, EvidenceItem]):
    candidates: list[dict[str, JsonValue]] = []
    for citation in field.evidence:
        evidence = evidence_by_id.get(citation.evidence_id)
        if evidence is None:
            continue
        percentages = tuple(
            match.group(1).replace(",", ".")
            for match in _PERCENTAGE.finditer(citation.quote)
        )
        candidates.append(
            {
                "candidate_id": citation.evidence_id,
                "value": percentages[0] if len(percentages) == 1 else citation.quote,
                "evidence_references": [citation.evidence_id],
                "source_type": citation.source_type.value,
                "quote": citation.quote,
                "conditions": list(evidence.conditions),
            }
        )
    return candidates


def _rate_values(value: JsonValue) -> tuple[tuple[str, Decimal], ...]:
    values: list[tuple[str, Decimal]] = []

    def visit(
        item: JsonValue, path: tuple[str, ...], *, rate_key: bool = False
    ) -> None:
        if isinstance(item, dict):
            for key, nested in item.items():
                visit(
                    nested,
                    (*path, key),
                    rate_key=key in {"min", "max", "rate_pct"},
                )
        elif isinstance(item, list):
            for index, nested in enumerate(item):
                visit(nested, (*path, str(index)), rate_key=rate_key)
        elif (
            rate_key
            and isinstance(item, (str, int, float))
            and not isinstance(item, bool)
        ):
            try:
                values.append((".".join(path), Decimal(str(item).replace(",", "."))))
            except InvalidOperation:
                pass

    visit(value, ())
    return tuple(values)


def compare_accepted_snapshots(
    previous: SnapshotAttempt | None,
    current: SnapshotAttempt,
) -> SnapshotChangeSet | None:
    if current.status is not SnapshotStatus.ACCEPTED:
        return None
    if previous is None:
        return SnapshotChangeSet(
            id=uuid4(),
            run_id=current.run_id,
            product=current.product,
            offering_id=current.offering_id,
            current_snapshot_id=current.id,
            changes=(),
            created_at=current.accepted_at or current.created_at,
        )
    fields = sorted(set(previous.normalized_tariff) | set(current.normalized_tariff))
    changes = tuple(
        SnapshotChange(
            field=field,
            previous=previous.normalized_tariff.get(field),
            current=current.normalized_tariff.get(field),
            previous_display=_display(previous.normalized_tariff.get(field)),
            current_display=_display(current.normalized_tariff.get(field)),
        )
        for field in fields
        if previous.normalized_tariff.get(field) != current.normalized_tariff.get(field)
    )
    return SnapshotChangeSet(
        id=uuid4(),
        run_id=current.run_id,
        product=current.product,
        offering_id=current.offering_id,
        previous_snapshot_id=previous.id,
        current_snapshot_id=current.id,
        changes=changes,
        created_at=current.accepted_at or current.created_at,
    )


def evidence_changed(
    previous: SnapshotAttempt | None,
    current: SnapshotAttempt,
) -> bool:
    if previous is None or previous.canonical_sha256 != current.canonical_sha256:
        return False
    return _stable_json(previous.evidence) != _stable_json(current.evidence)


def _canonicalize(value: Any) -> JsonValue:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json", exclude_none=False)
    if isinstance(value, dict):
        return {
            str(key): _canonicalize(nested)
            for key, nested in sorted(value.items(), key=lambda item: str(item[0]))
            if str(key) not in _PROVENANCE_KEYS
        }
    if isinstance(value, (list, tuple)):
        normalized = [_canonicalize(item) for item in value]
        return sorted(normalized, key=_stable_json)
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _stable_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )


def _display(value: JsonValue) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value[:2000]
    return _stable_json(value)[:2000]


def _result_timestamp_error():
    raise ValueError("semantic extraction result has no product timestamp")
