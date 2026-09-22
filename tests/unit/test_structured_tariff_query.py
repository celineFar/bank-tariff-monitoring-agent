import hashlib
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from app.domain.models import OfferingId, ProductType
from app.domain.semantic_extraction import ExtractionStatus
from app.domain.structured_tariffs import (
    FieldPath,
    QueryOperation,
    QueryStatus,
    RankDirection,
    ResolutionPlan,
)
from app.repositories.structured_tariff_query import RankedUnit
from app.services.structured_projection import StructuredTariffProjector
from app.services.structured_tariff_query import StructuredTariffQueryService
from tests.fixtures.structured_tariffs import accepted_snapshot

NOW = datetime(2026, 9, 22, tzinfo=UTC)
QUESTION = "What is the lowest nominal interest rate?"


def _plan(**changes):
    values = {
        "session_id": "session-1",
        "turn_id": "turn-1",
        "question_sha256": hashlib.sha256(QUESTION.encode()).hexdigest(),
        "issued_at": NOW - timedelta(minutes=1),
        "expires_at": NOW + timedelta(minutes=5),
        "product": ProductType.CONSUMER_LOAN,
        "offering_ids": (OfferingId.CONSUMER_STANDARD,),
        "operation": QueryOperation.SINGLE,
        "fields": (FieldPath.NOMINAL_RATE_MINIMUM,),
        "conditions": {"currency": "AMD"},
    }
    values.update(changes)
    return ResolutionPlan(**values)


class Repository:
    def __init__(self):
        first = StructuredTariffProjector().project(
            accepted_snapshot("consumer"), display_name="Synthetic consumer loan"
        )
        second_id = uuid4()
        self.profiles = (
            first.profile,
            first.profile.model_copy(
                update={"snapshot_id": second_id, "offering_id": OfferingId.OVERDRAFT}
            ),
        )
        self.facts_ = (
            *first.facts,
            *(
                fact.model_copy(
                    update={
                        "snapshot_id": second_id,
                        "offering_id": OfferingId.OVERDRAFT,
                        "number": Decimal("10")
                        if fact.field_path is FieldPath.NOMINAL_RATE_MINIMUM
                        else fact.number,
                    }
                )
                for fact in first.facts
            ),
        )
        self.units = first.units

    async def active_profiles(self, *, bank, product, offering_ids):
        return tuple(item for item in self.profiles if item.offering_id in offering_ids)

    async def facts(self, *, snapshots, fields, include_inactive=False):
        return tuple(
            item
            for item in self.facts_
            if item.snapshot_id in snapshots and item.field_path in fields
        )

    async def lexical_units(self, *, bank, product, offering_ids, query, limit):
        return tuple(
            RankedUnit(item, 0.5, "lexical")
            for item in self.units
            if item.offering_id in offering_ids
            and FieldPath.NOMINAL_RATE_MINIMUM in item.field_paths
        )[:limit]

    async def accepted_changes(self, *, product, offering_ids, limit):
        return ()


@pytest.mark.asyncio
async def test_single_answer_keeps_conditioned_fact_and_evidence_unit() -> None:
    result = await StructuredTariffQueryService(Repository()).answer(
        _plan(), QUESTION, now=NOW
    )
    assert result.status is QueryStatus.ANSWERED
    assert len(result.facts) == 1
    assert result.facts[0].currency == "AMD"
    assert result.facts[0].evidence
    assert result.retrieval_units
    assert all(result.retrieval_units[0].evidence_ids)


@pytest.mark.asyncio
async def test_rank_requires_common_currency_and_explicit_direction() -> None:
    repository = Repository()
    service = StructuredTariffQueryService(repository)
    ids = (OfferingId.CONSUMER_STANDARD, OfferingId.OVERDRAFT)
    plan = _plan(
        operation=QueryOperation.FAMILY_RANK,
        rank_direction=RankDirection.LOWEST,
        offering_ids=ids,
        conditions={},
    )
    incomparable = await service.answer(plan, QUESTION, now=NOW)
    assert incomparable.status is QueryStatus.INCOMPARABLE
    result = await service.answer(
        plan.model_copy(update={"conditions": {"currency": "AMD"}}),
        QUESTION,
        now=NOW,
    )
    assert result.status is QueryStatus.ANSWERED
    assert result.metadata["winner"] == OfferingId.OVERDRAFT.value
    highest = await service.answer(
        plan.model_copy(
            update={
                "conditions": {"currency": "AMD"},
                "rank_direction": RankDirection.HIGHEST,
            }
        ),
        QUESTION,
        now=NOW,
    )
    assert highest.metadata["winner"] == OfferingId.CONSUMER_STANDARD.value


