# Safe failure behavior

Monitoring failures are deterministic outcomes. A failed stage never supplies a default
tariff value, never turns a candidate into an accepted snapshot, and never replaces the
previous accepted documents. Human review is created only when trustworthy captured
official evidence gives a reviewer a bounded business choice.

## Stable source codes

| Condition | Stable code | Outcome |
|---|---|---|
| Unsafe URL or redirect target | `source.url_rejected` | fail offering, no review |
| Timeout after bounded retry | `source.timeout` | fail offering, no review |
| Transport failure | `source.transport` | fail offering, no review |
| HTTP 404 | `source.not_found` | fail required source; optional linked source is recorded as a warning |
| Other terminal HTTP status | `source.http_status` | controlled source failure |
| Invalid/unsupported MIME | `source.mime_rejected` | reject source, no review |
| Invalid length or excessive bytes | `source.size_rejected` | reject source, no review |
| Redirect loop, limit, or missing location | `source.redirect_rejected` | reject source, no review |
| Invalid PDF signature | `source.signature_rejected` | reject source, no review |
| Page/normalization parsing failure | `source.parsing_failed` | fail offering when no trustworthy evidence remains |
| PDF extraction failure | `source.pdf_extraction_failed` | fail offering when no trustworthy evidence remains |
| OCR fallback produced nothing | `source.ocr_failed` | recorded after every model attempt and OCR both failed; no values are emitted |
| Gemini/provider failure | `source.model_failed` | fail offering after bounded attempts, no review |
| Invalid structured model response | `source.malformed_structured_output` | bounded repair, then safe failure/review only with captured evidence |
| Other deterministic validation failure | `source.validation_failed` | reject candidate; never fabricate |

The stored audit detail contains only the stage, stable code, exception type, and —
for a provider error — its transport status, as in `ClientError:http_404_NOT_FOUND`.
That status token separates a retired model from a rate limit months later without
persisting the response. Response bodies, source bodies, credentials, database
addresses, and raw provider errors are not copied into stored details or
user-visible failure messages; the provider's own message is written to the log
file only.

The chat CLI turns a run's failure code into one sentence for the user
(`explain_failure_code` in `app/services/failure_mapping.py`) and still shows the
exact code. The sentence is derived from the stored code, never from the
exception, so it cannot claim a cause the run did not record.

RAG generation and malformed-output exceptions return an `AnswerResult` with no answer
and no citations using `answer.generation_failed`. Invalid model citations get one
bounded, source-only repair attempt. If citations still fail validation, the answer
remains hidden with `answer.invalid_citation`; the CLI log records whether the chunk
ID was unknown or the quoted excerpt was absent from that source chunk, without
logging the raw answer or source text. Retrieval without sufficient official evidence
continues to return `answer.insufficient_evidence`.

Typed HTTP adapters use bounded `{code, message}` error details for invalid scope,
missing resources, and persistence unavailability. The monitoring trigger remains
idempotent: active-run reuse is a normal `202` response rather than an error.

Candidate state is fail-closed across every row in the matrix: a source or model failure
cannot activate knowledge documents, a rejected or failed review answer is re-asked and
writes nothing, and a cancelled or interrupted run is closed with `run.cancelled` or
`run.interrupted` without touching accepted data. Deterministic fixtures cover the stable
codes; the native-review demonstration separately covers valid reviewer choices backed by
captured evidence.
