import hashlib
import json
from datetime import UTC, datetime
from typing import Literal
from urllib.parse import urlencode
from uuid import UUID, uuid4

from google.adk.tools import ToolContext

from app.domain.catalog import normalize_catalog_term
from app.domain.intent import (
    ConversationResolutionState,
    FreshnessStatus,
    HistoryQuery,
    HistoryRequestKind,
    RequestIntent,
)
from app.domain.models import OfferingId, ProductType
from app.domain.monitoring import QuestionCommand, RunCommand, RunStatus, RunTrigger
from app.domain.monitoring_workflow import MonitoringReviewResponse, ReviewResponseItem
from app.domain.review import ReviewDecision, ReviewDecisionType
from app.domain.semantic_extraction import ExtractionField
from app.domain.structured_tariffs import ResolutionPlan
from app.services.answer_read_model import TariffAnswerRouter
from app.services.chat_reviews import ChatReviewService, ReviewNotReadyError
from app.services.failure_mapping import explain_failure_code
from app.services.intent_resolution import RequestResolver
from app.services.monitoring_workflow import (
    MONITORING_WORKFLOW_APP_NAME,
    workflow_identity,
)
from app.services.rag_answer import RagAnswerService
from app.services.review_decisions import coerce_review_candidate_value
from app.services.review_input import ReviewInputError
from app.services.review_resolution import (
    review_input_format as _review_input_format,
)
from app.services.review_resolution import (
    reviewed_value as _reviewed_value,
)
from app.services.run_service import RunServicePort, run_covers_command
from app.services.semantic_extraction import validate_review_field_value
from app.services.structured_query_planning import issue_resolution_plan
from app.services.structured_tariff_query import StructuredTariffQueryService
from app.services.tariff_queries import (
    CurrentTariffService,
    RunWaitService,
    TariffHistoryService,
)

_run_service: RunServicePort | None = None
_answer_service: RagAnswerService | None = None
_structured_query_service: StructuredTariffQueryService | None = None
_answer_router: TariffAnswerRouter | None = None
_request_resolver: RequestResolver | None = None
_current_tariff_service: CurrentTariffService | None = None
_tariff_history_service: TariffHistoryService | None = None
_run_wait_service: RunWaitService | None = None
_chat_review_service: ChatReviewService | None = None
_RESOLUTION_STATE_KEY = "intent_resolution"
_TARIFF_PLAN_KEY = "tariff_resolution_plan"
_TARIFF_PLAN_USED_KEY = "tariff_resolution_plan_used"
_TARIFF_LAST_USED_TURN_KEY = "tariff_resolution_last_used_turn"
_TARIFF_SESSION_KEY = "tariff_resolution_session_id"
_MONITOR_AUTHORIZATION_KEY = "temp:monitoring_authorization"
_ACTIVE_RUN_KEY = "monitoring_active_run_id"
_CHAT_RUN_IDS_KEY = "monitoring_chat_run_ids"
_REVIEW_PROGRESS_KEY = "monitoring_review_progress"
_REVIEW_CURRENT_KEY = "monitoring_review_current_id"
_REVIEW_CHOICES_KEY = "monitoring_review_choices"
_ORIGINAL_QUESTION_KEY = "monitoring_original_question"
_MONITOR_OFFER_KEY = "monitoring_confirmation_offer"
_FULL_PRODUCT_ACK_KEY = "monitoring_full_product_ack"
_REVIEW_INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "review_id": {"type": "string"},
        "decision_type": {
            "type": "string",
            "enum": ["approve", "select_candidate", "reject_all", "override"],
        },
        "candidate_id": {"type": "string"},
        "override_value": {},
        "reason": {"type": "string"},
        "evidence_reference": {"type": "string"},
    },
    "required": ["review_id", "decision_type"],
}
_AFFIRMATIVE_REPLIES = frozenset({"yes", "yes please", "refresh", "այո", "թարմացրու"})


def configure_run_service(service: RunServicePort | None) -> None:
    """Bind the application service without exposing repositories to the model."""
    global _run_service
    _run_service = service


