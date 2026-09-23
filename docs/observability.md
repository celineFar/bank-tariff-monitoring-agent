# Observability

Three signals, three mechanisms, chosen so each answers a question the others
cannot:

| Question | Mechanism |
|---|---|
| What happened inside this one run? | OpenTelemetry traces, viewed in Langfuse |
| What has been happening across runs? | SQL over the audit tables |
| What exactly did stage X see and emit? | Rotating file logs and the pipeline audit archive |

## Traces

### What is instrumented

ADK instruments the agent and workflow layers on its own: `invoke_workflow`,
`invoke_node`, `invoke_agent`, `call_llm`, and `execute_tool`, plus
`generate_content` from the google-genai instrumentation library. The monitoring
workflow in `app/services/monitoring_workflow.py` is a real ADK `Workflow`, so
its nodes — including the human-review interrupt — appear without extra code.

Everything between acquisition and publication is ordinary Python and would
otherwise collapse into one opaque node span. `app/services/monitoring_pipeline.py`
opens a span per offering and a span per stage. Every stage already funnels
through one helper, so the seven stages are covered by one call site:

```
POST /api/v1/runs                     (or the scheduler, or the CLI)
└── execute_run                       (worker)
    └── offering mortgage_primary
        ├── stage acquisition
        ├── stage normalization
        ├── stage source_discovery
        │   └── invoke_agent → call_llm
        ├── stage semantic_extraction
        │   └── invoke_agent → call_llm
        ├── stage embedding
        │   └── generate_content
        ├── stage previous_snapshot
        └── stage publication
```

Stage spans carry `tariff.run_id`, `tariff.offering_id`, and `tariff.stage`, and
a failing stage carries `tariff.failure_code`. These are the same identifiers and
the same stage names used by `offering_executions.current_stage` and the
`OfferingFailureCode` taxonomy, so a trace and a metrics report join without a
translation table.

### One run, one trace, across processes

A run never executes where it was triggered. The API, the scheduler, and the CLI
all write a queued row that the worker later claims, and a run paused for review
resumes inside whichever process served the decision. Ambient OpenTelemetry
context does not survive either handoff.

`migrations/014_trace_context.sql` adds a `trace_parent` column to
`monitoring_runs` and `human_reviews`. The W3C traceparent is captured at submit
and at pause, and restored at claim and at resume, so every segment shares one
trace id and a backend that groups by trace id shows them as one trace.

Two consequences worth knowing:

- No single span stays open across a pause — a live span cannot be serialized
  across processes. Continuity comes from the shared trace id and parent
  pointers, not from one long-lived span. The parent ends before its children
  start, which trace viewers assemble correctly at query time.
- A trace's wall-clock duration therefore includes the reviewer's thinking time.
  That is why latency metrics come from SQL, where review wait is subtracted,
  rather than from trace durations.

Rows written while tracing was disabled carry no context, and the reader treats
that as "start a new trace" rather than failing.

### Content policy

ADK's `ADK_CAPTURE_MESSAGE_CONTENT_IN_SPANS` **defaults to on**, so prompts and
model responses would be exported by default. `app/services/telemetry.py` is the
single place that decides what leaves the process:

| `OTEL_TRACE_CONTENT` | Behavior |
|---|---|
| `none` (default) | Content attributes are dropped; ADK capture is switched off at the source |
| `mapped` | Content is bounded to 8000 characters and renamed to the attributes the trace backend reads |

The rewrite lives in a wrapping `SpanExporter`, not a second `SpanProcessor`: a
sibling processor receives the same read-only span and cannot change what the
exporter has already queued.

Because of that, **do not set `OTEL_EXPORTER_OTLP_ENDPOINT` or
`OTEL_EXPORTER_OTLP_TRACES_ENDPOINT`.** ADK would register its own exporter for
the same spans, bypassing the rewrite and exporting content unredacted. The
application refuses to enable tracing when it sees either variable, rather than
leaking silently. Configure `OTEL_TRACES_ENDPOINT` instead.

Use `mapped` only against a backend you control. It exports text projected from
bank source documents.

### Running it

Tracing is off by default. With `OTEL_ENABLED=true` and no endpoint, spans print
to the console, which is enough to verify the instrumentation without running a
backend:

