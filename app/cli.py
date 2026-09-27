"""Interactive tariff chat: one ADK invocation per turn, attached to the terminal.

A message starts an invocation of the single `app` agent. If monitoring is
needed, the monitoring node runs inside that invocation: its progress arrives
here as partial events, each review arrives as a native `adk_request_input`
pause, and the reviewer's answer resumes the same invocation. Ctrl-C cancels
the turn (and with it the run) and rewinds the conversation.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import re
import secrets
import signal
import socket
import threading
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from time import monotonic
from typing import Any

from google.adk.events import Event, EventActions
from google.adk.runners import Runner
from google.adk.sessions import BaseSessionService
from google.genai import types
from google.genai.errors import APIError
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from app.agent import app as agent_app
from app.app_utils import services
from app.config import get_settings
from app.domain.review import (
    ReviewDecision,
    ReviewDecisionInput,
    ReviewDecisionType,
    ReviewPromptView,
)
from app.domain.semantic_extraction import ExtractionField
from app.runtime import build_application_container
from app.services.adk_logging import (
    install_runtime_log_filters,
    suppress_resource_exhaustion_adk_logs,
)
from app.services.failure_mapping import explain_failure_code
from app.services.monitoring_node import PROGRESS_KIND
from app.services.monitoring_progress import (
    PipelineProgress,
    ProgressKind,
    stage_label,
)
from app.services.review_evidence import (
    DisplayPassage,
    DisplayUnit,
    ReviewDisplay,
    ReviewDisplayService,
)
from app.services.review_input import (
    ReviewInputError,
    parse_review_field_text,
    review_field_format,
    term_supported_by_passage,
)
from app.tools import configure_services

console = Console(highlight=False)
logger = logging.getLogger(__name__)

OWNER_STATE_KEY = "cli_owner"
MONITORING_TOOLS = frozenset({"run_tariff_monitoring", "review_pending_candidates"})
REVIEW_REQUEST = "adk_request_input"


def _notice(message: str, *, tone: str = "cyan", symbol: str = "•") -> None:
    line = Text()
    line.append(f"{symbol} ", style=f"bold {tone}")
    line.append(message, style=tone)
    console.print(line)


def _input(prompt: str) -> str:
    console.print(Text.from_markup(prompt), end="")
    return input("")


async def _ainput(prompt: str) -> str:
    """Read a line without blocking the loop or holding up interpreter exit.

    A daemon thread, unlike `asyncio.to_thread`, is not joined at shutdown, so
    Ctrl-C at a prompt exits at once instead of waiting for Enter.
    """
    loop = asyncio.get_running_loop()
    future: asyncio.Future[str] = loop.create_future()

    def read() -> None:
        try:
            value = _input(prompt)
        except BaseException as exc:  # handed to the loop, raised by the await
            loop.call_soon_threadsafe(_settle, future, None, exc)
        else:
            loop.call_soon_threadsafe(_settle, future, value, None)

    threading.Thread(target=read, daemon=True).start()
    return await future


def _settle(future: asyncio.Future, value: Any, error: BaseException | None) -> None:
    if future.done():
        return
    if error is not None:
        future.set_exception(error)
    else:
        future.set_result(value)


def _error(title: str, message: str) -> None:
    console.print(
        Panel(
            Text(message),
            title=Text(title, style="bold red"),
            border_style="red",
            expand=False,
        )
    )


def _duration(milliseconds: int | float) -> str:
    seconds = round(milliseconds / 1000)
    minutes, seconds = divmod(seconds, 60)
    return f"{minutes}m{seconds:02d}s" if minutes else f"{seconds}s"


def _leader(label: str, value: str, *, width: int = 40) -> str:
    dots = "·" * max(2, width - len(label))
    return f"{label} {dots} {value}"


# --- session events -------------------------------------------------------------


def live_events(events: list[Event]) -> list[Event]:
    """`events` without rewound invocations.

    `Runner.rewind_async` appends a marker instead of deleting history; this
    mirrors ADK's own filter (`google.adk.events._rewind_events._apply_rewinds`)
    so the CLI sees the same live conversation the model does.
    """
    kept: list[Event] = []
    index = len(events) - 1
    while index >= 0:
        event = events[index]
        target = event.actions.rewind_before_invocation_id if event.actions else None
        if target:
            index = next(
                (
                    position
                    for position in range(index)
                    if events[position].invocation_id == target
                ),
                index,
            )
        else:
            kept.append(event)
        index -= 1
    kept.reverse()
    return kept


@dataclass(frozen=True)
class PendingReview:
    invocation_id: str
    interrupt_id: str
    message: str | None
    payload: dict[str, Any]


def pending_review(events: list[Event]) -> PendingReview | None:
    """The latest `adk_request_input` pause the user has not answered yet."""
    open_calls: dict[str, PendingReview] = {}
    for event in live_events(events):
        for part in (event.content.parts if event.content else ()) or ():
            call = part.function_call
            if call is not None and call.name == REVIEW_REQUEST and call.id:
                args = dict(call.args or {})
                payload = args.get("payload")
                open_calls[call.id] = PendingReview(
                    invocation_id=event.invocation_id,
                    interrupt_id=call.id,
                    message=args.get("message"),
                    payload=payload if isinstance(payload, dict) else {},
                )
            response = part.function_response
            if response is not None and response.id in open_calls:
                open_calls.pop(response.id, None)
    return next(reversed(open_calls.values())) if open_calls else None


def dangling_monitoring_invocation(events: list[Event]) -> str | None:
    """The invocation of a monitoring call that never got a response.

    Only meaningful when no review pause is open: then the process that was
    executing the run died mid-run.
    """
    calls: dict[str, str] = {}
    for event in live_events(events):
        for part in (event.content.parts if event.content else ()) or ():
            call = part.function_call
            if call is not None and call.name in MONITORING_TOOLS and call.id:
                calls[call.id] = event.invocation_id
            response = part.function_response
            if response is not None and response.id in calls:
                calls.pop(response.id, None)
    return next(reversed(calls.values())) if calls else None


def _review_reply(interrupt_id: str, reply: dict[str, Any]) -> types.Content:
    return types.Content(
        role="user",
        parts=[
            types.Part(
                function_response=types.FunctionResponse(
                    id=interrupt_id,
                    name=REVIEW_REQUEST,
                    response={"result": reply},
                )
            )
        ],
    )


# --- rendering ------------------------------------------------------------------


class ProgressRenderer:
    """Turns the invocation's events into terminal output.

    Progress comes only from `custom_metadata["progress"]`; the event text is
    never parsed. A spinner with a local timer shows the stage in flight, so a
    long stage never looks frozen and nothing is polled.
    """

    def __init__(self, *, verbose: bool = False) -> None:
        self.verbose = verbose
        self._status = None
        self._ticker: asyncio.Task | None = None
        self._offerings = 1
        self._run_started: float | None = None
        self.saw_monitoring = False
        # Set when this turn follows a run another process executes.
        self.followed = False

    def render(self, event: Event) -> None:
        metadata = event.custom_metadata or {}
        if metadata.get("kind") == PROGRESS_KIND:
            self.saw_monitoring = True
            try:
                item = PipelineProgress.model_validate(metadata.get("progress"))
            except ValueError:
                return
            self._progress(item)
            return
        if self.verbose:
            self._verbose(event)
        if event.partial:
            return
        for part in (event.content.parts if event.content else ()) or ():
            if part.text and not getattr(part, "thought", False):
                self.stop()
                console.print(
                    Panel(
                        Markdown(part.text),
                        title=Text("Assistant", style="bold cyan"),
                        border_style="cyan",
                        padding=(0, 1),
                    )
                )

    def stop(self) -> None:
        if self._ticker is not None:
            self._ticker.cancel()
            self._ticker = None
        if self._status is not None:
            self._status.stop()
            self._status = None

    def _progress(self, item: PipelineProgress) -> None:
        indent = "    " if self._offerings > 1 else "  "
        if item.kind is ProgressKind.RUN_STARTED:
            self._run_started = monotonic()
            count = re.match(r"(\d+)", item.detail or "")
            self._offerings = int(count.group(1)) if count else 1
            scope = (
                item.offering_id.value
                if item.offering_id
                else (
                    f"{self._offerings} {item.product.value.replace('_', ' ')} "
                    "offerings"
                )
            )
            self.stop()
            _notice(f"Monitoring {scope}", symbol="▶")
            if self.verbose:
                _notice(f"run {item.run_id}", tone="dim", symbol=" ")
        elif item.kind is ProgressKind.OFFERING_STARTED:
            if self._offerings > 1 and item.offering_id is not None:
                self.stop()
                console.print(Text(f"  {item.offering_id.value}", style="bold"))
        elif item.kind is ProgressKind.STAGE_STARTED:
            self._start_spinner(f"{indent}{stage_label(item.stage)}")
        elif item.kind is ProgressKind.STAGE_COMPLETED:
            self.stop()
            console.print(
                Text(
                    f"{indent}✓ "
                    + _leader(stage_label(item.stage), _duration(item.elapsed_ms))
                )
            )
        elif item.kind is ProgressKind.OFFERING_FAILED:
            self.stop()
            label = stage_label(item.stage)
            line = Text(f"{indent}✗ {label}", style="red")
            if item.failure_code:
                line.append(f" · {explain_failure_code(item.failure_code)}")
                line.append(f" ({item.failure_code})", style="dim")
            console.print(line)
        elif item.kind is ProgressKind.OFFERING_REVIEW:
            self.stop()
        elif item.kind is ProgressKind.RUN_FINISHED:
            self.stop()
            elapsed = _duration(item.elapsed_ms)
            if item.detail == "awaiting_review":
                _notice(
                    "Some values need your review before they can be accepted",
                    tone="yellow",
                    symbol="●",
                )
            elif item.detail == "succeeded":
                _notice(f"Monitoring finished in {elapsed}", tone="green", symbol="✓")
            else:
                detail = (item.detail or "finished").replace("_", " ")
                _notice(f"Monitoring {detail} after {elapsed}", tone="yellow")
        elif item.kind is ProgressKind.FOLLOWING:
            self.followed = True
            self.stop()
            _notice(item.detail or "Following a run started elsewhere", symbol="↳")

    def _start_spinner(self, label: str) -> None:
        self.stop()
        started = monotonic()
        self._status = console.status(f"{label}…", spinner="dots")
        self._status.start()

        async def tick() -> None:
            while True:
                await asyncio.sleep(1)
                if self._status is not None:
                    self._status.update(
                        f"{label} · {_duration((monotonic() - started) * 1000)}"
                    )

        try:
            self._ticker = asyncio.get_running_loop().create_task(tick())
        except RuntimeError:  # pragma: no cover - rendering outside a loop
            self._ticker = None

    def _verbose(self, event: Event) -> None:
        for part in (event.content.parts if event.content else ()) or ():
            if part.function_call is not None:
                _notice(f"call {part.function_call.name}", tone="dim", symbol="→")
            if part.function_response is not None:
                _notice(
                    f"response {part.function_response.name}", tone="dim", symbol="←"
                )


# --- the attach loop --------------------------------------------------------------


class ChatSession:
    """One named conversation: run turns, answer pauses, cancel, recover."""

    def __init__(
        self,
        *,
        runner: Runner,
        sessions: BaseSessionService,
        app_name: str,
        user_id: str,
        session_id: str,
        owner: str,
        runs: Any = None,
        renderer: ProgressRenderer | None = None,
        displays: ReviewDisplayService | None = None,
    ) -> None:
        self.runner = runner
        self.sessions = sessions
        self.app_name = app_name
        self.user_id = user_id
        self.session_id = session_id
        self.owner = owner
        self.runs = runs
        self.renderer = renderer or ProgressRenderer()
        self.displays = displays
        self._invocation_id: str | None = None
        self._turn: asyncio.Task | None = None

    def interrupt(self, fallback: asyncio.Task) -> None:
        """Ctrl-C: cancel the running turn; at the prompt, cancel `fallback`.

        Installed as the loop's SIGINT handler, so every press is a clean
        cancellation. asyncio's own handler cancels only on the first press and
        raises KeyboardInterrupt afterwards, which killed the CLI on the third
        press without closing the run.
        """
        if self._turn is not None:
            # A finished turn is still closing (rewind, notices): let it.
            if not self._turn.done():
                self._turn.cancel()
            return
        fallback.cancel()

    async def events(self) -> list[Event]:
        session = await self.sessions.get_session(
            app_name=self.app_name, user_id=self.user_id, session_id=self.session_id
        )
        return list(session.events) if session is not None else []

    async def open(self) -> None:
        """Create the conversation if new, recover it if it was interrupted."""
        session = await self.sessions.get_session(
            app_name=self.app_name, user_id=self.user_id, session_id=self.session_id
        )
        if session is None:
            session = await self.sessions.create_session(
                app_name=self.app_name,
                user_id=self.user_id,
                session_id=self.session_id,
            )
        previous_owner = session.state.get(OWNER_STATE_KEY)
        events = list(session.events)
        request = pending_review(events)
        if request is not None:
            view = self._view(request)
            if view is not None:
                _notice(
                    "Continuing the review of "
                    f"{view.offering_id.value} · {view.issue_scope.replace('_', ' ')}",
                    tone="yellow",
                    symbol="↳",
                )
            await self.answer_reviews()
        elif (invocation := dangling_monitoring_invocation(events)) is not None:
            await self._close_interrupted(invocation, previous_owner)
        await self._record_owner()

    async def converse(self, text: str) -> None:
        """One user message; Ctrl-C (task cancellation) cancels and rewinds it."""
        self._invocation_id = None
        self.renderer.saw_monitoring = False
        self.renderer.followed = False
        turn = asyncio.create_task(
            self.run_turn(types.Content(role="user", parts=[types.Part(text=text)]))
        )
        self._turn = turn
        try:
            await turn
        except asyncio.CancelledError:
            if not turn.done():
                turn.cancel()
            await asyncio.wait({turn})
            current = asyncio.current_task()
            if current is not None:
                current.uncancel()
            self.renderer.stop()
            events = await self.events()
            reviewing = pending_review(events) is not None
            # Decided from the persisted call, not from whether a progress
            # event happened to reach the terminal before Ctrl-C.
            monitoring = (
                self.renderer.saw_monitoring
                or dangling_monitoring_invocation(events) is not None
            )
            await self.rewind()
            if reviewing:
                _notice(
                    "Review postponed. The candidates stay pending; say "
                    '"review them" to continue.',
                    tone="yellow",
                )
            elif monitoring and self.renderer.followed:
                # The run belongs to another process; the node asked it to stop.
                _notice(
                    "Monitoring cancelled. The run started elsewhere was asked to "
                    "stop and will end within a few seconds.",
                    tone="yellow",
                )
            elif monitoring:
                _notice("Monitoring cancelled.", tone="yellow")
            else:
                _notice("Cancelled.", tone="yellow")
        finally:
            self._turn = None
            self.renderer.stop()

    async def run_turn(self, message: types.Content) -> None:
        await self._stream(message)
        await self.answer_reviews()

    async def answer_reviews(self) -> None:
        """Answer every open review pause, resuming the paused invocation each time."""
        while (request := pending_review(await self.events())) is not None:
            self._invocation_id = self._invocation_id or request.invocation_id
            reply = await self.ask(request)
            await self._stream(_review_reply(request.interrupt_id, reply))

    async def ask(self, request: PendingReview) -> dict[str, Any]:
        """Show one review and return a reply already valid for the pause.

        The reply is validated here, before it is sent: ADK cannot retry a
        resume whose reply fails the request's schema (plan §5, E11).
        """
        view = self._view(request)
        if view is None:
            raise RuntimeError(f"unsupported input request: {request.message}")
        rejected = request.payload.get("rejected")
        if isinstance(rejected, dict):
            _error(
                "The previous answer was not applied",
                str(rejected.get("message") or rejected.get("reason_code")),
            )
        position = int(request.payload.get("position") or 1)
        total = int(request.payload.get("total") or 1)
        decision = await _ask_review_decision(
            view, position, total, await self._display(view)
        )
        reply = ReviewDecisionInput.model_validate(
            decision.model_dump(mode="json", exclude_none=True)
        )
        return reply.model_dump(mode="json", exclude_none=True)

    async def rewind(self) -> None:
        invocation = self._invocation_id or await self._last_user_invocation()
        if invocation is None:
            return
        await self.runner.rewind_async(
            user_id=self.user_id,
            session_id=self.session_id,
            rewind_before_invocation_id=invocation,
        )

    async def _stream(self, message: types.Content) -> None:
        with suppress_resource_exhaustion_adk_logs():
            async for event in self.runner.run_async(
                user_id=self.user_id, session_id=self.session_id, new_message=message
            ):
                if event.invocation_id:
                    self._invocation_id = self._invocation_id or event.invocation_id
                self.renderer.render(event)

    async def _close_interrupted(self, invocation: str, previous_owner: object) -> None:
        """The CLI died mid-run: close its run and drop the dangling call."""
        closed = 0
        if isinstance(previous_owner, str) and previous_owner and self.runs is not None:
            try:
                closed = await self.runs.fail_interrupted(owner_prefix=previous_owner)
            except Exception:
                logger.warning("could not fail interrupted runs", exc_info=True)
        await self.runner.rewind_async(
            user_id=self.user_id,
            session_id=self.session_id,
            rewind_before_invocation_id=invocation,
        )
        logger.info("closed interrupted monitoring runs=%s", closed)
        _notice(
            "Your earlier monitoring run was interrupted when the chat closed. "
            "Ask again to rerun it.",
            tone="yellow",
            symbol="↳",
        )

    async def _record_owner(self) -> None:
        """Remember which process owns this conversation's runs, for recovery."""
        session = await self.sessions.get_session(
            app_name=self.app_name, user_id=self.user_id, session_id=self.session_id
        )
        if session is None or session.state.get(OWNER_STATE_KEY) == self.owner:
            return
        await self.sessions.append_event(
            session,
            Event(
                author="user",
                invocation_id=f"cli-open-{secrets.token_hex(4)}",
                actions=EventActions(state_delta={OWNER_STATE_KEY: self.owner}),
            ),
        )

    async def _last_user_invocation(self) -> str | None:
        for event in reversed(await self.events()):
            if event.author == "user" and event.content is not None:
                return event.invocation_id
        return None

    async def _display(self, view: ReviewPromptView) -> ReviewDisplay | None:
        """The review's units, read from the database (RV9); without them the
        reviewer still sees the seed passages the pause carries."""
        if self.displays is None:
            return None
        try:
            return await self.displays.load(view.review_id)
        except Exception:
            logger.warning("could not load review %s", view.review_id, exc_info=True)
            return None

    @staticmethod
    def _view(request: PendingReview) -> ReviewPromptView | None:
        if request.payload.get("kind") != "tariff_review":
            return None
        try:
            return ReviewPromptView.model_validate(request.payload.get("view"))
        except ValueError:
            return None