def configure_services(
    run_service: RunServicePort | None,
    answer_service: RagAnswerService | None,
    request_resolver: RequestResolver | None = None,
    current_tariff_service: CurrentTariffService | None = None,
    tariff_history_service: TariffHistoryService | None = None,
    run_wait_service: RunWaitService | None = None,
    chat_review_service: ChatReviewService | None = None,
    structured_query_service: StructuredTariffQueryService | None = None,
    answer_router: TariffAnswerRouter | None = None,
) -> None:
    global _answer_service, _request_resolver, _structured_query_service
    global _current_tariff_service, _tariff_history_service, _run_wait_service
    global _chat_review_service, _answer_router
    configure_run_service(run_service)
    _answer_service = answer_service
    _structured_query_service = structured_query_service
    _answer_router = answer_router
    _request_resolver = request_resolver
    _current_tariff_service = current_tariff_service
    _tariff_history_service = tariff_history_service
    _run_wait_service = run_wait_service
    _chat_review_service = chat_review_service


def _current_user_text(tool_context: ToolContext) -> str | None:
    session = getattr(tool_context, "session", None)
    if session is None:
        return None
    invocation = getattr(tool_context, "invocation_id", None)
    for event in reversed(list(getattr(session, "events", ()) or ())):
        if getattr(event, "author", None) != "user":
            continue
        if invocation and getattr(event, "invocation_id", None) != invocation:
            continue
        parts = getattr(getattr(event, "content", None), "parts", ()) or ()
        values = [
            part.text for part in parts if isinstance(getattr(part, "text", None), str)
        ]
        if values:
            return "".join(values)
    return ""


def _tariff_session_id(tool_context: ToolContext) -> str:
    session = getattr(tool_context, "session", None)
    session_id = getattr(session, "id", None)
    if isinstance(session_id, str) and session_id:
        return session_id
    saved = tool_context.state.get(_TARIFF_SESSION_KEY)
    if isinstance(saved, str) and saved:
        return saved
    generated = str(uuid4())
    tool_context.state[_TARIFF_SESSION_KEY] = generated
    return generated


def _tariff_turn_id(tool_context: ToolContext) -> str:
    invocation = getattr(tool_context, "invocation_id", None)
    return invocation if isinstance(invocation, str) and invocation else str(uuid4())


