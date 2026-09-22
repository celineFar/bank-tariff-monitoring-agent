# Architecture

```text
FastAPI typed trigger ----+
                          +--> RunService --> PostgreSQL durable queue
ADK resolved trigger -----+                         |
Daily scheduler ----------+                         v
                                            worker claim/recovery
                                                    |
                                                    v
                                      resumable ADK monitoring workflow
                                                    |
                                                    v
                                           deterministic pipeline
 discovery -> secure retrieval -> deterministic PDF admission/input probe
 -> bounded Gemini PDF structure extraction + deterministic HTML parsing
 -> structural normalization -> cached/rule prefilter -> bounded Gemini source classification
 -> clean/chunk -> PostgreSQL + pgvector -> hybrid retrieval
 -> Gemini evidence-bound extraction -> deterministic validation
 -> snapshot comparison -> HITL routing -> report
```

Gemini is restricted to language-dependent intent resolution, bounded cache-aware
source classification, PDF structure transcription, and evidence-bound structured
extraction.
All security, persistence, validation, comparison, scheduling, and review routing controls
are deterministic application services. The ADK agent receives no raw network, filesystem,
shell, or SQL tool.

## Package boundaries

- `app/agent.py`: resumable ADK root chat agent, native `request_input`, and stable instructions.
- `app/cli.py` and `app/cli_entry.py`: interactive terminal entry points launched by `./tariff-chat` using a separate resumable ADK app. The entry module filters two known ADK experimental notices from the terminal. Rich renders the CLI chat, progress, field-matched review evidence, guided review prompts, and actionable API errors; the launcher checks that the container has the matching entry module before starting and sends CLI diagnostics to its own rotating `logs/cli.log`. Its `LongRunningFunctionTool` starts the same PostgreSQL worker run, returns an intermediate run ID, and the CLI polls persisted offering stages and run status before supplying a final function response to the original invocation. The review workflow prioritizes field-specific passages before its 20-passage prompt limit. The session ID allows recovery after the CLI exits. When a chat-level input call is no longer pending but the business run still awaits review, the CLI reads that run's saved review and resumes the durable ADK worker workflow directly without starting a new run.
- `app/config/`: one environment adapter plus nested typed groups shared by API,
  agent, and worker; consumers depend only on the relevant group.
- `app/tools.py`: narrow ADK adapters that call application services. Monitoring
  submission requires a one-use, scope-bound authorization produced by the resolver.
  Native root-chat review replies are read from ADK function responses and validated
  against the pending review and saved evidence.
- `app/api/`: user-trigger, run-status, and HITL diagnostics plus a token-protected
  `POST /api/v1/reviews/abort-pending` operation. Review decisions enter only
  through resumed ADK invocations.
- `app/domain/`: validated tariff/evidence models and pure business rules.
- `app/services/`: pipeline orchestration interfaces and deterministic application
  services. `AcquisitionService` combines restricted static HTML retrieval, faithful
  structural parsing, conditional Playwright rendering, bounded same-domain network
  capture, content-addressed artifact storage, and linked-PDF retrieval. `PdfDownloader`
  uses an injected, caller-owned HTTP client and returns
  immutable PDF artifacts only after URL/redirect, status, size, MIME, and signature
  checks complete. `StructuralNormalizationService` converts the acquired page,
  linked PDFs, and captured API payloads into one uniform evidence-linked bundle;
  HTML table reconstruction, scalar recognition, PDF admission/input-mode probing,
  and JSON-path flattening remain deterministic. PDF bytes cross only the tool-free,
  strict-schema Gemini PDF extraction boundary.
- `app/repositories/`: persistence interfaces and PostgreSQL implementations,
  including the transactional pgvector knowledge store and durable review repository.
  Offering execution stages are updated by the shared pipeline and read by the CLI
  to report progress during long monitoring runs.
- `app/security/`: URL, download, redirect, and logging guardrails.
- `app/runtime.py`: shared composition root for HTTP/worker run, review, and snapshot
  repositories, ingestion,
  `TariffPipeline`, `RunService`, `RequestResolver`, deterministic tariff query services
  (including the pending-review handoff), and `ChatReviewService` for original-chat
  review prompts, workflow resumption, and audited bulk abort,
  retrieval, and `RagAnswerService`.
- `app/services/structured_query_planning.py`, `app/services/intent_resolution.py`,
  and `app/tools.py`: deterministic bilingual resolution selects a bounded
  operation, canonical fields, conditions, and explicit offering IDs. ADK stores
  a 30-minute `ResolutionPlan` tied to the actual user text, session, and turn;
  `answer_tariff_query` consumes it once and accepts no model-supplied scope.
  The existing monitoring/review tools remain separate.
