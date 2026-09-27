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
from app.domain.pdf_extraction import is_ocr_source_item
from app.domain.review import ReviewEvidenceSet
from app.domain.semantic_extraction import (
    EvidenceItem,
    ExtractionField,
    ExtractionReviewItem,
    ExtractionStatus,
    LoanProduct,
    SemanticExtractionResult,
    SemanticExtractionRunStatus,
)
from app.domain.source_discovery import Authority
from app.services.review_evidence import (
    UNITS_PER_REVIEW,
    cited_evidence_set,
    field_evidence_set,
)

_OFFICIAL_EVIDENCE_AUTHORITIES = frozenset(
    {
        Authority.OFFICIAL_TERMS,
        Authority.OFFICIAL_PRODUCT_CONTENT,
        Authority.OFFICIAL_FAQ,
        Authority.OFFICIAL_CAMPAIGN_CONTENT,
    }
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
    review_rank_gap: float = 0.05,
    selected_sources_markdown: str | None = None,
) -> SnapshotAttempt:
    review_signals = detect_review_signals(result, rank_gap=review_rank_gap)
    accepted = extraction_is_acceptable(result) and not review_signals
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
    # The rate guard runs on every candidate that has something to compare
    # against, not only on otherwise-clean ones. Gating it on `accepted` meant
    # that a run needing any field review skipped it entirely: the reviewer
    # answered, say, `repayment`, the snapshot activated, and a rate jump went
    # live that nobody had been shown. That is the run that most needs the guard,
    # and on offerings whose extraction often needs a field review it rarely ran
    # at all. Each signal becomes its own review, and activation already waits
    # for every one of them.
    if previous_accepted_snapshot is not None:
        rate_signals = detect_large_rate_changes(
            previous_accepted_snapshot.normalized_tariff,
            payload,
            threshold=large_rate_change_percentage_points,
        )
        rate_signals = tuple(
            _with_new_value_evidence(signal, result) for signal in rate_signals
        )
        review_signals = (*review_signals, *rate_signals)
        accepted = accepted and not rate_signals
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
        selected_sources_markdown=selected_sources_markdown,
    )


def extraction_is_acceptable(result: SemanticExtractionResult) -> bool:
    if (
        result.status is not SemanticExtractionRunStatus.COMPLETED
        or result.loan_product is None
        or result.review_items
    ):
        return False
    evidence_by_id = {item.evidence_id: item for item in result.evidence_catalog}
    available_ids = set(evidence_by_id)
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
            if any(
                item.authority not in _OFFICIAL_EVIDENCE_AUTHORITIES
                or evidence_by_id[item.evidence_id].authority
                not in _OFFICIAL_EVIDENCE_AUTHORITIES
                or item.authority != evidence_by_id[item.evidence_id].authority
                for item in field.evidence
            ):
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
    *,
    rank_gap: float = 0.05,
) -> tuple[dict[str, JsonValue], ...]:
    """One signal per question a human must answer, each with its evidence set.

    The set is decided here, from what the pipeline knows at this point (the
    field's citations, a candidate's passage, the OCR page, or the passages the
    field's extraction call read), and stored as references (RV1).
    """
    catalog = result.evidence_catalog
    evidence_by_id = {item.evidence_id: item for item in catalog}
    canonical_url = _canonical_url(result)
    signals: list[dict[str, JsonValue]] = []

    def cited(ids, why: str, max_units: int = UNITS_PER_REVIEW):
        return cited_evidence_set(catalog, ids, why=why, max_units=max_units)

    for field in result.validated_fields:
        cited_ids = [item.evidence_id for item in field.evidence]
        # `memory:` marks a value a person already confirmed for this very
        # result (an approved OCR reading); asking again every run would pause
        # every run of an offering whose terms exist only as a scan.
        confirmed = field.batch_id.startswith("memory:")
        if field.status is ExtractionStatus.FOUND and not confirmed:
            ocr_citations = [
                item
                for item in field.evidence
                if is_ocr_source_item(item.source_item_id)
            ]
            if ocr_citations:
                # A value read off a page image is not the same evidence as one
                # read from a text layer. A misrecognised digit must not become
                # an accepted interest rate without a human looking at it.
                signals.append(
                    _signal(
                        "ocr_evidence",
                        field.field.value,
                        cited([item.evidence_id for item in ocr_citations], "ocr"),
                        candidates=[
                            {
                                "candidate_id": item.evidence_id,
                                "value": item.quote,
                                "evidence_references": [item.evidence_id],
                                "source_type": item.source_type.value,
                                "quote": item.quote,
                                "pdf_page": item.locator.pdf_page,
                                "conditions": [],
                            }
                            for item in ocr_citations
                        ],
                    )
                )
        if field.status is ExtractionStatus.FOUND and any(
            item.authority not in _OFFICIAL_EVIDENCE_AUTHORITIES
            or evidence_by_id.get(item.evidence_id) is None
            or evidence_by_id[item.evidence_id].authority
            not in _OFFICIAL_EVIDENCE_AUTHORITIES
            for item in field.evidence
        ):
            signals.append(
                _signal(
                    "source_applicability",
                    field.field.value,
                    cited(cited_ids, "cited"),
                )
            )
        if field.status is ExtractionStatus.CONFLICTING:
            candidates = _conflict_candidates(field, evidence_by_id)
            signals.append(
                _signal(
                    "official_source_conflict",
                    field.field.value,
                    cited(
                        [c["candidate_id"] for c in candidates],
                        "candidate",
                        max_units=max(UNITS_PER_REVIEW, min(len(candidates), 4)),
                    ),
                    candidates=candidates,
                )
            )
        elif field.status is ExtractionStatus.AMBIGUOUS:
            signals.append(
                _signal(
                    "source_applicability",
                    field.field.value,
                    cited(cited_ids, "cited"),
                )
            )
        elif (
            field.field in _REQUIRED_TARIFF_FIELDS
            and field.status is ExtractionStatus.NOT_STATED
        ):
            # Where the field would have been read from: the passages its own
            # extraction call read, not the first entries of the catalog (RV2).
            signals.append(
                _signal(
                    "missing_required_field",
                    field.field.value,
                    field_evidence_set(
                        catalog,
                        field.field,
                        read_ids=result.evidence_read_by(field.batch_id),
                        canonical_url=canonical_url,
                        rank_gap=rank_gap,
                    ),
                )
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
            _review_item_signal(
                result,
                item,
                canonical_url=canonical_url,
                rank_gap=rank_gap,
            )
        )
    return tuple(signals)


