from __future__ import annotations

import httpx
import pytest
from fastapi import FastAPI

from app.api.routes import router
from app.config.models import IntentResolutionSettings
from app.config.seed_catalog import load_seed_catalog
from app.domain.models import OfferingId
from app.domain.structured_tariffs import QueryStatus, TariffQueryResult
from app.services.intent_resolution import RequestResolver


class QueryService:
    def __init__(self) -> None:
        self.calls = []

    async def answer(self, plan, question):
        self.calls.append((plan, question))
        return TariffQueryResult(
            status=QueryStatus.INSUFFICIENT_EVIDENCE,
            operation=plan.operation,
            product=plan.product,
            offering_ids=plan.offering_ids,
            reason="no accepted evidence-backed fact",
        )


class NoAcquisition:
    async def submit(self, command):
        raise AssertionError("ordinary questions must not start acquisition")


@pytest.mark.asyncio
async def test_structured_route_uses_same_scoped_service_without_acquisition() -> None:
    app = FastAPI()
    app.include_router(router)
    query_service = QueryService()
    app.state.structured_query_service = query_service
    app.state.request_resolver = RequestResolver(
        load_seed_catalog(), IntentResolutionSettings()
    )
    app.state.run_service = NoAcquisition()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/v1/tariffs/query",
            json={"query": "What is the nominal interest rate for Overdraft?"},
        )
    assert response.status_code == 200
    assert response.json()["status"] == "insufficient_evidence"
    assert query_service.calls[0][0].offering_ids == (OfferingId.OVERDRAFT,)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        widened = await client.post(
            "/api/v1/tariffs/query",
            json={
                "query": "What is the nominal interest rate for Overdraft?",
                "offering_ids": ["mortgage_primary"],
            },
        )
    assert widened.status_code == 422
    assert len(query_service.calls) == 1


@pytest.mark.asyncio
async def test_structured_route_returns_controlled_unresolved_scope() -> None:
    app = FastAPI()
    app.include_router(router)
    app.state.structured_query_service = QueryService()
    app.state.request_resolver = RequestResolver(
        load_seed_catalog(), IntentResolutionSettings()
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/v1/tariffs/query", json={"query": "current mortgage rate"}
        )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "query.unresolved_scope"