- `POST /api/v1/tariffs/query`: resolves a query server-side and uses the same
  `StructuredTariffQueryService` as ADK. It rejects caller-supplied scope fields
  and never triggers acquisition.
- `app/services/answer_read_model.py` and `TARIFF_ANSWER_READ_MODEL`: the
  reversible cutover switch. `structured` (default) answers every ordinary
  question from typed accepted facts; `legacy` restores the old RAG answer path
  with no code change while production behaviour is still being observed. The
  ADK `answer_tariff_query` tool, the post-monitoring answer, and
  `POST /api/v1/questions` all route through `TariffAnswerRouter`, so both read
  models stay inside the same authorized scope. After cutover `/questions`
  builds an equivalent typed plan from its own product/offering scope and
  returns fact-evidence citations; the model cannot change the switch.
- `app/services/model_call_usage.py` and `model_call_usage`: redacted, dated paid-tier
  model call/cost ledger shared by direct Gemini adapters and ADK callbacks. The
  read-only `scripts/model_cost_report.py` reports known and unknown costs;
  `docs/model-cost-monitoring.md` records coverage and pricing assumptions.
- `app/repositories/embedding_cache.py` and migration `012`: document-text vectors
  reused only for matching model, dimensions, task type, and content hash. The
  cache is content-addressed and independent of active document versions.
- `app/repositories/structured_projection.py`: writes accepted offering profiles,
  facts, evidence, and retrieval units in the snapshot publication transaction;
  reviewer activation rebuilds from final reviewed extraction in its own acceptance
  transaction. Pending candidates create no active read projection.
- `app/services/logging_setup.py`: shared console and rotating file logging for API and
  worker; Compose mounts host `logs/` for archives that survive container recreation.
  `configure_retrieval_logging` additionally routes the `tariff.retrieval`
  logger to its own rotating file when `RETRIEVAL_LOG_FILE` is set.
- `app/services/retrieval_trace.py`: per-call, correlated step trace of one
  structured retrieval on the separate `tariff.retrieval` logger, at the
  `RETRIEVAL_TRACE_LEVEL` detail level (`off`, `summary`, `steps`, `verbose`).
  A trace always closes, carrying the outcome or the error type. Only `verbose`
  writes derived search terms and rendered unit text. Its correlation id is the
  active OpenTelemetry trace id when one is recording, so a log line and a trace
  share one identifier.
- `app/services/telemetry.py`: OpenTelemetry bootstrap for all three entry points
  and the single boundary deciding what model content leaves the process. Spans
  are rewritten by a wrapping exporter (`OTEL_TRACE_CONTENT=none|mapped`); the
  setup refuses to start when `OTEL_EXPORTER_OTLP_*` is set, because ADK would
  then export the same spans unredacted. `inject_trace_context` and
  `extract_trace_context` carry W3C trace context through PostgreSQL, so the
  triggering process, the worker, and the process that resolves a human review
  all contribute to one trace. See [observability](observability.md).
- `app/services/run_metrics.py` and `scripts/run_metrics_report.py`: aggregate
  run duration, stage and document-retrieval failures, per-field extraction
  completeness, evidence coverage, HITL rate and decision latency, model
  reliability, and change volume, read from the durable audit tables. Run
  latency excludes time waiting for a reviewer.
- `app/worker.py`: PostgreSQL queue worker plus daily Asia/Yerevan scheduler; both
  scheduled families are submitted independently through `RunService`. Claimed work
  enters the resumable monitoring workflow, which invokes the shared `TariffPipeline`
  once and returns immediately when native human input is requested.
- `app/services/structured_projection.py`: pure, fail-closed projection of final accepted
  semantic extraction into offering profiles, typed tariff facts, verified citations,
  and clean evidence-backed retrieval units. Accepted projections are published
  transactionally. Loan amounts arrive wrapped in conditions while overdraft and
  credit-line credit limits do not, so the amount projector accepts both shapes.
- `app/repositories/structured_tariff_query.py` and
  `app/services/structured_tariff_query.py`: typed reads of active accepted profiles,
  verified fact evidence, and bounded retrieval units. Single-offering queries use
  weighted PostgreSQL full-text search with `simple` tokenization, then optional
  same-model vector retrieval when lexical recall is sparse. The service uses fixed
  reciprocal-rank fusion (`rrf-v1-k60-lex1-vector0.7`) for explanatory units.
  Exact comparisons, rankings, and history use accepted typed facts/changes, never
  generated arithmetic. Historical changes require verified old and new citations.