async def resolve_request(
    query: str,
    tool_context: ToolContext,
) -> dict[str, object]:
    """Resolve intent and product/offering scope without starting business work."""
    if _request_resolver is None:
        return {
            "status": "unavailable",
            "reason_code": "intent.service_unavailable",
        }
    invocation = getattr(tool_context, "invocation_id", None)
    if (
        isinstance(invocation, str)
        and invocation
        and tool_context.state.get(_TARIFF_LAST_USED_TURN_KEY) == invocation
    ):
        return {"status": "rejected", "reason_code": "intent.turn_already_used"}
    # Each resolution replaces any prior business-data authorization.
    tool_context.state[_TARIFF_PLAN_KEY] = None
    tool_context.state[_TARIFF_PLAN_USED_KEY] = False
    user_text = _current_user_text(tool_context)
    if user_text is not None and query != user_text:
        return {"status": "rejected", "reason_code": "intent.query_mismatch"}
    raw_state = tool_context.state.get(_RESOLUTION_STATE_KEY)
    try:
        state = ConversationResolutionState.model_validate(raw_state or {})
    except ValueError:
        state = ConversationResolutionState()
    if normalize_catalog_term(query) in _AFFIRMATIVE_REPLIES and isinstance(
        tool_context.state.get(_MONITOR_OFFER_KEY), dict
    ):
        authorization = dict(tool_context.state[_MONITOR_OFFER_KEY])
        tool_context.state[_MONITOR_OFFER_KEY] = None
        tool_context.state[_MONITOR_AUTHORIZATION_KEY] = authorization
        return {
            "intent": RequestIntent.START_MONITORING_RUN.value,
            "language": "hy"
            if any("\u0531" <= char <= "\u0586" for char in query)
            else "en",
            "method": "exact",
            **authorization,
            "needs_clarification": False,
            "expects_single_value": False,
            "refresh_confirmation": True,
        }
    tool_context.state[_MONITOR_OFFER_KEY] = None
    turn = await _request_resolver.resolve_turn(query, state)
    tool_context.state[_RESOLUTION_STATE_KEY] = turn.state.model_dump(mode="json")
    resolved_intent = turn.resolution.continuation_intent or turn.resolution.intent
    if resolved_intent in {
        RequestIntent.ANSWER_INDEXED_TARIFF_QUESTION,
        RequestIntent.GET_CURRENT_TARIFFS,
    }:
        tool_context.state[_ORIGINAL_QUESTION_KEY] = query
    elif resolved_intent is RequestIntent.START_MONITORING_RUN:
        tool_context.state[_ORIGINAL_QUESTION_KEY] = None
    if (
        resolved_intent is RequestIntent.START_MONITORING_RUN
        and not turn.resolution.needs_clarification
        and turn.resolution.product is not None
    ):
        tool_context.state[_MONITOR_AUTHORIZATION_KEY] = {
            "product": turn.resolution.product.value,
            "offering_id": (
                turn.resolution.offering_id.value
                if turn.resolution.offering_id is not None
                else None
            ),
        }
    else:
        tool_context.state[_MONITOR_AUTHORIZATION_KEY] = None
    result = turn.resolution.model_dump(mode="json")
    if (
        resolved_intent
        in {
            RequestIntent.ANSWER_INDEXED_TARIFF_QUESTION,
            RequestIntent.GET_CURRENT_TARIFFS,
            RequestIntent.GET_CHANGE_HISTORY,
        }
        and not turn.resolution.needs_clarification
        and turn.resolution.product is not None
    ):
        try:
            plan = issue_resolution_plan(
                query,
                turn.resolution,
                session_id=_tariff_session_id(tool_context),
                turn_id=_tariff_turn_id(tool_context),
            )
        except ValueError:
            plan = None
        if plan is not None:
            tool_context.state[_TARIFF_PLAN_KEY] = plan.model_dump(mode="json")
            result["query_plan"] = {
                "operation": plan.operation.value,
                "offering_ids": [item.value for item in plan.offering_ids],
                "fields": [item.value for item in plan.fields],
                "conditions": plan.conditions,
                "rank_direction": (
                    plan.rank_direction.value if plan.rank_direction else None
                ),
            }
    active_run_id = tool_context.state.get(_ACTIVE_RUN_KEY)
    if isinstance(active_run_id, str):
        result["active_monitoring_run_id"] = active_run_id
    chat_run_ids = tool_context.state.get(_CHAT_RUN_IDS_KEY)
    if isinstance(chat_run_ids, list):
        result["chat_monitoring_run_ids"] = chat_run_ids
    if not state.introduction_shown:
        result["catalog_intro"] = _request_resolver.catalog_payload(
            turn.resolution.language,
            complete=False,
        )
    if resolved_intent is RequestIntent.LIST_SUPPORTED_PRODUCTS:
        result["supported_catalog"] = _request_resolver.catalog_payload(
            turn.resolution.language,
            complete=True,
        )
    return result


