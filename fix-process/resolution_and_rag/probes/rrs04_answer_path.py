"""RRS04: the structured answer path on the dev database (read-only, no Gemini).

`tariff_monitor` on port 5434 has only the Overdraft published. Plans are typed
(the shape the interpreter would propose), so no interpreter call is made; the
field finder runs lexical-only (no embedder), so no embedding call either.
"""

from __future__ import annotations

import asyncio

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.domain.models import OfferingId, ProductType
from app.domain.query_shape import Currency, QueryShape
from app.domain.structured_tariffs import FieldPath, QueryOperation, RankDirection
from app.repositories.structured_tariff_query import (
    PostgresStructuredTariffQueryRepository,
)
from app.services.structured_query_planning import issue_typed_plan
from app.services.structured_tariff_query import StructuredTariffQueryService

URL = "postgresql+asyncpg://tariff:tariff@localhost:5434/tariff_monitor"
C = ProductType.CONSUMER_LOAN
OVERDRAFT = (OfferingId.OVERDRAFT,)

CASES = (
    (
        "repayment term in AMD keeps currency-less facts (RR24)",
        "What is the overdraft repayment term in AMD?",
        OVERDRAFT,
        QueryShape(
            operation=QueryOperation.SINGLE,
            fields=(FieldPath.TERM_MINIMUM_MONTHS, FieldPath.TERM_MAXIMUM_MONTHS,
                    FieldPath.REPAYMENT_METHOD),
            currency=Currency.AMD,
        ),
    ),
    (
        "field finder: documents (D4)",
        "What documents do I need for the overdraft?",
        OVERDRAFT,
        QueryShape(operation=QueryOperation.SINGLE),
    ),
    (
        "field finder: fees, plural (D11)",
        "What are the overdraft fees?",
        OVERDRAFT,
        QueryShape(operation=QueryOperation.SINGLE),
    ),
    (
        "field finder: Armenian inflection (D11)",
        "Օվերդրաֆտի տոկոսադրույքները",
        OVERDRAFT,
        QueryShape(operation=QueryOperation.SINGLE),
    ),
    (
        "overview of two named offerings (RR18)",
        "What are the overdraft fees and the credit line fees?",
        (OfferingId.OVERDRAFT, OfferingId.CREDIT_LINE),
        QueryShape(operation=QueryOperation.OVERVIEW, fields=(FieldPath.FEE_OTHER,)),
    ),
    (
        "rank over the family (only one offering published)",
        "Which consumer loan has the lowest rate?",
        (),
        QueryShape(
            operation=QueryOperation.FAMILY_RANK,
            rank_field=FieldPath.NOMINAL_RATE_MINIMUM,
            rank_direction=RankDirection.LOWEST,
        ),
    ),
    (
        "history",
        "What changed in the overdraft?",
        OVERDRAFT,
        QueryShape(operation=QueryOperation.HISTORY),
    ),
)


async def main() -> None:
    engine = create_async_engine(URL)
    repository = PostgresStructuredTariffQueryRepository(
        async_sessionmaker(engine, expire_on_commit=False)
    )
    service = StructuredTariffQueryService(repository, unit_embedder=None)
    for title, question, offerings, shape in CASES:
        plan = issue_typed_plan(
            question, product=C, offering_ids=offerings, shape=shape,
            session_id="rrs04", turn_id="t",
        )
        result = await service.answer(plan, plan.question)
        fields = sorted({fact.field_path.value for fact in result.facts})
        print(f"\n{title}\n  {question!r} -> op={plan.operation.value} status={result.status.value}")
        print(f"  fields_source={result.metadata.get('fields_source')} fields={result.metadata.get('fields')}")
        print(f"  facts={len(result.facts)} fact fields={fields} reason={result.reason}")
        if "offerings_without_facts" in result.metadata:
            print(f"  offerings without facts: {result.metadata['offerings_without_facts']}")
    await engine.dispose()


asyncio.run(main())
