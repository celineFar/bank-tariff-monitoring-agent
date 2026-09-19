from __future__ import annotations

import hashlib
import math
import re

from app.config import SemanticExtractionSettings
from app.domain.models import ProductType
from app.domain.semantic_extraction import (
    EvidenceItem,
    ExtractionBatch,
    ExtractionField,
)
from app.domain.source_discovery import InformationRole, ProductAssociation

_GROUPS: tuple[tuple[str, tuple[ExtractionField, ...]], ...] = (
    (
        "identity",
        (
            ExtractionField.PRODUCT_NAME,
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
            ExtractionField.REQUIRED_DOCUMENTS,
            ExtractionField.SPECIAL_CONDITIONS,
        ),
    ),
)

_PRODUCT_FIELDS: dict[ProductType, tuple[ExtractionField, ...]] = {
    ProductType.CONSUMER_LOAN: (
        ExtractionField.COLLATERAL,
        ExtractionField.INCOME_VERIFICATION_REQUIRED,
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
        ExtractionField.PROPERTY_REQUIREMENTS,
    ),
}

_ROLE_GROUPS: dict[str, frozenset[InformationRole]] = {
    "identity": frozenset(
        {InformationRole.PRODUCT_DESCRIPTION, InformationRole.PRODUCT_TERMS}
    ),
    "core_financial": frozenset(
        {InformationRole.PRODUCT_TERMS, InformationRole.PRICING}
    ),
    "fees_and_repayment": frozenset(
        {InformationRole.FEES, InformationRole.REPAYMENT, InformationRole.PRODUCT_TERMS}
    ),
    "eligibility_and_documents": frozenset(
        {
            InformationRole.ELIGIBILITY,
            InformationRole.DOCUMENTS,
            InformationRole.FAQ,
            InformationRole.PRODUCT_TERMS,
            InformationRole.CAMPAIGN_TERMS,
        }
    ),
    "product_details": frozenset(
        {
            InformationRole.PRODUCT_TERMS,
            InformationRole.ELIGIBILITY,
            InformationRole.PRICING,
            InformationRole.DOCUMENTS,
        }
    ),
}

# Retrieval terms only: they rank evidence and never manufacture a value.
FIELD_KEYWORDS: dict[ExtractionField, tuple[str, ...]] = {
    ExtractionField.PRODUCT_NAME: (
        "product name",
        "loan name",
        "mortgage loan",
        "consumer loan",
    ),
    ExtractionField.CATEGORY: ("mortgage", "consumer loan", "overdraft", "credit line"),
    ExtractionField.PURPOSE: ("purpose", "purchase", "refinancing"),
    ExtractionField.LOAN_AMOUNT: (
        "minimum and maximum loan",
        "loan amount",
        "loan limit",
        "maximum amount",
        "minimum amount",
    ),
    ExtractionField.INTEREST_RATE: (
        "annual interest rate",
        "nominal interest",
        "interest rate",
    ),
    ExtractionField.EFFECTIVE_RATE: (
        "annual percentage rate",
        "effective interest",
        "apr",
    ),
    ExtractionField.TERM: ("term (months)", "loan term", "term in months", "duration"),
    ExtractionField.FEES: (
        "fee",
        "commission",
        "charge",
        "service fee",
        "disbursement fee",
    ),
    ExtractionField.REPAYMENT: (
        "repayment method",
        "forms of loan repayment",
        "annuity",
        "differentiated",
    ),
    ExtractionField.ELIGIBILITY: (
        "eligibility",
        "eligible",
        "customer's personal details",
        "borrower",
    ),
    ExtractionField.RESIDENCY_REQUIREMENTS: ("residency", "resident", "non-resident"),
    ExtractionField.AGE_REQUIREMENTS: ("age", "years old", "borrower's age"),
    ExtractionField.APPLICATION_CHANNEL: (
        "application channel",
        "apply online",
        "online application",
    ),
    ExtractionField.REQUIRED_DOCUMENTS: (
        "required documents",
        "documents required",
        "loan application",
    ),
    ExtractionField.SPECIAL_CONDITIONS: (
        "special conditions",
        "other terms",
        "subsid",
        "developer",
    ),
    ExtractionField.COLLATERAL: (
        "eligible collateral",
        "security",
        "pledge",
        "collateral",
    ),
    ExtractionField.INCOME_VERIFICATION_REQUIRED: (
        "income verification",
        "creditworthiness assessment",
        "proof of income",
    ),
    ExtractionField.PROPERTY_MARKET: (
        "primary market",
        "secondary market",
        "property market",
    ),
    ExtractionField.DOWN_PAYMENT_PCT: ("minimum down payment", "down payment"),
    ExtractionField.LTV_PCT: ("loan-to-value", "ltv ratio", "ltv"),
    ExtractionField.PROPERTY_REQUIREMENTS: (
        "property requirements",
        "real estate",
        "property abroad",
    ),
    ExtractionField.CREDIT_LIMIT: ("credit limit", "maximum limit", "minimum limit"),
    ExtractionField.GRACE_PERIOD_DAYS: ("grace period", "interest-free period"),
    ExtractionField.REVOLVING: ("revolving", "renewable credit"),
    ExtractionField.LINKED_ACCOUNT_OR_CARD: (
        "linked account",
        "linked card",
        "payment card",
    ),
}