async def start_tariff_monitoring(
    product: Literal["consumer_loan", "mortgage"],
    offering_id: str | None,
    tool_context: ToolContext,
) -> dict[str, object]:
    """Hand a canonical product to the deterministic monitoring pipeline."""
    if _run_service is None:
        return {
            "status": "UNAVAILABLE",
            "product": product,
            "reason_code": "run.service_unavailable",
        }
    try:
        resolved_product = ProductType(product)
        resolved_offering = OfferingId(offering_id) if offering_id else None
        command = RunCommand(
            product=resolved_product,
            offering_id=resolved_offering,
            trigger=RunTrigger.ADK,
        )
    except ValueError:
        return {
            "status": "rejected",
            "product": product,
            "offering_id": offering_id,
            "reason_code": "run.invalid_scope",
        }
    authorization = tool_context.state.get(_MONITOR_AUTHORIZATION_KEY)
    expected_authorization = {
        "product": product,
        "offering_id": resolved_offering.value if resolved_offering else None,
    }
    if authorization != expected_authorization:
        return {
            "status": "rejected",
            "product": product,
            "offering_id": offering_id,
            "reason_code": "run.intent_not_authorized",
        }
    # An unscoped run fans out to every enabled offering in the product family, so it
    # costs a multiple of a single-offering run. Make that scope explicit once before
    # spending it, rather than letting a question about one product launch all of them.
    if resolved_offering is None:
        family = tuple(
            item.value for item in OfferingId if item.product is resolved_product
        )
        if tool_context.state.get(_FULL_PRODUCT_ACK_KEY) != product:
            tool_context.state[_FULL_PRODUCT_ACK_KEY] = product
            return {
                "status": "needs_scope_confirmation",
                "product": product,
                "offering_id": None,
                "offering_count": len(family),
                "offerings": list(family),
                "reason_code": "run.full_product_scope",
            }
    tool_context.state[_FULL_PRODUCT_ACK_KEY] = None
    tool_context.state[_MONITOR_AUTHORIZATION_KEY] = None
    tool_context.state[_MONITOR_OFFER_KEY] = None
    result = await _run_service.submit(command)
    request_satisfied = run_covers_command(result.run, command)
    known_run_ids = list(tool_context.state.get(_CHAT_RUN_IDS_KEY) or [])
    chat_review_available = request_satisfied and (
        result.created or str(result.run.id) in known_run_ids
    )
    if chat_review_available:
        if str(result.run.id) not in known_run_ids:
            known_run_ids.append(str(result.run.id))
            tool_context.state[_CHAT_RUN_IDS_KEY] = known_run_ids
        _switch_chat_run(tool_context, str(result.run.id))
    review_user_id, review_session_id = workflow_identity(result.run)
    review_query = urlencode(
        {
            "app": MONITORING_WORKFLOW_APP_NAME,
            "userId": review_user_id,
            "session": review_session_id,
        }
    )
    return {
        "status": result.run.status.value if request_satisfied else "blocked",
        "run_status": result.run.status.value,
        "request_satisfied": request_satisfied,
        "chat_review_available": chat_review_available,
        "requested_product": command.product.value,
        "requested_offering_id": (
            command.offering_id.value if command.offering_id is not None else None
        ),
        "run_id": str(result.run.id),
        "status_url": f"/api/v1/runs/{result.run.id}",
        "review_handoff_url": f"/api/v1/runs/{result.run.id}/review-handoff",
        "reviews_url": f"/api/v1/reviews?run_id={result.run.id}",
        "review_url": f"/dev-ui/?{review_query}",
        "product": result.run.command.product.value,
        "offering_id": (
            result.run.command.offering_id.value
            if result.run.command.offering_id is not None
            else None
        ),
        "created": result.created,
        "reused_reason": (
            result.reused_reason.value if result.reused_reason is not None else None
        ),
    }


async def answer_tariff_query(
    query: str, tool_context: ToolContext
) -> dict[str, object]:
    """Read only the server-held per-turn scope from resolve_request."""
    if _answer_router is None and _structured_query_service is None:
        return {"status": "unavailable", "reason_code": "query.service_unavailable"}
    raw = tool_context.state.get(_TARIFF_PLAN_KEY)
    if not isinstance(raw, dict):
        return {"status": "rejected", "reason_code": "query.plan_absent"}
    if tool_context.state.get(_TARIFF_PLAN_USED_KEY):
        return {"status": "rejected", "reason_code": "query.plan_replayed"}
    try:
        plan = ResolutionPlan.model_validate(raw)
        if plan.session_id != _tariff_session_id(tool_context):
            raise ValueError("session mismatch")
        invocation = getattr(tool_context, "invocation_id", None)
        if isinstance(invocation, str) and invocation and plan.turn_id != invocation:
            raise ValueError("turn mismatch")
        if hashlib.sha256(query.encode("utf-8")).hexdigest() != plan.question_sha256:
            raise ValueError("question mismatch")
        if not plan.issued_at <= datetime.now(UTC) < plan.expires_at:
            raise ValueError("plan expired")
    except ValueError:
        return {"status": "rejected", "reason_code": "query.plan_invalid"}
    tool_context.state[_TARIFF_PLAN_USED_KEY] = True
    tool_context.state[_TARIFF_LAST_USED_TURN_KEY] = plan.turn_id
    if _answer_router is not None:
        result = await _answer_router.answer_plan(plan, query)
    else:
        result = await _structured_query_service.answer(plan, query)
    return result.model_dump(mode="json")


