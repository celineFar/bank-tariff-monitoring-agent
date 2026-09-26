from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass

from app.config import SemanticExtractionSettings
from app.domain.extraction_terms import FIELD_TERMS, term_pattern
from app.domain.models import ProductType
from app.domain.semantic_extraction import (
    EvidenceItem,
    ExtractionBatch,
    ExtractionField,
)
from app.domain.source_discovery import OfferingContext, ProductAssociation

_GROUPS: tuple[tuple[str, tuple[ExtractionField, ...]], ...] = (
    (
        "identity",
        (
            ExtractionField.PRODUCT_NAME,
            ExtractionField.FORMAL_TERMS_NAMES,
            ExtractionField.VARIANTS,
            ExtractionField.CATEGORY,
            ExtractionField.PURPOSE,
        ),
    ),
    (
        "core_financial",
        (
            ExtractionField.LOAN_AMOUNT,
            ExtractionField.INTEREST_RATE,
            ExtractionField.EFFECTIVE_RATE,
            ExtractionField.TERM,
        ),
    ),
    ("fees_and_repayment", (ExtractionField.FEES, ExtractionField.REPAYMENT)),
    (
        "eligibility_and_documents",
        (
            ExtractionField.ELIGIBILITY,
            ExtractionField.RESIDENCY_REQUIREMENTS,
            ExtractionField.AGE_REQUIREMENTS,
            ExtractionField.APPLICATION_CHANNEL,
            ExtractionField.SPECIAL_CONDITIONS,
        ),
    ),
    ("required_documents", (ExtractionField.REQUIRED_DOCUMENTS,)),
)

_PRODUCT_FIELDS: dict[ProductType, tuple[ExtractionField, ...]] = {
    ProductType.CONSUMER_LOAN: (
        ExtractionField.COLLATERAL,
        ExtractionField.INCOME_VERIFICATION_REQUIRED,
        ExtractionField.CREDITWORTHINESS_ASSESSMENT_REQUIRED,
        ExtractionField.CREDIT_LIMIT,
        ExtractionField.GRACE_PERIOD_DAYS,
        ExtractionField.REVOLVING,
        ExtractionField.LINKED_ACCOUNT_OR_CARD,
    ),
    ProductType.MORTGAGE: (
        ExtractionField.PROPERTY_MARKET,
        ExtractionField.DOWN_PAYMENT_PCT,
        ExtractionField.LTV_PCT,
        ExtractionField.COLLATERAL,
        ExtractionField.INCOME_VERIFICATION_REQUIRED,
        ExtractionField.CREDITWORTHINESS_ASSESSMENT_REQUIRED,
        ExtractionField.PROPERTY_REQUIREMENTS,
    ),
}

# Full mode sends the whole packet with every call, so input cost grows with the
# number of calls: the field groups are asked in three calls (Q10).
# How many of a field's best units share its budget before the rest.
_BREADTH = 3
# A line this short, or the part before its colon, is a label.
_LABEL_CHARS = 80

FULL_MODE_CALLS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("identity_and_core", ("identity", "core_financial")),
    ("terms_and_eligibility", ("fees_and_repayment", "eligibility_and_documents")),
    ("documents_and_details", ("required_documents", "product_details")),
)

# Never evidence for a value, in either mode.
_EXCLUDED_ASSOCIATIONS = frozenset(
    {
        ProductAssociation.GLOBAL_NAVIGATION,
        ProductAssociation.HISTORICAL_VERSION,
        ProductAssociation.FUTURE_VERSION,
    }
)


class EvidencePacketTooLargeError(ValueError):
    """The offering's selected evidence exceeds the full-mode ceiling.

    Raised instead of cutting anything: the operator either raises
    `SEMANTIC_EXTRACTION_MAX_PACKET_CHARS` or switches the offering's run to the
    budgeted mode.
    """

    def __init__(self, characters: int, ceiling: int) -> None:
        super().__init__(
            "semantic_extraction.packet_too_large: "
            f"{characters} evidence characters > {ceiling}"
        )
        self.characters = characters
        self.ceiling = ceiling