_PRIMARY_VARIANT_PATTERN = re.compile(
    r"(?:express|secondary[\s_-]*market|construction[\s_-]*loan|"
    r"renovation[\s_-]*loan|flexible[\s_-]*opportunit)",
    re.IGNORECASE,
)


def build_extraction_batches(
    product: ProductType,
    evidence: tuple[EvidenceItem, ...],
    settings: SemanticExtractionSettings,
    *,
    canonical_url: str | None = None,
) -> tuple[ExtractionBatch, ...]:
    if not evidence:
        raise ValueError("semantic extraction requires at least one evidence item")
    definitions = (*_GROUPS, ("product_details", _PRODUCT_FIELDS[product]))
    target_scope = _target_scope(product, canonical_url)
    batches: list[ExtractionBatch] = []
    for group, fields in definitions:
        selected = select_evidence_for_fields(
            group,
            fields,
            evidence,
            settings,
            canonical_url=canonical_url,
        )
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
                id=f"extract_{len(batches):03d}",
                product=product,
                group=group,
                fields=fields,
                evidence=selected,
                content_fingerprint=fingerprint,
                canonical_url=canonical_url,
                target_scope=target_scope,
            )
        )
    return tuple(batches)


def select_evidence_for_fields(
    group: str,
    fields: tuple[ExtractionField, ...],
    evidence: tuple[EvidenceItem, ...],
    settings: SemanticExtractionSettings,
    *,
    canonical_url: str | None = None,
) -> tuple[EvidenceItem, ...]:
    """Select evidence with a guaranteed quota for every requested field."""

    roles = _ROLE_GROUPS[group]
    per_field_limit = max(2, math.ceil(settings.max_items_per_batch / len(fields)))
    selected: list[EvidenceItem] = []
    selected_ids: set[str] = set()
    characters = 0

    def add(item: EvidenceItem, *, content_limit: int | None = None) -> bool:
        nonlocal characters
        if item.evidence_id in selected_ids:
            return False
        limit = settings.max_evidence_chars_per_item
        if content_limit is not None:
            limit = min(limit, max(1, content_limit))
        content = item.content[:limit]
        if selected and characters + len(content) > settings.max_chars_per_batch:
            return False
        selected.append(item.model_copy(update={"content": content}))
        selected_ids.add(item.evidence_id)
        characters += len(content)
        return True

    ranked_by_field = {
        field: tuple(
            item
            for item in sorted(
                evidence,
                key=lambda item: (
                    -_field_score(item, field, roles, canonical_url),
                    item.precedence,
                    item.document_id,
                    item.source_item_id,
                ),
            )
            if field_has_evidence_marker(field, item)
            and not _outside_canonical_scope(item, canonical_url)
        )
        for field in fields
    }

    # First pass reserves room for the strongest item for every field. This is
    # what prevents a long interest-rate table from crowding term or amount out.
    for index, field in enumerate(fields):
        ranked = ranked_by_field[field]
        if not ranked:
            continue
        remaining_fields = max(1, len(fields) - index)
        reserved = (settings.max_chars_per_batch - characters) // remaining_fields
        add(ranked[0], content_limit=reserved)

    for field in fields:
        ranked = ranked_by_field[field]
        field_count = 0
        for item in ranked:
            if add(item):
                field_count += 1
            if (
                field_count >= per_field_limit
                or len(selected) >= settings.max_items_per_batch
            ):
                break
        if len(selected) >= settings.max_items_per_batch:
            break

    ranked_context = sorted(
        evidence,
        key=lambda item: (
            -max(_field_score(item, field, roles, canonical_url) for field in fields),
            item.precedence,
            item.document_id,
            item.source_item_id,
        ),
    )
    for item in ranked_context:
        if len(selected) >= settings.max_items_per_batch:
            break
        if _outside_canonical_scope(item, canonical_url):
            continue
        add(item)

    if not selected:
        add(evidence[0])
    return tuple(selected)


