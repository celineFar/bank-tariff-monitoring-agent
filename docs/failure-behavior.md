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
| A linked document could not be downloaded or read (not a 404), and a field the last accepted snapshot found is no longer found | `source.linked_document_unavailable` | fail offering, nothing published; the previous tariffs stay current. Without such a lost field the failure stays a warning |
| Other terminal HTTP status | `source.http_status` | controlled source failure |
| Invalid/unsupported MIME | `source.mime_rejected` | reject source, no review |
| Invalid length or excessive bytes | `source.size_rejected` | reject source, no review |
| Redirect loop, limit, or missing location | `source.redirect_rejected` | reject source, no review |
| Invalid PDF signature | `source.signature_rejected` | reject source, no review |
| Headless browser cannot start | `source.browser_unavailable` | one retry after 10 s, then fail offering, no review; environment problem |
| Browser render or page interaction failed | `source.browser_failed` | one retry after 10 s, then fail offering, no review; no static fallback |
| Page below the completeness floor, or a sharp drop against the page's last good acquisition | `source.incomplete_content` | one retry after 10 s, then fail offering, no review; the audit payload lists the reasons (counts only); a drop keeps failing until `scripts/reset_acquisition_baseline.py` |
| Page/normalization parsing failure | `source.parsing_failed` | fail offering when no trustworthy evidence remains |
| PDF extraction failure | `source.pdf_extraction_failed` | fail offering when no trustworthy evidence remains |
| OCR fallback produced nothing | `source.ocr_failed` | recorded after every model attempt and OCR both failed; no values are emitted |
| Gemini/provider failure | `source.model_failed` | fail offering after bounded attempts, no review |
| Invalid structured model response | `source.malformed_structured_output` | bounded repair, then safe failure/review only with captured evidence |
| Other deterministic validation failure | `source.validation_failed` | reject candidate; never fabricate |

The acquisition retry (`acquire_with_retry`) covers only `source.browser_unavailable`,
`source.browser_failed` and `source.incomplete_content`: a browser failure or an
incompletely rendered page is often a network blip, so the page is fetched once more
after 10 s. Every other acquisition failure fails at once.

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

`POST /api/v1/questions` answers from accepted typed facts
(`app/services/answer_read_model.py`); no model writes the answer, so there is no
generation or citation-repair failure to report. An `AnswerResult` is `answered`
only when the structured query answered with at least one fact citation and an
`as_of`. Anything else — no accepted data, no evidence-backed fact for the field, an
incomparable ranking, or a scope that could not be turned into a plan — returns no
answer and no citations with `answer.insufficient_evidence`, and its audit metadata
carries the query status and reason. A request with no product returns
`answer.ambiguous_product`; an error while answering is a `503` with
`answer.persistence_failed`.

Typed HTTP adapters use bounded `{code, message}` error details for invalid scope,
missing resources, and persistence unavailability. The monitoring trigger remains
idempotent: active-run reuse is a normal `202` response rather than an error.

Candidate state is fail-closed across every row in the matrix: a source or model failure
cannot activate knowledge documents, a rejected or failed review answer is re-asked and
writes nothing, and a cancelled or interrupted run is closed with `run.cancelled` or
`run.interrupted` without touching accepted data. Deterministic fixtures cover the stable
codes; the native-review demonstration separately covers valid reviewer choices backed by
captured evidence.


## Embedding is off the publication path

A run embeds nothing. Its documents are stored as text (they anchor each fact's
evidence), and its retrieval units are published without vectors; the worker's
sweep embeds them later. An embedding refusal therefore never fails an offering:
a 5xx follows `EMBEDDING_MAX_ATTEMPTS` and `EMBEDDING_BACKOFF_BASE_SECONDS`, a 429
`EMBEDDING_QUOTA_*`, and when either budget is spent the sweep logs it and tries
again at its next interval. Until then the field finder searches those units
lexically.