async def answer_tariff_question(
    query: str,
    product: Literal["consumer_loan", "mortgage"] | None = None,
    offering_id: str | None = None,
) -> dict[str, object]:
    """Answer from the active index only; this tool never acquires source pages."""
    if _answer_service is None:
        return {"status": "unavailable", "reason_code": "answer.service_unavailable"}
    command = QuestionCommand(
        query=query,
        product=ProductType(product) if product else None,
        offering_id=OfferingId(offering_id) if offering_id else None,
    )
    return (await _answer_service.answer(command)).model_dump(mode="json")


async def get_current_tariffs(
    product: Literal["consumer_loan", "mortgage"] | None = None,
    offering_id: str | None = None,
    tool_context: ToolContext | None = None,
) -> dict[str, object]:
    """Read latest accepted tariffs and freshness without exposing review candidates."""
    if _current_tariff_service is None:
        return {"status": "unavailable", "reason_code": "current.service_unavailable"}
    try:
        result = await _current_tariff_service.get_current(
            product=ProductType(product) if product else None,
            offering_id=OfferingId(offering_id) if offering_id else None,
        )
    except ValueError:
        return {"status": "rejected", "reason_code": "current.invalid_scope"}
    if (
        tool_context is not None
        and product is not None
        and any(item.freshness is FreshnessStatus.MISSING for item in result.items)
    ):
        tool_context.state[_MONITOR_OFFER_KEY] = {
            "product": product,
            "offering_id": offering_id,
        }
    payload = result.model_dump(mode="json")
    if any(item.freshness is FreshnessStatus.MISSING for item in result.items):
        # Demonstration artifacts under `end-to-end/` look like completed work
        # but never publish a snapshot, so say what "missing" actually means.
        payload["missing_means"] = (
            "no monitoring run has published an accepted snapshot for this "
            "offering yet; demonstration artifacts do not count"
        )
    return payload


async def get_tariff_history(
    kind: Literal["what_changed", "show_history"],
    product: Literal["consumer_loan", "mortgage"] | None = None,
    offering_id: str | None = None,
    start_at: str | None = None,
    end_at: str | None = None,
    limit: int = 20,
) -> dict[str, object]:
    """Read bounded accepted snapshot history or accepted change sets."""
    if _tariff_history_service is None:
        return {"status": "unavailable", "reason_code": "history.service_unavailable"}
    try:
        query = HistoryQuery.model_validate(
            {
                "kind": HistoryRequestKind(kind),
                "product": ProductType(product) if product else None,
                "offering_id": OfferingId(offering_id) if offering_id else None,
                "start_at": start_at,
                "end_at": end_at,
                "limit": limit,
            }
        )
        result = await _tariff_history_service.query(query)
    except ValueError:
        return {"status": "rejected", "reason_code": "history.invalid_query"}
    return result.model_dump(mode="json")


async def wait_for_monitoring_run(
    run_id: str,
    timeout_seconds: float | None = None,
) -> dict[str, object]:
    """Wait briefly for a persisted run, stopping on terminal or review state."""
    if _run_wait_service is None:
        return {"status": "unavailable", "reason_code": "run_wait.service_unavailable"}
    try:
        result = await _run_wait_service.wait(
            UUID(run_id),
            timeout_seconds=timeout_seconds,
        )
    except ValueError:
        return {"status": "rejected", "reason_code": "run_wait.invalid_request"}
    return result.model_dump(mode="json")


def _switch_chat_run(tool_context: ToolContext, run_id: str) -> None:
    current = tool_context.state.get(_ACTIVE_RUN_KEY)
    if current == run_id:
        return
    progress = dict(tool_context.state.get(_REVIEW_PROGRESS_KEY) or {})
    if isinstance(current, str) and current != run_id:
        progress[current] = {
            "choices": tool_context.state.get(_REVIEW_CHOICES_KEY) or {},
            "current_review_id": tool_context.state.get(_REVIEW_CURRENT_KEY),
        }
    saved = progress.get(run_id, {})
    tool_context.state[_REVIEW_PROGRESS_KEY] = progress
    tool_context.state[_ACTIVE_RUN_KEY] = run_id
    tool_context.state[_REVIEW_CHOICES_KEY] = saved.get("choices", {})
    tool_context.state[_REVIEW_CURRENT_KEY] = saved.get("current_review_id")