def _review_item_signal(
    result: SemanticExtractionResult,
    item: ExtractionReviewItem,
    *,
    canonical_url: str | None,
    rank_gap: float,
) -> dict[str, JsonValue]:
    """A field extraction could not accept (RV5).

    A value that failed a check is `extraction_invalid`, with Gemini's value as
    the candidate and the failed checks named. A required field Gemini found
    nothing for (not stated, or missing from its answer) is
    `missing_required_field`, set from the passages its call read. Any other
    failure is `extraction_invalid` without a candidate: a field that does not
    validate is never dropped silently (Q2).
    """
    raw = item.raw_result
    failed_checks = [issue.message[:300] for issue in item.validation_issues][:10]
    proposed = raw is not None and raw.value_json is not None
    if (
        not proposed
        and item.field in _REQUIRED_TARIFF_FIELDS
        and (raw is None or raw.status is ExtractionStatus.NOT_STATED)
    ):
        return _signal(
            "missing_required_field",
            item.field.value,
            field_evidence_set(
                result.evidence_catalog,
                item.field,
                read_ids=result.evidence_read_by(item.batch_id),
                canonical_url=canonical_url,
                rank_gap=rank_gap,
            ),
            failed_checks=failed_checks,
        )
    cited_ids = [citation.evidence_id for citation in raw.evidence] if raw else []
    evidence_set = cited_evidence_set(result.evidence_catalog, cited_ids, why="cited")
    if not evidence_set.units:
        # Nothing it cited exists: show where the field would have been read.
        evidence_set = field_evidence_set(
            result.evidence_catalog,
            item.field,
            read_ids=result.evidence_read_by(item.batch_id),
            canonical_url=canonical_url,
            rank_gap=rank_gap,
        ).model_copy(update={"unknown_ids": evidence_set.unknown_ids})
    candidates: list[dict[str, JsonValue]] = []
    known = {i.evidence_id: i for i in result.evidence_catalog}
    valid_citations = [
        c for c in (raw.evidence if raw else ()) if c.evidence_id in known
    ]
    if proposed and valid_citations:
        candidates.append(
            {
                "candidate_id": f"extracted:{item.review_id}",
                "value": _proposed_value(raw.value_json),
                "evidence_references": list(
                    dict.fromkeys(c.evidence_id for c in valid_citations)
                )[:20],
                "source_type": known[
                    valid_citations[0].evidence_id
                ].locator.source_type.value,
                "quote": valid_citations[0].quote,
                "conditions": [],
            }
        )
    signal = _signal(
        "extraction_invalid",
        item.field.value,
        evidence_set,
        candidates=candidates,
        failed_checks=failed_checks,
    )
    if proposed:
        signal["proposed_value"] = _proposed_value(raw.value_json)
    return signal


def _with_new_value_evidence(
    signal: dict[str, JsonValue], result: SemanticExtractionResult
) -> dict[str, JsonValue]:
    """A rate change is confirmed against the passages the new value came from
    (RV4/B6); before and after stay in the signal for the guidance."""
    cited_ids = [
        citation.evidence_id
        for field in result.validated_fields
        if field.field.value == signal.get("field")
        for citation in field.evidence
    ]
    evidence_set = cited_evidence_set(
        result.evidence_catalog, cited_ids, why="rate_new"
    )
    return {
        **signal,
        "evidence_references": list(evidence_set.seed_ids)[:20],
        "evidence_set": evidence_set.model_dump(mode="json"),
    }


def _proposed_value(value_json: str) -> JsonValue:
    try:
        return json.loads(value_json)
    except ValueError:
        return value_json


