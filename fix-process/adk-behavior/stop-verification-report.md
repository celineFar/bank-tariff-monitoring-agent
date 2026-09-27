# Stop verification: can a run be stopped at any step, and does everything halt?

Date: 2026-09-27 · Branch: `fix/ADK-behaviour` · Gemini tokens spent: **0**

## Answer

**In the chat, one Ctrl-C at any step stops everything, completely.** In 11 scenarios
the real CLI was stopped with Ctrl-C through a terminal. The steps covered were:

- the root agent's model call;
- page acquisition, with Playwright running;
- PDF link selection;
- PDF transcription;
- source discovery and semantic extraction, several calls in flight;
- a retry backoff;
- a review prompt.

After each Ctrl-C:

- every in-flight model request was dropped within about 0.1 s;
- no model request followed over a 10 s watch (75 s for the backoff case);
- no browser or other child process remained;
- the idle process used 0.0 s of CPU;
- no asyncio task was left;
- the run was closed as `run.cancelled`, at the stage it was in.

**Outside that path, stopping is not complete.** Seven findings:

| # | Where | What happens | Keeps spending? |
|---|---|---|---|
| F1 | Worker, SIGTERM during a run | The worker ignores the signal until the run finishes, and every remaining model call is made. | **Yes**, the whole remaining run |
| F2 | Worker, `docker stop` (SIGTERM, then SIGKILL after 10 s) | The run is left `running` with no owner. A restarted worker does not close it. | No, but new runs for that scope are blocked |
| F3 | Chat following a run the worker owns | Ctrl-C prints "Monitoring cancelled." but only stops the chat watching. The worker's run carries on. | **Yes**, and the message says otherwise |
| F4 | Chat, cancel between submit and claim | The run is left `queued`. The next worker poll executes it. | **Yes**, after the user cancelled |
| F5 | Chat, cancel after claim, before execution starts | The run is left `running`, owned by the chat, and nobody executes it. The next request for that scope follows this phantom run for up to 30 min. | No, but monitoring that scope is blocked |
| F6 | Chat, third Ctrl-C in one CLI process | A raw `KeyboardInterrupt` kills the CLI and skips the cancel cleanup. The run is left `running` as in F5. | No (the process dies) |
| F7 | Recovery of orphaned runs | Only a worker at startup closes a `running` run, and only one claimed more than 30 min before. | Makes F2, F5 and F6 last indefinitely |

F4 and F5 are races that are milliseconds wide in production: two DB round trips. They
were hit on purpose by widening each window with a 2 s sleep inside the real call.
F1, F3 and F6 need no help to reproduce.

## Method

- **Fake Gemini** (`stop/fake_gemini.py`). The application runs unmodified, with
  `GOOGLE_GEMINI_BASE_URL` pointed at a local server and a dummy key. Nothing
  reaches Google.
  - The server identifies each caller from the agent name ADK puts in the system
    instruction.
  - It returns minimal, schema-valid answers, so a run goes through every stage.
  - It can hold a chosen caller's request open until the client disconnects, or
    answer it with 503.
  - It logs every request and every disconnect with timestamps.
- **Database.** The disposable `db-test` service (tmpfs, port 5433) with all
  migrations applied. The development database was not touched.
- **Real terminal** (`stop/cli_driver.py`). `app/cli_entry.py` runs in a
  pseudo-terminal. Ctrl-C is the byte `0x03`, which the terminal turns into SIGINT,
  just as it does in `./tariff-chat`.
- **Baseline (S00).** One uncancelled run: every stage ran against the fake, 21 s
  in total, including a 17 s real page fetch. It paused at "Review 1/10".
- **Watch after each stop.** New requests at the fake; how the run, offering
  execution and audit rows were closed; child processes (from `/proc`); the
  process's CPU time; and, in-process, the remaining asyncio tasks and threads.

## Results: chat, single Ctrl-C (all pass)

| Scenario | Step when Ctrl-C was pressed | In flight | Dropped | Requests after | Run closed as |
|---|---|---|---|---|---|
| C01 | root agent model call | 1 | 1 | 0 | no run yet ("Cancelled.") |
| C02 | acquisition (real fetch; Playwright node + Chromium running) | – | – | 0 | `run.cancelled` @ acquisition; no child process left |
| C03 | PDF link selection | 1 | 1 | 0 | `run.cancelled` @ pdf_selection |
| C04 | PDF transcription | 1 | 1 | 0 | `run.cancelled` @ normalization |
| C05 | source discovery | 3 | 3 | 0 | `run.cancelled` @ source_discovery |
| C06 | semantic extraction | 3 | 3 | 0 | `run.cancelled` @ semantic_extraction |
| C07 | extraction retry backoff (after a 503) | 0 | – | 0 in 75 s | `run.cancelled` @ semantic_extraction |
| C08 | review prompt | – | – | 0 | stays `awaiting_review` ("Review postponed"), as designed |
| C11 | two runs in one CLI, one Ctrl-C each | 3 + 3 | 6 | 0 | both `run.cancelled` |
| C12 | two presses 50 ms apart | 3 | 3 | 0 | `run.cancelled` |
| X03 | in-process: source discovery | 3 | 3 | 0 | `run.cancelled`; **0 asyncio tasks left**; 2 idle thread-pool threads (not spending) |

