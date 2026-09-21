from typing import Literal
from uuid import UUID

from google.adk.tools import ToolContext

from app.domain.catalog import normalize_catalog_term
from app.domain.intent import (
    ConversationResolutionState,
    HistoryQuery,
    HistoryRequestKind,
    RequestIntent,
)
from app.domain.models import OfferingId, ProductType
from app.domain.monitoring import QuestionCommand, RunCommand, RunTrigger
from app.services.intent_resolution import RequestResolver
from app.services.rag_answer import RagAnswerService
from app.services.run_service import RunServicePort
from app.services.tariff_queries import (
    CurrentTariffService,
    RunWaitService,
    TariffHistoryService,
)

_run_service: RunServicePort | None = None
_answer_service: RagAnswerService | None = None
_request_resolver: RequestResolver | None = None
_current_tariff_service: CurrentTariffService | None = None
_tariff_history_service: TariffHistoryService | None = None
_run_wait_service: RunWaitService | None = None
_RESOLUTION_STATE_KEY = "intent_resolution"
_MONITOR_AUTHORIZATION_KEY = "temp:monitoring_authorization"
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
) -> None:
    global _answer_service, _request_resolver
    global _current_tariff_service, _tariff_history_service, _run_wait_service
    configure_run_service(run_service)
    _answer_service = answer_service
    _request_resolver = request_resolver
    _current_tariff_service = current_tariff_service
    _tariff_history_service = tariff_history_service
    _run_wait_service = run_wait_service


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
    raw_state = tool_context.state.get(_RESOLUTION_STATE_KEY)
    try:
        state = ConversationResolutionState.model_validate(raw_state or {})
    except ValueError:
        state = ConversationResolutionState()
    if (
        normalize_catalog_term(query) in _AFFIRMATIVE_REPLIES
        and state.latest_product is not None
    ):
        authorization = {
            "product": state.latest_product.value,
            "offering_id": (
                state.latest_offering_id.value
                if state.latest_offering_id is not None
                else None
            ),
        }
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
    turn = await _request_resolver.resolve_turn(query, state)
    tool_context.state[_RESOLUTION_STATE_KEY] = turn.state.model_dump(mode="json")
    resolved_intent = turn.resolution.continuation_intent or turn.resolution.intent
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
    tool_context.state[_MONITOR_AUTHORIZATION_KEY] = None
    result = await _run_service.submit(command)
    return {
        "status": result.run.status.value,
        "run_id": str(result.run.id),
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
    return result.model_dump(mode="json")


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