- `app/services/structured_unit_embeddings.py` and migration `013`: lazily embed
  active accepted retrieval units, with content-addressed reuse and explicit
  model/dimension checks; rejected or superseded units are not embedded.
  Publishing re-renders any unit left at a lower renderer version and clears its
  stale vector, so a renderer upgrade cannot leave old text searchable.
- `FIELD_LABELS` in `app/domain/structured_tariffs.py` and
  `lexical_search_terms` in `app/repositories/structured_tariff_query.py`:
  renderer version 2 writes a human field label beside each canonical path, and
  the lexical query drops bilingual function words and Armenian intra-word marks
  before building an OR query (`simple-or-v1`). Without both, `simple`
  full-text search matched no natural-language question.
- `scripts/run_demonstration.py` and `scripts/demonstrations/`: the assignment
  deliverable demonstrations with machine-checked success criteria. Each
  scenario drives the real services against a disposable `_test` database and
  exits non-zero unless every criterion passed; see `docs/demonstrations.md`.
  `scripts/demonstrations/capture.py` loads a recorded `end-to-end/run_NNN`, so
  the extraction demonstration replays a real page and a real model response
  instead of fixture values, and skips recordings written against an older
  schema. `scripts/demonstrations/runs.py` allocates the numbered run
  directories both scripts write into — `end-to-end/run_NNN` for a capture and
  `artifacts/demonstrations/run_NNN` for the transcripts — so no invocation
  overwrites an earlier one's audit record.
- `tests/fixtures/target_questions.py`, `tests/eval/structured_metrics.py`,
  `scripts/structured_eval_metrics.py`, `scripts/seed_evaluation_corpus.py`, and
  `scripts/trace_structured_answer.py`: the 25 target questions with their
  expected typed route and outcome, the model-free quality metrics over them,
  a seeder for a disposable `_test` database, and a stage-by-stage trace of the
  structured answer path. `tests/eval/RESULTS.md` records the measured scores.
- `app/services/structured_backfill.py` and
  `scripts/backfill_structured_tariffs.py`: dry-run and additive historical
  projection from accepted semantic extractions. Apply mode processes bounded
  snapshot batches within an offering transaction and publication advisory lock,
  preserving accepted history and activating only the newest projectable
  accepted version. Unprojectable latest versions leave no active projection.
  `app/services/structured_projection_audit.py` and its script compare typed
  stored facts and verified citations with canonical accepted extraction without
  model calls; failed evidence gates are reported.
- `app/services/structured_shadow_read.py` and
  `scripts/shadow_read_report.py`: read-only shadow comparison of the legacy and
  structured paths over a checked-in set of representative queries. It records
  statuses, fact/citation counts, latency, and evidence-source overlap, and logs
  only a question hash, never question text, source text, or generated wording.
  The structured path runs alone by default; `--with-legacy` additionally spends
  one embedding and one generation call per case. The cutover gate stays closed
  until both paths ran, the structured model answered at least one query, and
  every divergence was audited.
- `app/services/evidence_retention_audit.py` and
  `scripts/audit_evidence_retention.py`: prove each active accepted fact carries
  a self-contained citation (exact quote, locator, retained provenance document
  with a matching checksum) before the legacy summary/source embeddings are
  deprecated. An empty structured read model is reported as not ready, never as
  vacuously safe. Physical cleanup of `knowledge_chunks` remains a separate,
  unscheduled task.
- `migrations/011_structured_tariff_read_model.sql`: additive read-model tables
  `offering_profiles`, `tariff_facts`, `fact_evidence`, and `retrieval_units`, plus
  `model_call_usage` for call and cost monitoring. Live new runs populate these
  tables; historical accepted snapshots require the Phase F backfill.
- `migrations/`: PostgreSQL/pgvector schema.
  Project-owned event timestamps retain their `timestamptz` instants and have
  stored `timestamp` columns suffixed `_yerevan` for direct local-time inspection.
  Migration `009` generates and backfills those columns; ADK-owned tables are unchanged.
- `tests/unit/`: deterministic logic tests.
- `tests/eval/`: non-deterministic agent/RAG behavioral evaluation.

## Human-readable end-to-end inspection

`scripts/demonstrate_end_to_end.py` is the manual audit entry point for the implemented
pipeline stages. Given an official source URL, it invokes the normal acquisition,
Gemini PDF transcription, structural normalization, source-discovery, and semantic-
extraction services in one process. It does not introduce an alternative pipeline or
expose filesystem/network tools to either ADK agent.