@pytest.mark.asyncio
async def test_comparison_preserves_both_offerings() -> None:
    result = await StructuredTariffQueryService(Repository()).answer(
        _plan(
            operation=QueryOperation.COMPARE,
            offering_ids=(OfferingId.CONSUMER_STANDARD, OfferingId.OVERDRAFT),
        ),
        QUESTION,
        now=NOW,
    )
    assert result.status is QueryStatus.ANSWERED
    assert {fact.offering_id for fact in result.facts} == {
        OfferingId.CONSUMER_STANDARD,
        OfferingId.OVERDRAFT,
    }
    assert len(result.comparison_rows) == 1
    assert result.comparison_rows[0].comparable is True


@pytest.mark.asyncio
async def test_missing_or_unsupported_fact_abstains() -> None:
    repository = Repository()
    repository.facts_ = tuple(
        item.model_copy(
            update={
                "status": ExtractionStatus.NOT_STATED,
                "value": None,
                "evidence": (),
            }
        )
        for item in repository.facts_
    )
    result = await StructuredTariffQueryService(repository).answer(
        _plan(), QUESTION, now=NOW
    )
    assert result.status is QueryStatus.INSUFFICIENT_EVIDENCE


@pytest.mark.asyncio
async def test_question_hash_and_expiry_are_enforced_before_repository_access() -> None:
    service = StructuredTariffQueryService(Repository())
    with pytest.raises(ValueError, match="question differs"):
        await service.answer(_plan(), "changed question", now=NOW)
    with pytest.raises(ValueError, match="expired"):
        await service.answer(_plan(), QUESTION, now=NOW + timedelta(minutes=6))


@pytest.mark.asyncio
async def test_history_maps_extraction_field_to_canonical_path() -> None:
    from app.domain.monitoring import SnapshotChange, SnapshotChangeSet

    class HistoryRepository(Repository):
        async def facts(self, *, snapshots, fields, include_inactive=False):
            original = await super().facts(
                snapshots=snapshots, fields=fields, include_inactive=include_inactive
            )
            return tuple(
                fact.model_copy(update={"offering_id": OfferingId.CONSUMER_STANDARD})
                for fact in original
            )

        async def accepted_changes(self, *, product, offering_ids, limit):
            return (
                SnapshotChangeSet(
                    id=uuid4(),
                    run_id=uuid4(),
                    product=product,
                    offering_id=OfferingId.CONSUMER_STANDARD,
                    previous_snapshot_id=self.profiles[0].snapshot_id,
                    current_snapshot_id=self.profiles[1].snapshot_id,
                    changes=(
                        SnapshotChange(
                            field="interest_rate",
                            previous="12",
                            current="11",
                        ),
                    ),
                    created_at=NOW,
                ),
            )

    result = await StructuredTariffQueryService(HistoryRepository()).answer(
        _plan(operation=QueryOperation.HISTORY), QUESTION, now=NOW
    )
    assert result.status is QueryStatus.ANSWERED
    assert result.metadata["changes"][0]["changes"][0]["field"] == "interest_rate"
    assert result.metadata["changes"][0]["changes"][0]["previous_evidence"]
    assert result.metadata["changes"][0]["changes"][0]["current_evidence"]


@pytest.mark.asyncio
async def test_fee_ranking_abstains_across_different_scopes() -> None:
    repository = Repository()
    repository.facts_ = tuple(
        fact.model_copy(update={"fee_scope": "general"})
        if fact.offering_id is OfferingId.OVERDRAFT
        and fact.field_path is FieldPath.FEE_APPLICATION
        else fact
        for fact in repository.facts_
    )
    result = await StructuredTariffQueryService(repository).answer(
        _plan(
            operation=QueryOperation.FAMILY_RANK,
            rank_direction=RankDirection.HIGHEST,
            offering_ids=(OfferingId.CONSUMER_STANDARD, OfferingId.OVERDRAFT),
            fields=(FieldPath.FEE_APPLICATION,),
            conditions={},
        ),
        QUESTION,
        now=NOW,
    )
    assert result.status is QueryStatus.INCOMPARABLE


@pytest.mark.asyncio
async def test_salary_privilege_is_retrievable_as_explicit_fact() -> None:
    result = await StructuredTariffQueryService(Repository()).answer(
        _plan(fields=(FieldPath.SALARY_PRIVILEGE,), conditions={}),
        QUESTION,
        now=NOW,
    )
    assert result.status is QueryStatus.ANSWERED
    assert len(result.facts) == 1
    assert result.facts[0].field_path is FieldPath.SALARY_PRIVILEGE
    assert result.facts[0].evidence


