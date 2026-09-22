"""One synthetic accepted read model covering the 25 target questions.

Values are fabricated test data with deliberately chosen spreads: they exercise
family extrema, currency separation, incomparable fee bases, a missing
offering, and one accepted change with old and new evidence. They are not
observed Ameriabank tariffs.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import NAMESPACE_DNS, uuid5

from app.domain.models import OfferingId, ProductType
from app.domain.monitoring import SnapshotChange, SnapshotChangeSet
from app.domain.semantic_extraction import LoanCategory, PropertyMarket
from app.domain.structured_tariffs import (
    FieldPath,
    OfferingProfile,
    RetrievalUnit,
    StructuredProjection,
    TariffFact,
)
from app.repositories.structured_tariff_query import RankedUnit
from app.services.structured_projection import StructuredTariffProjector
from tests.fixtures.structured_tariffs import (
    CONSUMER_URL,
    MORTGAGE_URL,
    SnapshotSpec,
    build_snapshot,
)

CORPUS_AS_OF = datetime(2026, 9, 21, tzinfo=UTC)
PREVIOUS_AS_OF = CORPUS_AS_OF - timedelta(days=30)

CORPUS_SPECS: tuple[SnapshotSpec, ...] = (
    SnapshotSpec(
        case="eval_consumer_standard",
        offering_id=OfferingId.CONSUMER_STANDARD,
        name="Consumer Loans",
        category=LoanCategory.CONSUMER_LOAN,
        url=CONSUMER_URL,
        nominal_min_amd=Decimal("12"),
        nominal_max_amd=Decimal("15"),
        effective_min=Decimal("16"),
        amount_max_amd=Decimal("10000000"),
        term_max_months=60,
        fees=(("Application fee", Decimal("5000"), None),),
        purposes=("Personal use",),
        age_range=(21, 63),
    ),
    SnapshotSpec(
        case="eval_overdraft",
        offering_id=OfferingId.OVERDRAFT,
        name="Overdraft",
        category=LoanCategory.OVERDRAFT,
        details_kind="overdraft",
        url=CONSUMER_URL,
        nominal_min_amd=Decimal("14"),
        nominal_max_amd=Decimal("18"),
        effective_min=Decimal("18"),
        amount_min_amd=Decimal("50000"),
        amount_max_amd=Decimal("2000000"),
        term_max_months=12,
        fees=(("Application fee", Decimal("3000"), None),),
        purposes=("Short-term card spending cover",),
        credit_limit_max_amd=Decimal("2000000"),
        grace_period_days=30,
        linked_account_or_card="Salary card account",
    ),
    SnapshotSpec(
        case="eval_credit_line",
        offering_id=OfferingId.CREDIT_LINE,
        name="Credit Line",
        category=LoanCategory.CREDIT_LINE,
        details_kind="credit_line",
        url=CONSUMER_URL,
        nominal_min_amd=Decimal("13"),
        nominal_max_amd=Decimal("17"),
        effective_min=Decimal("17"),
        amount_min_amd=Decimal("50000"),
        amount_max_amd=Decimal("3000000"),
        term_max_months=36,
        fees=(
            ("Application fee", Decimal("4000"), None),
            ("Service fee", None, Decimal("0.5")),
        ),
        purposes=("Revolving card financing",),
        credit_limit_max_amd=Decimal("3000000"),
        grace_period_days=45,
    ),
    SnapshotSpec(
        case="eval_online_consumer_finance",
        offering_id=OfferingId.ONLINE_CONSUMER_FINANCE,
        name="Online Consumer Finance",
        category=LoanCategory.CONSUMER_LOAN,
        url=CONSUMER_URL,
        nominal_min_amd=Decimal("9"),
        nominal_max_amd=Decimal("11"),
        effective_min=Decimal("15"),
        amount_min_amd=Decimal("50000"),
        amount_max_amd=Decimal("1500000"),
        term_max_months=24,
        fees=(("Application fee", Decimal("2000"), None),),
        purposes=("Financing an online purchase in instalments",),
    ),
    SnapshotSpec(
        case="eval_mortgage_primary",
        offering_id=OfferingId.MORTGAGE_PRIMARY,
        name="Primary Market Mortgage",
        category=LoanCategory.MORTGAGE,
        details_kind="mortgage",
        url=MORTGAGE_URL,
        nominal_min_amd=Decimal("11"),
        nominal_max_amd=Decimal("13"),
        effective_min=Decimal("14"),
        amount_min_amd=Decimal("1000000"),
        amount_max_amd=Decimal("60000000"),
        term_max_months=240,
        fees=(("Application fee", Decimal("10000"), None),),
        salary_privilege=False,
        purposes=("Purchase a primary-market home",),
        down_payment_pct=Decimal("20"),
        property_market=PropertyMarket.PRIMARY,
        collateral_description="Purchased primary-market property",
    ),
    SnapshotSpec(
        case="eval_mortgage_secondary",
        offering_id=OfferingId.MORTGAGE_SECONDARY_MARKET,
        name="Secondary Market Mortgage",
        category=LoanCategory.MORTGAGE,
        details_kind="mortgage",
        url=MORTGAGE_URL,
        nominal_min_amd=Decimal("12"),
        nominal_max_amd=Decimal("14"),
        effective_min=Decimal("15"),
        amount_min_amd=Decimal("1000000"),
        amount_max_amd=Decimal("45000000"),
        term_max_months=180,
        fees=(("Application fee", Decimal("12000"), None),),
        salary_privilege=False,
        purposes=("Purchase a resale home",),
        down_payment_pct=Decimal("30"),
        property_market=PropertyMarket.SECONDARY,
        collateral_description="Purchased resale property",
    ),
    SnapshotSpec(
        case="eval_mortgage_online",
        offering_id=OfferingId.MORTGAGE_ONLINE,
        name="Online Mortgage",
        category=LoanCategory.MORTGAGE,
        details_kind="mortgage",
        url=MORTGAGE_URL,
        nominal_min_amd=Decimal("11.5"),
        nominal_max_amd=Decimal("13.5"),
        effective_min=Decimal("14.5"),
        amount_min_amd=Decimal("1000000"),
        amount_max_amd=Decimal("40000000"),
        term_max_months=180,
        # A percentage application fee cannot be ranked against fixed amounts.
        fees=(("Application fee", None, Decimal("0.5")),),
        salary_privilege=False,
        purposes=("Buy a home online without visiting a branch",),
        down_payment_pct=Decimal("25"),
        property_market=PropertyMarket.MIXED,
        collateral_description="Purchased property",
    ),
    SnapshotSpec(
        case="eval_mortgage_diaspora",
        offering_id=OfferingId.MORTGAGE_DIASPORA,
        name="Mortgage Loan for Diaspora",
        category=LoanCategory.MORTGAGE,
        details_kind="mortgage",
        url=MORTGAGE_URL,
        nominal_min_amd=Decimal("10.5"),
        nominal_max_amd=Decimal("12.5"),
        effective_min=Decimal("13.5"),
        amount_min_amd=Decimal("1000000"),
        amount_max_amd=Decimal("50000000"),
        term_max_months=180,
        fees=(("Application fee", Decimal("15000"), None),),
        salary_privilege=False,
        purposes=("Home purchase by a diaspora customer",),
        down_payment_pct=Decimal("30"),
        property_market=PropertyMarket.SECONDARY,
        collateral_description="Purchased property",
    ),
)

# The prior accepted mortgage version behind the question-25 change set.
PREVIOUS_MORTGAGE_SPEC = SnapshotSpec(
    case="eval_mortgage_primary_previous",
    offering_id=OfferingId.MORTGAGE_PRIMARY,
    name="Primary Market Mortgage",
    category=LoanCategory.MORTGAGE,
    details_kind="mortgage",
    url=MORTGAGE_URL,
    nominal_min_amd=Decimal("10"),
    nominal_max_amd=Decimal("12"),
    effective_min=Decimal("13"),
    amount_min_amd=Decimal("1000000"),
    amount_max_amd=Decimal("60000000"),
    term_max_months=240,
    fees=(("Application fee", Decimal("10000"), None),),
    salary_privilege=False,
    purposes=("Purchase a primary-market home",),
    down_payment_pct=Decimal("20"),
    property_market=PropertyMarket.PRIMARY,
    collateral_description="Purchased primary-market property",
    accepted_at=PREVIOUS_AS_OF,
    extra_evidence_salt=":previous",
)

MISSING_OFFERING = OfferingId.MORTGAGE_EXPRESS


def build_corpus() -> tuple[
    tuple[StructuredProjection, ...], tuple[StructuredProjection, ...]
]:
    """Return the active projections and the inactive historical projections."""
    projector = StructuredTariffProjector()
    active = tuple(
        projector.project(build_snapshot(spec), display_name=spec.name)
        for spec in CORPUS_SPECS
    )
    historical = (
        projector.project(
            build_snapshot(PREVIOUS_MORTGAGE_SPEC),
            display_name=PREVIOUS_MORTGAGE_SPEC.name,
        ),
    )
    return active, historical


def mortgage_change_set(
    previous: StructuredProjection, current: StructuredProjection
) -> SnapshotChangeSet:
    return SnapshotChangeSet(
        id=uuid5(NAMESPACE_DNS, "eval-change-set"),
        run_id=uuid5(NAMESPACE_DNS, "eval-change-run"),
        product=ProductType.MORTGAGE,
        offering_id=OfferingId.MORTGAGE_PRIMARY,
        previous_snapshot_id=previous.profile.snapshot_id,
        current_snapshot_id=current.profile.snapshot_id,
        changes=(
            SnapshotChange(
                field="interest_rate",
                previous="10",
                current="11",
                previous_display="10% minimum nominal rate",
                current_display="11% minimum nominal rate",
            ),
        ),
        created_at=CORPUS_AS_OF,
    )


class EvaluationRepository:
    """In-memory stand-in for the PostgreSQL structured read repository."""

    def __init__(self) -> None:
        active, historical = build_corpus()
        self.active = active
        self.historical = historical
        self.profiles: tuple[OfferingProfile, ...] = tuple(
            item.profile for item in active
        )
        self.active_facts: tuple[TariffFact, ...] = tuple(
            fact for item in active for fact in item.facts
        )
        self.all_facts: tuple[TariffFact, ...] = self.active_facts + tuple(
            fact for item in historical for fact in item.facts
        )
        self.units: tuple[RetrievalUnit, ...] = tuple(
            unit for item in active for unit in item.units
        )
        self.changes = (
            mortgage_change_set(
                historical[0],
                next(
                    item
                    for item in active
                    if item.profile.offering_id is OfferingId.MORTGAGE_PRIMARY
                ),
            ),
        )
        self.lexical_calls: list[str] = []
        self.vector_calls: list[str] = []

    async def active_profiles(self, *, bank, product, offering_ids):
        return tuple(
            item
            for item in self.profiles
            if item.product is product and item.offering_id in offering_ids
        )

    async def facts(self, *, snapshots, fields, include_inactive=False):
        source = self.all_facts if include_inactive else self.active_facts
        wanted = set(fields)
        return tuple(
            item
            for item in source
            if item.snapshot_id in set(snapshots) and item.field_path in wanted
        )

    async def lexical_units(self, *, bank, product, offering_ids, query, limit):
        self.lexical_calls.append(query)
        terms = {token for token in query.casefold().split() if len(token) > 3}
        ranked = [
            unit
            for unit in self.units
            if unit.offering_id in offering_ids
            and any(term in unit.content.casefold() for term in terms)
        ]
        return tuple(RankedUnit(unit, 0.5, "lexical") for unit in ranked[:limit])

    async def vector_units(
        self, *, bank, product, offering_ids, embedding, model_id, limit
    ):
        self.vector_calls.append(model_id)
        return ()

    async def accepted_changes(self, *, product, offering_ids, limit):
        return tuple(
            item
            for item in self.changes
            if item.product is product and item.offering_id in offering_ids
        )[:limit]


def fact_numbers(
    facts: tuple[TariffFact, ...], field_path: FieldPath
) -> dict[str, Decimal | None]:
    return {
        fact.offering_id.value: fact.number
        for fact in facts
        if fact.field_path is field_path
    }