# --- review input -------------------------------------------------------------------


def _passages(
    item: object, display: ReviewDisplay | None
) -> tuple[DisplayPassage, ...]:
    """The passages the reviewer is shown: the review's units, or -- without
    access to the review's snapshot -- the seed excerpts the pause carries."""
    if display is not None:
        return display.shown
    return tuple(
        DisplayPassage(
            evidence_id=evidence.evidence_id,
            content=evidence.excerpt,
            seed=True,
            section=getattr(evidence, "section", None),
            source_url=evidence.source_url,
            page=evidence.page,
        )
        for evidence in item.evidence
    )


def _passage_text(number: int, passage: DisplayPassage) -> tuple[Text, Text]:
    """A numbered passage, whole (RV11); the rows that put its unit in the
    review are marked."""
    label = Text(f"{'▶' if passage.seed else ' '} {number}", style="bold cyan")
    location = passage.source_url or ""
    if passage.page:
        location += f" · page {passage.page}"
    body = Text(f"{location}\n", style="dim") if location else Text()
    body.append(passage.content)
    return label, body


def _show_review(
    item: object, index: int, total: int, display: ReviewDisplay | None = None
) -> None:
    heading = (
        f"Review {index}/{total} · {item.offering_id.value} · "
        f"{item.issue_scope} ({item.reason.value})"
    )
    guidance = (
        f"No {item.issue_scope.replace('_', ' ')} was extracted. Check the "
        "passages and enter the correct value, or reject this snapshot."
        if item.reason.value == "missing_required_field"
        else item.guidance
    )
    console.print(
        Panel(
            Text(guidance),
            title=Text(heading, style="bold yellow"),
            border_style="yellow",
        )
    )
    if item.candidates:
        candidates = Table(title="Extracted candidates", show_lines=True)
        candidates.add_column("#", style="cyan")
        candidates.add_column("Value")
        for number, candidate in enumerate(item.candidates, start=1):
            candidates.add_row(
                str(number), Text(json.dumps(candidate.value, ensure_ascii=False))
            )
        console.print(candidates)
    number = 0
    units = (
        display.units
        if display is not None
        else (
            (DisplayUnit("passage", "Passages", _passages(item, None), 0, "seed"),)
            if item.evidence
            else ()
        )
    )
    for unit in units:
        table = Table(
            title=f"{unit.kind.title()}: {unit.title}"[:200],
            show_lines=True,
            show_header=False,
        )
        table.add_column("#", no_wrap=True)
        table.add_column("Passage", overflow="fold")
        for passage in unit.passages:
            number += 1
            table.add_row(*_passage_text(number, passage))
        console.print(table)
        if unit.omitted:
            _notice(
                f"{unit.omitted} more passages of this {unit.kind} are not shown; "
                "type ? to read the sources.",
                tone="yellow",
            )
    if not number:
        _notice(
            "No captured passage is labelled for this field. Type ? to read the "
            "selected sources, or all to list every passage.",
            tone="yellow",
        )
    if display is not None and display.unknown_ids:
        _notice(
            f"Gemini cited {len(display.unknown_ids)} passage(s) that do not exist "
            "in the captured sources.",
            tone="yellow",
        )