@pytest.mark.asyncio
async def test_lexical_vector_fusion_keeps_only_requested_evidence() -> None:
    class HybridRepository(Repository):
        async def vector_units(
            self, *, bank, product, offering_ids, embedding, model_id, limit
        ):
            assert model_id == "test-model"
            assert len(embedding) == 768
            return (
                RankedUnit(
                    next(
                        unit
                        for unit in self.units
                        if FieldPath.NOMINAL_RATE_MINIMUM in unit.field_paths
                    ),
                    0.8,
                    "vector",
                ),
            )

    class Embedder:
        model_name = "test-model"
        ensure_calls = 0

        async def ensure(self, **kwargs):
            self.ensure_calls += 1
            return 1

        async def embed_query(self, question):
            return [0.1] * 768

    embedder = Embedder()
    result = await StructuredTariffQueryService(HybridRepository(), embedder).answer(
        _plan(), QUESTION, now=NOW
    )
    assert result.status is QueryStatus.ANSWERED
    assert result.metadata["ranking_version"] == "rrf-v1-k60-lex1-vector0.7"
    assert embedder.ensure_calls == 1
    assert all(
        set(unit.fact_ids) <= {fact.fact_id for fact in result.facts}
        for unit in result.retrieval_units
    )


@pytest.mark.asyncio
async def test_rate_basis_mismatch_abstains_from_family_ranking() -> None:
    from app.domain.semantic_extraction import RateBasis

    repository = Repository()
    repository.facts_ = tuple(
        fact.model_copy(update={"rate_basis": RateBasis.MONTHLY})
        if fact.offering_id is OfferingId.OVERDRAFT
        and fact.field_path is FieldPath.NOMINAL_RATE_MINIMUM
        else fact
        for fact in repository.facts_
    )
    result = await StructuredTariffQueryService(repository).answer(
        _plan(
            operation=QueryOperation.FAMILY_RANK,
            rank_direction=RankDirection.LOWEST,
            offering_ids=(OfferingId.CONSUMER_STANDARD, OfferingId.OVERDRAFT),
        ),
        QUESTION,
        now=NOW,
    )
    assert result.status is QueryStatus.INCOMPARABLE


@pytest.mark.asyncio
async def test_rank_refuses_unmatched_promotional_conditions() -> None:
    repository = Repository()
    repository.facts_ = tuple(
        fact.model_copy(
            update={
                "conditions": ({"dimension": "salary", "value": "payroll customer"},)
            }
        )
        if fact.offering_id is OfferingId.OVERDRAFT
        and fact.field_path is FieldPath.NOMINAL_RATE_MINIMUM
        else fact
        for fact in repository.facts_
    )
    result = await StructuredTariffQueryService(repository).answer(
        _plan(
            operation=QueryOperation.FAMILY_RANK,
            rank_direction=RankDirection.LOWEST,
            offering_ids=(OfferingId.CONSUMER_STANDARD, OfferingId.OVERDRAFT),
        ),
        QUESTION,
        now=NOW,
    )
    assert result.status is QueryStatus.INCOMPARABLE


@pytest.mark.asyncio
async def test_formula_comparison_is_explicitly_incomparable() -> None:
    repository = Repository()
    formula = next(
        fact
        for fact in repository.facts_
        if fact.offering_id is OfferingId.CONSUMER_STANDARD
        and fact.field_path is FieldPath.NOMINAL_RATE_MINIMUM
    )
    repository.facts_ = tuple(
        formula.model_copy(
            update={
                "offering_id": offering,
                "snapshot_id": snapshot_id,
                "field_path": FieldPath.CREDIT_LIMIT_FORMULA,
                "number": None,
                "unit": "formula",
                "value": "salary x 5",
            }
        )
        for offering, snapshot_id in (
            (OfferingId.CONSUMER_STANDARD, repository.profiles[0].snapshot_id),
            (OfferingId.OVERDRAFT, repository.profiles[1].snapshot_id),
        )
    )
    result = await StructuredTariffQueryService(repository).answer(
        _plan(
            operation=QueryOperation.COMPARE,
            offering_ids=(OfferingId.CONSUMER_STANDARD, OfferingId.OVERDRAFT),
            fields=(FieldPath.CREDIT_LIMIT_FORMULA,),
            conditions={},
        ),
        QUESTION,
        now=NOW,
    )
    assert result.status is QueryStatus.INCOMPARABLE
    assert result.comparison_rows[0].comparable is False