def field_has_evidence_marker(field: ExtractionField, item: EvidenceItem) -> bool:
    text = f"{item.section or ''} {item.content}".casefold()
    return any(keyword.casefold() in text for keyword in FIELD_KEYWORDS[field])


def _field_score(
    item: EvidenceItem,
    field: ExtractionField,
    roles: frozenset[InformationRole],
    canonical_url: str | None,
) -> int:
    text = f"{item.section or ''} {item.content}".casefold()
    keyword_score = sum(
        2 + min(3, keyword.count(" "))
        for keyword in FIELD_KEYWORDS[field]
        if keyword.casefold() in text
    )
    association_score = {
        ProductAssociation.CURRENT_PRODUCT: 14,
        ProductAssociation.UNKNOWN: 2,
        ProductAssociation.GENERIC_BANK_INFORMATION: -4,
        ProductAssociation.RELATED_PRODUCT: -14,
        ProductAssociation.GLOBAL_NAVIGATION: -20,
        ProductAssociation.HISTORICAL_VERSION: -30,
        ProductAssociation.FUTURE_VERSION: -30,
    }[item.product_association]
    source_url = str(item.locator.source_url).casefold()
    canonical_score = (
        8
        if canonical_url
        and source_url.rstrip("/") == canonical_url.casefold().rstrip("/")
        else 0
    )
    variant_penalty = 0
    if _outside_canonical_scope(item, canonical_url):
        variant_penalty = 24
    return (
        keyword_score
        + (6 if item.role in roles else 0)
        + max(0, 5 - item.precedence)
        + association_score
        + canonical_score
        - variant_penalty
    )


def _target_scope(product: ProductType, canonical_url: str | None) -> tuple[str, ...]:
    values = [f"product_family={product.value}"]
    if canonical_url:
        values.append(f"canonical_url={canonical_url}")
        if "/mortgage/primary" in canonical_url.casefold():
            values.extend(
                (
                    "target=base home-purchase mortgage for the primary market",
                    "exclude_as_base=Express Home, secondary-market, construction, renovation, and developer-program variants",
                )
            )
    return tuple(values)


def _outside_canonical_scope(item: EvidenceItem, canonical_url: str | None) -> bool:
    if item.product_association in {
        ProductAssociation.RELATED_PRODUCT,
        ProductAssociation.GLOBAL_NAVIGATION,
        ProductAssociation.HISTORICAL_VERSION,
        ProductAssociation.FUTURE_VERSION,
    }:
        return True
    if not canonical_url or "/mortgage/primary" not in canonical_url.casefold():
        return False
    scope_text = f"{item.locator.source_url} {item.section or ''}"
    return _PRIMARY_VARIANT_PATTERN.search(scope_text) is not None
