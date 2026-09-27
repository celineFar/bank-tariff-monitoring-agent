"""S10: Ctrl-C in the real CLI at each step of a chat-run monitoring turn.

For each scenario: start the real CLI in a pty against the fake Gemini, get
the turn to one step (holding that step's model request open where the step
calls Gemini), press Ctrl-C, then watch for a while:

- the fake Gemini: did the held request disconnect, did any request arrive
  after the Ctrl-C;
- PostgreSQL: how the run and its offering execution were closed;
- the process: still alive at the prompt, children, CPU used while idle.

Usage: s10_cli_stop.py [scenario ...]   (default: all)
"""

from __future__ import annotations

import asyncio
import json
import sys
import time

from cli_driver import CliProcess
from common import (
    OUT,
    FakeGeminiProcess,
    alive,
    cpu_seconds,
    descendants,
    kill_tree,
    log,
    reset_db,
    run_rows,
)

MONITOR = "run monitoring for overdraft"
CANCEL_NOTICE = r"Monitoring cancelled\.|Cancelled\.|Review postponed"
KEEP_ACQUISITION = ("acquisition_snapshots", "acquisition_baselines")


async def observe(cli: CliProcess, fake: FakeGeminiProcess, pressed: float, window: float):
    cpu_before = cpu_seconds(cli.pid) if alive(cli.pid) else None
    time.sleep(window)
    cpu_after = cpu_seconds(cli.pid) if alive(cli.pid) else None
    events = fake.events()
    return {
        "requests_after_ctrl_c": [
            item for item in events if item["event"] == "request" and item["t"] > pressed + 0.3
        ],
        "disconnects": [item for item in events if item["event"] == "disconnect"],
        "held_open_at_end": _held_open(events),
        "runs": await run_rows(),
        "cli_alive": alive(cli.pid),
        "children": descendants(cli.pid) if alive(cli.pid) else [],
        "idle_cpu_s": (
            round(cpu_after - cpu_before, 2)
            if cpu_before is not None and cpu_after is not None
            else None
        ),
    }


def _held_open(events: list[dict]) -> list[dict]:
    finished = {item["id"] for item in events if item["event"] != "request"}
    return [item for item in events if item["event"] == "request" and item["id"] not in finished]


def start(name: str) -> CliProcess:
    cli = CliProcess(f"stop-{name}-{int(time.time())}", OUT / f"{name}.cli.log")
    cli.expect(r"You >", 90)
    return cli


def finish(cli: CliProcess) -> None:
    if alive(cli.pid):
        cli.send("quit")
        if not cli.wait_exit(20):
            kill_tree(cli.pid)


async def held_step(name: str, role: str, *, window: float = 10.0, **config) -> dict:
    """Hold `role`'s request open, Ctrl-C while it is in flight."""
    await reset_db(keep=KEEP_ACQUISITION)
    with FakeGeminiProcess(name) as fake:
        fake.configure(hold=[role], **config)
        cli = start(name)
        try:
            began = time.time()
            cli.send(MONITOR)
            request = fake.wait_for(role, timeout=180, after=began)
            time.sleep(1.0)  # let every concurrent request of the step arrive
            in_flight = _held_open(fake.events())
            mark = cli.mark()
            pressed = cli.ctrl_c()
            notice = cli.expect(CANCEL_NOTICE, 30, since=mark)
            cli.expect(r"You >", 30, since=mark)
            result = await observe(cli, fake, pressed, window)
            result.update(
                scenario=name,
                step=role,
                in_flight_at_ctrl_c=len(in_flight),
                first_request_id=request["id"],
                notice=notice,
                cancel_to_prompt_s=round(time.time() - pressed - window, 2),
            )
            return result
        finally:
            finish(cli)


async def c01_root_agent() -> dict:
    return await held_step("c01_root_agent", "ameria_tariff_monitor")


async def c02_acquisition() -> dict:
    """Real network fetch in flight (no model call in this step)."""
    name = "c02_acquisition"
    await reset_db()  # no reusable acquisition: force a real fetch
    with FakeGeminiProcess(name) as fake:
        cli = start(name)
        try:
            mark = cli.mark()
            cli.send(MONITOR)
            cli.expect(r"Acquiring web content", 60, since=mark)
            time.sleep(2.0)
            children_at_press = descendants(cli.pid)
            mark = cli.mark()
            pressed = cli.ctrl_c()
            notice = cli.expect(CANCEL_NOTICE, 30, since=mark)
            result = await observe(cli, fake, pressed, 10.0)
            result.update(
                scenario=name,
                step="acquisition",
                notice=notice,
                children_at_ctrl_c=children_at_press,
            )
            return result
        finally:
            finish(cli)


async def c03_pdf_selection() -> dict:
    return await held_step("c03_pdf_selection", "pdf_link_selector")


async def c04_pdf_transcription() -> dict:
    return await held_step(
        "c04_pdf_transcription", "pdf_document_extractor", pdf_links="include"
    )