def _show_sources(item: object, display: ReviewDisplay | None) -> None:
    """`?`: the selected sources as captured, in a pager (RV10)."""
    if display is not None and display.selected_sources_markdown:
        with console.pager(styles=True):
            console.print(Markdown(display.selected_sources_markdown))
        return
    _notice(
        "This snapshot has no saved source text; listing every captured passage.",
        tone="yellow",
    )
    _show_all(item, display)


def _show_all(
    item: object, display: ReviewDisplay | None
) -> tuple[DisplayPassage, ...]:
    """`all`: every passage of the snapshot, numbered, for citing one the
    review's units do not show (logged as a ranking miss, RV13)."""
    passages = display.all_passages if display is not None else _passages(item, None)
    table = Table(title="All captured passages", show_lines=True, show_header=False)
    table.add_column("#", no_wrap=True)
    table.add_column("Passage", overflow="fold")
    for number, passage in enumerate(passages, start=1):
        label, body = _passage_text(number, replace(passage, seed=False))
        table.add_row(label, body)
    console.print(table)
    return passages


def _review_value(
    field: ExtractionField, raw: str, *, evidence: tuple[DisplayPassage, ...] = ()
) -> object:
    """Read a reviewer's typed answer with the shared deterministic parser."""
    return parse_review_field_text(
        field, raw, excerpts=tuple(item.content for item in evidence)
    )