def _awaiting_cli_monitoring_result(tool_context: ToolContext) -> bool:
    """Whether a CLI monitoring call is still waiting for the CLI's own result.

    `start_tariff_monitoring_cli` is long-running: the CLI narrates the run and
    supplies the final function response. Until it does, there is nothing this
    chat can learn by asking again, and every ask costs a model round trip.
    """
    events = list(getattr(tool_context.session, "events", ()) or ())
    answered: set[str] = set()
    pending: set[str] = set()
    for event in events:
        for part in getattr(event.content, "parts", None) or ():
            call = getattr(part, "function_call", None)
            if call is not None and call.name == "start_tariff_monitoring_cli":
                pending.add(call.id)
            response = getattr(part, "function_response", None)
            if response is not None and response.name == "start_tariff_monitoring_cli":
                answered.add(response.id)
    return bool(pending - answered)


async def get_next_monitoring_review(
    tool_context: ToolContext, run_id: str | None = None
) -> dict[str, object]:
    """Get the next evidence-bound review item for this conversation's run."""
    if _chat_review_service is None or _run_service is None:
        return {"status": "unavailable", "reason_code": "review.service_unavailable"}
    if _awaiting_cli_monitoring_result(tool_context):
        return {
            "status": "rejected",
            "reason_code": "review.awaiting_cli_result",
            "action": "stop_and_wait",
        }
    known_run_ids = tool_context.state.get(_CHAT_RUN_IDS_KEY) or []
    if run_id is not None:
        if run_id not in known_run_ids:
            return {"status": "rejected", "reason_code": "review.run_not_owned_by_chat"}
        _switch_chat_run(tool_context, run_id)
    raw_run_id = tool_context.state.get(_ACTIVE_RUN_KEY)
    if not isinstance(raw_run_id, str):
        return {"status": "rejected", "reason_code": "review.no_chat_run"}
    run_id = UUID(raw_run_id)
    run = await _run_service.get(run_id)
    if run is None:
        return {"status": "rejected", "reason_code": "review.run_missing"}
    if run.status is not RunStatus.AWAITING_REVIEW:
        if not run.status.is_terminal:
            # Deliberately carries no live detail: a tool that reports a
            # running run's stage invites the model to poll it, and each poll
            # is a model call that tells the user nothing.
            return {
                "status": "in_progress",
                "run_id": raw_run_id,
                "reason_code": "review.run_not_ready",
                "action": "stop_and_wait",
            }
        return {
            "status": run.status.value,
            "run_id": raw_run_id,
            "failure_code": run.failure_code,
            "failure_summary": explain_failure_code(run.failure_code)
            if run.failure_code
            else None,
            "failure_detail": run.failure_detail,
            "original_question": tool_context.state.get(_ORIGINAL_QUESTION_KEY),
        }
    try:
        request = await _chat_review_service.pending_request(run_id)
    except ReviewNotReadyError:
        return {"status": "preparing", "run_id": raw_run_id}
    choices = tool_context.state.get(_REVIEW_CHOICES_KEY) or {}
    if not isinstance(choices, dict):
        choices = {}
    next_item = next(
        (item for item in request.reviews if str(item.review_id) not in choices),
        None,
    )
    if next_item is None:
        # A complete choice set with a still-pending run means the prior resume
        # did not commit. Ask again so an interrupted/failed decision can be retried.
        tool_context.state[_REVIEW_CHOICES_KEY] = {}
        choices = {}
        next_item = request.reviews[0]
    tool_context.state[_REVIEW_CURRENT_KEY] = str(next_item.review_id)
    response_schema = {
        **_REVIEW_INPUT_SCHEMA,
        "properties": {
            **_REVIEW_INPUT_SCHEMA["properties"],
            "decision_type": {
                "type": "string",
                "enum": [choice.value for choice in next_item.allowed_decisions],
            },
        },
    }
    return {
        "status": "needs_input",
        "run_id": raw_run_id,
        "completed_reviews": len(choices),
        "total_reviews": len(request.reviews),
        "review": next_item.model_dump(mode="json"),
        "input_format": _review_input_format(next_item.issue_scope),
        "response_schema": response_schema,
    }


