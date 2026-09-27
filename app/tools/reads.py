"""Business-data read tools. None of them takes a scope argument (plan §6.6).

Each reads the turn's `ResolutionPlan` (the read grant `resolve_request`
issued) and touches only the family and offerings named in it. The model can
choose *how* to read — the question text, a history window — but never *what*.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from google.adk.tools import ToolContext

from app.domain.intent import FreshnessStatus, HistoryQuery, HistoryRequestKind
from app.domain.structured_tariffs import ANSWERABLE_OPERATIONS, ResolutionPlan
from app.domain.tariff_queries import CurrentTariffResult, TariffHistoryResult
from app.services.snapshot_lifecycle import tariff_fields
from app.services.tariff_queries import field_citations
from app.services.tariff_queries import (
    model_facing_query_result as model_facing_result,
)
from app.tools._services import services
from app.tools._state import (
    MONITOR_OFFER_KEY,
    TARIFF_PLAN_KEY,
    TARIFF_PLAN_USED_KEY,
    invocation_id,
    tariff_session_id,
)


def _read_plan(tool_context: ToolContext) -> ResolutionPlan | dict[str, object]:
    """The turn's read grant, or a rejection envelope.

    Checks session, turn and expiry (the plan checks its own question against
    its hash). Does not check or set the one-use flag.
    """
    raw = tool_context.state.get(TARIFF_PLAN_KEY)
    if not isinstance(raw, dict):
        return {"status": "rejected", "reason_code": "query.plan_absent"}
    try:
        plan = ResolutionPlan.model_validate(raw)
        if plan.session_id != tariff_session_id(tool_context):
            raise ValueError("session mismatch")
        invocation = invocation_id(tool_context)
        if invocation is not None and plan.turn_id != invocation:
            raise ValueError("turn mismatch")
        if not plan.issued_at <= datetime.now(UTC) < plan.expires_at:
            raise ValueError("plan expired")
    except ValueError:
        return {"status": "rejected", "reason_code": "query.plan_invalid"}
    return plan


async def answer_tariff_query(tool_context: ToolContext) -> dict[str, object]:
    """Answer this message's tariff question from accepted, cited facts.

    Takes no arguments: the question, scope and fields are the ones
    resolve_request granted for this turn.
    """
    if services.answer_router is None and services.structured_query_service is None:
        return {"status": "unavailable", "reason_code": "query.service_unavailable"}
    if isinstance(tool_context.state.get(TARIFF_PLAN_KEY), dict) and (
        tool_context.state.get(TARIFF_PLAN_USED_KEY)
    ):
        return {"status": "rejected", "reason_code": "query.plan_replayed"}
    plan = _read_plan(tool_context)
    if isinstance(plan, dict):
        return plan
    if plan.question is None:
        return {"status": "rejected", "reason_code": "query.plan_invalid"}
    if plan.product is None or plan.operation not in ANSWERABLE_OPERATIONS:
        # A scope-only grant: there is no field shape to answer from.
        return {
            "status": "rejected",
            "reason_code": "query.scope_only_plan",
            "hint": (
                "ask which tariff field the user wants (rate, term, fees, ...) "
                "and resolve again; get_current_tariffs reports freshness only"
            ),
        }
    tool_context.state[TARIFF_PLAN_USED_KEY] = True
    if services.answer_router is not None:
        result = await services.answer_router.answer_plan(plan, plan.question)
    else:
        result = await services.structured_query_service.answer(plan, plan.question)
    return model_facing_result(result.model_dump(mode="json"))


async def get_current_tariffs(tool_context: ToolContext) -> dict[str, object]:
    """Read latest accepted tariffs and freshness for this turn's resolved scope."""
    if services.current_tariff_service is None:
        return {"status": "unavailable", "reason_code": "current.service_unavailable"}
    plan = _read_plan(tool_context)
    if isinstance(plan, dict):
        return plan
    try:
        result = await services.current_tariff_service.get_current(
            product=plan.product,
            offering_ids=plan.offering_ids,
        )
    except ValueError:
        return {"status": "rejected", "reason_code": "current.invalid_scope"}
    missing = any(item.freshness is FreshnessStatus.MISSING for item in result.items)
    if missing and plan.product is not None:
        # The offer is computed from the grant, never from a tool argument, so
        # the scope of a later paid run cannot originate with the model.
        tool_context.state[MONITOR_OFFER_KEY] = {
            "kind": "monitoring",
            "product": plan.product.value,
            "offering_id": (
                plan.offering_ids[0].value if len(plan.offering_ids) == 1 else None
            ),
            "invocation_id": invocation_id(tool_context),
        }
    payload = current_tariffs_payload(result)
    if missing:
        # Demonstration artifacts under `end-to-end/` look like completed work
        # but never publish a snapshot, so say what "missing" actually means.
        payload["missing_means"] = (
            "no monitoring run has published an accepted snapshot for this "
            "offering yet; demonstration artifacts do not count"
        )
    return payload