The script writes source artifacts and readable reconstructions, inline annotated
normalization documents, detailed source-discovery decisions in
`selection_decisions.md`, a layout-preserving green/orange/red selection diff in
`selection_diff.md`, independent linked-document reports under
`source-discovery/documents/` (including one decision and one diff file per PDF), and
layout-preserving `selected_webpage.md` and per-document `selected_*.md` files. Those
selected Markdown files render `selected_sources.json`, the structured filtered bundle
used by semantic extraction. The semantic-extraction overlay highlights only exact
cited quotations with field labels. The root selection reports contain only the
canonical webpage so their layout remains directly comparable with acquisition.
Machine-readable plans and results are retained next to those reports.
Semantic extraction preserves source-discovery product association and effective
periods on every evidence item. Its deterministic planner reserves evidence capacity
per field, retains webpage/PDF provenance independently, excludes known sibling
variants from canonical-product packets, deterministically adapts known serialization
variants to the canonical field contracts, and invokes a bounded one-field ADK repair
only when evidence-aware validation still detects an invalid or suspicious value.
Each invocation atomically creates the next `run_NNN` directory beneath the
configured output root, preventing concurrent or repeated audit runs from overwriting
earlier evidence. Exact PDF, source-discovery, and semantic-extraction responses are
shared across those numbered runs under `end-to-end/.cache/`; their existing content,
model, prompt/schema version, product, and policy fingerprints must match before reuse.

## Pipeline audit archive

Every ordinary pipeline run — API, worker, and scheduler alike — collects the same
rendered Markdown overlays in one place. `app/services/pipeline_audit_archive.py`
is the deterministic sink: `IndexingPipeline.refresh()` hands it each stage output,
and it renders the reports from `app/services/pipeline_audit.py` off the event loop
into `<PIPELINE_AUDIT_DIR>/run_<run_id>/<offering_id>/`, by default
`artifacts/pipeline-audit/` (git-ignored). Filenames carry the stage number that
produced them:

| File | Stage |
|---|---|
| `0_run_context.md` | run, offering, and seed URL of the directory |
| `2_normalized_webpage.md`, `2_normalization_diff.md` | normalization |
| `3_source_selection_decisions.md`, `3_source_selection_diff.md`, `3_selected_sources.md` | source discovery |
| `4_extraction_evidence.md`, `4_pre_validation.md`, `4_review_queue.md` | semantic extraction |

Acquisition (stage 1) has no colour-coded overlay of its own; the acquired page
Markdown is the baseline of the stage 2 normalization diff. Source discovery and
semantic extraction also write their reports when the stage fails, with the stage
error rendered into the report, so a failed run remains inspectable. The semantic
extraction plan is captured before extraction runs, because afterwards its batches
are cache hits and the evidence overlay would report them as never sent. The archive
is best effort: an unwritable report is logged and never fails or alters a run, and
it stores no data that is not already persisted in PostgreSQL.

## PDF retrieval boundary

Official-source discovery hands a typed `PdfCandidate` to `PdfDownloader`; the
downloader is an application service and is not exposed directly to Gemini. It uses
a caller-owned `httpx.AsyncClient`, manually validates the initial URL and every
redirect target, and retries only timeouts, transport failures, HTTP 429, and HTTP
5xx responses with bounded exponential backoff, proportional jitter, and bounded
`Retry-After` support for both delta-seconds and HTTP-date values.

The service returns an immutable `DownloadedPdf` only after the complete stream has
passed the configured byte limit, `application/pdf` MIME check, and `%PDF-`
signature check. The result contains the source/final URLs, bytes, SHA-256 checksum,
size, retrieval timestamps, and only the bounded provenance headers ETag,
Last-Modified, and Content-Disposition. Failed or interrupted attempts return a
typed `PdfDownloadError` and never expose a partial document.

## Acquisition boundary

Acquisition is deterministic and does not decide what a loan field means. Initial URLs,
HTTP redirects, browser subrequests, and the final browser URL must pass the same exact
HTTPS host allowlist. Browser rendering is used only when static content is insufficient
or the DOM advertises interactive/client-rendered content. It blocks non-GET requests,
forms, downloads, cross-domain traffic, service workers, and unnecessary heavy assets.

The output is an immutable `PageArtifact` containing raw/rendered HTML, Markdown,
structural blocks, span-aware tables, linked FAQ questions and answers, inline links
with their original `href` and fragment targets,
image/control metadata, downloaded PDFs, bounded textual XHR/fetch payloads, source
locators, timestamps, and a deterministic content hash. Raw bytes are stored
under SHA-256-derived paths; source-controlled strings never become filesystem paths.
See `docs/acquisition.md` for the complete contract.

Acquisition, parsing, PDF, model, and validation exceptions are translated at the
pipeline boundary into stable source failure codes while retaining only exception type
and stage in bounded audit payloads. RAG generation/malformed-output failures return a
typed no-answer result. See `docs/failure-behavior.md`.

