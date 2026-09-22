"""Synthetic accepted snapshots for structured tariff migration tests.

These values are test data, not observed Ameriabank tariffs.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from decimal import Decimal
from uuid import NAMESPACE_DNS, uuid5

from app.domain.acquisition import SourceLocator, SourceType
from app.domain.models import OfferingId, ProductType
from app.domain.monitoring import SnapshotAttempt, SnapshotStatus
from app.domain.semantic_extraction import (
    AbsoluteMoneyRange,
    AgeRange,
    Condition,
    ConditionalValue,
    ConsumerLoanDetails,
    CreditLineDetails,
    EvidenceCitation,
    EvidenceItem,
    ExtractedValue,
    ExtractionField,
    ExtractionStatus,
    FeeScope,
    LoanCategory,
    LoanFee,
    LoanProduct,
    MoneyRange,
    MortgageDetails,
    OtherAmountFormula,
    OverdraftDetails,
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


@dataclass(frozen=True)
class SnapshotSpec:
    """Every dimension an evaluation case may vary on one synthetic snapshot."""

    case: str
    offering_id: OfferingId
    name: str
    category: LoanCategory
    details_kind: str = "consumer"
    url: str = CONSUMER_URL
    rate_key: str = "rate"
    reviewed: bool = False
    nominal_min_amd: Decimal = Decimal("12")
    nominal_max_amd: Decimal = Decimal("15")
    nominal_min_usd: Decimal = Decimal("10")
    nominal_max_usd: Decimal = Decimal("13")
    effective_min: Decimal = Decimal("16")
    amount_min_amd: Decimal = Decimal("100000")
    amount_max_amd: Decimal = Decimal("10000000")
    amount_min_usd: Decimal = Decimal("1000")
    amount_max_usd: Decimal = Decimal("50000")
    salary_multiple_max: Decimal | None = Decimal("10")
    term_max_months: int = 60
    fees: tuple[tuple[str, Decimal | None, Decimal | None], ...] = (
        ("Application fee", Decimal("5000"), None),
    )
    salary_privilege: bool = True
    age_range: tuple[int | None, int | None] | None = None
    purposes: tuple[str, ...] = ("Personal use",)
    accepted_at: datetime = AS_OF
    down_payment_pct: Decimal | None = Decimal("20")
    property_market: PropertyMarket | None = None
    collateral_description: str | None = None
    credit_limit_max_amd: Decimal | None = None
    grace_period_days: int | None = None
    linked_account_or_card: str | None = None
    extra_evidence_salt: str = ""
    tags: tuple[str, ...] = field(default=())

    @property
    def product(self) -> ProductType:
        return self.offering_id.product


_LEGACY_SPECS = {
    "consumer": SnapshotSpec(
        case="consumer",
        offering_id=OfferingId.CONSUMER_STANDARD,
        name="Synthetic consumer loan",
        category=LoanCategory.CONSUMER_LOAN,
    ),
    "reviewed_consumer": SnapshotSpec(
        case="reviewed_consumer",
        offering_id=OfferingId.CONSUMER_STANDARD,
        name="Synthetic consumer loan",
        category=LoanCategory.CONSUMER_LOAN,
        rate_key="rate_review",
        reviewed=True,
        nominal_min_amd=Decimal("11"),
    ),
    "mortgage": SnapshotSpec(
        case="mortgage",
        offering_id=OfferingId.MORTGAGE_PRIMARY,
        name="Synthetic primary-market mortgage",
        category=LoanCategory.MORTGAGE,
        details_kind="mortgage",
        url=MORTGAGE_URL,
        term_max_months=240,
        salary_privilege=False,
        purposes=("Purchase a primary-market home",),
        property_market=PropertyMarket.PRIMARY,
        collateral_description="Purchased property",
    ),
}


def _key(spec: SnapshotSpec, name: str) -> str:
    return name + spec.extra_evidence_salt


def build_snapshot(spec: SnapshotSpec) -> SnapshotAttempt:
    """Build one fully typed accepted snapshot from a declarative fixture spec."""
    url = spec.url
    condition_amd = (Condition(dimension="currency", value="AMD"),)
    condition_usd = (Condition(dimension="currency", value="USD"),)
    amount: tuple[ConditionalValue, ...] = (
        ConditionalValue(
            value=AbsoluteMoneyRange(
                range=MoneyRange(
                    min=spec.amount_min_amd, max=spec.amount_max_amd, currency="AMD"
                )
            ),
            conditions=condition_amd,
        ),
        ConditionalValue(
            value=AbsoluteMoneyRange(
                range=MoneyRange(
                    min=spec.amount_min_usd, max=spec.amount_max_usd, currency="USD"
                )
            ),
            conditions=condition_usd,
        ),
    )
    if spec.salary_multiple_max is not None:
        amount += (
            ConditionalValue(
                value=SalaryMultiple(max_multiple=spec.salary_multiple_max)
            ),
            ConditionalValue(
                value=OtherAmountFormula(
                    expression="up to verified income times policy factor"
                )
            ),
        )
    rates = (
        ConditionalValue(
            value=Rate(
                min=spec.nominal_min_amd,
                max=spec.nominal_max_amd,
                rate_type=RateType.FIXED,
            ),
            conditions=condition_amd,
        ),
        ConditionalValue(
            value=Rate(
                min=spec.nominal_min_usd,
                max=spec.nominal_max_usd,
                rate_type=RateType.FIXED,
            ),
            conditions=condition_usd,
        ),
    )
    fees = tuple(
        LoanFee(
            description=description,
            scope=FeeScope.PRODUCT,
            amount=amount_value,
            currency="AMD" if amount_value is not None else None,
            rate_pct=rate_pct,
        )
        for description, amount_value, rate_pct in spec.fees
    )
    common = {
        "product_name": _found(spec.name, _key(spec, "name"), spec.name, url),
        "formal_terms_names": _missing(),
        "variants": _missing(),
        "category": spec.category,
        "purpose": _found(spec.purposes, _key(spec, "purpose"), "Product purpose", url),
        "loan_amount": _found(
            amount,
            _key(spec, "amount"),
            "Amount terms in AMD, USD and formulas",
            url,
        ),
        "interest_rate": _found(
            rates, _key(spec, spec.rate_key), "Nominal rate schedule", url
        ),
        "effective_rate": _found(
            (
                ConditionalValue(
                    value=Rate(min=spec.effective_min, rate_type=RateType.FIXED)
                ),
            ),
            _key(spec, "effective"),
            "Effective rate",
            url,
        ),
        "term": _found(
            (ConditionalValue(value=TermRange(max_months=spec.term_max_months)),),
            _key(spec, "term"),
            "Maximum term",
            url,
        ),
        "fees": _found(fees, _key(spec, "fee"), "Application fee", url),
        "repayment": _missing(),
        "eligibility": _missing(),
        "residency_requirements": _missing(),
        "age_requirements": (
            _found(
                (
                    ConditionalValue(
                        value=AgeRange(
                            min_age=spec.age_range[0], max_age=spec.age_range[1]
                        )
                    ),
                ),
                _key(spec, "age"),
                "Applicant age range",
                url,
            )
            if spec.age_range is not None
            else _missing()
        ),
        "application_channel": _missing(),
        "required_documents": _missing(),
        "special_conditions": (
            _found(
                ("Salary customers may receive a privilege",),
                _key(spec, "salary"),
                "Salary-customer privilege",
                url,
            )
            if spec.salary_privilege
            else _missing()
        ),
        "canonical_url": url,
        "retrieved_at": AS_OF,
    }
    collateral = (
        _found(
            (
                ConditionalValue(
                    value={
                        "description": spec.collateral_description,
                        "applicable": True,
                    }
                ),
            ),
            _key(spec, "collateral"),
            f"{spec.collateral_description} as collateral",
            url,
        )
        if spec.collateral_description is not None
        else _missing()
    )
    if spec.details_kind == "mortgage":
        details = MortgageDetails(
            property_market=(
                _found(
                    spec.property_market,
                    _key(spec, "market"),
                    "Property market",
                    url,
                )
                if spec.property_market is not None
                else _missing()
            ),
            down_payment_pct=(
                _found(
                    (ConditionalValue(value=spec.down_payment_pct),),
                    _key(spec, "down"),
                    f"Down payment {spec.down_payment_pct}%",
                    url,
                )
                if spec.down_payment_pct is not None
                else _missing()
            ),
            ltv_pct=_missing(),
            collateral=collateral,
            income_verification_required=_missing(),
            creditworthiness_assessment_required=_missing(),
            property_requirements=_missing(),
        )
    elif spec.details_kind == "overdraft":
        details = OverdraftDetails(
            credit_limit=_found(
                (
                    AbsoluteMoneyRange(
                        range=MoneyRange(max=spec.credit_limit_max_amd, currency="AMD")
                    ),
                ),
                _key(spec, "limit"),
                "Overdraft credit limit",
                url,
            ),
            grace_period_days=(
                _found(
                    spec.grace_period_days,
                    _key(spec, "grace"),
                    "Grace period",
                    url,
                )
                if spec.grace_period_days is not None
                else _missing()
            ),
            revolving=_found(True, _key(spec, "revolving"), "Revolving limit", url),
            linked_account_or_card=(
                _found(
                    spec.linked_account_or_card,
                    _key(spec, "linked"),
                    "Linked account",
                    url,
                )
                if spec.linked_account_or_card is not None
                else _missing()
            ),
        )
    elif spec.details_kind == "credit_line":
        details = CreditLineDetails(
            credit_limit=_found(
                (
                    AbsoluteMoneyRange(
                        range=MoneyRange(max=spec.credit_limit_max_amd, currency="AMD")
                    ),
                ),
                _key(spec, "limit"),
                "Credit line limit",
                url,
            ),
            grace_period_days=(
                _found(
                    spec.grace_period_days,
                    _key(spec, "grace"),
                    "Grace period",
                    url,
                )
                if spec.grace_period_days is not None
                else _missing()
            ),
            revolving=_found(True, _key(spec, "revolving"), "Revolving limit", url),
        )
    else:
        details = ConsumerLoanDetails(
            collateral=collateral,
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
            batch_id="review:synthetic" if spec.reviewed else "synthetic-rate",
        ),
    )
    extraction = SemanticExtractionResult(
        product=spec.product,
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
        id=uuid5(NAMESPACE_DNS, f"synthetic-snapshot-{spec.case}"),
        run_id=uuid5(NAMESPACE_DNS, f"synthetic-run-{spec.case}"),
        offering_execution_id=uuid5(NAMESPACE_DNS, f"synthetic-execution-{spec.case}"),
        product=spec.product,
        offering_id=spec.offering_id,
        status=SnapshotStatus.ACCEPTED,
        normalized_tariff=payload,
        evidence=tuple(item.model_dump(mode="json") for item in evidence_catalog),
        semantic_extraction=extraction.model_dump(mode="json"),
        validation={"accepted": True, "reviewed": spec.reviewed},
        canonical_sha256=canonical_sha256(payload),
        created_at=spec.accepted_at,
        accepted_at=spec.accepted_at,
    )


def accepted_snapshot(case: str) -> SnapshotAttempt:
    """Return a fully typed, accepted synthetic snapshot for one named scenario."""
    if case not in _LEGACY_SPECS:
        raise ValueError(case)
    return build_snapshot(_LEGACY_SPECS[case])


def spec_for(case: str) -> SnapshotSpec:
    return _LEGACY_SPECS[case]


def derive(case: str, **changes) -> SnapshotSpec:
    """Return a variant of a named base spec with an isolated evidence namespace."""
    base = _LEGACY_SPECS[case]
    changes.setdefault("extra_evidence_salt", ":" + str(changes.get("case", case)))
    return replace(base, **changes)
