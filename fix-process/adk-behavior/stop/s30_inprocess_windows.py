"""S30: in-process cancellation checks the real CLI cannot show from outside.

Builds exactly what `app.cli.chat()` builds (container, Runner, ChatSession)
and cancels `ChatSession.converse` the way the CLI's SIGINT handling does.

X01  Cancel between `RunService.submit` and `RunRepository.claim`.
X02  Cancel after `claim` committed, before the pipeline task starts.
     (Both windows are milliseconds wide in production; each is widened
     here with a 2 s sleep inside the real call to hit it on purpose.)
X03  Cancel while source discovery's model calls are in flight, then list
     every asyncio task and thread still alive in the process.

Usage: s30_inprocess_windows.py [scenario ...]
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from common import OUT, ROOT, FakeGeminiProcess, app_env, log, reset_db, run_rows  # noqa: E402

os.environ.update(app_env(OUT / "s30.app.log"))
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))

from google.adk.runners import Runner  # noqa: E402

from app import cli  # noqa: E402
from app.agent import app as agent_app  # noqa: E402
from app.app_utils import services  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.runtime import build_application_container  # noqa: E402
from app.tools import configure_services  # noqa: E402

KEEP_ACQUISITION = ("acquisition_snapshots", "acquisition_baselines")
MONITOR = "run monitoring for overdraft"


async def open_session(name: str):
    settings = get_settings()
    owner = cli.process_owner()
    container = build_application_container(settings, monitoring_owner=owner)
    session_service = await services.ensure_session_service_ready()
    configure_services(
        request_resolver=container.request_resolver,
        current_tariff_service=container.current_tariff_service,
        tariff_history_service=container.tariff_history_service,
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
    session = cli.ChatSession(
        runner=runner,
        sessions=session_service,
        app_name=agent_app.name,
        user_id="cli-user",
        session_id=f"stop-{name}-{int(time.time())}",
        owner=owner,
        runs=container.runs,
    )
    await session.open()
    return container, session


async def cancel_turn(turn: asyncio.Task) -> None:
    """What the CLI does on Ctrl-C: cancel the running `converse`."""
    turn.cancel()
    await turn  # converse absorbs the cancellation


def inventory() -> dict:
    current = asyncio.current_task()
    return {
        "asyncio_tasks": sorted(
            repr(task.get_coro())[:120]
            for task in asyncio.all_tasks()
            if task is not current
        ),
        "threads": sorted(
            f"{thread.name} daemon={thread.daemon}"
            for thread in threading.enumerate()
            if thread is not threading.main_thread()
        ),
    }


async def x01_submit_claim_window() -> dict:
    name = "x01_submit_claim_window"
    await reset_db(keep=KEEP_ACQUISITION)
    with FakeGeminiProcess(name):
        container, session = await open_session(name)
        submitted = asyncio.Event()
        real_submit = container.run_service.submit

        async def slow_submit(command, **kwargs):
            result = await real_submit(command, **kwargs)
            submitted.set()
            await asyncio.sleep(2)  # widen the window
            return result

        container.run_service.submit = slow_submit
        try:
            turn = asyncio.create_task(session.converse(MONITOR))
            await asyncio.wait_for(submitted.wait(), 60)
            await cancel_turn(turn)
            await asyncio.sleep(3)
            return {"scenario": name, "runs_after_cancel": await run_rows()}
        finally:
            await container.close()


async def x02_claim_execute_window() -> dict:
    name = "x02_claim_execute_window"
    await reset_db(keep=KEEP_ACQUISITION)
    with FakeGeminiProcess(name) as fake:
        container, session = await open_session(name)
        claimed = asyncio.Event()
        real_claim = container.runs.claim

        async def slow_claim(run_id, owner):
            result = await real_claim(run_id, owner)
            claimed.set()
            await asyncio.sleep(2)  # widen the window
            return result

        container.runs.claim = slow_claim
        try:
            turn = asyncio.create_task(session.converse(MONITOR))
            await asyncio.wait_for(claimed.wait(), 60)
            await cancel_turn(turn)
            await asyncio.sleep(3)
            after_cancel = await run_rows()
            # The same user asks again in the same conversation.
            container.runs.claim = real_claim
            began = time.time()
            again = asyncio.create_task(session.converse(MONITOR))
            await asyncio.sleep(12)
            second_turn_done = again.done()
            if not second_turn_done:
                await cancel_turn(again)
            return {
                "scenario": name,
                "runs_after_cancel": after_cancel,
                "second_request_finished_within_12s": second_turn_done,
                "model_requests_during_second_request": [
                    item["role"] for item in fake.requests(after=began)
                ],
                "runs_at_end": await run_rows(),
            }
        finally:
            await container.close()


async def x03_leftovers_after_cancel() -> dict:
    name = "x03_leftovers_after_cancel"
    await reset_db(keep=KEEP_ACQUISITION)
    role = "source_discovery_classifier"
    with FakeGeminiProcess(name) as fake:
        fake.configure(hold=[role])
        container, session = await open_session(name)
        try:
            before = inventory()
            began = time.time()
            turn = asyncio.create_task(session.converse(MONITOR))
            while not fake.requests(role, after=began):
                await asyncio.sleep(0.1)
            await asyncio.sleep(1.0)
            during = inventory()
            pressed = time.time()
            await cancel_turn(turn)
            await asyncio.sleep(3)
            after = inventory()
            return {
                "scenario": name,
                "tasks_before_turn": before["asyncio_tasks"],
                "task_count_during_step": len(during["asyncio_tasks"]),
                "tasks_3s_after_cancel": after["asyncio_tasks"],
                "threads_before_turn": before["threads"],
                "threads_3s_after_cancel": after["threads"],
                "held_requests_disconnected": [
                    item["id"] for item in fake.events() if item["event"] == "disconnect"
                ],
                "requests_after_cancel": [
                    item["role"] for item in fake.requests(after=pressed + 0.3)
                ],
                "runs": await run_rows(),
            }
        finally:
            await container.close()


SCENARIOS = {
    "x01_submit_claim_window": x01_submit_claim_window,
    "x02_claim_execute_window": x02_claim_execute_window,
    "x03_leftovers_after_cancel": x03_leftovers_after_cancel,
}


async def main(names: list[str]) -> None:
    for name in names or list(SCENARIOS):
        log(f"=== {name}")
        try:
            result = await SCENARIOS[name]()
        except Exception as exc:
            result = {"scenario": name, "harness_error": f"{type(exc).__name__}: {exc}"}
        (OUT / f"{name}.result.json").write_text(json.dumps(result, indent=2, default=str))
        log(json.dumps(result, indent=1, default=str)[:4000])


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1:]))