In every case the CLI returned to the prompt about 0.1 s after the press and used
0.0 s of CPU while idle. The retry loops (`classify`, `extract`, `embed_documents`) sleep
with `asyncio.sleep` and catch only `APIError`, so cancellation interrupts the backoff.
C07 confirms it: no retry in 75 s, which is longer than the 60 s maximum backoff.

## Findings in detail

### F1: the worker keeps running a run after SIGTERM (W01)

`app/worker.py` `main()` maps SIGINT/SIGTERM to `stop.set()`, and `run_forever` checks
`stop` only between runs. SIGTERM was sent while source discovery was held:

- the worker was still alive after 15 s, and the held request stayed open;
- when the fake answered again, the worker carried on and made 5 more model calls
  (1 discovery, 4 extraction) at 14.9–15.1 s after SIGTERM;
- the run completed to `awaiting_review`, and the worker then exited 1.7 s later.

On real Gemini, the remaining calls cost what the rest of the run costs: minutes of
calls for a whole-family run.

*Fix direction:* on the first signal, cancel the task running `process_next`.
`TariffPipeline._cancel` already closes the run as `run.cancelled`, as the chat path
shows. Optionally, a second signal exits at once.

### F2: `docker stop` leaves the run `running` (W03)

SIGTERM does not stop the worker (F1), so after the 10 s grace Docker sends SIGKILL.
The run and its offering execution stay `running`. A worker restarted 8 s later did
not close it: `recover_abandoned` only closes runs claimed more than 30 minutes
earlier. Until then, a chat request for that scope is told another run is in progress,
or follows the run (F5). Fixing F1 removes most of F2. Separately,
`stop_grace_period` in `docker-compose.yml` should be longer than the cancel cleanup
takes.

### F3: Ctrl-C while following says "cancelled", but the run continues (C15)

When the worker owns the run, the chat node only polls it (`_follow`). Ctrl-C stops the
polling. The CLI printed "• Monitoring cancelled." Meanwhile:

- the worker's held request stayed open;
- after release, the run made 5 more model calls;
- the run finished normally.

This contradicts what the user was told. There is no cross-process cancel at all: the
pipeline checks no cancel flag, and no API route cancels a run.

*Fix direction:* at minimum, say "Stopped following; the run started by the API
continues". Better, add a durable cancel request (a column, or an audit event the
pipeline checks between stages), plus a way to set it from the chat and the API.

### F4: cancel between submit and claim leaves a `queued` run (X01)

`monitoring_node` calls `run_service.submit` and then `runs.claim`. A cancel between
the two leaves a `queued` run that no one has claimed. The compose worker polls every
2 s and will execute it, spending the full run after the user pressed Ctrl-C.

*Fix direction:* on `CancelledError` in the node, fail (or cancel) a run this call
created and has not yet claimed. Doing the submit and the claim in one transaction
would also close the window.

### F5: cancel between claim and execution leaves an orphan `running` run (X02)

The run is `running` and owned by this chat, but has no offering execution. Nothing
executes it, because the pipeline task never started. The cancel handler inside
`TariffPipeline.execute` only runs once the task is running: a task cancelled before
its first step never enters the coroutine, so `_cancel` is skipped.

Asking again in the same conversation followed this phantom run and had not finished
after 12 s. `_follow` gives up after 30 minutes. The rewind also removes the dangling
invocation, so reopening the CLI does not close it either (the recovery in
`ChatSession.open` never triggers).

*Fix direction:* close a claimed run in the node's own `except CancelledError`, when
the pipeline did not already. That is a no-op if `_cancel` already ran.

### F6: the third Ctrl-C in one CLI process kills it without cleanup (C13)

This is how `asyncio.Runner` handles SIGINT (`_interrupt_count` is never reset):