## Structural normalization boundary

Acquisition preserves what each source delivered; structural normalization makes
that material safe and predictable for chunking and evidence-bound extraction. Its
immutable `NormalizedSourceBundle` contains normalized documents, blocks, rectangular
tables, notes, scalar candidates, source references, quality scores, and typed
warnings. It never assigns tariff-field meaning.

HTML tables are reconstructed from cell coordinates and rowspan/colspan metadata,
with phantom columns and duplicate carry-only rows removed. A deterministic probe
records each PDF as machine-readable, image-only, mixed, or unknown, but its extracted
text is not used as business evidence. Before any model call, deterministic link
metadata decides admission: a document with no product-relevant term that matches an
off-topic marker is admitted as irrelevant, and (unless `PDF_EXTRACTION_SKIP_HISTORICAL`
is disabled) a document whose metadata resolves to a historical temporal status is also
skipped. Skipped documents yield an empty `pdf_skipped` normalized document and never
reach the model. Otherwise a tool-free ADK agent sends the original PDF
bytes to Gemini and requires page-complete blocks, rectangular tables, notes, and
footnotes. PDF outputs retain page locators and are cached by source hash, schema,
prompt, model, and admission/probe fingerprint. Captured JSON leaves retain exact JSON paths. Raw source text
and acquisition locators remain attached throughout, so later chunks and extracted
values can cite the original evidence rather than a rendered Markdown approximation.
See `docs/normalization.md` for the complete contract and inspection workflow.

## Source discovery boundary

`SourceDiscoveryService` consumes only the normalized bundle. It groups page blocks,
tables, PDFs, and API payloads into bounded classification units; applies deterministic
rules; reuses content-addressed PostgreSQL assessments; and sends only unresolved
semantic cases to a tool-free ADK classifier with strict structured output. Child
blocks and JSON leaves inherit their container decision, so model use scales with
semantic novelty rather than raw normalized block count.

Downloaded PDFs with strongly product-relevant link text, title, URL, or surrounding
heading receive a deterministic document assessment, so their extracted content is
not sent through source classification again. Relevance does not imply currentness:
archive/previous-term context and explicit effective dates independently classify a
PDF as current, historical, future, time-bounded, or unknown. Historical and future
documents remain auditable but are excluded from current-tariff extraction evidence.

Exact reuse requires matching product, content fingerprint, policy version, prompt
version, and model name. Stable structure with changed content supplies only a prior
hint and still requires reassessment. Deterministic Python validates response IDs,
persists assessments, expands inheritance, and constructs the precedence-ordered
extraction context. See `docs/source-discovery.md` for the full contract and no-LLM
preflight workflow.

## Semantic extraction boundary

`SemanticExtractionService` combines the normalized source bundle with the accepted
source-discovery assessments. It deterministically restores full normalized blocks,
table rows, and notes; assigns immutable evidence IDs; groups fields into bounded
packets; and sends only uncached packets to a tool-free ADK agent with a strict
structured response schema. Every packet includes the exact JSON Schema for each
requested field. Required documents use a dedicated completeness-oriented packet so
the webpage and admitted PDFs can be unioned without competing with other eligibility
fields for evidence capacity. The model cannot browse, fetch documents, query storage,
or alter the evidence packet.

Python validates each returned field independently, requiring known in-batch evidence
IDs and citation quotes that occur verbatim in the cited evidence. Valid fields are
retained even when another field is malformed. Invalid fields become deterministic
review records containing the raw value, validation paths, evidence references, batch,
and model; the run completes as `completed_with_review` with a partial product. A full
`LoanProduct` is emitted only when every field required for assembly validates. Exact
batch reuse requires matching product, schema version, prompt version, model name,
and selected-evidence fingerprint, and only wholly validated batches are cacheable.
Before validation, a deterministic contract adapter may only reshape documented
serialization variants (for example, amount ranges, term units, condition objects, and
percentage-point notation); both raw and adapted responses remain in the audit output.
Remaining repairs receive the original field, exact schema, validation paths, and only
the original batch evidence. Income verification and creditworthiness assessment are
separate requirement policies, and fees retain product-versus-general-service scope.
Umbrella products retain a typed variant catalog; repayment, age, application channel,
required-document, and collateral terms are conditional structured values keyed to
those variants where applicable. Canonical webpage identity is kept separate from
formal linked-document titles, and threshold-limited terms must be represented as
non-overlapping conditional subranges.
Invalid legacy cache entries are ignored. PostgreSQL migration
`004_semantic_extraction.sql` owns that cache. Claim generation, cross-source
verification/repair, snapshot comparison, and HITL decisions remain downstream.
See `docs/semantic-extraction.md` for the complete contract and demonstration flow.