def _supports(field: ExtractionField, raw: str, passage: DisplayPassage) -> bool:
    if field is ExtractionField.TERM:
        return term_supported_by_passage(raw, passage.content)
    return raw.casefold() in passage.content.casefold()


def _entry_format(issue_scope: str) -> str:
    """Say what a valid answer looks like before the reviewer types one."""
    try:
        field_format = review_field_format(ExtractionField(issue_scope))
    except (KeyError, ValueError):
        return (
            "Enter the value as JSON matching this field's stored structure, or "
            "choose a candidate."
        )
    return field_format.help_text


async def _ask_review_decision(
    item: object, index: int, total: int, display: ReviewDisplay | None = None
) -> ReviewDecision:
    _show_review(item, index, total, display)
    allowed = set(item.allowed_decisions)
    options = []
    if ReviewDecisionType.APPROVE in allowed:
        options.append("approve the extracted value")
    if ReviewDecisionType.SELECT_CANDIDATE in allowed and item.candidates:
        options.append("enter a candidate number")
    if ReviewDecisionType.OVERRIDE in allowed:
        options.append(f"enter the correct {item.issue_scope.replace('_', ' ')}")
    if ReviewDecisionType.REJECT_ALL in allowed:
        options.append("type reject_all to discard this run")
    _notice(
        "You can "
        + ", ".join(options)
        + ". Type ? to read the selected sources, all to list every passage.",
        tone="yellow",
    )
    if ReviewDecisionType.OVERRIDE in allowed:
        _notice(_entry_format(item.issue_scope), tone="cyan")
    shown = _passages(item, display)
    while True:
        raw = (
            await _ainput(
                f"[bold yellow]{item.issue_scope.replace('_', ' ').title()}[/] [yellow]>[/] ",
            )
        ).strip()
        if raw.lower() in {"quit", "exit"}:
            raise EOFError
        if raw == "?":
            _show_sources(item, display)
            continue
        if raw.lower() == "all":
            _show_all(item, display)
            continue
        if raw.lower() == "reject_all" and ReviewDecisionType.REJECT_ALL in allowed:
            return ReviewDecision(decision_type=ReviewDecisionType.REJECT_ALL)
        if raw.lower() == "approve" and ReviewDecisionType.APPROVE in allowed:
            return ReviewDecision(decision_type=ReviewDecisionType.APPROVE)
        if raw.isdigit() and ReviewDecisionType.SELECT_CANDIDATE in allowed:
            number = int(raw)
            if 1 <= number <= len(item.candidates):
                return ReviewDecision(
                    decision_type=ReviewDecisionType.SELECT_CANDIDATE,
                    candidate_id=item.candidates[number - 1].candidate_id,
                )
        if raw.startswith("{"):
            try:
                payload = json.loads(raw)
                if not isinstance(payload, dict):
                    raise ValueError("decision must be an object")
                if "review_id" in payload and payload["review_id"] != str(
                    item.review_id
                ):
                    raise ValueError("review_id does not match this review")
                decision = ReviewDecision.model_validate(
                    {key: value for key, value in payload.items() if key != "review_id"}
                )
                if decision.decision_type not in allowed:
                    raise ValueError("decision is not allowed for this review")
                return decision
            except ValueError as exc:
                _error("Invalid decision", str(exc))
                continue
        if ReviewDecisionType.OVERRIDE not in allowed:
            _error("Invalid choice", "Choose one of the displayed options.")
            continue
        try:
            field = ExtractionField(item.issue_scope)
            value = _review_value(field, raw, evidence=shown)
        except ReviewInputError as exc:
            _error(f"Invalid {field.value.replace('_', ' ')}", str(exc))
            continue
        except ValueError as exc:
            _error("Invalid value", str(exc))
            continue
        choices = shown
        if not choices:
            _notice("Choose the passage that supports this value.", tone="yellow")
            choices = _show_all(item, display)
        if not choices:
            _error(
                "No evidence",
                "This field cannot be overridden without captured evidence.",
            )
            continue
        supporting = [p for p in choices if _supports(field, raw, p)]
        if len(supporting) == 1:
            selected = supporting[0]
            _notice(
                f"Using passage {choices.index(selected) + 1}, which states it, "
                "as support.",
                tone="yellow",
            )
        else:
            while True:
                number_text = (
                    await _ainput(
                        f"[bold yellow]Supporting passage (1-{len(choices)}, or all)[/] "
                        "[yellow]>[/] ",
                    )
                ).strip()
                if number_text.lower() in {"quit", "exit"}:
                    raise EOFError
                if number_text == "?":
                    _show_sources(item, display)
                    continue
                if number_text.lower() == "all":
                    choices = _show_all(item, display)
                    continue
                if number_text.isdigit() and 1 <= int(number_text) <= len(choices):
                    selected = choices[int(number_text) - 1]
                    if field is ExtractionField.TERM and not term_supported_by_passage(
                        raw, selected.content
                    ):
                        _error(
                            "Unsupported term",
                            "The entered term is not in that passage. Enter the term as shown in the source.",
                        )
                        continue
                    break
                _error("Invalid passage", "Enter a passage number shown above.")
        return ReviewDecision(
            decision_type=ReviewDecisionType.OVERRIDE,
            override_value=value,
            reason="Reviewer confirmed the value against the selected official passage.",
            evidence_reference=selected.evidence_id,
        )


