# Monitoring run lifecycle

All triggers submit a typed `RunCommand` through `RunService`. `POST /api/v1/runs` is the
non-chat monitoring entry point: it accepts canonical `product` and optional
`offering_id`, returns `202`, and never runs natural-language classification or the
pipeline inline. The ADK monitoring tool submits only after intent/scope resolution and a
one-use authorization. The scheduler independently submits consumer-loan and mortgage
commands at 06:00 `Asia/Yerevan`.

PostgreSQL is the durable queue and business-state authority:

| State | Meaning | Worker behavior |
|---|---|---|
| `queued` | Durable work is ready to claim. | Claim with `FOR UPDATE SKIP LOCKED`. |
| `running` | One worker owns a bounded claim and invokes the shared workflow. | Execute `TariffPipeline` once. |
| `awaiting_review` | Native `RequestInput` was persisted and one or more reviews are pending. | Release the claim and return immediately. |
| `succeeded` | Every offering completed successfully. | Terminal; do not reclaim. |
| `partial_success` | At least one offering succeeded and at least one failed/rejected. | Terminal; preserve successful publications. |
| `failed` | No offering produced an accepted outcome, or recovery failed safely. | Terminal; preserve earlier publications. |

A run may transition directly from `running` to a terminal state. On review, ADK owns the
paused invocation/interrupt while PostgreSQL owns the run and review rows. Resume targets
the same durable session and invocation; completed pipeline nodes are replayed from ADK
events instead of rerun. Reconciliation repairs a missing interrupt when it can do so
without inventing a decision and otherwise fails inconsistent state safely.

An idempotency key returns its original run. The active-family constraint includes
`queued`, `running`, and `awaiting_review`, so a paused run cannot be bypassed by another
API, schedule, or chat submission. Startup recovery marks expired running claims failed;
it does not re-execute partially completed nondeterministic work.

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
`GET /api/v1/tariffs/history`, `GET /api/v1/reviews`, and
`GET /api/v1/reviews/{review_id}`. `POST /api/v1/questions` answers only from active
indexed evidence. Review decisions are intentionally absent from FastAPI and enter through
the native ADK Web resume flow documented in `docs/native-hitl-review.md`.