## RAG index / knowledge-store boundary

`KnowledgeIndexer` accepts page-aware source-faithful and deterministic-summary chunks,
requests `RETRIEVAL_DOCUMENT` embeddings through an injected embedding provider, and
passes only validated 768-dimensional vectors to `PostgresKnowledgeStore`. Neither
the embedding client nor the repository is exposed as an ADK tool.

Document-version UUIDs are derived from bank, product, stable document identity, and
source checksum. Chunk IDs are SHA-256 digests of the document checksum and stable
location fields. Re-ingesting unchanged input therefore upserts the same rows. A
per-document PostgreSQL advisory transaction lock serializes concurrent ingestion;
new versions retire prior active versions and their chunks while retaining history.
Re-chunking the same version also retires chunks absent from the new input.

`knowledge_documents` retains source/version metadata, active state, retrieval time,
extraction method, and quality. `knowledge_chunks` retains page/section/language,
content, extraction metadata, a generated `tsvector`, and a `vector(768)` embedding.
GIN and HNSW indexes support the lexical/vector retrieval component implemented in a
later checklist item. Migration `002_rag_knowledge_store.sql` owns this schema.

## RAG retrieval boundary

`RagRetriever` accepts an already resolved bank, product, query, and tariff-field
scope. It creates a `RETRIEVAL_QUERY` embedding and calls only the narrow
`HybridRetrievalRepository`; no database handle or SQL operation crosses into the
agent/tool layer. `PostgresRagRetrievalRepository` unions full-text and cosine
candidates while enforcing bank/product and active-version predicates in every SQL
branch.

The application service performs documented weighted reciprocal-rank fusion,
absolute relevance scoring, threshold rejection, deterministic tie-breaking,
same-document overlap deduplication, and top-k limiting. It returns immutable typed
hits with complete document/chunk provenance, or an explicit
`INSUFFICIENT_EVIDENCE` result. See `docs/rag-retrieval.md` for the exact formula and
query contract.


## RAG answer boundary

`RagAnswerService` is shared by `POST /api/v1/questions` and the ADK question tool.
It retrieves active offering summaries and official source chunks with typed
bank/product/offering/document-kind filters, constructs a bounded evidence packet, and
performs one structured generation call. Summaries improve precision but cannot be
cited. Citation IDs and exact excerpts must match retrieved source chunks; URL,
document, page, and section are restored server-side. Missing scope returns
`ambiguous_product`; missing or invalid evidence returns `insufficient_evidence`.
Question answering never invokes acquisition. See `docs/rag-answering.md`.
`scripts/trace_rag_answer.py` runs this same answer path for one scoped question
and prints retrieval, generation, and citation-validation stages for inspection.

## Intent and offering resolution boundary

`RequestResolver` consumes only the versioned seed catalog and resolution settings. It
classifies the approved eight intents, detects English/Armenian/mixed input, resolves both
`ProductType` and `OfferingId`, and returns typed ambiguity rather than invoking business
services. Unicode/canonical/name/alias/transliteration exact matching runs first, followed
by conservative fuzzy ranking. Only insufficient deterministic results reach a tool-free
Gemini classifier, and Python restricts its output to the supplied enum values and catalog
candidate IDs.

Pending clarification and latest scope live only in ADK session state. A monitoring
intent creates a temporary one-use authorization for the exact resolved scope; the ADK
monitoring tool rejects missing, stale, mismatched, and non-monitoring authorization.
Typed API and scheduler commands remain classifier-free. See
`docs/intent-resolution.md`.

## Current tariff, history, and wait boundary

`CurrentTariffService` reads only latest accepted snapshots and classifies them with the
configured seven-day freshness policy. A newer review candidate is exposed only as a
boolean; its tariff values remain hidden. `TariffHistoryService` provides bounded accepted
snapshot and change reads with sixty-day “what changed?” and thirty-day history defaults.
Both services have typed HTTP and ADK adapters. `RunWaitService` is chat-side only and
polls persisted state for at most two minutes; `POST /api/v1/runs` remains asynchronous.
See `docs/tariff-query-services.md`.

## HTTP and lifecycle contract

FastAPI is the typed, non-chat surface. It does not classify free-form intent and it does
not expose a review-decision endpoint:

