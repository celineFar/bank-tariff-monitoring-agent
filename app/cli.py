"""Interactive ADK chat with durable monitoring completion in one terminal session."""

from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import dataclass, replace
from time import monotonic
from uuid import UUID, uuid4

from google.adk.agents import Agent
from google.adk.apps import App, ResumabilityConfig
from google.adk.runners import Runner
from google.adk.tools import LongRunningFunctionTool, ToolContext, request_input
from google.genai import types
from google.genai.errors import APIError

from app.agent import root_agent
from app.app_utils import services
from app.config import get_settings
from app.domain.monitoring import RunStatus
from app.domain.monitoring_workflow import MonitoringReviewResponse, ReviewResponseItem
from app.domain.review import ReviewDecision, ReviewDecisionType
from app.runtime import build_application_container
from app.services.chat_reviews import ReviewNotReadyError
from app.tools import (
    answer_tariff_question,
    configure_services,
    get_current_tariffs,
    get_next_monitoring_review,
    get_tariff_history,
    resolve_request,
    start_tariff_monitoring,
    submit_monitoring_review_input,
)


async def start_tariff_monitoring_cli(
    product: str,
    offering_id: str | None,
    tool_context: ToolContext,
) -> dict[str, object] | None:
    """Start a durable monitoring run and pause until the CLI supplies its result."""
    return await start_tariff_monitoring(product, offering_id, tool_context)


cli_agent = Agent(
    name="ameria_tariff_monitor_cli",
    model=root_agent.model,
    instruction=(
        "You are the Ameria Bank tariff-monitoring assistant. If this "
        "conversation has an active run awaiting review, any request to continue "
        "must call get_next_monitoring_review and present its saved review. "
        "Never offer to restart monitoring while a review is pending. "
        "On ordinary text turns without a pending review, call resolve_request "
        "first and follow its canonical scope, language, "
        "clarification, and catalog guidance. For tariff questions check accepted "
        "snapshots with get_current_tariffs. When a required snapshot is missing, "
        "explain that monitoring is needed and ask for confirmation. Only after "
        "explicit authorization call start_tariff_monitoring_cli. This long-running "
        "tool starts the worker and pauses this invocation; do not call it twice. "
        "The CLI supplies its final function response when the worker reaches a "
        "terminal or review state. On a failed result, report the exact saved "
        "failure_code without claiming tariff data. On success, answer the original "
        "question from accepted snapshots with answer_tariff_question. On review, "
        "call get_next_monitoring_review, show the field, candidate, and evidence, "
        "then call request_input with the returned review_id and response_schema. "
        "After native input, call submit_monitoring_review_input; repeat until "
        "complete. Route history to get_tariff_history. Never invent tariff values, "
        "evidence, status, or source URLs. Never expose pending candidates as "
        "accepted tariffs."
    ),
    tools=[
        resolve_request,
        get_current_tariffs,
        get_tariff_history,
        LongRunningFunctionTool(start_tariff_monitoring_cli),
        get_next_monitoring_review,
        request_input,
        submit_monitoring_review_input,
        answer_tariff_question,
    ],
)
cli_app = App(
    name="app_cli",
    root_agent=cli_agent,
    resumability_config=ResumabilityConfig(is_resumable=True),
)


@dataclass(frozen=True)
class PendingInput:
    invocation_id: str
    function_call_id: str
    name: str
    arguments: dict[str, object]
    initial_response: dict[str, object] | None = None


def pending_input(events: list[object]) -> PendingInput | None:
    """Find the latest unmatched ADK long-running call in saved session events."""
    pending: dict[str, PendingInput] = {}
    for event in events:
        for part in (event.content.parts if event.content else ()) or ():
            call = part.function_call
            if call is not None and call.id in (event.long_running_tool_ids or ()):
                pending[call.id] = PendingInput(
                    invocation_id=event.invocation_id,
                    function_call_id=call.id,
                    name=call.name,
                    arguments=dict(call.args or {}),
                )
            response = part.function_response
            if response is not None and response.id in pending:
                if event.author == "user":
                    pending.pop(response.id, None)
                else:
                    initial = dict(response.response or {})
                    if (
                        pending[response.id].name == "start_tariff_monitoring_cli"
                        and not initial.get("request_satisfied")
                    ):
                        pending.pop(response.id, None)
                    else:
                        pending[response.id] = replace(
                            pending[response.id], initial_response=initial
                        )
    return next(reversed(pending.values())) if pending else None