def _native_input(tool_context: ToolContext) -> dict[str, object] | None:
    events = list(getattr(tool_context.session, "events", ()) or ())
    for index in range(len(events) - 1, -1, -1):
        event = events[index]
        if event.author != "user":
            continue
        if (
            getattr(tool_context, "invocation_id", None) is not None
            and event.invocation_id != tool_context.invocation_id
        ):
            return None
        for part in getattr(event.content, "parts", None) or ():
            response = getattr(part, "function_response", None)
            if response is None or response.name != "adk_request_input":
                continue
            if not any(
                call.id == response.id and call.name == "adk_request_input"
                for previous in events[:index]
                for earlier_part in getattr(previous.content, "parts", None) or ()
                if (call := getattr(earlier_part, "function_call", None)) is not None
            ):
                return None
            raw = dict(response.response or {})
            if "review_id" in raw:
                return raw
            result = raw.get("result")
            if isinstance(result, dict):
                return result
            if isinstance(result, str):
                try:
                    parsed = json.loads(result)
                except ValueError:
                    return None
                return parsed if isinstance(parsed, dict) else None
            return None
        return None
    return None


async def submit_monitoring_review_input(
    tool_context: ToolContext,
) -> dict[str, object]:
    """Apply only the human's native ADK input for the current review item."""
    if _chat_review_service is None:
        return {"status": "unavailable", "reason_code": "review.service_unavailable"}
    raw_run_id = tool_context.state.get(_ACTIVE_RUN_KEY)
    expected_review_id = tool_context.state.get(_REVIEW_CURRENT_KEY)
    if not isinstance(raw_run_id, str) or not isinstance(expected_review_id, str):
        return {"status": "rejected", "reason_code": "review.no_pending_chat_input"}
    raw = _native_input(tool_context)
    if raw is None:
        return {"status": "rejected", "reason_code": "review.native_input_required"}
    if raw.get("review_id") != expected_review_id:
        return {"status": "rejected", "reason_code": "review.input_scope_mismatch"}
    try:
        run_id = UUID(raw_run_id)
        request = await _chat_review_service.pending_request(run_id)
        item = next(
            view
            for view in request.reviews
            if str(view.review_id) == expected_review_id
        )
        decision = ReviewDecision.model_validate(
            {key: value for key, value in raw.items() if key != "review_id"}
        )
        if decision.decision_type not in item.allowed_decisions:
            raise ValueError("decision is not allowed for this review")
        if decision.decision_type is ReviewDecisionType.SELECT_CANDIDATE and not any(
            candidate.candidate_id == decision.candidate_id
            for candidate in item.candidates
        ):
            raise ValueError("candidate is outside this review")
        if decision.decision_type is ReviewDecisionType.OVERRIDE and not any(
            evidence.evidence_id == decision.evidence_reference
            for evidence in item.evidence
        ):
            raise ValueError("evidence is outside this review")
        if decision.decision_type is ReviewDecisionType.SELECT_CANDIDATE:
            selected = next(
                candidate
                for candidate in item.candidates
                if candidate.candidate_id == decision.candidate_id
            )
            if selected.conditions.get("conditions"):
                return {
                    "status": "rejected",
                    "reason_code": "review.candidate_requires_override",
                    "message": "This candidate has conditions; provide a structured override with evidence or reject the review.",
                }
            value = coerce_review_candidate_value(
                ExtractionField(item.issue_scope), selected.value
            )
            try:
                validate_review_field_value(ExtractionField(item.issue_scope), value)
            except ValueError:
                return {
                    "status": "rejected",
                    "reason_code": "review.candidate_value_invalid",
                    "message": (
                        "The captured candidate is text that cannot be stored as "
                        f"a valid {item.issue_scope} value. Provide a structured "
                        "override with evidence or reject the review."
                    ),
                }
        if decision.decision_type is ReviewDecisionType.OVERRIDE:
            field = ExtractionField(item.issue_scope)
            excerpt = next(
                (
                    evidence.excerpt
                    for evidence in item.evidence
                    if evidence.evidence_id == decision.evidence_reference
                ),
                "",
            )
            try:
                decision = decision.model_copy(
                    update={
                        "override_value": _reviewed_value(
                            field, decision.override_value, excerpt
                        )
                    }
                )
            except ReviewInputError as exc:
                return {
                    "status": "rejected",
                    "reason_code": "review.override_value_invalid",
                    "message": str(exc),
                    "input_format": _review_input_format(item.issue_scope),
                }
            except ValueError:
                return {
                    "status": "rejected",
                    "reason_code": "review.override_value_invalid",
                    "message": (
                        f"The override does not match the {item.issue_scope} field "
                        "schema. Correct the structured value and try again."
                    ),
                    "input_format": _review_input_format(item.issue_scope),
                }
    except ReviewNotReadyError:
        run = await _run_service.get(run_id) if _run_service is not None else None
        tool_context.state[_REVIEW_CURRENT_KEY] = None
        return {
            "status": run.status.value if run is not None else "unavailable",
            "reason_code": "review.no_longer_pending",
            "run_id": raw_run_id,
        }
    except (ValueError, StopIteration):
        return {"status": "rejected", "reason_code": "review.invalid_input"}
    choices = dict(tool_context.state.get(_REVIEW_CHOICES_KEY) or {})
    choices[expected_review_id] = decision.model_dump(mode="json")
    tool_context.state[_REVIEW_CHOICES_KEY] = choices
    tool_context.state[_REVIEW_CURRENT_KEY] = None
    if decision.decision_type is ReviewDecisionType.REJECT_ALL:
        response = MonitoringReviewResponse(
            decisions=tuple(
                ReviewResponseItem(
                    review_id=view.review_id,
                    decision=ReviewDecision(
                        decision_type=ReviewDecisionType.REJECT_ALL
                    ),
                )
                for view in request.reviews
            )
        )
    elif len(choices) == len(request.reviews):
        response = MonitoringReviewResponse(
            decisions=tuple(
                ReviewResponseItem(
                    review_id=view.review_id,
                    decision=ReviewDecision.model_validate(
                        choices[str(view.review_id)]
                    ),
                )
                for view in request.reviews
            )
        )
    else:
        return await get_next_monitoring_review(tool_context)
    try:
        result = await _chat_review_service.resume(
            run_id,
            response,
            actor_user_id=str(getattr(tool_context, "user_id", "unknown")),
            actor_session_id=str(
                getattr(getattr(tool_context, "session", None), "id", "unknown")
            ),
        )
    except (ValueError, ReviewNotReadyError):
        tool_context.state[_REVIEW_CHOICES_KEY] = {}
        tool_context.state[_REVIEW_CURRENT_KEY] = None
        return {"status": "rejected", "reason_code": "review.resume_conflict"}
    tool_context.state[_REVIEW_CHOICES_KEY] = {}
    original_question = tool_context.state.get(_ORIGINAL_QUESTION_KEY)
    output: dict[str, object] = {
        "status": result.status.value,
        "run_id": raw_run_id,
        "original_question": original_question,
    }
    if (
        result.status in {RunStatus.SUCCEEDED, RunStatus.PARTIAL_SUCCESS}
        and isinstance(original_question, str)
        and (_answer_router is not None or _answer_service is not None)
        and _run_service is not None
    ):
        run = await _run_service.get(run_id)
        if run is not None:
            try:
                command = QuestionCommand(
                    query=original_question,
                    product=run.command.product,
                    offering_id=run.command.offering_id,
                )
                answer = await (
                    _answer_router.answer_question(command)
                    if _answer_router is not None
                    else _answer_service.answer(command)
                )
                output["answer"] = answer.model_dump(mode="json")
            except Exception:
                output["answer_status"] = "temporarily_unavailable"
    return output