| Route | Contract |
|---|---|
| `POST /api/v1/runs` | Validate a canonical family/offering, enqueue through `RunService`, and return `202` plus the durable run, status link, and review-handoff link. |
| `GET /api/v1/runs/{run_id}` | Read the persisted run state and summary. |
| `POST /api/v1/questions` | Answer from the active evidence corpus through `TariffAnswerRouter`; never acquire sources. |
| `POST /api/v1/tariffs/query` | Resolve one free-text query server-side and answer it from accepted typed facts; caller-supplied scope is rejected. |
| `GET /api/v1/tariffs/current` | Read accepted snapshots only, with freshness and pending-newer-review indicators. |
| `GET /api/v1/tariffs/history` | Read bounded accepted snapshot/change history. |
| `GET /api/v1/reviews[/{review_id}]` | Inspect durable review records; decisions enter through native ADK resume only. |
| `POST /api/v1/reviews/abort-pending` | Token-protected admin rejection of pending reviews through their saved ADK workflow invocations. |
| `GET /api/v1/runs/{run_id}/review-handoff` | Read pending review scopes and the saved ADK Web session link for a paused run. |
| `GET /api/v1/healthz` | Liveness probe. |

ADK's own surface (`/dev-ui/`, the agent run endpoints) and the A2A routes under
`/a2a/app` are mounted by `get_fast_api_app` and the generated
`app/app_utils/a2a.py`; they are not project routes and carry no tariff contract
of their own.

The business lifecycle is `queued -> running -> awaiting_review -> terminal`, where the
terminal states are `succeeded`, `partial_success`, and `failed`. A run may go directly
from `running` to a terminal state. `awaiting_review` remains an active state for family
deduplication and owns no worker claim while waiting for a person.

State ownership is deliberately split. PostgreSQL business tables own runs, offering
executions, candidates, evidence, reviews, snapshots, changes, and publication state.
ADK session/event tables own workflow node progress, invocation/interrupt identity, and
the native function response. Correlation IDs link the stores; neither store silently
infers a decision belonging to the other.

## Review and quarantine boundary

Typed review tasks are durable business records correlated to candidate snapshots and,
when available, ADK workflow identifiers. Candidate documents and chunks are persisted
inactive; they cannot displace the prior accepted active version. Same-scope newer reviews
supersede older pending reviews under a database lock and uniqueness constraint. A native
decision is validated against its field schema and captured evidence. After all reviews
for a snapshot are approved, one database transaction updates and accepts the snapshot,
records its change set, activates candidate documents/chunks, retires replaced active
versions, and completes the offering. Rejection leaves the previous accepted publication
active. See `docs/review-quarantine.md` and `docs/native-hitl-review.md`.

## Resumable monitoring workflow boundary

`app/services/monitoring_workflow.py` wraps the imperative `TariffPipeline` in a
coarse-grained ADK 2.9.2 `Workflow`; deterministic acquisition, extraction,
normalization, validation, and persistence remain inside the application service rather
than becoming artificial agent nodes. The graph has explicit execute, outcome-routing,
native `RequestInput`, deterministic decision, and final-result nodes and enables
`ResumabilityConfig(is_resumable=True)`.

Each business run uses a stable session ID (`monitoring-run-{run_id}`) and a user ID
scoped to its API, schedule, ADK, or legacy-user origin. The runner uses the same shared
session and artifact services as the other ADK surfaces. When candidate data requires
review, `TariffPipeline` durably creates review tasks and changes the run from `RUNNING`
to nonterminal `AWAITING_REVIEW`; the request-input node then stores its app, user,
session, invocation, and interrupt identifiers on every pending task. The worker returns
as soon as the interrupt event is emitted.

Migration `008_monitoring_workflow.sql` includes `AWAITING_REVIEW` in active-run
uniqueness. Migration `010_offering_scoped_active_runs.sql` makes that boundary
specific to an offering, while keeping family-wide work exclusive across the family.
A paused run cannot be bypassed by another request for the same offering.

Resumption sends a native `adk_request_input` function response with the persisted
interrupt ID into that same session. ADK restores the paused invocation from its events,
so completed pipeline work is replayed as node output rather than executed again. Only a
narrow deterministic decision service may accept the bounded response, validate its
candidate/evidence references, rebuild the reviewed snapshot, and transition the business
run to a terminal state. Reviewer identity is derived from and checked against the
persisted ADK user/session correlation rather than accepted from the response payload.
`RuntimeAgentLoader` exposes the composition-root workflow `App` in ADK Web while keeping
its repositories injected. No module-level repository handle is used by workflow nodes.

The shared service factory resolves the validated PostgreSQL `SESSION_SERVICE_URI` even
in the headless worker, whose Pydantic `.env` loading does not mutate process environment
variables. FastAPI and worker startup eagerly prepare and require ADK 2.9.2 JSON session
schema version `1`; ADK Web, A2A, the conversational runner, and the monitoring runner all
resolve the same cached `shared://session` instance within each process and the same
PostgreSQL event store across processes.

