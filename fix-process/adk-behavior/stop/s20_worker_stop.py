"""S20: stopping the worker (`python -m app.worker`), and a chat following it.

W01  SIGTERM while the worker executes a run: does the run stop, or does it
     keep calling the model until it finishes?
W02  SIGTERM while idle: prompt exit (control).
W03  `docker stop` semantics: SIGTERM, then SIGKILL after 10 s. What state is
     the run left in, and does a restarted worker close it?
C15  A chat asks to monitor while the worker owns the run (it follows the
     run); the user presses Ctrl-C. Does the worker's run stop?

Usage: s20_worker_stop.py [scenario ...]
"""

from __future__ import annotations

import asyncio
import json
import os
import signal
import subprocess
import sys
import time

from cli_driver import CliProcess
from common import (
    DB_URL,
    OUT,
    PYTHON,
    ROOT,
    FakeGeminiProcess,
    alive,
    app_env,
    kill_tree,
    log,
    reset_db,
    run_rows,
)

KEEP_ACQUISITION = ("acquisition_snapshots", "acquisition_baselines")
HELD = "source_discovery_classifier"


async def submit_api_run() -> str:
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.domain.models import OfferingId, ProductType
    from app.domain.monitoring import RunCommand, RunTrigger
    from app.repositories.monitoring import PostgresRunRepository
    from app.services.run_service import RunService

    engine = create_async_engine(DB_URL)
    try:
        service = RunService(PostgresRunRepository(async_sessionmaker(engine)))
        result = await service.submit(
            RunCommand(
                product=ProductType.CONSUMER_LOAN,
                offering_id=OfferingId.OVERDRAFT,
                trigger=RunTrigger.API,
            )
        )
        return str(result.run.id)
    finally:
        await engine.dispose()


def start_worker(name: str) -> subprocess.Popen:
    return subprocess.Popen(
        [PYTHON, "-m", "app.worker"],
        cwd=ROOT,
        env=app_env(OUT / f"{name}.worker.log"),
        stdout=(OUT / f"{name}.worker.stdout").open("w"),
        stderr=subprocess.STDOUT,
    )


def wait_exit(process: subprocess.Popen, timeout: float) -> float | None:
    started = time.time()
    try:
        process.wait(timeout)
    except subprocess.TimeoutExpired:
        return None
    return round(time.time() - started, 2)


def requests_after(fake: FakeGeminiProcess, moment: float) -> list[dict]:
    return [
        {"role": item["role"], "t_after_s": round(item["t"] - moment, 2)}
        for item in fake.events()
        if item["event"] == "request" and item["t"] > moment
    ]


async def w01_sigterm_mid_run() -> dict:
    name = "w01_sigterm_mid_run"
    await reset_db(keep=KEEP_ACQUISITION)
    with FakeGeminiProcess(name) as fake:
        fake.configure(hold=[HELD])
        worker = start_worker(name)
        try:
            time.sleep(3)
            began = time.time()
            run_id = await submit_api_run()
            fake.wait_for(HELD, timeout=180, after=began)
            time.sleep(1.0)
            sent = time.time()
            worker.send_signal(signal.SIGTERM)
            exited_while_held = wait_exit(worker, 15)
            state_while_held = await run_rows()
            disconnects = [e for e in fake.events() if e["event"] == "disconnect"]
            # Let the model answer again: what does a SIGTERMed worker do next?
            fake.configure()
            exited_after_release = (
                exited_while_held if exited_while_held is not None else wait_exit(worker, 60)
            )
            return {
                "scenario": name,
                "run_id": run_id,
                "exit_s_after_sigterm_while_model_call_held": exited_while_held,
                "disconnects_while_held": disconnects,
                "run_state_15s_after_sigterm": state_while_held,
                "exit_s_after_release": exited_after_release,
                "model_requests_after_sigterm": requests_after(fake, sent + 0.3),
                "run_state_at_end": await run_rows(),
            }
        finally:
            if worker.poll() is None:
                kill_tree(worker.pid)


async def w02_sigterm_idle() -> dict:
    name = "w02_sigterm_idle"
    await reset_db(keep=KEEP_ACQUISITION)
    with FakeGeminiProcess(name):
        worker = start_worker(name)
        try:
            time.sleep(4)
            worker.send_signal(signal.SIGTERM)
            return {"scenario": name, "exit_s_after_sigterm": wait_exit(worker, 20)}
        finally:
            if worker.poll() is None:
                kill_tree(worker.pid)


async def w03_docker_stop() -> dict:
    name = "w03_docker_stop"
    await reset_db(keep=KEEP_ACQUISITION)
    with FakeGeminiProcess(name) as fake:
        fake.configure(hold=[HELD])
        worker = start_worker(name)
        restarted = None
        try:
            time.sleep(3)
            began = time.time()
            await submit_api_run()
            fake.wait_for(HELD, timeout=180, after=began)
            time.sleep(1.0)
            worker.send_signal(signal.SIGTERM)
            graceful = wait_exit(worker, 10)
            if graceful is None:
                worker.send_signal(signal.SIGKILL)
                worker.wait(10)
            after_kill = await run_rows()
            restarted = start_worker(name + "_restart")
            time.sleep(8)
            after_restart = await run_rows()
            return {
                "scenario": name,
                "exited_within_docker_grace_s": graceful,
                "run_state_after_sigkill": after_kill,
                "run_state_after_worker_restart": after_restart,
            }
        finally:
            for process in (worker, restarted):
                if process is not None and process.poll() is None:
                    kill_tree(process.pid)


async def c15_ctrl_c_while_following() -> dict:
    name = "c15_ctrl_c_while_following"
    await reset_db(keep=KEEP_ACQUISITION)
    with FakeGeminiProcess(name) as fake:
        fake.configure(hold=[HELD])
        worker = start_worker(name)
        cli = None
        try:
            time.sleep(3)
            began = time.time()
            await submit_api_run()
            fake.wait_for(HELD, timeout=180, after=began)
            cli = CliProcess(f"stop-{name}-{int(time.time())}", OUT / f"{name}.cli.log")
            cli.expect(r"You >", 90)
            mark = cli.mark()
            cli.send("run monitoring for overdraft")
            cli.expect(r"following it|already in progress", 60, since=mark)
            time.sleep(2)
            mark = cli.mark()
            pressed = cli.ctrl_c()
            time.sleep(3)
            chat_output = cli.since(mark)
            held_still_open = not any(
                e["event"] == "disconnect" and e["t"] > pressed for e in fake.events()
            )
            runs_after = await run_rows()
            fake.configure()  # release: does the worker's run carry on?
            time.sleep(20)
            return {
                "scenario": name,
                "chat_said": chat_output[-400:],
                "worker_request_still_open_after_ctrl_c": held_still_open,
                "run_state_3s_after_ctrl_c": runs_after,
                "model_requests_after_ctrl_c": requests_after(fake, pressed + 0.3),
                "run_state_at_end": await run_rows(),
            }
        finally:
            if cli is not None and alive(cli.pid):
                kill_tree(cli.pid)
            if worker.poll() is None:
                kill_tree(worker.pid)


SCENARIOS = {
    "w01_sigterm_mid_run": w01_sigterm_mid_run,
    "w02_sigterm_idle": w02_sigterm_idle,
    "w03_docker_stop": w03_docker_stop,
    "c15_ctrl_c_while_following": c15_ctrl_c_while_following,
}


async def main(names: list[str]) -> None:
    sys.path.insert(0, str(ROOT))
    os.chdir(ROOT)
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
