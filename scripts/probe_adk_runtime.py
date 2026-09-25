"""Re-demonstrate the ADK behaviours the monitoring runtime relies on.

Plan §5 lists them (E1-E9); this script shows the four that shape the design,
against the installed google-adk, with a scripted model and no credentials:

- E1  a node run inside a tool streams partial progress events that are not
      persisted;
- E2  a `RequestInput` yielded by the node pauses the invocation without a
      model call;
- E3/E5  answering the pause replays the *original* tool call; the node re-runs
      with every answer so far in `ctx.resume_inputs`;
- E8/E9  cancelling the consumer raises `CancelledError` inside the node, and
      `Runner.rewind_async` leaves a clean context for the next turn.

Run with: uv run python scripts/probe_adk_runtime.py
"""

from __future__ import annotations

import asyncio
import logging

from google.adk.agents import Agent
from google.adk.apps import App, ResumabilityConfig
from google.adk.events import Event
from google.adk.events.request_input import RequestInput
from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_response import LlmResponse
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools import ToolContext
from google.adk.workflow import FunctionNode
from google.genai import types
from pydantic import PrivateAttr

APP, USER, SESSION = "probe", "u", "s"
node_runs = 0
cancelled_inside_node = False


class ScriptedModel(BaseLlm):
    _script: list = PrivateAttr(default_factory=list)
    _calls: int = PrivateAttr(default=0)

    async def generate_content_async(self, llm_request, stream=False):
        self._calls += 1
        part = self._script.pop(0) if self._script else types.Part(text="answer")
        yield LlmResponse(content=types.Content(role="model", parts=[part]))


async def monitoring(ctx, offering: str, block: bool = False):
    global node_runs, cancelled_inside_node
    node_runs += 1
    resume = dict(ctx.resume_inputs or {})
    if not resume:
        for stage in ("acquisition", "normalization", "semantic_extraction"):
            yield Event(  # E1: streamed to the caller, never persisted
                content=types.Content(
                    role="model", parts=[types.Part(text=f"stage {stage}")]
                ),
                partial=True,
            )
            try:
                await asyncio.sleep(10 if block else 0.01)
            except asyncio.CancelledError:
                cancelled_inside_node = True  # E8
                raise
    for review_id in ("review-1", "review-2"):  # E5: one pause per review
        if review_id not in resume:
            yield RequestInput(
                interrupt_id=review_id,
                message=f"Decide {review_id}",
                payload={"review_id": review_id},
                response_schema={"type": "object"},
            )
            return  # E6: always return after a RequestInput
    yield {"status": "succeeded", "decisions": resume}


node = FunctionNode(
    func=monitoring,
    name="monitoring",
    rerun_on_resume=True,
    parameter_binding="node_input",
)


async def run_tariff_monitoring(
    offering: str, tool_context: ToolContext, block: bool = False
) -> dict:
    """Run tariff monitoring for one offering."""
    return await tool_context.run_node(node, {"offering": offering, "block": block})


def text(value: str) -> types.Content:
    return types.Content(role="user", parts=[types.Part(text=value)])


def reply(interrupt_id: str, payload: dict) -> types.Content:
    return types.Content(
        role="user",
        parts=[
            types.Part(
                function_response=types.FunctionResponse(
                    id=interrupt_id,
                    name="adk_request_input",
                    response={"result": payload},
                )
            )
        ],
    )


def monitor_call(block: bool = False) -> types.Part:
    return types.Part(
        function_call=types.FunctionCall(
            name="run_tariff_monitoring", args={"offering": "overdraft", "block": block}
        )
    )


async def main() -> None:
    logging.disable(logging.WARNING)  # ADK's experimental notices
    model = ScriptedModel(model="scripted")
    app = App(
        name=APP,
        root_agent=Agent(name="root", model=model, tools=[run_tariff_monitoring]),
        resumability_config=ResumabilityConfig(is_resumable=True),  # required (E4)
    )
    sessions = InMemorySessionService()
    await sessions.create_session(app_name=APP, user_id=USER, session_id=SESSION)
    runner = Runner(app=app, session_service=sessions)

    def turn(message):
        return runner.run_async(user_id=USER, session_id=SESSION, new_message=message)

    async def persisted():
        session = await sessions.get_session(
            app_name=APP, user_id=USER, session_id=SESSION
        )
        return session.events

    print("== Turn 1: monitor (E1, E2)")
    model._script = [monitor_call()]
    streamed = 0
    async for event in turn(text("monitor overdraft")):
        if event.partial:
            streamed += 1
        if event.long_running_tool_ids:
            print(f"   paused on {sorted(event.long_running_tool_ids)}")
    print(f"   {streamed} progress events streamed; model calls so far: {model._calls}")
    stored = [event for event in await persisted() if event.partial]
    print(f"   progress events persisted: {len(stored)}")

    print("== Turns 2-3: answer both reviews (E3, E5)")
    async for _ in turn(reply("review-1", {"decision_type": "approve"})):
        pass
    final = []
    async for event in turn(reply("review-2", {"decision_type": "reject_all"})):
        final.append(event)
    outputs = [event.output for event in final if event.output is not None]
    print(f"   node ran {node_runs} times for 2 reviews; result: {outputs[-1]}")
    print(f"   model calls: {model._calls} (one to choose the tool, one to answer)")

    print("== Turn 4: cancel mid-run, then rewind (E8, E9)")
    model._script = [monitor_call(block=True)]
    invocation: list[str] = []

    async def consume():
        async for event in turn(text("monitor again")):
            invocation.append(event.invocation_id)

    task = asyncio.create_task(consume())
    await asyncio.sleep(0.2)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    print(f"   CancelledError raised inside the node: {cancelled_inside_node}")
    await runner.rewind_async(
        user_id=USER, session_id=SESSION, rewind_before_invocation_id=invocation[0]
    )
    async for _ in turn(text("hello")):
        pass
    print("   rewound; the next turn started a clean invocation")


if __name__ == "__main__":
    asyncio.run(main())
