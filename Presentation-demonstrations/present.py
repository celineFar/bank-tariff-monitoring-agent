#!/usr/bin/env python3
"""Every demonstration, in the order they must run, asking before each one.

    python3 present.py            # set up, then each demonstration in order
    python3 present.py --check    # what setup would do; changes nothing
    python3 present.py --list     # the demonstrations and their order
    python3 present.py --from failures
    python3 present.py --only change --only ocr
    python3 present.py --yes      # don't ask between demonstrations (rehearsal)

Setup is automatic: it builds the images if they are missing, starts the demo
stack, clears whatever an interrupted demonstration left behind, runs the
change demonstration's one-time setup if it has none, and puts the demo
database back to the real-bank checkpoint. Before each demonstration it asks
whether to start it, skip it, or stop.

The only other thing asked of you is the review in the change demonstration,
which is the point of it: the chat opens in this terminal at the right moment.

Why this order:

1. Normal extraction    publishes the bank's real Overdraft tariff.
2. Controlled failures  needs an accepted tariff, and shows it untouched.
3. Change and review    restores its own checkpoint (erasing 1 and 2 from the
                        database) and, once approved, leaves a synthetic +4
                        point rate as current. Anything that reads the tariff
                        afterwards sees that rate; a normal extraction would
                        compare the live 21% against it and stop for review.
4. OCR fallback         needs no database; it can run at any point.

Standard library only. Run it from an interactive terminal.
"""

from __future__ import annotations

import argparse
import os
import shutil
import signal
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "demo-stack"))

import stack  # noqa: E402

BANK_CHECKPOINT = "bank-baseline"
CHANGE = HERE / "Change-detection-and-review"
CHANGE_CHECKPOINT = "change-demo"
MIRROR_OVERLAY = CHANGE / "mirror.yml"
IMAGES = ("second-monitor-api:latest", "second-monitor-worker:latest")
TRUST_VOLUMES = ("demo_trust", "demo_nssdb")
MIRROR_HOST = "tariff-mirror.demo"
# Lines the change demonstration prints when a review is waiting for a person.
REVIEW_CUES = ("Waiting for the decision", "The run is waiting for a review")


@dataclass(frozen=True)
class Demo:
    key: str
    title: str
    deliverable: str
    folder: str
    commands: tuple[tuple[str, ...], ...]
    cost: str
    outputs: tuple[str, ...]
    review: bool = False

    @property
    def cwd(self) -> Path:
        return HERE / self.folder


DEMOS = (
    Demo(
        "extraction",
        "Normal tariff extraction",
        "9",
        "Normal-extraction",
        (("python3", "extraction_demo.py", "--cold"),),
        "about 90 s, about $0.13 (every model call live)",
        (
            "output/overdraft/card.md",
            "output/overdraft/report.md",
            "pipeline-audit/  (newest run_* folder: 4_extraction_evidence.md)",
        ),
    ),
    Demo(
        "failures",
        "Controlled failures",
        "13",
        "Controlled-failures",
        (("python3", "failure_demo.py"),),
        "about 2 min (the timeout takes a minute), $0",
        ("failures/*.yml", "output/report.md"),
    ),
    Demo(
        "change",
        "Tariff change detection and human review",
        "10 and 12",
        "Change-detection-and-review",
        (("python3", "change_demo.py"),),
        "about 2 min plus your review, about $0.08",
        ("output/report.md",),
        review=True,
    ),
    Demo(
        "ocr",
        "OCR fallback",
        "11",
        "OCR-fallback",
        (("./run.sh",), ("./run.sh", "score.py")),
        "about 30 s, $0 (offline; the Gemini comparison is already saved)",
        (
            "samples/mortgage-tariffs.pdf",
            "output/mortgage-tariffs.ocr.md",
            "output/comparison.md",
        ),
    ),
)


def step(text: str) -> None:
    print(f"\n\033[1m==> {text}\033[0m", flush=True)


def note(text: str) -> None:
    print(f"    {text}", flush=True)


def banner(text: str) -> None:
    line = "=" * max(60, len(text) + 4)
    print(f"\n\033[1;36m{line}\n  {text}\n{line}\033[0m", flush=True)


# --------------------------------------------------------------------------
# setup


def run_quiet(*command: str, cwd: Path = stack.REPO) -> subprocess.CompletedProcess:
    return subprocess.run(command, cwd=cwd, capture_output=True, text=True)