async def _run_and_print(runner: Runner, **kwargs: object) -> None:
    async for event in runner.run_async(**kwargs):
        for part in (event.content.parts if event.content else ()) or ():
            if part.text and not getattr(part, "thought", False):
                print(f"Assistant  {part.text}")


async def _resume(
    runner: Runner,
    *,
    user_id: str,
    session_id: str,
    pending: PendingInput,
    response: dict[str, object],
) -> None:
    await _run_and_print(
        runner,
        user_id=user_id,
        session_id=session_id,
        invocation_id=pending.invocation_id,
        new_message=types.Content(
            role="user",
            parts=[
                types.Part(
                    function_response=types.FunctionResponse(
                        id=pending.function_call_id,
                        name=pending.name,
                        response=response,
                    )
                )
            ],
        ),
    )


_STAGE_LABELS = {
    "acquisition": "Acquiring web content",
    "normalization": "Reading source documents",
    "source_discovery": "Finding tariff evidence",
    "semantic_extraction": "Extracting tariff fields",
    "previous_snapshot": "Checking previous snapshot",
    "embedding": "Indexing evidence",
    "publication": "Saving candidate tariffs",
    "review_approved": "Review approved",
    "review_rejected": "Review rejected",
    "published": "Snapshot published",
}


async def _wait_for_run(run_service: object, run_id: UUID, seconds: float):
    last_progress = None
    last_message_at = 0.0
    while True:
        run = await run_service.get(run_id)
        if run is None:
            raise RuntimeError(f"monitoring run {run_id} was not found")
        offerings = await run_service.list_offering_executions(run_id)
        active = tuple(
            (item.offering_id.value, item.current_stage or item.status.value)
            for item in offerings
            if item.status.value in {"running", "pending"}
        )
        progress = (run.status.value, active)
        now = monotonic()
        if progress != last_progress or (
            run.status is RunStatus.RUNNING and now - last_message_at >= 30
        ):
            if active:
                for offering_id, stage in active:
                    label = _STAGE_LABELS.get(stage, stage.replace("_", " ").capitalize())
                    print(f"  {offering_id}: {label}…", flush=True)
            elif run.status is RunStatus.QUEUED:
                print("  Waiting for the worker…", flush=True)
            elif run.status is RunStatus.RUNNING:
                print("  Monitoring is still running…", flush=True)
            else:
                print(f"  Monitoring {run.status.value.replace('_', ' ')}.", flush=True)
            last_progress = progress
            last_message_at = now
        if run.status.is_terminal or run.status is RunStatus.AWAITING_REVIEW:
            return run
        await asyncio.sleep(seconds)


async def _continue_pending(
    runner: Runner,
    session_service: object,
    run_service: object,
    *,
    user_id: str,
    session_id: str,
    poll_seconds: float,
) -> None:
    while True:
        session = await session_service.get_session(
            app_name=cli_app.name, user_id=user_id, session_id=session_id
        )
        pending = pending_input(session.events)
        if pending is None:
            return
        if pending.name == "start_tariff_monitoring_cli":
            result = pending.initial_response or {}
            if not result.get("request_satisfied") or not result.get("run_id"):
                return
            run = await _wait_for_run(
                run_service, UUID(str(result["run_id"])), poll_seconds
            )
            await _resume(
                runner,
                user_id=user_id,
                session_id=session_id,
                pending=pending,
                response={
                    "run_id": str(run.id),
                    "status": run.status.value,
                    "failure_code": run.failure_code,
                    "failure_detail": run.failure_detail,
                    "review_required": run.status is RunStatus.AWAITING_REVIEW,
                },
            )
            continue
        if pending.name == "adk_request_input":
            print("\nReview needed")
            print(pending.arguments.get("message", "Review input required"))
            print(
                'Answer as JSON, for example: '
                '{"review_id":"<shown ID>","decision_type":"reject_all"}'
            )
            print(
                "Choices: approve, select_candidate, override, reject_all. "
                "Type ? to see the full input schema."
            )
            while True:
                raw = await asyncio.to_thread(input, "Review> ")
                if raw.strip() == "?":
                    print(json.dumps(
                        pending.arguments.get("response_schema", {}), indent=2
                    ))
                    continue
                try:
                    answer = json.loads(raw)
                    if not isinstance(answer, dict):
                        raise ValueError("response must be a JSON object")
                    break
                except ValueError as exc:
                    print(f"Invalid review response: {exc}")
            await _resume(
                runner,
                user_id=user_id,
                session_id=session_id,
                pending=pending,
                response={"result": answer},
            )
            continue
        raise RuntimeError(f"unsupported pending ADK input: {pending.name}")


