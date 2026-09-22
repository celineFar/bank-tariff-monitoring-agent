# Fix Plan: Silent Monitoring, Missing Overdraft Snapshot, and the CLI Crash

Reported from the chat session `670fd952-a853-4660-a1be-da80332ea802` on 2026-09-22.
Three symptoms were reported; the investigation found four defects, all reproduced from
persisted evidence rather than inferred.

## 1. Evidence baseline

All facts below come from the live containers, not from reading code alone.

- The run the chat started is `8a6ec4f8-cda5-409f-80de-9c2b410a90c5`
  (`monitoring_runs`, one row, status `failed`).
- `offering_executions` holds one row: `overdraft | failed | source_discovery |
  source.model_failed | ClientError`.
- `tariff_snapshots`, `tariff_facts`, `knowledge_documents`, `knowledge_chunks`, and
  `retrieval_units` are all **empty** in `tariff_monitor`.
- The ADK event log for the session shows the tool sequence for the final turn:
  - `16:14:38` `call:start_tariff_monitoring_cli {"product":"consumer_loan","offering_id":"overdraft"}`
  - `16:14:39` `resp:... {"run_id":"8a6ec4f8…","status":"queued","created":true}`
  - `16:14:39 → 16:15:48` **45 consecutive `get_next_monitoring_review` call/response
    pairs**, each returning `{"status":"running","failure_code":null,…}`.
  - `16:15:48` model text: "The monitoring run failed with … `source.model_failed`".
- `logs/cli.log` counts 54 Gemini requests for the session, ~45 of them inside that
  70-second window — one model round trip per poll.
- `logs/worker.log` at `20:15:47–20:15:48` (+04:00): source discovery called
  `gemini-2.5-flash-lite`, and the pipeline logged
  `offering failed … stage=source_discovery code=source.model_failed reason=ClientError`.
  Earlier in the same run, PDF extraction hit the same model and logged
  `HTTP 404 / NOT_FOUND: This model models/gemini-2.5-flash-lite is no longer available
  to new users`, then **recovered by falling back** to `gemini-3.1-flash-lite`.
- `end-to-end/run_006/source_url.txt` and `run_007/source_url.txt` are
  `https://ameriabank.am/en/personal/loans/consumer-loans/overdraft`.

## 2. Problem A — Monitoring shows a blinking cursor instead of progress

### 2.1 Root cause