def missing_images() -> list[str]:
    return [
        image
        for image in IMAGES
        if run_quiet("docker", "image", "inspect", image).returncode != 0
    ]


def stack_is_up() -> bool:
    try:
        stack.api("GET", "/healthz")
        return True
    except (stack.StackError, OSError):
        return False


def worker_overlays() -> list[str]:
    """Compose files the demo worker runs with, beyond the normal two."""
    container = stack.compose("ps", "-q", "worker", capture=True).stdout.strip()
    if not container:
        return []
    label = run_quiet(
        "docker",
        "inspect",
        container,
        "--format",
        '{{index .Config.Labels "com.docker.compose.project.config_files"}}',
    ).stdout.strip()
    normal = {str(stack.REPO / "docker-compose.yml"), str(stack.OVERLAY)}
    return [path for path in label.split(",") if path and path not in normal]


def mirror_running() -> bool:
    return bool(
        run_quiet(
            "docker",
            "ps",
            "-q",
            "--filter",
            f"label=com.docker.compose.project={stack.PROJECT}",
            "--filter",
            "label=com.docker.compose.service=mirror",
        ).stdout.strip()
    )


def change_setup_missing() -> list[str]:
    """What the change demonstration's one-time setup would have to create."""
    missing = []
    if not (stack.CHECKPOINTS / f"{CHANGE_CHECKPOINT}.dump").exists():
        missing.append(f"checkpoint '{CHANGE_CHECKPOINT}'")
    if not (CHANGE / "runtime" / "certs" / f"{MIRROR_HOST}.pem").exists():
        missing.append("mirror certificate")
    volumes = run_quiet("docker", "volume", "ls", "-q").stdout.split()
    for volume in TRUST_VOLUMES:
        if f"{stack.PROJECT}_{volume}" not in volumes:
            missing.append(f"volume {stack.PROJECT}_{volume}")
    return missing


def state_is_real_bank() -> tuple[bool, str]:
    """Whether the demo database holds only real-bank Overdraft data."""
    pending = stack.sql(
        "SELECT count(*) AS n FROM human_reviews WHERE decided_at IS NULL"
    )[0]["n"]
    mirrored = stack.sql(
        f"""SELECT count(*) AS n FROM fact_evidence
            WHERE source_url LIKE 'https://{MIRROR_HOST}/%'"""
    )[0]["n"]
    if pending:
        return False, f"{pending} review(s) still open"
    if mirrored:
        return False, "it holds tariff data read from the demonstration mirror"
    return True, "real-bank data only"


def setup(check_only: bool) -> None:
    """Bring the stack to the state the first demonstration expects."""
    step("Setup" + (" (check only: nothing is changed)" if check_only else ""))

    images = missing_images()
    if images:
        note(f"missing images: {', '.join(images)}")
        if not check_only:
            note("building them (docker compose build api worker), a few minutes ...")
            subprocess.run(
                ["docker", "compose", "build", "api", "worker"],
                cwd=stack.REPO,
                check=True,
            )
    else:
        note("images: present (rebuild with `docker compose build api worker` "
             "after changing app/)")  # fmt: skip

    if not (stack.REPO / ".env").exists():
        raise stack.StackError(".env is missing at the repository root")

    if stack_is_up():
        note(f"demo stack: up, API at {stack.API}")
    else:
        note("demo stack: down")
        if check_only:
            note("would start it; the rest of the check needs it running")
            return
        note("starting it ...")
        stack.compose("up", "-d", "--no-build", "db", "api", "worker", capture=True)
        stack.wait_for_api()
        note("demo stack: up")

    busy = stack.active_runs()
    if busy:
        keys = ", ".join(run["idempotency_key"] or run["id"][:8] for run in busy)
        note(f"a run is in progress: {keys}")
        if check_only:
            return
        note("waiting for it to end (Ctrl-C to stop) ...")
        while stack.active_runs():
            time.sleep(5)

    overlays = worker_overlays()
    if overlays:
        names = ", ".join(Path(path).name for path in overlays)
        note(f"worker runs with a leftover overlay: {names}")
        if not check_only:
            stack.restart_worker()
            note("restarted the normal worker")
    if mirror_running():
        note("the change demonstration's mirror is still running")
        if not check_only:
            stack.compose(
                "rm", "-sf", "mirror",
                overlays=(MIRROR_OVERLAY,), capture=True, check=False,
            )  # fmt: skip
            note("stopped it")

    missing = change_setup_missing()
    if missing:
        note(f"change demonstration setup missing: {', '.join(missing)}")
        if not check_only:
            prepare_bank_state(check_only)
            note("running its one-time setup (one real run against the mirror) ...")
            run_demo_command(
                ("python3", "change_demo.py", "setup"), CHANGE, review=True
            )
    else:
        note("change demonstration setup: present")

    prepare_bank_state(check_only)