1. The **1st** press cancels the main task. `converse` absorbs it with `uncancel()`.
2. The **2nd** press raises `KeyboardInterrupt` out of the event loop. `asyncio.run`
   starts its shutdown, which cancels every task. `converse` absorbs that cancellation
   too, so the chat keeps working, but now inside asyncio's shutdown phase with
   Python's default SIGINT handler. C11 passes only because of this. `stop/sigint_repro.py` shows the same
   sequence without the application.
3. The **3rd** press raises `KeyboardInterrupt` directly in whatever code is running.
   The CLI exits, and the pipeline's `except CancelledError` never runs.

In C13 the third run was left `running`, with no `run.cancelled` audit. The model
connections closed because the process exited.

*Fix direction:* the CLI should own SIGINT. Use
`loop.add_signal_handler(SIGINT, …)` to cancel the current turn task, or exit when idle
at the prompt. Then every press is a clean cancel.

### F7: orphaned runs are closed only at worker startup, after 30 min

`recover_abandoned` is called only from `MonitoringWorker.startup_checks`. The CLI's
`fail_interrupted` runs only when a conversation is reopened with a dangling
invocation. F2, F5 and F6 therefore leave a run `running` until a worker restarts at
least 30 minutes later, and meanwhile they block that scope.

*Fix direction:* a periodic recovery pass in the worker loop. Better, a lease
heartbeat, so a live chat run is never mistaken for an abandoned one.

## Not covered

- **Stops that go through a real model.** Cancelling review application while
  embedding (`ReviewDecisionService._embed_activated`) and cancelling the
  post-monitoring answer are not exercised. The fake run always pauses for review,
  and approving needs all 10 reviews answered. Both paths use the same cancellable
  async calls as the stages tested.
- **Tokens for requests already sent.** Dropping an in-flight HTTP request stops
  waiting for it. Gemini may still bill the input tokens of a request it already
  received. No client-side stop can avoid that.
- **Stopping during OCR.** `pytesseract` runs in a thread (`asyncio.to_thread`).
  After a cancel it finishes its page, bounded by `OCR` `timeout_seconds`. This spends
  CPU, not tokens, and was not triggered here: no scanned PDF was selected.

## Reproducing

```bash
docker compose --profile test up -d db-test
for m in migrations/*.sql; do docker compose exec -T db-test psql -q -v ON_ERROR_STOP=1 \
  -U tariff -d tariff_monitor_test < "$m"; done
.venv/bin/python fix-process/adk-behavior/stop/s00_smoke.py "run monitoring for overdraft"
.venv/bin/python fix-process/adk-behavior/stop/s10_cli_stop.py            # C01–C13
.venv/bin/python fix-process/adk-behavior/stop/s20_worker_stop.py          # W01–W03, C15
.venv/bin/python fix-process/adk-behavior/stop/s30_inprocess_windows.py    # X01–X03
```

Per-scenario results are in `stop/out/*.result.json` and the fake's request logs in
`stop/out/*.gemini.jsonl`. The suites share the test database: run them one at a time.

## After the fix (2026-09-27, `integration/process-fixes`)

The same harness was run against the fixed code. Pre-fix results are kept in
`stop/out-before-fix/`.

| # | Scenario | Before | After |
|---|---|---|---|
| F1 | W01: SIGTERM mid-run | ran on; 5 model calls after SIGTERM | exits in 0.9 s; 3 held calls dropped; 0 calls after; `run.cancelled` @ source_discovery |
| F2 | W03: `docker stop` | SIGKILL; run left `running` | exits in 0.9 s, inside the grace period; `run.cancelled` |
| F3 | C15: Ctrl-C while following | worker ran on; "Monitoring cancelled." | worker's run `run.cancelled` within 3 s (audit `run.cancel_requested`); 0 calls after; the chat says the run elsewhere was asked to stop |
| F4 | X01: cancel between submit and claim | left `queued` | `run.cancelled` |
| F5 | X02: cancel after claim | orphan `running`; next request followed it | `run.cancelled`; next request ran normally |
| F6 | C13: three Ctrl-C in one CLI | third killed the CLI; run left `running` | all three turns `run.cancelled`; CLI alive at the prompt |
| F7 | recovery | worker start only, after 30 min | lease of 120 s, checked every 60 s by the worker and by the chat |

Regression checks C03, C07, C12 and X03 still pass: 0 requests after Ctrl-C,
0 asyncio tasks left, idle CPU 0.0 s.

Tests: `uv run pytest tests/unit tests/integration` with `TEST_DATABASE_URL` set gives
1,107 passed. `test_agent.py::test_agent_stream` and the three `test_server_e2e.py` tests
fail the same way without these changes: they need a real `GEMINI_API_KEY` or a
server started with a full environment.