# The details each category's product model holds (SE21). Without a category
# (a caller outside the catalog), the product family's union is asked.
CATEGORY_FIELDS: dict[str, tuple[ExtractionField, ...]] = {
    "consumer_loan": (
        ExtractionField.COLLATERAL,
        ExtractionField.INCOME_VERIFICATION_REQUIRED,
        ExtractionField.CREDITWORTHINESS_ASSESSMENT_REQUIRED,
    ),
    "overdraft": (
        ExtractionField.CREDIT_LIMIT,
        ExtractionField.GRACE_PERIOD_DAYS,
        ExtractionField.REVOLVING,
        ExtractionField.LINKED_ACCOUNT_OR_CARD,
    ),
    "credit_line": (
        ExtractionField.CREDIT_LIMIT,
        ExtractionField.GRACE_PERIOD_DAYS,
        ExtractionField.REVOLVING,
    ),
    "mortgage": _PRODUCT_FIELDS[ProductType.MORTGAGE],
}


def field_groups(
    product: ProductType, category: str | None = None
) -> tuple[tuple[str, tuple[ExtractionField, ...]], ...]:
    details = CATEGORY_FIELDS[category] if category else _PRODUCT_FIELDS[product]
    return (*_GROUPS, ("product_details", details))


def build_extraction_batches(
    product: ProductType,
    evidence: tuple[EvidenceItem, ...],
    settings: SemanticExtractionSettings,
    *,
    canonical_url: str | None = None,
    offering_id: str | None = None,
    category: str | None = None,
    offering: OfferingContext | None = None,
) -> tuple[ExtractionBatch, ...]:
    if not evidence:
        raise ValueError("semantic extraction requires at least one evidence item")
    usable = tuple(
        item
        for item in sorted(evidence, key=lambda item: item.order)
        if item.product_association not in _EXCLUDED_ASSOCIATIONS
    ) or tuple(evidence)
    category = category or (offering.category if offering else None)
    groups = field_groups(product, str(category) if category else None)
    target_scope = _target_scope(product, canonical_url, offering, category)
    if settings.evidence_mode == "full":
        characters = sum(len(item.content) for item in usable)
        if characters > settings.max_packet_chars:
            raise EvidencePacketTooLargeError(characters, settings.max_packet_chars)
        plans = [(name, fields, usable, (), ()) for name, fields in _calls(groups)]
    else:
        units = build_units(usable, canonical_url)
        plans = [
            (name, fields, *select_units(fields, units, settings.budget_chars))
            for name, fields in _calls(groups)
        ]
    batches: list[ExtractionBatch] = []
    for group, fields, selected, left_out, limited in plans:
        fingerprint = hashlib.sha256(
            "\x1e".join(
                (
                    group,
                    *(field.value for field in fields),
                    *target_scope,
                    *(
                        "\x1f".join(
                            (
                                item.evidence_id,
                                item.content,
                                item.product_association.value,
                                item.temporal_status.value,
                                repr(item.conditions),
                                repr(item.effective_periods),
                            )
                        )
                        for item in selected
                    ),
                )
            ).encode()
        ).hexdigest()
        batches.append(
            ExtractionBatch(
                # Named by offering and field group, never by position: the ID
                # keys raw responses, repairs and review identities.
                id=f"{offering_id or product.value}:{group}",
                product=product,
                group=group,
                fields=fields,
                evidence=selected,
                content_fingerprint=fingerprint,
                canonical_url=canonical_url,
                target_scope=target_scope,
                evidence_mode=settings.evidence_mode,
                units_left_out=left_out,
                budget_limited_fields=limited,
                category=str(category) if category else None,
            )
        )
    return tuple(batches)


def _calls(
    groups: tuple[tuple[str, tuple[ExtractionField, ...]], ...],
) -> list[tuple[str, tuple[ExtractionField, ...]]]:
    """The field groups merged into the three calls of `FULL_MODE_CALLS`."""
    by_group = dict(groups)
    calls = [
        (
            name,
            tuple(field for group in members for field in by_group.get(group, ())),
        )
        for name, members in FULL_MODE_CALLS
    ]
    return [(name, fields) for name, fields in calls if fields]