def prepare_bank_state(check_only: bool) -> None:
    """Put the demo database back to the real-bank checkpoint.

    Without one, the current state becomes it, provided it holds nothing from
    the change demonstration.
    """
    checkpoint = stack.CHECKPOINTS / f"{BANK_CHECKPOINT}.dump"
    if checkpoint.exists():
        if check_only:
            note(f"would restore checkpoint '{BANK_CHECKPOINT}' (real-bank Overdraft)")
            return
        stack.restore_checkpoint(BANK_CHECKPOINT)
        answer = stack.current_tariff("consumer_loan", "overdraft")
        note(
            f"restored checkpoint '{BANK_CHECKPOINT}': Overdraft rates "
            f"{answer['rates']} (snapshot {str(answer['snapshot_id'])[:8]})"
        )
        return
    clean, why = state_is_real_bank()
    if not clean:
        raise stack.StackError(
            f"no '{BANK_CHECKPOINT}' checkpoint, and the demo database is not a "
            f"real-bank state ({why}). Start from an empty database with "
            "`python3 demo-stack/stack.py destroy`, then run this again."
        )
    if check_only:
        note(f"would save the current state as checkpoint '{BANK_CHECKPOINT}'")
        return
    stack.save_checkpoint(BANK_CHECKPOINT)
    note(f"saved the current real-bank state as checkpoint '{BANK_CHECKPOINT}'")


# --------------------------------------------------------------------------
# running a demonstration


class Relay:
    """Copies a child's output to the terminal, and holds it while the chat runs."""

    def __init__(self, process: subprocess.Popen) -> None:
        self.process = process
        self.review_waiting = threading.Event()
        self._holding = False
        self._held: list[str] = []
        self._lock = threading.Lock()
        self._thread = threading.Thread(target=self._pump, daemon=True)
        self._thread.start()

    def _pump(self) -> None:
        assert self.process.stdout is not None
        for line in self.process.stdout:
            with self._lock:
                if self._holding:
                    self._held.append(line)
                else:
                    sys.stdout.write(line)
                    sys.stdout.flush()
            if any(cue in line for cue in REVIEW_CUES):
                self.review_waiting.set()

    def hold(self) -> None:
        with self._lock:
            self._holding = True

    def release(self) -> None:
        with self._lock:
            self._holding = False
            sys.stdout.write("".join(self._held))
            sys.stdout.flush()
            self._held.clear()

    def join(self) -> None:
        self._thread.join()


def pending_reviews() -> int:
    return stack.sql(
        "SELECT count(*) AS n FROM human_reviews WHERE decided_at IS NULL"
    )[0]["n"]


def open_chat() -> None:
    """The chat CLI of the demo stack, in this terminal."""
    banner("Your review: the chat opens now")
    print(
        "    1. Type:   Review the pending candidates\n"
        "    2. Read the candidate, the previous value and the evidence.\n"
        "    3. Type:   approve      (or reject_all to keep the old rate)\n"
        "    4. Type:   quit         to come back here\n",
        flush=True,
    )
    subprocess.run(
        ["python3", str(HERE / "demo-stack" / "stack.py"), "chat"], check=False
    )


def run_demo_command(command: tuple[str, ...], cwd: Path, review: bool) -> int:
    """Run one command of a demonstration; open the chat when a review waits.

    The demonstration never reads the terminal: its `docker compose exec` calls
    would otherwise take keystrokes meant for the chat. Its output reaches the
    terminal directly, or, when a review may come, through a relay that holds
    it while the chat is open.
    """
    process = subprocess.Popen(
        command,
        cwd=cwd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE if review else None,
        stderr=subprocess.STDOUT if review else None,
        text=True,
        env={**os.environ, "PYTHONUNBUFFERED": "1"},
    )
    relay = Relay(process) if review else None
    try:
        while process.poll() is None:
            if relay is None or not relay.review_waiting.wait(timeout=1):
                try:
                    process.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    pass
                continue
            relay.review_waiting.clear()
            # Let the demonstration finish printing its instructions first.
            time.sleep(1)
            relay.hold()
            try:
                open_chat()
                while process.poll() is None and pending_reviews():
                    answer = ask(
                        "The review is still open. Enter reopens the chat, "
                        "a abandons this demonstration: "
                    )
                    if answer == "a":
                        # SIGINT, not SIGTERM: the demonstration's own cleanup
                        # (normal worker back, mirror stopped) runs on it.
                        process.send_signal(signal.SIGINT)
                        break
                    open_chat()
            finally:
                relay.release()
    except KeyboardInterrupt:
        # The demonstration got the same Ctrl-C and is cleaning up; killing it
        # now would leave the worker on its overlay.
        print("\n    Stopping: letting the demonstration put things back ...")
        wait_out(process)
        raise
    finally:
        if relay is not None:
            relay.join()
    return process.returncode


