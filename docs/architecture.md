# Architecture

```text
FastAPI typed trigger ----+
                          +--> RunService --> PostgreSQL durable queue
ADK resolved trigger -----+                         |
Daily scheduler ----------+                         v
                                            worker claim/recovery
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

- `app/agent.py`: ADK root agent and stable instructions.
- `app/config/`: one environment adapter plus nested typed groups shared by API,
  agent, and worker; consumers depend only on the relevant group.
- `app/tools.py`: narrow ADK adapters that call application services. Monitoring
  submission requires a one-use, scope-bound authorization produced by the resolver.
- `app/api/`: user-trigger, run-status, and HITL review HTTP contracts.
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
- `app/security/`: URL, download, redirect, and logging guardrails.
- `app/runtime.py`: shared composition root for HTTP/worker run, review, and snapshot
  repositories, ingestion,
  `TariffPipeline`, `RunService`, `RequestResolver`, deterministic tariff query services,
  retrieval, and `RagAnswerService`.
- `app/worker.py`: PostgreSQL queue worker plus daily Asia/Yerevan scheduler; both
  scheduled families are submitted independently through `RunService`.
- `migrations/`: PostgreSQL/pgvector schema.
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

## Structural normalization boundary

Acquisition preserves what each source delivered; structural normalization makes
that material safe and predictable for chunking and evidence-bound extraction. Its
immutable `NormalizedSourceBundle` contains normalized documents, blocks, rectangular
tables, notes, scalar candidates, source references, quality scores, and typed
warnings. It never assigns tariff-field meaning.

HTML tables are reconstructed from cell coordinates and rowspan/colspan metadata,
with phantom columns and duplicate carry-only rows removed. A deterministic probe
records each PDF as machine-readable, image-only, mixed, or unknown, but its extracted
text is not used as business evidence. A tool-free ADK agent sends the original PDF
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

## Review and quarantine boundary

Typed review tasks are durable business records correlated to candidate snapshots and,
when available, ADK workflow identifiers. Candidate documents and chunks are persisted
inactive; they cannot displace the prior accepted active version. Same-scope newer reviews
supersede older pending reviews under a database lock and uniqueness constraint. Review
approval does not itself publish candidate data. See `docs/review-quarantine.md`.

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
  state. One active API/schedule/ADK run is allowed per product family.
- `offering_executions` isolates per-offering lifecycle and counters inside a family run.
- `source_manifests` links observed sources to their offering execution and optional
  knowledge-document version.
- `tariff_snapshots` stores every extraction attempt, its acceptance status, canonical
  hash, evidence, validation output, and link to the preceding accepted snapshot.
- `tariff_changes` links canonical field changes to the current and previous snapshots.
- `knowledge_documents` and `knowledge_chunks` carry offering and document-kind scope for
  retrieval and supersession.

`PostgresRunRepository.submit` serializes family submission with a PostgreSQL advisory
transaction lock, applies idempotency keys, and returns an existing active run when
appropriate. Workers claim queued rows with `FOR UPDATE SKIP LOCKED`; claim state is
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