@dataclass(frozen=True)
class EvidenceUnit:
    """A whole table (its rows and notes) or a whole section's blocks."""

    key: str
    items: tuple[EvidenceItem, ...]
    labels: str
    related: bool
    canonical: bool

    @property
    def order(self) -> int:
        return self.items[0].order

    @property
    def characters(self) -> int:
        return sum(len(item.content) for item in self.items)


def build_units(
    evidence: tuple[EvidenceItem, ...], canonical_url: str | None = None
) -> tuple[EvidenceUnit, ...]:
    grouped: dict[str, list[EvidenceItem]] = {}
    for item in evidence:
        related = item.product_association is ProductAssociation.RELATED_PRODUCT
        table = re.split(r":(?:row|note):", item.source_item_id, maxsplit=1)
        container = (
            f"table:{table[0]}" if len(table) == 2 else f"section:{item.section or ''}"
        )
        key = f"{item.document_id}|{container}|{'related' if related else 'own'}"
        grouped.setdefault(key, []).append(item)
    canonical = (canonical_url or "").rstrip("/").casefold()
    return tuple(
        sorted(
            (
                EvidenceUnit(
                    key=key,
                    items=tuple(items),
                    labels=" \n ".join(
                        dict.fromkeys(
                            label for item in items for label in _labels(item)
                        )
                    ),
                    related=key.endswith("|related"),
                    canonical=bool(canonical)
                    and str(items[0].locator.source_url).rstrip("/").casefold()
                    == canonical,
                )
                for key, items in grouped.items()
            ),
            key=lambda unit: unit.order,
        )
    )


def _labels(item: EvidenceItem) -> list[str]:
    """What names an item: its section, row labels, column paths and keys --
    never its body text (a disclosure that mentions "annual interest rate" is not
    about the rate)."""
    labels = [item.section or ""]
    for raw in item.content.splitlines():
        line = raw.strip()
        if not line or line == "Notes:":
            continue
        if line.startswith("Section:"):
            labels.append(line.removeprefix("Section:"))
        elif "→" in line:
            labels.append(line.split("→", 1)[0])
        elif ":" in line and len(line.split(":", 1)[0]) <= _LABEL_CHARS:
            labels.append(line.split(":", 1)[0])
        elif len(line) <= _LABEL_CHARS:
            labels.append(line)
    return [label.strip() for label in labels if label and label.strip()]