def _ordered_evidence(item: object) -> tuple[object, ...]:
    field = item.issue_scope.replace("_", " ").casefold()
    candidate_references = {
        reference
        for candidate in item.candidates
        for reference in candidate.evidence_references
    }

    def rank(evidence: object) -> int:
        excerpt = evidence.excerpt.casefold()
        if evidence.evidence_id in candidate_references:
            return 0
        if f"row: {field}" in excerpt:
            return 1
        if field in excerpt:
            return 2
        return 3

    return tuple(sorted(item.evidence, key=rank))


def _show_review(
    item: object, index: int, total: int, *, all_evidence: bool = False
) -> None:
    print(
        f"\nReview {index}/{total}: {item.offering_id.value} / "
        f"{item.issue_scope} ({item.reason.value})"
    )
    print(item.guidance)
    for candidate in item.candidates:
        print(
            f"  Candidate {candidate.candidate_id}: "
            f"{json.dumps(candidate.value, ensure_ascii=False)}"
        )
    evidence_items = _ordered_evidence(item)
    visible = evidence_items if all_evidence else evidence_items[:5]
    for evidence in visible:
        location = f" page {evidence.page}" if evidence.page else ""
        print(
            f"  Evidence {evidence.evidence_id}: "
            f"{evidence.source_url}{location}"
        )
        print(f"    {evidence.excerpt[:400].replace(chr(10), ' ')}")
    if len(visible) < len(evidence_items):
        print(f"  {len(evidence_items) - len(visible)} more evidence items; type ? to see all.")


async def _recover_review(
    runner: Runner,
    session_service: object,
    run_service: object,
    review_service: object,
    *,
    user_id: str,
    session_id: str,
) -> bool:
    """Resume a business review directly when no root ADK input is outstanding."""
    session = await session_service.get_session(
        app_name=cli_app.name, user_id=user_id, session_id=session_id
    )
    if session is None or pending_input(session.events) is not None:
        return False
    raw_run_id = session.state.get("monitoring_active_run_id")
    known = session.state.get("monitoring_chat_run_ids") or []
    if not isinstance(raw_run_id, str) or raw_run_id not in known:
        return False
    run = await run_service.get(UUID(raw_run_id))
    if run is None or run.status is not RunStatus.AWAITING_REVIEW:
        return False

    print(
        f"\nMonitoring for {run.command.offering_id.value if run.command.offering_id else run.command.product.value} "
        f"is paused for review (run {run.id}). Continuing here; no new run is needed."
    )
    while True:
        try:
            request = await review_service.pending_request(run.id)
        except ReviewNotReadyError:
            print("The review is no longer pending.")
            return True
        decisions = []
        reject_all = False
        for index, item in enumerate(request.reviews, start=1):
            _show_review(item, index, len(request.reviews))
            allowed = {choice.value for choice in item.allowed_decisions}
            print("Enter a JSON decision, or type reject_all to discard this run.")
            print(
                "For an override, include override_value, reason, and an "
                "evidence_reference shown above."
            )
            while True:
                raw = (await asyncio.to_thread(input, "Review> ")).strip()
                if raw.lower() in {"quit", "exit"}:
                    raise EOFError
                if raw == "?":
                    _show_review(item, index, len(request.reviews), all_evidence=True)
                    continue
                try:
                    if raw == "reject_all":
                        decision = ReviewDecision(
                            decision_type=ReviewDecisionType.REJECT_ALL
                        )
                    else:
                        payload = json.loads(raw)
                        if not isinstance(payload, dict):
                            raise ValueError("decision must be a JSON object")
                        if "review_id" in payload and payload["review_id"] != str(item.review_id):
                            raise ValueError("review_id does not match this review")
                        decision = ReviewDecision.model_validate(
                            {key: value for key, value in payload.items() if key != "review_id"}
                        )
                    if decision.decision_type.value not in allowed:
                        raise ValueError("decision is not allowed for this review")
                    break
                except ValueError as exc:
                    print(f"Invalid decision: {exc}")
            if decision.decision_type is ReviewDecisionType.REJECT_ALL:
                reject_all = True
                break
            decisions.append(
                ReviewResponseItem(review_id=item.review_id, decision=decision)
            )
        if reject_all:
            decisions = [
                ReviewResponseItem(
                    review_id=item.review_id,
                    decision=ReviewDecision(
                        decision_type=ReviewDecisionType.REJECT_ALL
                    ),
                )
                for item in request.reviews
            ]
        try:
            result = await review_service.resume(
                run.id,
                MonitoringReviewResponse(decisions=tuple(decisions)),
                actor_user_id=user_id,
                actor_session_id=session_id,
            )
        except (ValueError, ReviewNotReadyError) as exc:
            print(f"Review was not applied: {exc}. Please correct the decision.")
            continue
        except Exception as exc:
            print(
                f"Review remains pending after {type(exc).__name__}. "
                "Check the API logs and reopen this session to retry."
            )
            return True
        print(f"Review completed. Monitoring status: {result.status.value}.")
        if result.status in {RunStatus.SUCCEEDED, RunStatus.PARTIAL_SUCCESS}:
            original_question = session.state.get("monitoring_original_question")
            if isinstance(original_question, str) and original_question:
                await _run_and_print(
                    runner,
                    user_id=user_id,
                    session_id=session_id,
                    new_message=types.Content(
                        role="user",
                        parts=[types.Part(
                            text=(
                                "The saved monitoring review is complete. Answer "
                                "my original tariff question from accepted data: "
                                f"{original_question}"
                            )
                        )],
                    ),
                )
        return True


