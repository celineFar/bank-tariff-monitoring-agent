"""Redacted, versioned usage and estimated paid-tier cost for model calls."""

from __future__ import annotations

import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, TypeVar
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.services.model_pricing import get_model_price


@dataclass(frozen=True)
class ModelCallUsage:
    call_id: str
    attempt: int
    called_at: datetime
    stage: str
    operation: str
    model_id: str
    outcome: str
    latency_ms: int
    run_id: UUID | None = None
    offering_id: str | None = None
    request_id: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    input_count: int | None = None
    error_class: str | None = None


@dataclass(frozen=True)
class CostEstimate:
    price_version: str | None
    input_rate: Decimal | None
    output_rate: Decimal | None
    cost: Decimal | None
    unknown_reason: str | None


def estimate_cost(usage: ModelCallUsage) -> CostEstimate:
    """Use observed tokens only; never present absent usage as a zero-dollar call."""
    if usage.outcome == "cache_hit":
        return CostEstimate("local-cache-v1", Decimal(0), Decimal(0), Decimal(0), None)
    try:
        price = get_model_price(usage.model_id, on_date=usage.called_at.date())
    except ValueError:
        return CostEstimate(None, None, None, None, "unpriced_model_or_date")
    input_rate = Decimal(str(price.input_per_million_tokens_usd))
    output_rate = Decimal(str(price.output_per_million_tokens_usd))
    version = f"{price.basis}:{price.model}:{price.starts_on.isoformat()}"
    if usage.input_tokens is None:
        return CostEstimate(
            version, input_rate, output_rate, None, "missing_input_usage"
        )
    if output_rate and usage.output_tokens is None:
        return CostEstimate(
            version, input_rate, output_rate, None, "missing_output_usage"
        )
    cost = (
        Decimal(usage.input_tokens) * input_rate
        + Decimal(usage.output_tokens or 0) * output_rate
    ) / Decimal(1_000_000)
    return CostEstimate(version, input_rate, output_rate, cost, None)


def response_tokens(response: Any) -> tuple[int | None, int | None]:
    """Read SDK usage metadata without touching prompt or response content."""
    metadata = getattr(response, "usage_metadata", None)
    if metadata is None:
        return None, None
    input_tokens = getattr(metadata, "prompt_token_count", None)
    candidate_tokens = getattr(metadata, "candidates_token_count", None)
    thoughts_tokens = getattr(metadata, "thoughts_token_count", None)
    output_tokens = (
        (candidate_tokens or 0) + (thoughts_tokens or 0)
        if candidate_tokens is not None or thoughts_tokens is not None
        else None
    )
    return input_tokens, output_tokens


class PostgresModelCallUsageRepository:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def record(self, usage: ModelCallUsage) -> None:
        estimate = estimate_cost(usage)
        async with self._sessions() as session, session.begin():
            await session.execute(
                text(
                    """INSERT INTO model_call_usage (
                        id, call_id, attempt, called_at, stage, operation,
                        model_id, billing_platform, run_id, offering_id,
                        request_id, input_tokens, output_tokens, input_count,
                        latency_ms, outcome, error_class, price_version,
                        input_rate_usd_per_million, output_rate_usd_per_million,
                        estimated_cost_usd, unknown_cost_reason
                    ) VALUES (
                        :id, :call_id, :attempt, :called_at, :stage, :operation,
                        :model_id, 'gemini_developer_api', :run_id, :offering_id,
                        :request_id, :input_tokens, :output_tokens, :input_count,
                        :latency_ms, :outcome, :error_class, :price_version,
                        :input_rate, :output_rate, :cost, :unknown_reason
                    ) ON CONFLICT (call_id, attempt) DO NOTHING"""
                ),
                {
                    "id": uuid4(),
                    **usage.__dict__,
                    "price_version": estimate.price_version,
                    "input_rate": estimate.input_rate,
                    "output_rate": estimate.output_rate,
                    "cost": estimate.cost,
                    "unknown_reason": estimate.unknown_reason,
                },
            )

    async def totals(
        self, *, from_time: datetime, to_time: datetime
    ) -> tuple[dict[str, object], ...]:
        async with self._sessions() as session:
            rows = (
                (
                    await session.execute(
                        text(
                            """SELECT date_trunc('day', called_at) AS day, stage,
                            model_id, count(*) AS calls,
                            count(*) FILTER (WHERE outcome = 'failed') AS failures,
                            count(*) FILTER (WHERE outcome = 'cache_hit') AS cache_hits,
                            sum(input_tokens) AS input_tokens,
                            sum(output_tokens) AS output_tokens,
                            sum(estimated_cost_usd) AS known_cost_usd,
                            count(*) FILTER (WHERE estimated_cost_usd IS NULL) AS unknown_calls
                        FROM model_call_usage
                        WHERE called_at >= :from_time AND called_at < :to_time
                        GROUP BY 1, 2, 3 ORDER BY 1, 2, 3"""
                        ),
                        {"from_time": from_time, "to_time": to_time},
                    )
                )
                .mappings()
                .all()
            )
        return tuple(dict(row) for row in rows)

    async def budget_status(
        self,
        *,
        from_time: datetime,
        to_time: datetime,
        threshold_usd: Decimal,
    ) -> dict[str, object]:
        if threshold_usd <= 0:
            raise ValueError("budget threshold must be positive")
        rows = await self.totals(from_time=from_time, to_time=to_time)
        known = sum(
            (row["known_cost_usd"] or Decimal(0) for row in rows),
            Decimal(0),
        )
        unknown = sum(int(row["unknown_calls"]) for row in rows)
        return {
            "known_cost_usd": known,
            "threshold_usd": threshold_usd,
            "unknown_calls": unknown,
            "status": (
                "threshold_reached"
                if known >= threshold_usd
                else "incomplete"
                if unknown
                else "within_budget"
            ),
        }


