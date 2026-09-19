# Monitoring run lifecycle

All triggers submit a typed `RunCommand` through `RunService`. `POST /api/v1/runs`
returns `202`, the ADK monitoring tool submits after product resolution, and the worker
scheduler independently submits consumer-loan and mortgage commands at 06:00
`Asia/Yerevan`.

PostgreSQL is the durable queue. Runs transition `queued -> running -> succeeded`,
`partial_success`, or `failed`. An idempotency key returns its original run, and the
active-family constraint returns existing queued/running work rather than duplicating
it. Workers claim with `FOR UPDATE SKIP LOCKED`; startup recovery marks expired claims
failed so a later submission can proceed safely.

Each family run owns per-offering executions. Successful offerings publish
independently; a failed sibling leaves its previous current index/snapshot untouched and
produces family `partial_success`. Audit records contain IDs, counts, reason codes, and
stage timings—not source bodies or secrets.

API examples:

```bash
curl -X POST http://localhost:8080/api/v1/runs \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: example-consumer-refresh-1' \
  -d '{"product":"consumer_loan","offering_id":"consumer_standard"}'

curl http://localhost:8080/api/v1/runs/00000000-0000-0000-0000-000000000000
```