async def c05_source_discovery() -> dict:
    return await held_step("c05_source_discovery", "source_discovery_classifier")


async def c06_semantic_extraction() -> dict:
    return await held_step("c06_semantic_extraction", "semantic_loan_extractor")


async def c07_retry_backoff() -> dict:
    """Extraction answers 503: Ctrl-C while the retry loop sleeps."""
    name = "c07_retry_backoff"
    await reset_db(keep=KEEP_ACQUISITION)
    with FakeGeminiProcess(name) as fake:
        fake.configure(fail={"semantic_loan_extractor": 503})
        cli = start(name)
        try:
            began = time.time()
            cli.send(MONITOR)
            fake.wait_for("semantic_loan_extractor", timeout=180, after=began)
            time.sleep(1.0)  # the 503s are answered; the loop is in its backoff
            mark = cli.mark()
            pressed = cli.ctrl_c()
            notice = cli.expect(CANCEL_NOTICE, 30, since=mark)
            # Longer than the largest backoff (60 s max, 5 s base doubling).
            result = await observe(cli, fake, pressed, 75.0)
            result.update(scenario=name, step="semantic_extraction backoff", notice=notice)
            return result
        finally:
            finish(cli)


async def c08_review_prompt() -> dict:
    name = "c08_review_prompt"
    await reset_db(keep=KEEP_ACQUISITION)
    with FakeGeminiProcess(name) as fake:
        cli = start(name)
        try:
            mark = cli.mark()
            cli.send(MONITOR)
            cli.expect(r"Review 1/", 180, since=mark)
            time.sleep(1.0)
            mark = cli.mark()
            pressed = cli.ctrl_c()
            notice = cli.expect(CANCEL_NOTICE, 30, since=mark)
            result = await observe(cli, fake, pressed, 10.0)
            result.update(scenario=name, step="review prompt", notice=notice)
            return result
        finally:
            finish(cli)


async def c11_second_ctrl_c() -> dict:
    """Two turns in one CLI process, each cancelled with one Ctrl-C."""
    return await _repeated_ctrl_c("c11_second_ctrl_c", 2)


async def c13_third_ctrl_c() -> dict:
    """Three turns in one CLI process, each cancelled with one Ctrl-C."""
    return await _repeated_ctrl_c("c13_third_ctrl_c", 3)


async def _repeated_ctrl_c(name: str, turn_count: int) -> dict:
    await reset_db(keep=KEEP_ACQUISITION)
    role = "source_discovery_classifier"
    with FakeGeminiProcess(name) as fake:
        fake.configure(hold=[role])
        cli = start(name)
        try:
            turns = []
            for turn in range(1, turn_count + 1):
                began = time.time()
                mark = cli.mark()
                cli.send(MONITOR)
                fake.wait_for(role, timeout=180, after=began)
                time.sleep(1.0)
                pressed = cli.ctrl_c()
                try:
                    notice = cli.expect(CANCEL_NOTICE, 20, since=mark)
                except TimeoutError:
                    notice = None
                time.sleep(3.0)
                turns.append(
                    {
                        "turn": turn,
                        "notice": notice,
                        "cli_alive": alive(cli.pid),
                        "output_after_ctrl_c": cli.since(mark)[-600:],
                        "pressed": pressed,
                    }
                )
                if not alive(cli.pid):
                    break
            result = await observe(cli, fake, turns[-1]["pressed"], 10.0)
            result.update(scenario=name, step="second turn", turns=turns)
            return result
        finally:
            finish(cli)


async def c12_double_ctrl_c() -> dict:
    """Two quick presses in the first turn (an impatient user)."""
    name = "c12_double_ctrl_c"
    await reset_db(keep=KEEP_ACQUISITION)
    role = "semantic_loan_extractor"
    with FakeGeminiProcess(name) as fake:
        fake.configure(hold=[role])
        cli = start(name)
        try:
            began = time.time()
            mark = cli.mark()
            cli.send(MONITOR)
            fake.wait_for(role, timeout=180, after=began)
            time.sleep(1.0)
            pressed = cli.ctrl_c()
            time.sleep(0.05)
            cli.ctrl_c()
            time.sleep(5.0)
            result = await observe(cli, fake, pressed, 10.0)
            result.update(
                scenario=name,
                step="semantic_extraction, two presses 50 ms apart",
                output_after_ctrl_c=cli.since(mark)[-800:],
            )
            return result
        finally:
            finish(cli)


SCENARIOS = {
    name: function
    for name, function in globals().items()
    if name[:1] == "c" and name[1:3].isdigit() and callable(function)
}


async def main(names: list[str]) -> None:
    for name in names or list(SCENARIOS):
        log(f"=== {name}")
        try:
            result = await SCENARIOS[name]()
        except Exception as exc:  # keep going; record the failure
            result = {"scenario": name, "harness_error": f"{type(exc).__name__}: {exc}"}
        (OUT / f"{name}.result.json").write_text(json.dumps(result, indent=2, default=str))
        log(json.dumps(result, indent=1, default=str)[:3000])


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1:]))
