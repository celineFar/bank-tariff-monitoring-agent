from __future__ import annotations

import hashlib

from app.config import SemanticExtractionSettings
from app.domain.models import ProductType
from app.domain.semantic_extraction import (
    EvidenceItem,
    ExtractionBatch,
    ExtractionField,
)
from app.domain.source_discovery import InformationRole

_GROUPS: tuple[tuple[str, tuple[ExtractionField, ...], tuple[str, ...]], ...] = (
    (
        "identity",
        (
            ExtractionField.PRODUCT_NAME,
            ExtractionField.CATEGORY,
            ExtractionField.PURPOSE,
        ),
        ("product", "loan", "purpose", "mortgage", "credit line", "overdraft"),
    ),
    (
        "core_financial",
        (
            ExtractionField.LOAN_AMOUNT,
            ExtractionField.INTEREST_RATE,
            ExtractionField.EFFECTIVE_RATE,
            ExtractionField.TERM,
        ),
        ("amount", "rate", "interest", "apr", "term", "month", "%", "amd", "usd", "eur"),
    ),
    (
        "fees_and_repayment",
        (ExtractionField.FEES, ExtractionField.REPAYMENT),
        ("fee", "commission", "repayment", "annuity", "payment", "charge"),
    ),
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
        ("eligible", "resident", "age", "application", "document", "passport", "condition"),
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


def build_extraction_batches(
    product: ProductType,
    evidence: tuple[EvidenceItem, ...],
    settings: SemanticExtractionSettings,
) -> tuple[ExtractionBatch, ...]:
    if not evidence:
        raise ValueError("semantic extraction requires at least one evidence item")
    definitions = (*_GROUPS, ("product_details", _PRODUCT_FIELDS[product], ()))
    batches: list[ExtractionBatch] = []
    for group, fields, keywords in definitions:
        selected = _select_evidence(group, keywords, evidence, settings)
        fingerprint = hashlib.sha256(
            "\x1e".join(
                (
                    group,
                    *(field.value for field in fields),
                    *(f"{item.evidence_id}\x1f{item.content}" for item in selected),
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
            )
        )
    return tuple(batches)


def _select_evidence(
    group: str,
    keywords: tuple[str, ...],
    evidence: tuple[EvidenceItem, ...],
    settings: SemanticExtractionSettings,
) -> tuple[EvidenceItem, ...]:
    roles = _ROLE_GROUPS[group]
    ranked = sorted(
        evidence,
        key=lambda item: (
            -_relevance_score(item, roles, keywords),
            item.precedence,
            item.document_id,
            item.source_item_id,
        ),
    )
    selected: list[EvidenceItem] = []
    characters = 0
    for item in ranked:
        score = _relevance_score(item, roles, keywords)
        if score == 0 and selected:
            continue
        content = item.content[: settings.max_evidence_chars_per_item]
        if selected and characters + len(content) > settings.max_chars_per_batch:
            continue
        selected.append(item.model_copy(update={"content": content}))
        characters += len(content)
        if len(selected) >= settings.max_items_per_batch:
            break
    if not selected:
        item = evidence[0]
        selected.append(
            item.model_copy(
                update={"content": item.content[: settings.max_evidence_chars_per_item]}
            )
        )
    return tuple(selected)


def _relevance_score(
    item: EvidenceItem,
    roles: frozenset[InformationRole],
    keywords: tuple[str, ...],
) -> int:
    text = f"{item.section or ''} {item.content}".casefold()
    return (
        (5 if item.role in roles else 0)
        + sum(keyword in text for keyword in keywords)
        + max(0, 4 - item.precedence)
    )
