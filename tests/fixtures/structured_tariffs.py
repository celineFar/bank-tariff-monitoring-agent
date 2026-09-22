"""Synthetic accepted snapshots for structured tariff migration tests.

These values are test data, not observed Ameriabank tariffs.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from decimal import Decimal
from uuid import NAMESPACE_DNS, uuid5

from app.domain.acquisition import SourceLocator, SourceType
from app.domain.models import OfferingId, ProductType
from app.domain.monitoring import SnapshotAttempt, SnapshotStatus
from app.domain.semantic_extraction import (
    AbsoluteMoneyRange,
    Condition,
    ConditionalValue,
    ConsumerLoanDetails,
    EvidenceCitation,
    EvidenceItem,
    ExtractedValue,
    ExtractionField,
    ExtractionStatus,
    LoanCategory,
    LoanFee,
    LoanProduct,
    MoneyRange,
    MortgageDetails,
    OtherAmountFormula,
    PropertyMarket,
    Rate,
    RateType,
    SalaryMultiple,
    SemanticExtractionResult,
    TermRange,
    ValidatedFieldResult,
)
from app.domain.source_discovery import Authority, InformationRole, TemporalStatus
from app.services.snapshot_lifecycle import canonical_sha256, canonical_tariff_payload

AS_OF = datetime(2026, 9, 21, tzinfo=UTC)
CONSUMER_URL = "https://ameriabank.am/en/personal/loans/consumer-loans/consumer-loans"
MORTGAGE_URL = "https://ameriabank.am/en/personal/loans/mortgage/primary"


def _citation(key: str, quote: str, url: str) -> EvidenceCitation:
    evidence_id = "ev_" + hashlib.sha256(key.encode()).hexdigest()[:24]
    return EvidenceCitation(
        evidence_id=evidence_id,
        source_item_id=key,
        source_url=url,
        source_type=SourceType.PAGE,
        quote=quote,
        section="Synthetic fixture",
        locator=SourceLocator(
            source_url=url,
            source_type=SourceType.PAGE,
            block_id=key,
        ),
        authority=Authority.OFFICIAL_PRODUCT_CONTENT,
    )


def _found(value, key: str, quote: str, url: str):
    return ExtractedValue(
        status=ExtractionStatus.FOUND,
        value=value,
        evidence=(_citation(key, quote, url),),
    )


def _missing():
    return ExtractedValue(status=ExtractionStatus.NOT_STATED)


def accepted_snapshot(case: str) -> SnapshotAttempt:
    """Return a fully typed, accepted synthetic snapshot for one named scenario."""
    if case not in {"consumer", "reviewed_consumer", "mortgage"}:
        raise ValueError(case)
    mortgage = case == "mortgage"
    reviewed = case == "reviewed_consumer"
    url = MORTGAGE_URL if mortgage else CONSUMER_URL
    product_type = ProductType.MORTGAGE if mortgage else ProductType.CONSUMER_LOAN
    offering_id = (
        OfferingId.MORTGAGE_PRIMARY if mortgage else OfferingId.CONSUMER_STANDARD
    )
    name = (
        "Synthetic primary-market mortgage" if mortgage else "Synthetic consumer loan"
    )
    condition_amd = (Condition(dimension="currency", value="AMD"),)
    condition_usd = (Condition(dimension="currency", value="USD"),)
    amount = (
        ConditionalValue(
            value=AbsoluteMoneyRange(
                range=MoneyRange(
                    min=Decimal("100000"), max=Decimal("10000000"), currency="AMD"
                )
            ),
            conditions=condition_amd,
        ),
        ConditionalValue(
            value=AbsoluteMoneyRange(
                range=MoneyRange(
                    min=Decimal("1000"), max=Decimal("50000"), currency="USD"
                )
            ),
            conditions=condition_usd,
        ),
        ConditionalValue(value=SalaryMultiple(max_multiple=Decimal("10"))),
        ConditionalValue(
            value=OtherAmountFormula(
                expression="up to verified income times policy factor"
            )
        ),
    )
    nominal_amd = Decimal("11") if reviewed else Decimal("12")
    rates = (
        ConditionalValue(
            value=Rate(min=nominal_amd, max=Decimal("15"), rate_type=RateType.FIXED),
            conditions=condition_amd,
        ),
        ConditionalValue(
            value=Rate(min=Decimal("10"), max=Decimal("13"), rate_type=RateType.FIXED),
            conditions=condition_usd,
        ),
    )
    fee = LoanFee(
        description="Application fee",
        scope="product",
        amount=Decimal("5000"),
        currency="AMD",
    )
    common = {
        "product_name": _found(name, "name", name, url),
        "formal_terms_names": _missing(),
        "variants": _missing(),
        "category": LoanCategory.MORTGAGE if mortgage else LoanCategory.CONSUMER_LOAN,
        "purpose": _found(
            ("Purchase a primary-market home",) if mortgage else ("Personal use",),
            "purpose",
            "Product purpose",
            url,
        ),
        "loan_amount": _found(
            amount, "amount", "Amount terms in AMD, USD and formulas", url
        ),
        "interest_rate": _found(
            rates, "rate_review" if reviewed else "rate", "Nominal rate schedule", url
        ),
        "effective_rate": _found(
            (
                ConditionalValue(
                    value=Rate(min=Decimal("16"), rate_type=RateType.FIXED)
                ),
            ),
            "effective",
            "Effective rate",
            url,
        ),
        "term": _found(
            (ConditionalValue(value=TermRange(max_months=240 if mortgage else 60)),),
            "term",
            "Maximum term",
            url,
        ),
        "fees": _found((fee,), "fee", "Application fee", url),
        "repayment": _missing(),
        "eligibility": _missing(),
        "residency_requirements": _missing(),
        "age_requirements": _missing(),
        "application_channel": _missing(),
        "required_documents": _missing(),
        "special_conditions": _found(
            ("Salary customers may receive a privilege",),
            "salary",
            "Salary-customer privilege",
            url,
        )
        if not mortgage
        else _missing(),
        "canonical_url": url,
        "retrieved_at": AS_OF,
    }
    if mortgage:
        details = MortgageDetails(
            property_market=_found(
                PropertyMarket.PRIMARY, "market", "Primary market", url
            ),
            down_payment_pct=_found(
                (ConditionalValue(value=Decimal("20")),),
                "down",
                "Down payment 20%",
                url,
            ),
            ltv_pct=_missing(),
            collateral=_found(
                (
                    ConditionalValue(
                        value={"description": "Purchased property", "applicable": True}
                    ),
                ),
                "collateral",
                "Purchased property as collateral",
                url,
            ),
            income_verification_required=_missing(),
            creditworthiness_assessment_required=_missing(),
            property_requirements=_missing(),
        )
    else:
        details = ConsumerLoanDetails(
            collateral=_missing(),
            income_verification_required=_missing(),
            creditworthiness_assessment_required=_missing(),
        )
    product = LoanProduct(**common, details=details)
    citations = {
        citation.evidence_id: citation
        for _, extracted in product
        if isinstance(extracted, ExtractedValue)
        for citation in extracted.evidence
    }
    for _, extracted in details:
        if isinstance(extracted, ExtractedValue):
            for citation in extracted.evidence:
                citations[citation.evidence_id] = citation
    evidence_catalog = tuple(
        EvidenceItem(
            evidence_id=citation.evidence_id,
            document_id="synthetic-page",
            source_item_id=citation.source_item_id,
            content=citation.quote,
            role=InformationRole.PRICING,
            authority=citation.authority,
            temporal_status=TemporalStatus.CURRENT,
            precedence=1,
            locator=citation.locator,
        )
        for citation in citations.values()
    )
    validated_fields = (
        ValidatedFieldResult(
            field=ExtractionField.INTEREST_RATE,
            status=ExtractionStatus.FOUND,
            value=rates,
            evidence=product.interest_rate.evidence,
            batch_id="review:synthetic" if reviewed else "synthetic-rate",
        ),
    )
    extraction = SemanticExtractionResult(
        product=product_type,
        model_name="synthetic-fixture",
        loan_product=product,
        evidence_catalog=evidence_catalog,
        batch_results=(),
        validated_fields=validated_fields,
        review_items=(),
        reused_batch_count=0,
    )
    payload = canonical_tariff_payload(product)
    return SnapshotAttempt(
        id=uuid5(NAMESPACE_DNS, f"synthetic-snapshot-{case}"),
        run_id=uuid5(NAMESPACE_DNS, f"synthetic-run-{case}"),
        offering_execution_id=uuid5(NAMESPACE_DNS, f"synthetic-execution-{case}"),
        product=product_type,
        offering_id=offering_id,
        status=SnapshotStatus.ACCEPTED,
        normalized_tariff=payload,
        evidence=tuple(item.model_dump(mode="json") for item in evidence_catalog),
        semantic_extraction=extraction.model_dump(mode="json"),
        validation={"accepted": True, "reviewed": reviewed},
        canonical_sha256=canonical_sha256(payload),
        created_at=AS_OF,
        accepted_at=AS_OF,
    )