def new_usage(
    *,
    stage: str,
    operation: str,
    model_id: str,
    outcome: str,
    latency_ms: int,
    call_id: str | None = None,
    attempt: int = 1,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    input_count: int | None = None,
    run_id: UUID | None = None,
    offering_id: str | None = None,
    request_id: str | None = None,
    error_class: str | None = None,
) -> ModelCallUsage:
    return ModelCallUsage(
        call_id=call_id or str(uuid4()),
        attempt=attempt,
        called_at=datetime.now(UTC),
        stage=stage,
        operation=operation,
        model_id=model_id,
        outcome=outcome,
        latency_ms=latency_ms,
        run_id=run_id,
        offering_id=offering_id,
        request_id=request_id,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        input_count=input_count,
        error_class=error_class,
    )


_Result = TypeVar("_Result")
_logger = logging.getLogger(__name__)


async def observe_model_call(
    call: Callable[[], Awaitable[_Result]],
    *,
    repository: PostgresModelCallUsageRepository | None,
    stage: str,
    operation: str,
    model_id: str,
    call_id: str | None = None,
    attempt: int = 1,
    input_count: int | None = None,
    run_id: UUID | None = None,
    offering_id: str | None = None,
    request_id: str | None = None,
) -> _Result:
    """Record one actual provider attempt, including failures, without payloads."""
    if repository is None:
        return await call()
    start = time.perf_counter()
    response: _Result | None = None
    error: Exception | None = None
    try:
        response = await call()
        return response
    except Exception as exc:
        error = exc
        raise
    finally:
        input_tokens, output_tokens = response_tokens(response)
        usage = new_usage(
            stage=stage,
            operation=operation,
            model_id=model_id,
            outcome="failed" if error else "succeeded",
            latency_ms=max(0, round((time.perf_counter() - start) * 1000)),
            call_id=call_id,
            attempt=attempt,
            input_count=input_count,
            run_id=run_id,
            offering_id=offering_id,
            request_id=request_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            error_class=type(error).__name__ if error else None,
        )
        try:
            await repository.record(usage)
        except Exception:
            _logger.exception("model usage ledger write failed stage=%s", stage)


def adk_usage_callbacks(
    repository: PostgresModelCallUsageRepository | None,
    *,
    stage: str,
    model_id: str,
) -> dict[str, object]:
    """Observe each ADK model response/error without reading request content."""
    if repository is None:
        return {}
    starts: dict[str, list[tuple[float, str]]] = {}

    async def before_model(callback_context, llm_request):
        del llm_request
        key = callback_context.invocation_id
        call_id = str(uuid4())
        starts.setdefault(key, []).append((time.perf_counter(), call_id))
        return None

    async def _record(callback_context, response, error):
        key = callback_context.invocation_id
        stack = starts.get(key, [])
        started, call_id = stack.pop() if stack else (time.perf_counter(), str(uuid4()))
        if not stack:
            starts.pop(key, None)
        input_tokens, output_tokens = response_tokens(response)
        raw_run_id = callback_context.state.get("monitoring_active_run_id")
        try:
            run_id = UUID(str(raw_run_id)) if raw_run_id else None
        except ValueError:
            run_id = None
        usage = new_usage(
            stage=stage,
            operation="generate_content",
            model_id=model_id,
            outcome="failed" if error else "succeeded",
            latency_ms=max(0, round((time.perf_counter() - started) * 1000)),
            call_id=call_id,
            request_id=key[:100],
            run_id=run_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            error_class=type(error).__name__ if error else None,
        )
        try:
            await repository.record(usage)
        except Exception:
            _logger.exception("ADK model usage ledger write failed stage=%s", stage)

    async def after_model(callback_context, llm_response):
        await _record(callback_context, llm_response, None)
        return None

    async def on_model_error(callback_context, llm_request, error):
        del llm_request
        await _record(callback_context, None, error)
        return None

    return {
        "before_model_callback": before_model,
        "after_model_callback": after_model,
        "on_model_error_callback": on_model_error,
    }


_default_usage_repository: PostgresModelCallUsageRepository | None = None


def configure_default_model_usage_repository(
    repository: PostgresModelCallUsageRepository | None,
) -> None:
    """Bind the same runtime ledger used by ADK root and CLI agents."""
    global _default_usage_repository
    _default_usage_repository = repository


class _DefaultUsageProxy:
    async def record(self, usage: ModelCallUsage) -> None:
        repository = _default_usage_repository
        if repository is not None:
            await repository.record(usage)


DEFAULT_USAGE_PROXY = _DefaultUsageProxy()


async def record_model_cache_hit(
    repository: PostgresModelCallUsageRepository | None,
    *,
    stage: str,
    operation: str,
    model_id: str,
    input_count: int = 1,
) -> None:
    if repository is None or input_count <= 0:
        return
    try:
        await repository.record(
            new_usage(
                stage=stage,
                operation=operation,
                model_id=model_id,
                outcome="cache_hit",
                latency_ms=0,
                input_count=input_count,
            )
        )
    except Exception:
        _logger.exception("model cache-hit ledger write failed stage=%s", stage)