def _print_api_error(exc: APIError) -> None:
    logger.warning("Gemini CLI request failed: code=%s status=%s", exc.code, exc.status)
    if exc.code == 429 and exc.status == "RESOURCE_EXHAUSTED":
        retry_delay = None
        details = exc.details.get("error", {}).get("details", [])
        if isinstance(details, list):
            retry_delay = next(
                (
                    item.get("retryDelay")
                    for item in details
                    if isinstance(item, dict)
                    and item.get("@type", "").endswith("RetryInfo")
                ),
                None,
            )
        wait = f" in about {retry_delay}" if retry_delay else " after the quota resets"
        _error(
            "Gemini rate limit reached",
            "Gemini's request quota was reached. Retry this session"
            f"{wait}. No chat answer was produced.",
        )
    elif exc.code == 402 and exc.status == "RESOURCE_EXHAUSTED":
        _error(
            "Gemini credits exhausted",
            "Gemini prepaid credits are depleted. Add credits to the configured "
            "Google AI project, then retry in this session. No chat answer "
            "was produced.",
        )
    else:
        _error(
            "Gemini request failed",
            f"{exc.code} {exc.status}. Check the API and worker logs, "
            "then retry in this session.",
        )


def _print_unexpected_error(exc: Exception, step: str, session_name: str) -> None:
    """Keep one broken step from ending a durable conversation.

    The traceback still reaches `logs/cli.log`; the terminal gets the step that
    broke and how to reopen this conversation.
    """
    logger.exception("CLI step failed: %s", step)
    _error(
        "Something went wrong",
        f"{step} failed: {type(exc).__name__}: {exc}\n"
        "The full traceback is in logs/cli.log. This conversation is still open.\n"
        f'Reopen it later with: ./tariff-chat --session "{session_name}"',
    )


