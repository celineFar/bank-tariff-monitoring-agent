"""Run the structured answer path on the local dev DB with no embedder (no Gemini)."""

import asyncio

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config.models import IntentResolutionSettings
from app.config.seed_catalog import load_seed_catalog
from app.domain.models import OfferingId, ProductType
from app.domain.structured_tariffs import FieldPath, QueryOperation, RankDirection
from app.repositories.structured_tariff_query import (
    PostgresStructuredTariffQueryRepository,
    lexical_search_terms,
)
from app.services.intent_resolution import RequestResolver
from app.services.structured_query_planning import issue_read_grant, _plan, QuerySelection
from app.services.structured_tariff_query import StructuredTariffQueryService

URL = "postgresql+asyncpg://tariff:tariff@localhost:5434/tariff_monitor"


async def ask(resolver, service, q):
    turn = await resolver.resolve_turn(q)
    r = turn.resolution
    plan = issue_read_grant(q, r, history=False, session_id="s", turn_id="t")
    res = await service.answer(plan, q)
    print(f"\nQ: {q!r}\n  plan op={plan.operation.value} fields={[f.value for f in plan.fields]} cond={plan.conditions}")
    print(f"  status={res.status.value} facts={len(res.facts)} units={len(res.retrieval_units)} reason={res.reason}")
    for u in res.retrieval_units:
        print(f"    unit {u.kind.value} {u.field_paths[0].value if u.field_paths else ''}")
    print(f"  lexical tsquery: {lexical_search_terms(q)}")


class RankRepo:
    """Real overdraft facts, plus the same facts relabelled as credit_line."""

    def __init__(self, real, profiles, facts):
        self.real, self.profiles, self._facts = real, profiles, facts

    async def active_profiles(self, **_):
        return self.profiles

    async def facts(self, **_):
        return self._facts


async def main():
    engine = create_async_engine(URL)
    repo = PostgresStructuredTariffQueryRepository(async_sessionmaker(engine, expire_on_commit=False))
    service = StructuredTariffQueryService(repo, unit_embedder=None)
    resolver = RequestResolver(load_seed_catalog(), IntentResolutionSettings())
    for q in [
        "What is the overdraft interest rate?",
        "What is the overdraft interest rate in AMD?",
        "What is the overdraft repayment term?",
        "What is the overdraft repayment term in AMD?",
        "What are the overdraft fees?",
        "What is the overdraft amount?",
    ]:
        await ask(resolver, service, q)

    # FAMILY_RANK over two offerings whose facts are identical.
    profiles = await repo.active_profiles(
        bank="ameria", product=ProductType.CONSUMER_LOAN, offering_ids=(OfferingId.OVERDRAFT,)
    )
    facts = await repo.facts(
        snapshots=[profiles[0].snapshot_id], fields=(FieldPath.NOMINAL_RATE_MINIMUM,)
    )
    twin = tuple(f.model_copy(update={"offering_id": OfferingId.CREDIT_LINE, "fact_id": "c" * 64}) for f in facts)
    p2 = profiles[0].model_copy(update={"offering_id": OfferingId.CREDIT_LINE})
    rank_service = StructuredTariffQueryService(RankRepo(repo, (profiles[0], p2), facts + twin))
    q = "Which consumer loan has the lowest rate?"
    plan = _plan(
        q,
        QuerySelection(
            product=ProductType.CONSUMER_LOAN,
            offering_ids=(OfferingId.OVERDRAFT, OfferingId.CREDIT_LINE),
            operation=QueryOperation.FAMILY_RANK,
            fields=(FieldPath.NOMINAL_RATE_MINIMUM,),
            conditions={},
            rank_direction=RankDirection.LOWEST,
        ),
        session_id="s",
        turn_id="t",
    )
    res = await rank_service.answer(plan, q)
    print(f"\nRANK over identical offerings: status={res.status.value} reason={res.reason}")
    await engine.dispose()


asyncio.run(main())
