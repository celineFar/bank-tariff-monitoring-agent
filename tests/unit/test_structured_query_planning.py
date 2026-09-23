from __future__ import annotations

import pytest

from app.config.models import IntentResolutionSettings
from app.config.seed_catalog import load_seed_catalog
from app.domain.models import OfferingId, ProductType
from app.domain.structured_tariffs import FieldPath, QueryOperation, RankDirection
from app.services.intent_resolution import RequestResolver
from app.services.structured_query_planning import select_tariff_query


@pytest.mark.asyncio
async def test_bilingual_comparison_selects_bounded_fields_and_same_family() -> None:
    resolver = RequestResolver(load_seed_catalog(), IntentResolutionSettings())
    for question in (
        "How does Overdraft differ from the standard Consumer Loan in amount and fees?",
        "Համեմատիր Օվերդրաֆտ և Սպառողական վարկ տոկոսադրույքը",
    ):
        resolution = (await resolver.resolve_turn(question)).resolution
        selection = select_tariff_query(question, resolution)
        assert selection.operation is QueryOperation.COMPARE
        assert set(selection.offering_ids) == {
            OfferingId.OVERDRAFT,
            OfferingId.CONSUMER_STANDARD,
        }
        assert selection.product is ProductType.CONSUMER_LOAN
        assert 0 < len(selection.fields) <= 20


@pytest.mark.asyncio
async def test_family_rank_has_explicit_direction_and_single_canonical_path() -> None:
    question = "Which consumer loan offering has the lowest nominal interest rate?"
    resolution = (
        await RequestResolver(
            load_seed_catalog(), IntentResolutionSettings()
        ).resolve_turn(question)
    ).resolution
    selection = select_tariff_query(question, resolution)
    assert selection.operation is QueryOperation.FAMILY_RANK
    assert selection.rank_direction is RankDirection.LOWEST
    assert selection.fields == (FieldPath.NOMINAL_RATE_MINIMUM,)


@pytest.mark.asyncio
async def test_single_query_keeps_resolved_product_and_currency() -> None:
    question = "What is the AMD minimum amount for the Overdraft?"
    resolution = (
        await RequestResolver(
            load_seed_catalog(), IntentResolutionSettings()
        ).resolve_turn(question)
    ).resolution
    selection = select_tariff_query(question, resolution)
    assert selection.operation is QueryOperation.SINGLE
    assert selection.offering_ids == (OfferingId.OVERDRAFT,)
    assert selection.conditions == {"currency": "AMD"}
    assert FieldPath.AMOUNT_MINIMUM in selection.fields