The CLI *does* have a progress renderer: `_STAGE_LABELS` and `_wait_for_run` in
[app/cli.py:228-278](app/cli.py#L228-L278) poll `offering_executions.current_stage`
and print "Acquiring web content · overdraft", etc. The stage keys it maps match the
stage names the pipeline writes in
[app/services/monitoring_pipeline.py:146-190](app/services/monitoring_pipeline.py#L146-L190).

That renderer never got a chance to run, for two independent reasons:

1. **The model busy-polls instead of yielding.** `start_tariff_monitoring_cli` is a
   `LongRunningFunctionTool` ([app/cli.py:131](app/cli.py#L131)): it is supposed to
   return `queued`, end the model turn, and let the CLI drive the wait and resume the
   call. Instead the model called `get_next_monitoring_review` 45 times in a row.
   `get_next_monitoring_review` invites this: for any run that is not
   `AWAITING_REVIEW` it happily returns the run's live status and failure code
   ([app/tools.py:534-541](app/tools.py#L534-L541)), which makes it usable as a status
   poller. The agent instruction ([app/cli.py:97-126](app/cli.py#L97-L126)) says "do not
   call it twice" about the monitoring tool, but never forbids polling for status while
   a run is in flight.
2. **Progress rendering is sequenced after the model turn.** `_run_and_print` runs to
   completion before `_continue_pending` → `_wait_for_run` is entered
   ([app/cli.py:855-878](app/cli.py#L855-L878)). So even a well-behaved model prints
   nothing during its own turn; and here the turn lasted the whole run.

The user therefore saw a bare cursor for 70 seconds, and the run cost ~45 extra Gemini
calls that bought nothing — directly against the cost-bounding goal of commit `9703bed`.

### 2.2 Fix direction

Make the tool boundary enforce the hand-off rather than relying on instruction wording,
and keep a heartbeat visible from the moment the run is submitted.

### 2.3 To-do — done (commit for phase A)

- [x] In `get_next_monitoring_review` ([app/tools.py:516](app/tools.py#L516)), stop
      returning live run status as a pollable result. When the run exists but is neither
      `AWAITING_REVIEW` nor terminal, return
      `{"status": "in_progress", "reason_code": "review.run_not_ready", "action":
      "stop_and_wait"}` with no other fields, so there is nothing for the model to loop on.
- [x] Detect the unanswered long-running call and reject with
      `review.awaiting_cli_result`. Built by reading the session's own events for a
      `start_tariff_monitoring_cli` call with no matching response, rather than the
      planned state key: the CLI resumes that call from outside any tool, so a state
      key would have had no owner to clear it and could have stuck the chat.
- [x] Tighten the CLI agent instruction ([app/cli.py:97-126](app/cli.py#L97-L126)): after
      `start_tariff_monitoring_cli` returns, emit one short line for the user and end the
      turn; never call any tool to check progress; the CLI supplies the result.
- [x] Print an immediate "Monitoring run <id> started for <offering>…" notice as soon as
      `_continue_pending` picks up the pending call, before the first poll, so there is
      never a silent gap.
- [x] Audited the full stage vocabulary the pipeline and review repository write:
      `acquisition`, `normalization`, `source_discovery`, `semantic_extraction`,
      `previous_snapshot`, `embedding`, `publication`, `review_approved`,
      `review_rejected`, plus `starting` and `internal`. There is no `validation`
      or `change_detection` stage; only `starting` and `internal` were missing
      from `_STAGE_LABELS`, and both are now labelled.
- [x] Show elapsed time on the repeating heartbeat (`_wait_for_run` already re-prints
      every 30s) so a long stage does not look frozen.
- [x] Tests: a unit test asserting `get_next_monitoring_review` returns the non-pollable
      shape for a `RUNNING` run and rejects while a CLI result is pending; a CLI test
      asserting the "started" notice precedes the first stage line.

## 3. Problem B — The earlier end-to-end run left no Overdraft snapshot

### 3.1 Root cause

`scripts/demonstrate_end_to_end.py` is a **file-only demonstration harness**, not a
pipeline run. It builds `FileSystemSourceDiscoveryRepository`,
`FileSystemSemanticExtractionRepository`, `FileSystemPdfExtractionRepository`, and
`FileSystemArtifactStore` ([scripts/demonstrate_end_to_end.py:31-47](scripts/demonstrate_end_to_end.py#L31-L47))
and writes everything under `end-to-end/run_NNN/`. It contains no reference to
snapshots, publication, or PostgreSQL, and its stages stop at semantic extraction:
`acquisition`, `normalization`, `source-discovery`, `semantic-extraction`
([scripts/demonstrate_end_to_end.py:104-305](scripts/demonstrate_end_to_end.py#L104-L305)).

So `end-to-end/run_006` and `run_007` really did process the Overdraft page, but they
never reached validation, snapshot publication, change detection, or persistence. The
chat's `get_current_tariffs` reads accepted rows from `tariff_snapshots`, which is empty
— hence "no accepted tariff snapshots", correctly. The database holds exactly one run:
today's failed one.

Note for expectation-setting: a *successful* pipeline run does not necessarily need a
human review. `snapshot_lifecycle` accepts a snapshot outright when the extraction is
acceptable and no review signal fires
([app/services/snapshot_lifecycle.py:110-141](app/services/snapshot_lifecycle.py#L110-L141)).
So once Problem D is fixed, one real run can populate the answer.

### 3.2 Fix direction — decision required

The demonstration artifacts are evidence of stages, not a data source. Two paths, not
mutually exclusive:

- **B1 (recommended, primary):** treat Problem D as the real fix — make a live worker run
  succeed so Overdraft gets a genuine, evidence-bound accepted snapshot.
- **B2 (optional, for demos):** add a replay script that feeds an `end-to-end/run_NNN`
  artifact set through the *real* validation → publication → persistence path, so a demo
  can populate snapshots without re-hitting the network or the model. This must reuse
  `TariffPipeline`'s publication services, never insert rows directly, so evidence
  retention and the accept/review decision stay unchanged.

### 3.3 To-do — done (commit for phase B)

- [x] Decided with the user on 2026-09-22: **B1 alone**. No replay script; the
      demonstration boundary is documented instead, and Phase D is what makes a real
      run able to publish.
- [x] Document in `docs/demonstrations.md` — explicitly — that
      `demonstrate_end_to_end.py` writes files only, stops after semantic extraction, and
      never produces an accepted snapshot or affects chat answers.
- [x] Make the chat's "snapshot missing" message say *why* monitoring is needed, so the
      difference between a demonstration artifact and a persisted snapshot is visible to
      the user.
- [–] Not done: B2 was declined, so no replay script and no replay integration test.

## 4. Problem C — The CLI crashed with an uncaught `AttributeError`

### 4.1 Root causes (three layered ones)

1. **The method does not exist.** `_wait_for_run` calls
   `run_service.list_offering_executions(run_id)` ([app/cli.py:250](app/cli.py#L250)),
   but `RunService` exposes only `submit` and `get`
   ([app/services/run_service.py:28-44](app/services/run_service.py#L28-L44)). The method
   lives one layer down on `PostgresRunRepository`
   ([app/repositories/monitoring.py:668](app/repositories/monitoring.py#L668)) and is
   declared on the `RunRepository` protocol
   ([app/repositories/contracts.py:108](app/repositories/contracts.py#L108)), but was
   never proxied through the service. Introduced by commit `83391e3`
   ("fix(cli): support indefinite tariff terms and show durable progress"), which added
   the repository method and the CLI call site but not the service pass-through. **CLI
   monitoring has been broken since that commit** — the crash fires on the first poll of
   any run started from chat.
2. **Nothing contains the error.** The chat loop catches only `APIError`
   ([app/cli.py:840-884](app/cli.py#L840-L884)). Any other exception escapes `chat()`,
   escapes `asyncio.run` in `main()` — which only handles `KeyboardInterrupt`/`EOFError`
   ([app/cli.py:900-913](app/cli.py#L900-L913)) — and dumps a traceback, killing the
   session and the resume hint.
3. **The tests and the type checker could not see it.**
   `tests/unit/test_cli.py:124-153` passes a hand-written `_Runs` fake that *defines*
   `list_offering_executions`, so the test proves the label rendering, not the contract.
   `_wait_for_run(run_service: object, …)` annotates the parameter as `object`, and
   `pyproject.toml` sets `unresolved-attribute = "ignore"` under `[tool.ty.rules]`
   ([pyproject.toml:81-90](pyproject.toml#L81-L90)) — so neither `ty` nor `ruff` would
   have flagged the call even with a precise annotation.

### 4.2 Fix direction

Add the missing pass-through, type the CLI against a real protocol, contain unexpected
errors in the chat loop, and replace the duck-typed fake with something contract-bound.

### 4.3 To-do — done (commit for phase C)

- [x] Add `async def list_offering_executions(self, run_id: UUID) ->
      tuple[OfferingExecution, ...]` to `RunService`, delegating to the repository
      ([app/services/run_service.py](app/services/run_service.py)).
- [x] Add a narrow protocol for what the CLI waiter needs (`get` +
      `list_offering_executions`) and annotate `_wait_for_run` and `_continue_pending`
      with it instead of `object`. Prefer a separate protocol over widening
      `RunServicePort`, so the many `RunServicePort` fakes in `tests/unit/` stay valid.
- [x] Decide whether `unresolved-attribute` can be re-enabled (at least for `app/cli.py`
      and `app/services/`); if the third-party noise makes that impractical, record why in
      `pyproject.toml` next to the rule.
- [x] Wrap the interactive loop body and the startup recovery in a broad
      `except Exception` that prints a rich error panel with the failing step, keeps the
      session alive, and repeats the `./tariff-chat --session-id …` resume hint, instead
      of unwinding to a traceback.
- [x] Keep genuinely fatal conditions distinguishable: log the exception with
      `logging.exception` to `logs/cli.log` so the traceback is still recoverable.
- [x] Tests: replace the ad-hoc `_Runs` fake with one built against the CLI waiter
      protocol (or `RunService` wrapping a fake repository), so a missing service method
      fails the test; add a test that an unexpected exception inside the turn prints the
      error panel and the loop survives.

## 5. Problem D — The run itself failed: `source.model_failed`

Surfaced by the investigation; it is the reason Overdraft still has no snapshot even
after the user authorized monitoring.

### 5.1 Root cause

The configured source-discovery fallback chain is never used in production.
`.env` sets `SOURCE_DISCOVERY_MODEL_NAME=gemini-2.5-flash-lite` and
`SOURCE_DISCOVERY_FALLBACK_MODEL_NAMES=gemini-3.1-flash-lite`, and the loader carries it
into `SourceDiscoverySettings.fallback_model_names`
([app/config/loader.py:134](app/config/loader.py#L134),
[app/config/models.py:284-285](app/config/models.py#L284-L285)) — but the only consumer
of a fallback chain is `pdf_extraction` ([app/services/pdf_extraction.py:112](app/services/pdf_extraction.py#L112)).
`runtime.py` builds a single `AdkSourceDiscoveryClassifier` from `model_name` alone
([app/runtime.py:135-149](app/runtime.py#L135-L149)), and
`is_model_fallback_error` ([app/services/discovery_classifier.py:197](app/services/discovery_classifier.py#L197))
is referenced **only by the demonstration scripts**, never by the pipeline.

Result: `gemini-2.5-flash-lite` now returns
`404 … no longer available to new users` — PDF extraction survives it by falling back,
source discovery does not, and the whole offering fails with `source.model_failed`.
This also explains why the demonstration scripts keep working while live runs fail:
the demos implement the fallback loop themselves.

Secondary defect: `failure_detail` for that row is the bare string `ClientError`. The
actual 404 message was logged but not persisted, so neither the chat nor the API can
explain the failure.

### 5.2 To-do — done (commit for phase D)

- [x] Move the fallback loop out of the demonstration scripts into a shared helper and
      use it in the production source-discovery path, so
      `source_discovery.fallback_model_names` is honored by the worker.
- [x] Audit every production model call site for the same gap — at minimum semantic
      extraction ([app/services/semantic_extraction.py](app/services/semantic_extraction.py)
      via [app/runtime.py:162-166](app/runtime.py#L162-L166)) has no fallback chain
      configured or applied; decide whether it needs one.
- [x] Persist a useful `failure_detail`: include the model id, HTTP status, and the
      provider message (truncated to the column's 2000-char limit) instead of the
      exception class name.
- [x] Settled with the user on 2026-09-22: `gemini-3.1-flash-lite` is now the
      primary for both stages and both fallback lists are empty. It was already the
      configured fallback, today's logs show it working, and at $0.25/$1.50 it is the
      cheapest model still served that fits the stages' $1.50 ceiling — the named
      successor `gemini-3.5-flash-lite` prices output at $2.50 and would require
      raising that ceiling. Original finding: `gemini-2.5-flash-lite` is the
      primary for both `PDF_EXTRACTION_MODEL_NAME` and `SOURCE_DISCOVERY_MODEL_NAME`
      and now answers `404 … no longer available to new users`; the provider names
      `gemini-3.5-flash-lite` as its successor, while the configured fallback
      `gemini-3.1-flash-lite` is proven working in today's logs. Every run now pays
      one wasted call on the retired primary before falling back. Changing the
      primary is a model change, so it waits for the user.
- [x] Surface the failure to the user in words, not just a code: map
      `source.model_failed` to a sentence that says the discovery model was unavailable
      and the run can be retried, keeping the exact code visible for the audit trail.
      Done as `explain_failure_code`, printed by the CLI itself and handed to the
      model as `failure_summary` so both say the same thing.
- [x] Tests: unit test that a `404`/unavailable error on the primary discovery model
      falls through to the configured fallback and the run completes; unit test that a
      failure on every model in the chain persists a detailed `failure_detail`.
      The stored detail is bounded to `ClientError:http_404_NOT_FOUND` rather than
      the provider's message: `docs/failure-behavior.md` forbids persisting
      provider text, and the message stays in the log file.

## 6. Suggested order of work

1. **C** — restore the CLI (pass-through + error containment). Without it nothing else
   is observable from chat.
2. **D** — restore the fallback chain, so a run can actually finish.
3. **A** — stop the model poll loop and make progress visible.
4. **B** — documentation, and the replay script if the user wants it.

After 1–3, re-run the reported scenario end to end: ask for the Overdraft tariff, confirm
monitoring, and expect per-stage progress lines, a completed run, an accepted snapshot in
`tariff_snapshots`, and an evidence-backed answer. Then run
`uv run pytest tests/unit tests/integration`.

## 7. Verification checklist for the implementer

- [ ] `grep -rn "list_offering_executions" app/` shows service, protocol, repository, and
      CLI in agreement.
- [ ] A chat-started run prints: started notice → per-stage lines → terminal status.
- [ ] The ADK event log for a new session shows **zero** `get_next_monitoring_review`
      calls while the run is merely running.
- [ ] `select count(*) from model_call_usage where stage='adk.cli'` for the new run's
      window is in single digits, not ~45.
- [ ] `tariff_snapshots` holds an accepted Overdraft row with intact evidence.
- [ ] Killing the worker mid-run leaves the chat alive with a readable error, no traceback.
