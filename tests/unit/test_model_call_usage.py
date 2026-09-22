from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.services.model_call_usage import (
    ModelCallUsage,
    estimate_cost,
    response_tokens,
)


def _usage(**changes) -> ModelCallUsage:
    values = {
        "call_id": "call-1",
        "attempt": 1,
        "called_at": datetime(2026, 9, 22, tzinfo=UTC),
        "stage": "rag.answer",
        "operation": "generate_content",
        "model_id": "gemini-3.7-flash",
        "outcome": "succeeded",
        "latency_ms": 42,
        "input_tokens": 1000,
        "output_tokens": 200,
    }
    values.update(changes)
    return ModelCallUsage(**values)


def test_generation_cost_uses_dated_paid_tier_rates() -> None:
    estimate = estimate_cost(_usage())
    assert estimate.cost == Decimal("0.0015")
    assert estimate.unknown_reason is None
    assert "2026-01-01" in estimate.price_version


def test_embedding_cost_uses_input_tokens_only() -> None:
    estimate = estimate_cost(
        _usage(
            model_id="gemini-embedding-001",
            operation="embed_content",
            output_tokens=None,
        )
    )
    assert estimate.cost == Decimal("0.00015")


def test_missing_usage_and_unknown_model_remain_unknown() -> None:
    assert (
        estimate_cost(_usage(input_tokens=None)).unknown_reason == "missing_input_usage"
    )
    assert (
        estimate_cost(_usage(model_id="unknown-model")).unknown_reason
        == "unpriced_model_or_date"
    )
    assert (
        estimate_cost(_usage(output_tokens=None)).unknown_reason
        == "missing_output_usage"
    )


def test_local_cache_hit_has_no_api_cost() -> None:
    estimate = estimate_cost(
        _usage(outcome="cache_hit", input_tokens=None, output_tokens=None)
    )
    assert estimate.cost == 0
    assert estimate.price_version == "local-cache-v1"


def test_response_usage_includes_thinking_tokens() -> None:
    class Usage:
        prompt_token_count = 10
        candidates_token_count = 5
        thoughts_token_count = 3

    class Response:
        usage_metadata = Usage()

    assert response_tokens(Response()) == (10, 8)
    assert response_tokens(object()) == (None, None)


@pytest.mark.asyncio
async def test_adk_callback_logs_usage_without_request_or_response_text() -> None:
    from types import SimpleNamespace

    from app.services.model_call_usage import adk_usage_callbacks

    class Repository:
        def __init__(self):
            self.calls = []

        async def record(self, usage):
            self.calls.append(usage)

    repository = Repository()
    callbacks = adk_usage_callbacks(
        repository, stage="semantic.extraction", model_id="gemini-3.7-flash"
    )
    context = SimpleNamespace(
        invocation_id="invocation-1",
        agent_name="extractor",
        state={},
    )
    request = SimpleNamespace(secret_prompt="sensitive tariff content")
    response = SimpleNamespace(
        secret_response="sensitive extracted text",
        usage_metadata=SimpleNamespace(
            prompt_token_count=10,
            candidates_token_count=4,
            thoughts_token_count=2,
        ),
    )
    await callbacks["before_model_callback"](context, request)
    await callbacks["after_model_callback"](context, response)
    assert len(repository.calls) == 1
    usage = repository.calls[0]
    assert usage.input_tokens == 10
    assert usage.output_tokens == 6
    assert usage.outcome == "succeeded"
    assert "sensitive" not in repr(usage)


@pytest.mark.asyncio
async def test_monitored_provider_failure_is_logged_and_re_raised() -> None:
    from app.services.model_call_usage import observe_model_call

    class Repository:
        def __init__(self):
            self.calls = []

        async def record(self, usage):
            self.calls.append(usage)

    async def failed():
        raise TimeoutError("sensitive payload")

    repository = Repository()
    with pytest.raises(TimeoutError):
        await observe_model_call(
            failed,
            repository=repository,
            stage="rag.answer_generation",
            operation="generate_content",
            model_id="gemini-3.7-flash",
        )
    assert repository.calls[0].outcome == "failed"
    assert repository.calls[0].error_class == "TimeoutError"
    assert "sensitive" not in repr(repository.calls[0])


@pytest.mark.asyncio
async def test_budget_status_preserves_unknown_cost_risk() -> None:
    from app.services.model_call_usage import PostgresModelCallUsageRepository

    class Repository(PostgresModelCallUsageRepository):
        async def totals(self, *, from_time, to_time):
            return ({"known_cost_usd": Decimal("0.20"), "unknown_calls": 1},)

    repository = Repository(None)
    now = datetime(2026, 9, 22, tzinfo=UTC)
    status = await repository.budget_status(
        from_time=now, to_time=now, threshold_usd=Decimal("1")
    )
    assert status["status"] == "incomplete"
    assert status["known_cost_usd"] == Decimal("0.20")
    reached = await repository.budget_status(
        from_time=now, to_time=now, threshold_usd=Decimal("0.10")
    )
    assert reached["status"] == "threshold_reached"