def _signal(
    reason: str,
    field: str,
    evidence_set: ReviewEvidenceSet,
    **extra: JsonValue,
) -> dict[str, JsonValue]:
    signal: dict[str, JsonValue] = {
        "reason": reason,
        "issue_scope": field,
        "field": field,
        # Kept for readers of older signals; the set is the source of truth.
        "evidence_references": list(evidence_set.seed_ids)[:20],
        "evidence_set": evidence_set.model_dump(mode="json"),
    }
    signal.update({key: value for key, value in extra.items() if value})
    return signal


def _canonical_url(result: SemanticExtractionResult) -> str | None:
    product = result.loan_product or result.partial_product
    url = getattr(product, "canonical_url", None) if product else None
    return str(url) if url else None


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
        deltas = [
            (
                abs(current_rates[key] - prior_rates[key]),
                prior_rates[key],
                current_rates[key],
            )
            for prior_rates, current_rates in _paired_rate_entries(
                _rate_entries(previous.get(field)),
                _rate_entries(current.get(field)),
            )
            for key in sorted(prior_rates.keys() & current_rates.keys())
        ]
        if not deltas:
            continue
        largest = max(deltas, key=lambda item: item[0])
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


# Rate entries are paired by what they describe, never by list position. The
# canonical payload sorts every list by its full content, and the extractor's
# condition wording varies between runs over identical pages ("scoring-based
# loans or specific industries" one run, "... or loans to workers of specific
# industries" the next), which moves an entry to a different index. Pairing by
# position then compared one card tier's rate with another's and raised a large
# change on rates that had not moved at all.
#
# Dimension names vary too (`card_type` one run, `card_tier` the next), so an
# entry's identity is the set of words in its condition values alone. An entry
# pairs only with its mutual best match, and only above a floor. Measured on real
# Overdraft snapshots on 2026-09-24: correct pairs scored 0.60 to 0.88 and wrong
# pairs 0.00 to 0.15, so the floor sits well inside that gap. An entry with no
# counterpart is not a rate change; change detection reports it structurally.
_CONDITION_WORD = re.compile(r"[a-z0-9]+")
_RATE_ENTRY_MATCH_FLOOR = 0.3


def _rate_entries(
    value: JsonValue,
) -> list[tuple[frozenset[str], dict[str, Decimal]]]:
    items = value.get("value") if isinstance(value, dict) else value
    if not isinstance(items, list):
        items = [] if value is None else [value]
    entries: list[tuple[frozenset[str], dict[str, Decimal]]] = []
    for item in items:
        rates = dict(_rate_values(item))
        if not rates:
            continue
        conditions = item.get("conditions") if isinstance(item, dict) else None
        words = frozenset(
            word
            for condition in (conditions if isinstance(conditions, list) else ())
            if isinstance(condition, dict)
            for word in _CONDITION_WORD.findall(str(condition.get("value", "")).lower())
        )
        entries.append((words, rates))
    return entries


def _condition_similarity(left: frozenset[str], right: frozenset[str]) -> float:
    union = left | right
    return len(left & right) / len(union) if union else 1.0


def _paired_rate_entries(
    previous: list[tuple[frozenset[str], dict[str, Decimal]]],
    current: list[tuple[frozenset[str], dict[str, Decimal]]],
) -> list[tuple[dict[str, Decimal], dict[str, Decimal]]]:
    """Pair each entry with its mutual best match, lowest index on a tie."""
    pairs: list[tuple[dict[str, Decimal], dict[str, Decimal]]] = []
    if not previous or not current:
        return pairs
    for index, (words, rates) in enumerate(previous):
        scores = [_condition_similarity(words, other) for other, _ in current]
        best = max(range(len(current)), key=lambda k: (scores[k], -k))
        back = max(
            range(len(previous)),
            key=lambda k: (
                _condition_similarity(previous[k][0], current[best][0]),
                -k,
            ),
        )
        if back == index and scores[best] >= _RATE_ENTRY_MATCH_FLOOR:
            pairs.append((rates, current[best][1]))
    return pairs


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


def tariff_fields(normalized_tariff: dict[str, JsonValue]) -> dict[str, JsonValue]:
    """Each tariff field of a snapshot payload by its extraction-field name.

    The category-specific fields (down payment, LTV, credit limit, grace period,
    collateral, ...) sit inside `details`. Flattened, each is compared, cited and
    answered on its own, as the top-level fields are, instead of all of them
    changing together as one uncitable `details` value.
    """
    fields = {
        key: value for key, value in normalized_tariff.items() if key != "details"
    }
    details = normalized_tariff.get("details")
    if isinstance(details, dict):
        fields.update((key, value) for key, value in details.items() if key != "type")
    return fields


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
    before = tariff_fields(previous.normalized_tariff)
    after = tariff_fields(current.normalized_tariff)
    changes = tuple(
        SnapshotChange(
            field=field,
            previous=before.get(field),
            current=after.get(field),
            previous_display=_display(before.get(field)),
            current_display=_display(after.get(field)),
        )
        for field in sorted(set(before) | set(after))
        if before.get(field) != after.get(field)
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