def wait_out(process: subprocess.Popen) -> None:
    while True:
        try:
            process.wait()
            return
        except KeyboardInterrupt:
            continue


def run_demo(demo: Demo) -> str:
    banner(f"Deliverable {demo.deliverable}: {demo.title}")
    started = time.monotonic()
    status = "PASS"
    for command in demo.commands:
        code = run_demo_command(command, demo.cwd, demo.review)
        if code != 0:
            status = f"FAIL (exit {code})"
            break
    elapsed = time.monotonic() - started
    step(f"{demo.title}: {status} in {elapsed:.0f}s. Open, in {demo.folder}/:")
    for output in demo.outputs:
        note(f"- {output}")
    return status


# --------------------------------------------------------------------------


def ask(prompt: str) -> str:
    try:
        return input(f"\033[1;33m{prompt}\033[0m").strip().lower()
    except EOFError:
        return "q"


def confirm(demo: Demo, number: int, total: int) -> str:
    print(
        f"\n\033[1mNext ({number}/{total}): deliverable {demo.deliverable}, "
        f"{demo.title}\033[0m\n    {demo.cost}",
        flush=True,
    )
    while True:
        answer = ask("Enter to start, s to skip, q to stop: ")
        if answer in {"", "s", "q"}:
            return answer
        print("    Type nothing, s, or q.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    keys = [demo.key for demo in DEMOS]
    parser.add_argument("--check", action="store_true", help="report setup only")
    parser.add_argument("--list", action="store_true", help="list the order")
    parser.add_argument("--from", dest="start", choices=keys, help="start here")
    parser.add_argument("--only", action="append", choices=keys, help="repeatable")
    parser.add_argument("--yes", action="store_true", help="don't ask between demos")
    args = parser.parse_args()

    if args.list:
        for number, demo in enumerate(DEMOS, 1):
            print(
                f"{number}. {demo.key:<11} deliverable {demo.deliverable:<10} "
                f"{demo.title}: {demo.cost}"
            )
        return 0
    if shutil.which("docker") is None:
        sys.exit("error: docker is not on PATH")
    if not args.check and not sys.stdin.isatty():
        sys.exit("error: run this from an interactive terminal (the review needs it)")

    selected = list(DEMOS)
    if args.start:
        selected = selected[keys.index(args.start) :]
    if args.only:
        selected = [demo for demo in selected if demo.key in args.only]

    print("Order: " + " → ".join(f"{demo.title}" for demo in selected))
    try:
        setup(args.check)
        if args.check:
            return 0
        results: list[tuple[Demo, str]] = []
        for number, demo in enumerate(selected, 1):
            answer = "" if args.yes else confirm(demo, number, len(selected))
            if answer == "q":
                break
            if answer == "s":
                results.append((demo, "skipped"))
                continue
            try:
                results.append((demo, run_demo(demo)))
            except KeyboardInterrupt:
                print()
                results.append((demo, "interrupted"))
                if (
                    ask("Interrupted. Enter to go on to the next one, q to stop: ")
                    == "q"
                ):
                    break
    except stack.StackError as exc:
        sys.exit(f"error: {exc}")
    except KeyboardInterrupt:
        print("\nStopped.")
        return 130

    step("Summary")
    for demo, status in results:
        note(f"{status:<14} deliverable {demo.deliverable:<10} {demo.title}")
    if any(demo.key == "change" and status == "PASS" for demo, status in results):
        note(
            "If you approved the change, the demo database now serves its +4 point "
            "rates. The next run of present.py restores the real-bank checkpoint "
            "first."
        )
    return 0 if all(s in {"PASS", "skipped"} for _, s in results) else 1


if __name__ == "__main__":
    sys.exit(main())