def _print_api_error(exc: APIError) -> None:
    if exc.code == 402 and exc.status == "RESOURCE_EXHAUSTED":
        print(
            "Gemini prepaid credits are depleted. Add credits to the configured "
            "Google AI project, then retry in this session. No chat answer "
            "was produced."
        )
    else:
        print(
            f"Gemini request failed ({exc.code} {exc.status}). "
            "Check the API and worker logs, then retry in this session."
        )


async def chat(user_id: str, session_id: str, poll_seconds: float) -> None:
    settings = get_settings()
    container = build_application_container(settings)
    session_service = await services.ensure_session_service_ready()
    configure_services(
        container.run_service,
        container.answer_service,
        container.request_resolver,
        container.current_tariff_service,
        container.tariff_history_service,
        container.run_wait_service,
        container.chat_review_service,
    )
    runner = Runner(
        app=cli_app,
        session_service=session_service,
        artifact_service=services.get_artifact_service(),
    )
    try:
        session = await session_service.get_session(
            app_name=cli_app.name, user_id=user_id, session_id=session_id
        )
        if session is None:
            await session_service.create_session(
                app_name=cli_app.name, user_id=user_id, session_id=session_id
            )
        print("Ameria Tariff Chat")
        print(f"Session: {session_id}")
        print("Type quit to exit. Use this session ID to resume later.\n")
        try:
            await _continue_pending(
                runner, session_service, container.run_service,
                user_id=user_id, session_id=session_id, poll_seconds=poll_seconds,
            )
            await _recover_review(
                runner, session_service, container.run_service,
                container.chat_review_service,
                user_id=user_id, session_id=session_id,
            )
        except APIError as exc:
            _print_api_error(exc)
        while True:
            prompt = (await asyncio.to_thread(input, "You> ")).strip()
            if prompt.lower() in {"exit", "quit"}:
                return
            if not prompt:
                continue
            try:
                recovered = await _recover_review(
                    runner, session_service, container.run_service,
                    container.chat_review_service,
                    user_id=user_id, session_id=session_id,
                )
                if recovered:
                    continue
                await _run_and_print(
                    runner,
                    user_id=user_id,
                    session_id=session_id,
                    new_message=types.Content(
                        role="user", parts=[types.Part(text=prompt)]
                    ),
                )
                await _continue_pending(
                    runner, session_service, container.run_service,
                    user_id=user_id, session_id=session_id, poll_seconds=poll_seconds,
                )
                await _recover_review(
                    runner, session_service, container.run_service,
                    container.chat_review_service,
                    user_id=user_id, session_id=session_id,
                )
            except APIError as exc:
                _print_api_error(exc)
    finally:
        configure_services(None, None, None, None, None, None, None)
        await container.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Durable Ameria tariff ADK chat")
    parser.add_argument("--user-id", default="cli-user")
    parser.add_argument("--session-id", default=None)
    parser.add_argument("--poll-seconds", type=float, default=3.0)
    args = parser.parse_args()
    if args.poll_seconds <= 0:
        parser.error("--poll-seconds must be positive")
    session_id = args.session_id or str(uuid4())
    try:
        asyncio.run(chat(args.user_id, session_id, args.poll_seconds))
    except (KeyboardInterrupt, EOFError):
        print(
            f"\nResume with: ./tariff-chat --user-id {args.user_id} "
            f"--session-id {session_id}"
        )


if __name__ == "__main__":
    main()
