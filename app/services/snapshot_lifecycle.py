from __future__ import annotations

import hashlib
import json
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
    ExtractionStatus,
    LoanProduct,
    SemanticExtractionResult,
    SemanticExtractionRunStatus,
)

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
) -> SnapshotAttempt:
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
        if field.status is ExtractionStatus.FOUND:
            if field.value is None or not field.evidence:
                return False
            if any(item.evidence_id not in available_ids for item in field.evidence):
                return False
    return True


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
