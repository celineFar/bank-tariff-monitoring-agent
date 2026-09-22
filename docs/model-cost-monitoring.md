# Model usage and cost monitoring

`model_call_usage` stores one redacted record for a logical Gemini call, application
retry attempt, or local model-result/embedding cache hit. It records stage, operation,
model, timestamp, outcome, latency, available token counts, optional run/offering
scope, dated paid-tier list rate, and estimated USD cost. It does **not** store
prompts, source text, responses, API keys, or exception messages.

Run `uv run python scripts/model_cost_report.py --days 7 --budget-usd 10` to read
daily stage/model totals. `known_cost_usd` sums only rows with enough usage data;
`unknown_calls` counts rows whose cost cannot be estimated. Budget status is
`incomplete` when any cost is unknown and the known total is below the threshold.
The budget report is observational; it does not stop calls.

The rate catalog uses the Gemini Developer API **paid tier**, standard synchronous
operation, in USD per million tokens. It is versioned by effective start date.
The configured `gemini-3.7-flash` rate on 2026-09-22 is $0.75 input and $3.75
output; `gemini-embedding-001` text input is $0.15. These are list-price
estimates, not invoice reconciliation or Vertex AI billing. Rate source:
[Google Gemini API pricing](https://ai.google.dev/gemini-api/docs/pricing).

Direct document/query embeddings and RAG answer calls are timed at the SDK boundary.
ADK intent, discovery, PDF transcription, semantic extraction, root-chat, and CLI
calls use model callbacks. Application retries are represented as separate logical
calls; Google SDK internal HTTP retries are folded into the callback's latency and
are not individually observable. Embedding responses expose billable character
count but not reliable input token usage; such calls retain the published input
rate and `unknown_cost_reason=missing_input_usage` rather than claiming zero cost.
Old calls made before this ledger was installed cannot be reconstructed. Local
cache hits have an explicit zero API cost and are counted separately.