def process_owner() -> str:
    """`cli:<host>:<pid>:<token>` — unique per CLI process, never a prefix of another."""
    import os

    return f"cli:{socket.gethostname()}:{os.getpid()}:{secrets.token_hex(4)}"


async def chat(
    user_id: str, session_name: str, *, verbose: bool = False, new: bool = False
) -> None:
    install_runtime_log_filters()
    settings = get_settings()
    owner = process_owner()
    container = build_application_container(settings, monitoring_owner=owner)
    session_service = await services.ensure_session_service_ready()
    configure_services(
        container.run_service,
        container.answer_service,
        container.request_resolver,
        container.current_tariff_service,
        container.tariff_history_service,
        structured_query_service=container.structured_query_service,
        answer_router=container.answer_router,
        monitoring_node=container.monitoring_node,
        runs=container.runs,
        reviews=container.reviews,
    )
    runner = Runner(
        app=agent_app,
        session_service=session_service,
        artifact_service=services.get_artifact_service(),
    )
    session = ChatSession(
        runner=runner,
        sessions=session_service,
        app_name=agent_app.name,
        user_id=user_id,
        session_id=session_name,
        owner=owner,
        runs=container.runs,
        renderer=ProgressRenderer(verbose=verbose),
        displays=getattr(container, "review_display", None),
    )
    loop = asyncio.get_running_loop()
    main_task = asyncio.current_task()
    if main_task is not None:
        loop.add_signal_handler(signal.SIGINT, session.interrupt, main_task)
    try:
        heading = f'Ameria Tariff Chat · conversation "{session_name}"'
        hint = "Type quit to exit. Ctrl-C cancels a running turn."
        if new:
            hint = (
                f'This is a new conversation; reopen it with --session "{session_name}".\n'
                + hint
            )
        console.print(
            Panel(
                Text(hint), title=Text(heading, style="bold cyan"), border_style="cyan"
            )
        )
        try:
            await session.open()
        except APIError as exc:
            _print_api_error(exc)
        except EOFError:
            return
        except Exception as exc:
            _print_unexpected_error(exc, "Reopening the conversation", session_name)
        while True:
            prompt = (await _ainput("[bold cyan]You[/] [cyan]>[/] ")).strip()
            if prompt.lower() in {"exit", "quit"}:
                return
            if not prompt:
                continue
            try:
                await session.converse(prompt)
            except APIError as exc:
                _print_api_error(exc)
            except EOFError:
                return
            except Exception as exc:
                _print_unexpected_error(exc, "This turn", session_name)
    finally:
        loop.remove_signal_handler(signal.SIGINT)
        session.renderer.stop()
        configure_services(None, None)
        await container.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Durable Ameria tariff ADK chat")
    parser.add_argument(
        "--user",
        "--user-id",
        dest="user",
        default="cli-user",
        help="whose conversations to open (default: cli-user)",
    )
    parser.add_argument(
        "--session",
        "--session-id",
        dest="session",
        default="default",
        help='conversation name to open or continue (default: "default")',
    )
    parser.add_argument(
        "--new",
        action="store_true",
        help="start a new conversation named after the current time",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="also show tool calls and run ids",
    )
    args = parser.parse_args()
    session_name = (
        datetime.now(UTC).strftime("%Y-%m-%d-%H%M%S") if args.new else args.session
    )
    try:
        asyncio.run(chat(args.user, session_name, verbose=args.verbose, new=args.new))
    except (KeyboardInterrupt, EOFError, asyncio.CancelledError):
        # Ctrl-C at the prompt cancels the chat itself: a normal way out.
        console.print()


if __name__ == "__main__":
    main()