```bash
OTEL_ENABLED=true uv run python -m app.worker
```

For the UI, bring up the opt-in profile and point the endpoint at it:

```bash
docker compose --profile observability up -d
# then in .env:
#   OTEL_ENABLED=true
#   OTEL_TRACES_ENDPOINT=http://langfuse:3000/api/public/otel/v1/traces
```

Langfuse is at `http://localhost:3001` (3000 is reserved for the frontend
origin). It is six containers next to a three-container application, which is
why it is opt-in rather than part of the default stack.

Langfuse ingests **traces only** — its OTLP endpoint has no metrics or logs
path. That is the reason metrics come from SQL and logs stay as files rather
than being pushed through the same pipeline.

## Metrics

`scripts/run_metrics_report.py` reads aggregates from the durable tables:

```bash
uv run python scripts/run_metrics_report.py --days 30
uv run python scripts/run_metrics_report.py --days 7 --section extraction_completeness
```

| Section | Source | Notes |
|---|---|---|
| `run_outcomes` | `monitoring_runs`, `human_reviews` | Duration excludes review wait |
| `stage_failures` | `offering_executions` | By `OfferingFailureCode` and terminal stage |
| `document_retrieval` | `source_manifests` | By `SourceFailureCode` reason code |
| `extraction_completeness` | `tariff_facts` | Per `field_path`, not one percentage |
| `evidence_coverage` | `fact_evidence` | Expected 100%; the value is seeing a regression |
| `validation_signals` | `tariff_snapshots.validation` | Deterministic rejects by check and field |
| `review_rate`, `review_activity` | `offering_executions`, `human_reviews` | Rate, reason mix, decision latency |
| `model_reliability` | `model_call_usage` | Failures, cache hits, retries, latency by stage |
| `change_activity` | `tariff_changes` | Detected change volume |

Model token usage and estimated cost stay in `scripts/model_cost_report.py`; see
[model cost monitoring](model-cost-monitoring.md).

ADK also emits OpenTelemetry metrics (token usage, invocation and tool
durations, call counts). They are not exported: Langfuse cannot receive them,
and the same data is present both in span attributes and in `model_call_usage`,
which additionally carries cost. Nothing is lost by not collecting them. If
time-series metrics are ever wanted, `OTEL_EXPORTER_OTLP_METRICS_ENDPOINT`
pointed at a collector is the escape hatch and needs no code change.

## Logs

Logging is unchanged: rotating files per process, ISO 8601 with an explicit
offset, described in the README. The retrieval step trace on the
`tariff.retrieval` logger now uses the **active OpenTelemetry trace id** as its
correlation id when one is recording, falling back to a random id otherwise, so
a log line and a trace share one identifier instead of two parallel schemes.

OpenTelemetry log export is deliberately not used. The durable record is the
rotating files plus the `audit_events` table, and events worth seeing in trace
context belong on the span rather than in a second pipeline.

## What was considered and rejected

- **DeepEval for RAG evaluation.** Redundant with `agents-cli eval` and the
  deterministic suite in `scripts/structured_eval_metrics.py`. Its headline
  metrics are LLM-judged proxies for groundedness, while this system answers
  from typed accepted facts with mandatory evidence rows — ground truth is an
  exact value at an exact source location, so exact-match is both stronger
  evidence and cheaper than a judge.
- **OpenTelemetry metrics and logs export.** The chosen backend cannot ingest
  either signal, so unifying on it would have meant a second backend rather
  than fewer moving parts.
- **Google Cloud Trace** (`OTEL_TO_CLOUD`) remains available and untouched for a
  deployed environment; it is not used locally because it requires a project.

## Limitations

- The SQL in `app/services/run_metrics.py` has not been executed against a live
  database in this change; it is covered by review, not by a passing query. Run
  `scripts/run_metrics_report.py` against the test database before relying on it.
- Deterministic validation rejects are reported from the signals
  `detect_review_signals` writes into `tariff_snapshots.validation`. Rejects
  raised earlier than snapshot construction — a rejected download MIME type, an
  oversized file — are counted under `document_retrieval` by their source reason
  code instead, not under `validation_signals`.
- Langfuse's own retention bounds how long a trace stays visible. The audit
  tables are the durable record.