async def get_tariff_history(
    kind: Literal["what_changed", "show_history"],
    tool_context: ToolContext,
    start_at: str | None = None,
    end_at: str | None = None,
    limit: int = 20,
) -> dict[str, object]:
    """Read accepted snapshot history or change sets for this turn's scope.

    The window and page size are clamped by the history service; the family
    and offerings come only from resolve_request.
    """
    if services.tariff_history_service is None:
        return {"status": "unavailable", "reason_code": "history.service_unavailable"}
    plan = _read_plan(tool_context)
    if isinstance(plan, dict):
        return plan
    try:
        query = HistoryQuery.model_validate(
            {
                "kind": HistoryRequestKind(kind),
                "product": plan.product,
                "offering_ids": plan.offering_ids,
                "start_at": start_at,
                "end_at": end_at,
                # A page size is a presentation choice: clamp it, never refuse.
                "limit": max(1, min(int(limit), 100)),
            }
        )
        result = await services.tariff_history_service.query(query)
    except ValueError:
        return {"status": "rejected", "reason_code": "history.invalid_query"}
    return tariff_history_payload(result)


def current_tariffs_payload(result: CurrentTariffResult) -> dict[str, object]:
    """What the model needs from current tariffs: freshness, and which fields the
    accepted snapshot has, by status -- never values or evidence (RV8, D5).

    Values reach the user only through answer_tariff_query, which carries its
    own citations. The REST route returns the full result; it calls the service.
    """
    return {
        "bank": result.bank,
        "as_of": result.as_of.isoformat(),
        "items": [
            {
                "product": item.product.value,
                "offering_id": item.offering_id.value,
                "freshness": item.freshness.value,
                "snapshot_id": str(item.snapshot_id) if item.snapshot_id else None,
                "accepted_at": (
                    item.accepted_at.isoformat() if item.accepted_at else None
                ),
                "age_seconds": item.age_seconds,
                "pending_newer_review": item.pending_newer_review,
                "fields": _field_statuses(item.normalized_tariff),
            }
            for item in result.items
        ],
    }


def tariff_history_payload(result: TariffHistoryResult) -> dict[str, object]:
    """History for the model: values and times, each value with a compact
    citation (RR28), without the evidence catalog and extraction internals a
    stored snapshot carries (a snapshot's evidence alone is hundreds of kB).

    A changed value whose non-missing side has no citation is left out and
    listed under `omitted_changes`, never shown uncited (D14).
    """
    payload = result.model_dump(
        mode="json",
        exclude={
            "snapshots": {"__all__": {"evidence", "semantic_extraction", "validation"}}
        },
    )
    for dumped, snapshot in zip(
        payload.get("snapshots", ()), getattr(result, "snapshots", ()), strict=False
    ):
        dumped["citations"] = {
            field: list(citations)
            for field in tariff_fields(snapshot.normalized_tariff)
            if (citations := field_citations(snapshot, field))
        }
    omitted: list[dict[str, object]] = []
    for change in payload.get("changes", ()):
        kept = []
        for item in change["changes"]:
            missing_previous = (
                item["previous"] is not None and not item["previous_evidence"]
            )
            missing_current = (
                item["current"] is not None and not item["current_evidence"]
            )
            if missing_previous or missing_current:
                omitted.append(
                    {
                        "offering_id": change["offering_id"],
                        "field": item["field"],
                        "reason": "no verified citation for the "
                        + ("previous" if missing_previous else "current")
                        + " value",
                    }
                )
                continue
            kept.append(item)
        change["changes"] = kept
    if omitted:
        payload["omitted_changes"] = omitted
    return payload


def _field_statuses(tariff: dict[str, object] | None) -> dict[str, str]:
    return {
        name: str(value["status"])
        for name, value in (tariff or {}).items()
        if isinstance(value, dict) and isinstance(value.get("status"), str)
    }
