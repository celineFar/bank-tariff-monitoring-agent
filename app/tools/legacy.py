"""The pre-redesign chat monitoring and review protocol (removed in Phase 4).

The old CLI agent and the current root agent still register these tools; the
ADK-native replacements live in `app/tools/monitoring.py`.
"""

import json
from typing import Literal
from urllib.parse import urlencode
from uuid import UUID

from google.adk.tools import ToolContext

from app.domain.models import OfferingId, ProductType
from app.domain.monitoring import QuestionCommand, RunCommand, RunStatus, RunTrigger
from app.domain.monitoring_workflow import MonitoringReviewResponse, ReviewResponseItem
from app.domain.review import ReviewDecision, ReviewDecisionType
from app.domain.semantic_extraction import ExtractionField
from app.services.chat_reviews import ReviewNotReadyError
from app.services.failure_mapping import explain_failure_code
from app.services.monitoring_workflow import (
    MONITORING_WORKFLOW_APP_NAME,
    workflow_identity,
)
from app.services.review_decisions import coerce_review_candidate_value
from app.services.review_input import ReviewInputError
from app.services.review_resolution import (
    review_input_format as _review_input_format,
)
from app.services.review_resolution import (
    reviewed_value as _reviewed_value,
)
from app.services.run_service import run_covers_command
from app.services.semantic_extraction import validate_review_field_value
from app.tools._services import services
from app.tools._state import (
    FULL_PRODUCT_ACK_KEY,
    MONITOR_AUTHORIZATION_KEY,
    MONITOR_OFFER_KEY,
    ORIGINAL_QUESTION_KEY,
    issued_this_turn,
)

_MONITOR_AUTHORIZATION_KEY = MONITOR_AUTHORIZATION_KEY
_ACTIVE_RUN_KEY = "monitoring_active_run_id"
_CHAT_RUN_IDS_KEY = "monitoring_chat_run_ids"
_REVIEW_PROGRESS_KEY = "monitoring_review_progress"
_REVIEW_CURRENT_KEY = "monitoring_review_current_id"
_REVIEW_CHOICES_KEY = "monitoring_review_choices"
_ORIGINAL_QUESTION_KEY = ORIGINAL_QUESTION_KEY
_MONITOR_OFFER_KEY = MONITOR_OFFER_KEY
_FULL_PRODUCT_ACK_KEY = FULL_PRODUCT_ACK_KEY
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


async def start_tariff_monitoring(
    product: Literal["consumer_loan", "mortgage"],
    offering_id: str | None,
    tool_context: ToolContext,
) -> dict[str, object]:
    """Hand a canonical product to the deterministic monitoring pipeline."""
    if services.run_service is None:
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
    if (
        not issued_this_turn(authorization, tool_context)
        or {key: authorization.get(key) for key in expected_authorization}
        != expected_authorization
    ):
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
    result = await services.run_service.submit(command)
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


async def answer_tariff_question(
    query: str,
    product: Literal["consumer_loan", "mortgage"] | None = None,
    offering_id: str | None = None,
) -> dict[str, object]:
    """Answer from the active index only; this tool never acquires source pages."""
    if services.answer_service is None:
        return {"status": "unavailable", "reason_code": "answer.service_unavailable"}
    command = QuestionCommand(
        query=query,
        product=ProductType(product) if product else None,
        offering_id=OfferingId(offering_id) if offering_id else None,
    )
    return (await services.answer_service.answer(command)).model_dump(mode="json")


async def wait_for_monitoring_run(
    run_id: str,
    timeout_seconds: float | None = None,
) -> dict[str, object]:
    """Wait briefly for a persisted run, stopping on terminal or review state."""
    if services.run_wait_service is None:
        return {"status": "unavailable", "reason_code": "run_wait.service_unavailable"}
    try:
        result = await services.run_wait_service.wait(
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
    if services.chat_review_service is None or services.run_service is None:
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
    run = await services.run_service.get(run_id)
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
        request = await services.chat_review_service.pending_request(run_id)
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
    if services.chat_review_service is None:
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
        request = await services.chat_review_service.pending_request(run_id)
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
        run = (
            await services.run_service.get(run_id)
            if services.run_service is not None
            else None
        )
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
        result = await services.chat_review_service.resume(
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
        and (services.answer_router is not None or services.answer_service is not None)
        and services.run_service is not None
    ):
        run = await services.run_service.get(run_id)
        if run is not None:
            try:
                command = QuestionCommand(
                    query=original_question,
                    product=run.command.product,
                    offering_id=run.command.offering_id,
                )
                answer = await (
                    services.answer_router.answer_question(command)
                    if services.answer_router is not None
                    else services.answer_service.answer(command)
                )
                output["answer"] = answer.model_dump(mode="json")
            except Exception:
                output["answer_status"] = "temporarily_unavailable"
    return output