def select_units(
    fields: tuple[ExtractionField, ...],
    units: tuple[EvidenceUnit, ...],
    budget: int,
) -> tuple[tuple[EvidenceItem, ...], tuple[str, ...], tuple[ExtractionField, ...]]:
    """Evidence for one call within `budget` characters, chosen by labels.

    1. Each field gets an equal share of the budget, spent on the items
       labelled for it (a row "Loan disbursement fee", a section "Loan service
       fees"), from its best units down. So one long table labelled for many
       fields cannot crowd out another field's only table.
    2. The rest of the budget takes whole units by score, best first; a unit
       that does not fit contributes its items labelled for the call's fields.
    3. Related-product units only with room left.

    Items are whole records, never cut (SE7); ties go by reading order. Returns
    the items in reading order, the units left out (`[partial]` when some of
    their items were), and the fields that a left-out item was labelled for.
    """
    weights = _term_weights(units)
    scores = {
        unit.key: {field: _score(unit, field, weights) for field in fields}
        for unit in units
    }
    item_labels = {
        item.evidence_id: " ".join(_labels(item))
        for unit in units
        for item in unit.items
    }

    def labelled(item: EvidenceItem, field: ExtractionField) -> bool:
        text = item_labels[item.evidence_id]
        return any(term_pattern(term).search(text) for term in FIELD_TERMS[field])

    def rank(unit: EvidenceUnit, field: ExtractionField | None = None) -> tuple:
        score = scores[unit.key][field] if field else max(scores[unit.key].values())
        return (unit.related, -score, not unit.canonical, unit.order)

    chosen: dict[str, EvidenceItem] = {}
    used = 0

    def choose(item: EvidenceItem, limit: int) -> bool:
        nonlocal used
        if item.evidence_id in chosen:
            return True
        size = len(item.content)
        if used + size > limit and chosen:
            return False
        chosen[item.evidence_id] = item
        used += size
        return True

    own = [unit for unit in units if not unit.related]
    share = budget // max(len(fields), 1)
    for field in fields:
        candidates = sorted(
            (unit for unit in own if scores[unit.key][field] > 0),
            key=lambda unit: rank(unit, field),
        )
        # Breadth first: the field's top units split its share, so the second
        # table labelled for it (a fee schedule after the tariff table) is read
        # too; what they leave is spent in rank order.
        top = candidates[:_BREADTH]
        spent = 0
        for unit in top:
            unit_share = share // len(top)
            unit_spent = 0
            for item in unit.items:
                size = len(item.content)
                if labelled(item, field) and unit_spent + size <= unit_share:
                    if choose(item, budget):
                        unit_spent += size
            spent += unit_spent
        for unit in candidates:
            for item in unit.items:
                size = len(item.content)
                if (
                    item.evidence_id not in chosen
                    and labelled(item, field)
                    and spent + size <= share
                    and choose(item, budget)
                ):
                    spent += size
    positive = sorted(
        (unit for unit in units if max(scores[unit.key].values()) > 0), key=rank
    )
    for unit in positive:
        remaining = [item for item in unit.items if item.evidence_id not in chosen]
        if sum(len(item.content) for item in remaining) <= budget - used:
            for item in remaining:
                choose(item, budget)
            continue
        for item in remaining:
            if any(labelled(item, field) for field in fields):
                choose(item, budget)
    if not chosen and units:
        first = min(units, key=lambda unit: (not unit.canonical, unit.order))
        for item in first.items:
            choose(item, budget)
    left_out_units = [
        unit
        for unit in positive
        if any(item.evidence_id not in chosen for item in unit.items)
    ]
    left_out = tuple(
        f"{unit.key} [partial]"
        if any(item.evidence_id in chosen for item in unit.items)
        else unit.key
        for unit in left_out_units
    )
    limited = tuple(
        field
        for field in fields
        if any(
            labelled(item, field) and item.evidence_id not in chosen
            for unit in left_out_units
            for item in unit.items
        )
    )
    items = tuple(sorted(chosen.values(), key=lambda item: item.order))
    return items, left_out, limited


def _term_weights(units: tuple[EvidenceUnit, ...]) -> dict[str, float]:
    """Inverse unit frequency: a term on every unit ("loan") counts for little."""
    count = len(units)
    weights: dict[str, float] = {}
    for terms in FIELD_TERMS.values():
        for term in terms:
            if term in weights:
                continue
            pattern = term_pattern(term)
            frequency = sum(1 for unit in units if pattern.search(unit.labels))
            weights[term] = math.log((count + 1) / (frequency + 0.5))
    return weights


def _score(
    unit: EvidenceUnit, field: ExtractionField, weights: dict[str, float]
) -> float:
    return sum(
        max(weights[term], 0.0)
        for term in FIELD_TERMS[field]
        if term_pattern(term).search(unit.labels)
    )


def _target_scope(
    product: ProductType,
    canonical_url: str | None,
    offering: OfferingContext | None = None,
    category: str | None = None,
) -> tuple[str, ...]:
    """Which product the call is about, from the catalog and the page (SE20).

    The same for every offering: no URL-specific rules. Which items belong to
    another product is discovery's `related_product` label.
    """
    values = [f"product_family={product.value}"]
    if category:
        values.append(f"category={category}")
    if offering is not None:
        values.append(f"offering={offering.display_name} ({offering.offering_id})")
        if offering.names:
            values.append("also_called=" + "; ".join(offering.names[:8]))
        for key, value in (
            ("page_title", offering.page_title),
            ("page_heading", offering.page_heading),
            ("page_summary", offering.page_summary),
        ):
            if value:
                values.append(f"{key}={value}")
    if canonical_url:
        values.append(f"canonical_url={canonical_url}")
    return tuple(values)
