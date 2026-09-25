# Monitoring run lifecycle

All triggers submit a typed `RunCommand` through `RunService`. `POST /api/v1/runs` is the
non-chat monitoring entry point: it accepts canonical `product` and optional
`offering_id`, returns `202`, and never runs natural-language classification or the
pipeline inline. The chat monitoring tool submits only after intent/scope resolution and
an invocation-bound spend grant. The scheduler independently submits consumer-loan and
mortgage commands at 06:00 `Asia/Yerevan`.

Two hosts execute the same `TariffPipeline`; PostgreSQL decides which one owns a run:

- **Chat-initiated runs** are claimed and executed by the process the conversation runs
  in (the CLI, or the API under ADK Web), inside the monitoring node, with
  `RunRepository.claim(run_id, owner)`. The owner (`claimed_by`) is
  `cli:<host>:<pid>:<token>` or `api:<host>:<pid>`. Progress streams to the chat.
- **Scheduled and API runs** are claimed by the worker with `FOR UPDATE SKIP LOCKED` and
  executed there, with progress written to the log. The worker has no ADK session.

A chat that asks for a scope whose run another process already owns *follows* that run:
it streams the persisted stages until the run is terminal or paused, then continues as if
it had executed it.

PostgreSQL is the durable queue and business-state authority:

| State | Meaning | Owner behavior |
|---|---|---|
| `queued` | Durable work is ready to claim. | Chat: `claim(run_id)`. Worker: `claim_next` (`SKIP LOCKED`). |
| `running` | One process owns the claim and executes `TariffPipeline` once. | Report progress; handle cancellation. |
| `awaiting_review` | One or more reviews are pending. | Release the claim. A chat pauses its invocation on the first review; a worker run waits for the CLI. |
| `succeeded` | Every offering completed successfully. | Terminal; do not reclaim. |
| `partial_success` | At least one offering succeeded and at least one failed/rejected. | Terminal; preserve successful publications. |
| `failed` | No offering produced an accepted outcome, the run was cancelled or interrupted, or recovery failed safely. | Terminal; preserve earlier publications. |

A run may transition directly from `running` to a terminal state. A paused run is closed
by `ReviewResolutionService.complete_run` once no review is pending: all approved →
`succeeded`; some rejected with a prior success → `partial_success`; otherwise `failed`.
A paused run with no review rows fails closed.

Failure codes owned by the lifecycle itself:

| Code | When |
|---|---|
| `run.cancelled` | The caller cancelled the run it was executing (Ctrl-C in the CLI). The pipeline fails the in-flight offering execution and the run before the cancellation propagates, and records a `run.cancelled` audit event. |
| `run.interrupted` | The CLI process executing a chat run died. The next start of that conversation fails the runs owned by the previous process's owner (`RunRepository.fail_interrupted`). |
| `run.abandoned` | A `running` claim outlived the worker lease (`recover_abandoned` at worker start) — the backstop for both hosts. |

An idempotency key returns its original run. Active-run constraints cover `queued`,
`running`, and `awaiting_review`. Targeted runs for different offerings in the same
family may proceed independently; a request for the same offering reuses its active
run. A family-wide run overlaps every offering in its family, so it cannot start
while any targeted run is active, and targeted requests reuse an active family-wide
run. PostgreSQL advisory locking serializes these cross-scope submission checks.
If an older service returns a run that does not cover the requested offering, the API
returns `409 run.active_scope_conflict` and the chat tool reports `blocked` instead of
claiming the requested offering started. Startup recovery marks expired or interrupted
running claims failed; it does not re-execute partially completed nondeterministic work.
On start the worker also completes any paused run whose reviews were all decided.

Each family run owns per-offering executions. Successful offerings publish independently;
a failed sibling leaves its previous current index/snapshot untouched and produces family
`partial_success`. Audit records contain IDs, counts, reason codes, and stage timings—not
source bodies or secrets.

Typed API examples:

```bash
curl -X POST http://localhost:8080/api/v1/runs \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: example-consumer-refresh-1' \
  -d '{"product":"consumer_loan","offering_id":"consumer_standard"}'

curl http://localhost:8080/api/v1/runs/00000000-0000-0000-0000-000000000000
```

Read-only companion routes are `GET /api/v1/tariffs/current`,
`GET /api/v1/tariffs/history`, `GET /api/v1/reviews[?run_id=]` and
`GET /api/v1/reviews/{review_id}`. `POST /api/v1/questions` answers only from active
indexed evidence. Review decisions are taken in the chat CLI, as native ADK pauses of the
conversation (`docs/native-hitl-review.md`); runs the scheduler or the API started are
reviewed there too. `POST /api/v1/reviews/abort-pending` is a token-protected admin
operation that rejects every pending review, closes those runs, and reports any run it
could not close.
