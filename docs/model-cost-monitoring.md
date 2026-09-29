# Model usage and cost monitoring

`model_call_usage` stores one redacted record for a logical Gemini call, application
retry attempt, or local model-result/embedding cache hit. It records stage, operation,
model, timestamp, outcome, latency, available token counts, optional run/offering
scope, dated paid-tier list rate, and estimated USD cost. A failed call keeps its
exception class and, when the transport reports one, the HTTP status in
`error_class` (for example `ClientError:http_429_RESOURCE_EXHAUSTED`), so a quota wall
is told apart from a bad request. It does **not** store prompts, source text,
responses, API keys, or exception messages.

Every recorded call also writes one line to the `tariff.model_usage` logger and, when
`LOG_FILE` is set, to a rotating `model_usage.log` beside it (`logs/model_usage.log`
on the Compose host): stage, operation, model, outcome, attempt, error class, token
counts, cost (or why it is unknown), latency, and run id. A refused call with no cost still appears there.

Run and offering scope: the pipeline wraps each offering's work in
`pipeline_usage_scope` (a `ContextVar`), so every discovery, PDF transcription and
extraction call is costed to its run and offering. In a chat, the monitoring node
sets `temp:monitoring_active_run` on the invocation's state while it executes or
resumes a run, so that turn's chat model calls carry the run id (no offering); chat
calls outside a run keep a `NULL` run.

Run `uv run python scripts/model_cost_report.py --days 7 --budget-usd 10` to read
daily stage/model totals. `known_cost_usd` sums only rows with enough usage data;
`unknown_calls` counts rows whose cost cannot be estimated. Budget status is
`incomplete` when any cost is unknown and the known total is below the threshold.
The budget report is observational; it does not stop calls.

The rate catalog uses the Gemini Developer API **paid tier**, standard synchronous
operation, in USD per million tokens. It is versioned by effective start date.
The configured `gemini-3.7-flash` rate on 2026-09-22 is $0.75 input and $3.75
output; `gemini-embedding-001` text input is $0.15. The stage and fallback models
are priced too: `gemini-3.1-flash-lite` (PDF transcription and source discovery,
$0.25/$1.50), `gemini-3.5-flash-lite` (discovery fallback, $0.30/$2.50), and
`gemini-3.8-flash` (extraction fallback, $0.75/$3.75 through 2026); see
`app/services/model_pricing.py`. These are list-price estimates, not invoice
reconciliation or Vertex AI billing. Rate source:
[Google Gemini API pricing](https://ai.google.dev/gemini-api/docs/pricing).

Direct document/query embeddings are timed at the SDK boundary.
ADK intent, discovery, PDF transcription, semantic extraction, root-chat, and CLI
calls use model callbacks. Application retries are represented as separate logical
calls; Google SDK internal HTTP retries are folded into the callback's latency and
are not individually observable. Embedding responses expose billable character
count but not reliable input token usage; such calls retain the published input
rate and `unknown_cost_reason=missing_input_usage` rather than claiming zero cost.
Old calls made before this ledger was installed cannot be reconstructed. Local
cache hits have an explicit zero API cost and are counted separately.