`WorkflowReconciliationService` runs before normal worker recovery. It bounds scans,
recreates missing request-input events for live pending reviews, fails an orphaned
`AWAITING_REVIEW` run safely, completes a paused run whose reviews are all terminal, and
reports stale/orphaned interrupts without supplying or inventing a decision. Pause,
resume attempt, approval/rejection, failed resume, supersession, and reconciliation
outcomes are durable business audit events. PostgreSQL restart coverage disposes the
first ADK service after pause and resumes through a new service instance while proving
that deterministic pipeline work executes exactly once.

## Indexing coordinator boundary

`IndexingPipeline.refresh()` orders acquisition, normalization, discovery, extraction,
projection, embedding, and atomic publication for one offering. `TariffPipeline` owns
the family run and isolates siblings, allowing `partial_success`. Source-faithful
documents preserve normalized evidence locations; accepted snapshots additionally
produce deterministic offering summaries. See `docs/indexing-projection.md`,
`docs/run-lifecycle.md`, and `docs/snapshot-lifecycle.md`.

## Offering and seed-catalog boundary

`OfferingId` is the stable identity of a concrete bank offering; `ProductType` remains
the broader consumer-loan or mortgage family. The frozen catalog models in
`app/domain/catalog.py` bind each offering to exactly one family and approved seed URL,
with validated English and Armenian names, aliases, synonyms, and transliterations for
both families and every offering.
`app/config/seed_catalog.yaml` is the runtime source of truth for the thirteen approved
URLs from `Project Documents/Loan_data_extraction.md`. The loader rejects duplicate
offering identities, duplicate enabled URLs, family mismatches, non-HTTPS URLs, and
hosts outside the acquisition allowlist before a run can be submitted.

A `RunCommand` without an `offering_id` fans out to every enabled offering in the
product family, so it costs a multiple of a single-offering run. `start_tariff_monitoring`
therefore returns `needs_scope_confirmation` with the offering count the first time an
unscoped run is requested in a session, and submits only after the caller repeats the
request. Chat agents pass the `offering_id` that `resolve_request` resolved, so an
ordinary question about one offering never launches the whole family.

Offering identity and `KnowledgeDocumentKind` participate in knowledge-document and
chunk identities. Consequently, two offerings cannot overwrite one another even if they
share structural source keys. Knowledge rows are never retired merely because an
offering was absent or a run failed; only publication of changed content for the same
bank, product, offering, document kind, and document key supersedes that source’s
previous active version.

## Monitoring run and publication persistence

The frozen contracts in `app/domain/monitoring.py` define run commands and lifecycle,
offering executions, source manifests, extraction attempts/snapshots, change sets,
publication results, and question/answer results. Lifecycle and outcome values are enums,
and stable namespaced failure codes make API, worker, audit, and retry behavior
machine-readable.

Migration `006_monitoring_pipeline_foundation.sql` adds the durable queue and publication
foundation:

- `monitoring_runs` owns trigger, scope, idempotency, claim, timing, summary, and failure
  state. Targeted offerings have independent active runs; a family-wide run
  conflicts with every targeted run in its product family.
- `offering_executions` isolates per-offering lifecycle and counters inside a family run.
- `source_manifests` links observed sources to their offering execution and optional
  knowledge-document version.
- `tariff_snapshots` stores every extraction attempt, its acceptance status, canonical
  hash, evidence, validation output, and link to the preceding accepted snapshot.
- `tariff_changes` links canonical field changes to the current and previous snapshots.
- `knowledge_documents` and `knowledge_chunks` carry offering and document-kind scope for
  retrieval and supersession.

`PostgresRunRepository.submit` serializes family submission with a PostgreSQL advisory
transaction lock, applies idempotency keys, and returns an existing run only when its
scope overlaps the request. Migration `010` replaces the single active-family index
with indexes for targeted offerings and family-wide runs. Workers claim queued rows with `FOR UPDATE SKIP LOCKED`; claim state is
stored in PostgreSQL. On startup, the worker marks expired running claims failed before
claiming new work, which releases the family constraint without replaying partially
published work.

`POST /api/v1/runs`, the ADK monitoring tool, and the 06:00 scheduler all submit the
same typed `RunCommand` through `RunService`. The HTTP adapter returns `202` with the
durable run record and honors `Idempotency-Key`; `GET /api/v1/runs/{run_id}` reads the
same repository state. Only the worker invokes `TariffPipeline`, after a durable claim.

`PostgresOfferingPublicationRepository` publishes the offering’s knowledge versions,
source manifest, snapshot, optional change set, execution status, and audit event in one
database transaction. Any indexing or persistence failure rolls back the entire offering
