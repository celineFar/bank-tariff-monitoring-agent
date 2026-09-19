# Monitoring Pipeline Implementation Plan

## 1. Purpose

This document is the working implementation plan for the phase that connects the
existing acquisition, structural-normalization, source-discovery, semantic-extraction,
knowledge-index, and RAG-retrieval components into one operational monitoring system.

The phase delivers:

- a typed catalog of all approved Ameria Bank seed URLs;
- durable scheduled and API-triggered runs;
- one shared application pipeline for both trigger paths;
- per-run source manifests and per-offering processing outcomes;
- candidate and accepted tariff snapshots with meaningful change detection;
- a dual-representation RAG corpus;
- evidence-bound question answering through one shared application service; and
- updated API, worker, ADK-tool, test, architecture, and checklist integration.

The goal is integration and lifecycle completion. The already implemented content
processing components are not to be redesigned in this phase.

## 2. Existing Components to Reuse

The implementation must compose the following existing boundaries:

- acquisition, including bounded HTML retrieval, Playwright rendering, network
  payload capture, linked-PDF download, artifacts, hashes, and URL controls;
- structural normalization for pages, PDFs, tables, and network payloads;
- source discovery, deterministic filtering, and Gemini-assisted classification;
- semantic extraction with typed loan-product schemas and evidence validation;
- Gemini document/query embedding adapters;
- PostgreSQL/pgvector document and chunk versioning;
- hybrid lexical/vector retrieval; and
- deterministic scalar normalization and existing change-comparison primitives.

Changes inside these components are limited to narrow integration defects or contract
extensions required by the agreed orchestration. Their established responsibilities,
model configuration, prompts, security controls, and generated ADK/A2A plumbing must
otherwise remain intact.

## 3. Agreed Architecture Decisions

### 3.1 Product and offering identity

`ProductType` remains the broad family:

- `consumer_loan`
- `mortgage`

Snapshots, source manifests, index metadata, API filters, and change history also use
a stable `offering_id`. A URL is not a business identity and may change without
breaking snapshot continuity.

Approved offering IDs:

| Product family | Offering ID | Seed URL |
|---|---|---|
| `consumer_loan` | `consumer_standard` | `https://ameriabank.am/en/personal/loans/consumer-loans/consumer-loans` |
| `consumer_loan` | `overdraft` | `https://ameriabank.am/en/personal/loans/consumer-loans/overdraft` |
| `consumer_loan` | `credit_line` | `https://ameriabank.am/en/personal/loans/consumer-loans/credit-line` |
| `consumer_loan` | `online_consumer_finance` | `https://ameriabank.am/en/personal/loans/consumer-loan/online-consumer-finance` |
| `mortgage` | `mortgage_online` | `https://ameriabank.am/en/personal/loans/mortgage/online` |
| `mortgage` | `mortgage_primary` | `https://ameriabank.am/en/personal/loans/mortgage/primary` |
| `mortgage` | `mortgage_diaspora` | `https://ameriabank.am/en/campaigns/mortgage-loan-for-diaspora` |
| `mortgage` | `mortgage_secondary_market` | `https://ameriabank.am/en/personal/loans/mortgage/secondary-market` |
| `mortgage` | `mortgage_commercial` | `https://ameriabank.am/en/personal/loans/mortgage/commercial-mortgage` |
| `mortgage` | `mortgage_express` | `https://ameriabank.am/en/personal/loans/mortgage/express-loan` |
| `mortgage` | `mortgage_no_income_verification` | `https://ameriabank.am/en/personal/loans/mortgage/no-income-verification` |
| `mortgage` | `mortgage_renovation` | `https://ameriabank.am/en/personal/loans/mortgage/renovation-mortgage` |
| `mortgage` | `mortgage_construction` | `https://ameriabank.am/en/personal/loans/mortgage/construction-mortgage` |

### 3.2 Seed catalog

The seed catalog will be checked-in YAML validated at startup into frozen Pydantic
models. Each entry will contain:

- product family;
- stable offering ID;
- display name;
- seed URL;
- enabled flag; and
- optional language and metadata.

Invalid families, duplicate offering IDs, duplicate active seeds, unsupported schemes,
or URLs outside the configured Ameria allowlist must fail during startup validation.

### 3.3 Orchestration approach

Use an imperative application coordinator, not an ADK graph and not event-driven stage
choreography. A concrete `TariffPipeline` composes the existing services and owns:

- run and per-offering lifecycle;
- idempotency and concurrency;
- stage ordering;
- failure isolation;
- source/run manifests;
- candidate-versus-accepted snapshot decisions;
- atomic publication; and
- terminal run status.

FastAPI, the scheduler/worker, and ADK tools are thin adapters around application
services. They must not duplicate pipeline logic.

### 3.4 Asynchronous run execution

`POST /api/v1/runs` is asynchronous:

- validate a typed run command;
- persist a `QUEUED` run;
- return `202 Accepted` with the durable run ID; and
- let the worker claim and execute queued work from PostgreSQL.

No external message broker is required in this phase. PostgreSQL is the durable queue.
The worker must claim work safely across multiple processes, using row locking such as
`FOR UPDATE SKIP LOCKED` plus product-family advisory locking where appropriate.

### 3.5 Typed trigger boundary

The run API accepts:

- required `product`: `consumer_loan` or `mortgage`;
- optional `offering_id` constrained to that family; and
- an optional `Idempotency-Key` HTTP header.

The HTTP route does not resolve free text. Natural-language product/offering resolution
belongs to the ADK layer, which submits the same typed command after resolution.
Scheduled jobs always submit canonical product families.

### 3.6 Idempotency and concurrency

- Only one `QUEUED` or `RUNNING` run may exist for a product family at a time.
- Repeating an idempotency key returns the original run.
- A new request received while its family already has active work returns the existing
  active run with `202`, rather than duplicating acquisition or Gemini work.
- Consumer-loan and mortgage runs may execute independently.
- Database constraints and locks, not process-local state, enforce these rules.

### 3.7 Scheduled monitoring

At 06:00 `Asia/Yerevan`, the scheduler enqueues two independent family runs:

- one `consumer_loan` run; and
- one `mortgage` run.

Each has its own run ID, status, lock, manifest, and failure outcome. A failure in one
family must not suppress the other or prevent a future schedule.

### 3.8 Partial-success behavior

A family run contains one or more offering executions. The family may finish as
`PARTIAL_SUCCESS`:

- persist each offering/source outcome independently;
- publish successful offerings;
- preserve the last known-good index and accepted snapshot for failed offerings; and
- do not treat an acquisition/discovery failure as evidence that an old source vanished.

Recommended run statuses are `QUEUED`, `RUNNING`, `SUCCEEDED`, `PARTIAL_SUCCESS`, and
`FAILED`. Per-offering statuses should distinguish pending/running/succeeded/failed and
candidate-review outcomes without overloading the family status.

### 3.9 Source discovery and retirement

This phase wires the existing acquisition and source-discovery behavior. It does not
introduce a new crawl or classification strategy.

A previously active source is never retired merely because it was not rediscovered.
Only a successfully indexed newer version with the same stable `document_key`
supersedes the prior active version. Administrative retirement is a future capability.

### 3.10 Dual RAG representation

The RAG corpus contains two complementary document kinds.

#### Source-faithful documents

- Derived from normalized source documents/Markdown.
- Preserve official wording and complete provenance.
- Keep a small source document whole when it fits configured limits.
- Split oversized content only at natural document, heading, table, or page boundaries.
- Never mix source documents or detach a table from the context needed to understand it.
- Carry source URL, document identity/version, offering ID, language, page/section,
  source locators, extraction method, checksum, and quality metadata.

#### Deterministic offering summaries

- One compact retrieval document per successfully extracted offering snapshot.
- Rendered deterministically from validated structured extraction; no second free-form
  Gemini synthesis step.
- Optimized for precise retrieval of product names, amounts, terms, rates, fees,
  conditions, and eligibility.
- Retains references to the underlying extraction evidence IDs/source chunks.
- Is a retrieval aid, not an official source, and must never be presented as the
  citation of record.

Semantic extraction already consumes the normalized bundle plus source-discovery
result directly. It does not depend on RAG, so indexing the deterministic summary after
extraction does not create a dependency cycle.

### 3.11 Snapshot acceptance lifecycle

Every semantic-extraction attempt is persisted for audit.

- A complete result that passes deterministic schema and evidence checks may become an
  accepted snapshot.
- `completed_with_review`, conflicting, malformed, or otherwise invalid results remain
  candidate snapshots.
- Candidate snapshots do not replace the latest accepted snapshot.
- Candidate snapshots do not generate tariff-change alerts.
- The prior accepted snapshot remains current until a new accepted snapshot is
  atomically published.

This phase does not introduce claim extraction or semantic claim verification. The
acceptance gate uses the existing extraction contract and essential deterministic
checks: schema validity, known evidence IDs, citation/evidence consistency, and the
rule that every found value has evidence.

### 3.12 Change semantics

Compare accepted snapshots for the same bank, family, and offering ID.

Meaningful comparison includes canonical structured business values, states, bounds,
currencies, units, and conditions. It excludes:

- retrieval and processing timestamps;
- formatting-only differences;
- prose wording that normalizes to the same business value;
- citation ordering; and
- evidence page/section/location changes when the supported value is unchanged.

Evidence-only changes remain persisted audit/provenance events but do not emit tariff
changes. The first accepted snapshot is `FIRST_OBSERVATION`, not a change.

### 3.13 Per-offering atomic publication

An offering is the publication unit. External calls and preparation occur before the
publication transaction. Once all required artifacts are ready, one database
transaction publishes:

- new knowledge-document versions and chunks;
- the extraction attempt and accepted/candidate decision;
- the accepted snapshot, when eligible;
- detected changes, when eligible;
- the source manifest; and
- offering/audit status updates.

If publication fails, the previous index and accepted snapshot for that offering remain
current. Successful sibling offerings are not rolled back.

### 3.14 RAG answer service

Both the HTTP question endpoint and ADK question tool call one shared
`RagAnswerService`. Its application contract is:

```text
QuestionCommand
  -> validate/resolve typed filters
  -> retrieve accepted offering summary and active source evidence
  -> build a bounded evidence packet
  -> perform one evidence-bound generation pass
  -> validate all returned citations against retrieved evidence
  -> return AnswerResult
```

`AnswerResult` includes:

- `status`: `ANSWERED`, `INSUFFICIENT_EVIDENCE`, or `AMBIGUOUS_PRODUCT`;
- resolved product and offering ID where available;
- answer text;
- citations with official URL, document name, excerpt, page/section, and chunk/evidence
  identifier; and
- snapshot `as_of` time.

Retrieval diagnostics are retained for audit but excluded from ordinary user output.
The service must abstain when evidence is insufficient or conflicting. The ADK root
agent may resolve intent and present the returned result, but must not perform a second
factual generation pass or replace citations.

## 4. Target Runtime Flow

```text
FastAPI typed request ----+
                          +--> Run submission service --> PostgreSQL QUEUED run
06:00 scheduler ----------+                                  |
                                                             v
                                                       worker claim/lock
                                                             |
                                                             v
                                                     concrete TariffPipeline
                                                             |
                  +------------------------------------------+------------------+
                  |                                                             |
          for each selected offering                                      run lifecycle
                  |
                  v
 acquire -> normalize -> discover/select -> semantic extract -> validate
                  |                                      |
                  |                                      +-> candidate/accepted snapshot
                  +-> source-faithful documents          +-> deterministic summary
                                      \                  /
                                       embed and stage
                                             |
                                             v
                              atomic per-offering publication
                                             |
                                             v
                        accepted snapshot comparison + audit/change records

Question API/ADK tool -> RagAnswerService -> active summary/source retrieval
                                         -> evidence-bound generation
                                         -> citation validation -> AnswerResult
```

## 5. Persistence Plan

Use forward-only migrations; do not rewrite already established migrations merely to
fit the new phase.

### 5.1 Monitoring runs

Extend or replace the minimal run schema with fields for:

- run ID;
- product family;
- optional requested offering ID;
- trigger (`api`, `schedule`, or `adk` if retained separately);
- idempotency key;
- status;
- request/query metadata when applicable;
- queued, started, and completed timestamps;
- failure code and bounded failure detail;
- aggregate counts; and
- created/updated timestamps.

Add constraints/indexes that enforce idempotency and active-family uniqueness safely.

### 5.2 Offering executions

Add a per-run/per-offering record with:

- run ID and offering ID;
- status and current stage;
- start/completion time;
- counts for sources, documents, chunks, warnings, failures, and review items;
- candidate/accepted snapshot IDs;
- failure code/detail; and
- manifest metadata.

### 5.3 Run/source manifests

Persist exactly what each run observed and attempted:

- configured seed and final URL;
- acquisition/normalization/discovery outcome;
- document key/version/checksum;
- selected/excluded status and reason;
- index write outcome;
- warning/failure codes; and
- stage timings/counts.

The manifest is audit data. It is not a duplicate copy of every source body.

### 5.4 Extraction attempts and snapshots

Persist:

- the semantic-extraction result or bounded structured projection needed for audit;
- candidate/accepted state and validation outcome;
- bank, product, offering ID, run ID, and timestamps;
- canonical comparison payload;
- evidence references; and
- linkage to the preceding accepted snapshot.

Only one latest accepted snapshot is selected by repository query; history remains
immutable/auditable.

### 5.5 Changes and audit events

Changes reference both accepted snapshots and store field/location, previous/current
canonical values, display values, and evidence. Audit events record stable event names,
correlation IDs, reason codes, and bounded structured payloads.

### 5.6 Knowledge-store extensions

Add offering and document-kind metadata/columns where necessary for mandatory filters.
Extend the repository with a batch/staged publication boundary so document versions,
chunks, snapshot state, and changes can become current atomically per offering.

Preserve existing deterministic document/chunk identity rules. A newer version with the
same `document_key` may retire the older active version. Absence alone never retires it.

## 6. Application Contracts

The exact class/module names may follow existing project conventions, but the following
responsibilities must remain distinct.

### 6.1 `SeedCatalog`

- Load and validate the YAML catalog once.
- List enabled offerings by family.
- Resolve and validate an offering ID within its family.
- Expose immutable domain models, not raw dictionaries.

### 6.2 `RunService`

- Submit typed API, ADK, and scheduled commands.
- Apply idempotency/active-family rules.
- Return the created or existing run.
- Read run and per-offering status.
- Claim queued work for the worker.

### 6.3 `IndexingPipeline`

`refresh(offering, run_id)` wires the existing components:

1. acquire the offering seed;
2. structurally normalize the acquired artifact;
3. run existing source discovery/selection;
4. run existing semantic extraction from the normalized/discovered evidence;
5. validate the extraction acceptance state;
6. build source-faithful `KnowledgeDocument` values;
7. build the deterministic offering summary when possible;
8. obtain embeddings before publication; and
9. return a prepared offering result and source manifest.

It must return typed results rather than writing ad hoc status strings.

### 6.4 Concrete `TariffPipeline`

- Mark a claimed run as running.
- Resolve the selected offerings from the catalog.
- Execute offerings with bounded concurrency; sequential execution is acceptable for
  the initial slice if it simplifies model/network limits.
- Isolate offering failures.
- Compare each accepted candidate with the prior accepted snapshot.
- Publish each offering atomically.
- Finalize the family as succeeded, partial success, or failed.
- Persist stable audit events throughout.

### 6.5 Snapshot repository

- Save all attempts as candidates or accepted snapshots.
- Get the latest accepted snapshot for one offering before the current run.
- Prevent pending/review/invalid results from becoming current.
- Persist and retrieve meaningful changes.
- Support atomic publication with the knowledge store.

### 6.6 `RagAnswerService`

- Accept a bounded question and optional typed filters.
- Retrieve only active source versions and accepted offering summaries.
- Generate once from supplied evidence.
- Validate citation identifiers and excerpts.
- Return a structured answer or explicit abstention.
- Never crawl or refresh websites during question answering.

## 7. API and Adapter Plan

### 7.1 Run API

- Replace the `501` run-creation placeholder with typed asynchronous submission.
- Return `202` and a representation containing at least run ID, status, product,
  optional offering ID, trigger, and status URL.
- Replace the run-status placeholder with repository-backed status and per-offering
  summaries.
- Map validation, unknown offering, conflict, and persistence failures to stable HTTP
  responses without exposing internal exceptions.

### 7.2 Question API

Add a question endpoint that calls `RagAnswerService`; it must not invoke acquisition.
Validate query length and typed filters, and return the structured answer contract.

### 7.3 Worker and scheduler

- Replace the scheduler logging placeholder with calls to `RunService`.
- Enqueue two independent family jobs at the configured time.
- Add a loop that claims queued runs and calls the same concrete `TariffPipeline`.
- Preserve graceful shutdown, coalescing, stable job ID, and bounded concurrency.
- Recover abandoned `RUNNING` work through an explicit timeout/recovery policy rather
  than silently leaving it active forever.

### 7.4 ADK tools

- Replace `start_tariff_monitoring`'s `SCAFFOLDED` result with typed run submission.
- Keep natural-language resolution in the ADK boundary and validate the resolved family
  and offering against the catalog.
- Add or wire a question tool to `RagAnswerService`.
- Do not expose repositories, SQL, filesystem, shell, raw HTTP, embedding clients, or
  unrestricted URLs to the model.
- Preserve `app/app_utils/` plumbing unless a concrete integration defect requires a
  narrowly scoped change.

### 7.5 Dependency composition

Create one composition root/factory used by FastAPI and the worker so they receive
equivalent repositories and the same concrete pipeline implementation. Manage shared
HTTP/database/client lifetimes at the application boundary; do not instantiate them in
domain models or per-field helpers.

## 8. Concrete To-Do List

Work in this order unless a discovered dependency requires a documented change.

### A. Baseline and contracts

- [x] Run `agents-cli info` and record the current scaffold/project state.
- [x] Run the existing deterministic unit/integration suite and record the baseline,
      keeping live credential/database cases explicitly identified.
- [x] Add offering identity and run/snapshot/result domain models.
- [x] Replace ambiguous string statuses with enums and validated Pydantic contracts.
- [x] Define stable error/reason codes for run, offering, indexing, snapshot, and answer
      failures.

### B. Seed catalog

- [x] Add the YAML catalog containing every approved URL in this document.
- [x] Implement frozen Pydantic catalog models and loader.
- [x] Validate uniqueness, family/offering compatibility, HTTPS, and allowlisted hosts.
- [x] Add unit tests for valid loading and every failure case.

### C. Persistence and migrations

- [x] Add forward-only migration(s) for enriched runs, offering executions, manifests,
      extraction attempts/snapshots, changes, and required audit links.
- [x] Add offering/document-kind fields and indexes needed by knowledge retrieval.
- [x] Add active-family and idempotency constraints/indexes.
- [x] Implement run queue/claim repository operations with safe row locking.
- [x] Implement snapshot/change repositories and latest-accepted selection.
- [x] Implement per-offering atomic publication across knowledge and snapshot state.
- [x] Add PostgreSQL integration tests for rollback, concurrency, idempotency, previous
      snapshot selection, and restart-safe queue behavior.

Implementation record (2026-09-19):

- `agents-cli info`: CLI version 1.6.1; valid Python/A2A project scaffolded with
  version 1.5.0; application directory `app`; no deployment target configured. The
  scaffold was not upgraded because upgrade work is outside this phase.

- Baseline command: `uv run pytest tests/unit tests/integration`, with the disposable
  PostgreSQL URL enabled and the ignored local-only
  `tests/unit/test_build_extraction_review_bundle.py` excluded. Result: 198 passed and
  three existing live integration tests failed (`test_agent_stream`, `test_adk_run_sse`,
  and `test_a2a_chat_stream`) because Gemini credentials and configured external database
  connectivity are unavailable in this environment.

- The excluded test is ignored by `.gitignore`, is not part of the repository, and imports
  the nonexistent `app.domain.discovery`; it was preserved unchanged.

- Focused A/B contract and catalog verification: 16 passed. New PostgreSQL durability
  verification: five passed. Existing pgvector knowledge-store verification: five passed.

### D. Knowledge-document projections

- [x] Implement source-faithful normalized-bundle to `KnowledgeDocument` projection.
- [x] Preserve locators for blocks, tables, PDF pages, and JSON paths.
- [x] Keep small documents whole and split oversized content at natural boundaries.
- [x] Implement deterministic `LoanProduct`/snapshot-to-summary rendering.
- [x] Mark document kind and ensure summaries reference underlying evidence.
- [x] Add stable-ID, content-hash, table, page, metadata, and repeatability tests.

### E. Pipeline orchestration

- [ ] Implement `IndexingPipeline.refresh(offering, run_id)` using the existing
      acquisition, normalization, discovery, extraction, and indexing services.
- [ ] Return a complete typed source manifest with counts, versions, warnings, and
      failures.
- [ ] Implement essential deterministic acceptance checks without claim verification.
- [ ] Implement canonical comparison payloads for rich extracted values and conditions.
- [ ] Implement the concrete imperative `TariffPipeline`.
- [ ] Isolate per-offering failures and compute family `PARTIAL_SUCCESS` correctly.
- [ ] Ensure a failed offering leaves its previous index/snapshot current.
- [ ] Add audit events and stage timings without logging source bodies or secrets.

### F. Trigger adapters and worker

- [ ] Implement typed run submission and run-status FastAPI routes.
- [ ] Implement idempotency-header and active-family behavior.
- [ ] Implement worker queue claiming/execution and abandoned-run recovery.
- [ ] Make the scheduler enqueue independent consumer-loan and mortgage runs.
- [ ] Replace the ADK monitoring tool placeholder with the shared run service.
- [ ] Add API/worker/tool tests proving all entry paths reach the same application
      service and cannot duplicate active family work.

### G. Snapshot and change lifecycle

- [ ] Persist every extraction attempt.
- [ ] Promote only complete, deterministically valid results.
- [ ] Retain review-required/conflicting/invalid results as candidates.
- [ ] Compare only against the preceding accepted snapshot for the same offering.
- [ ] Ignore formatting, timestamp, citation-order, and evidence-location-only changes.
- [ ] Persist provenance-only events separately from tariff changes.
- [ ] Test first observation, unchanged, meaningful change, status transition,
      candidate rejection, and failed publication rollback.

### H. RAG answering

- [ ] Define `QuestionCommand`, `AnswerResult`, citation, and answer-status models.
- [ ] Extend retrieval filters for offering/document kind where required.
- [ ] Retrieve deterministic summaries for precision and official source chunks for
      evidence/coverage.
- [ ] Implement bounded prompt construction and one generation pass.
- [ ] Validate citation IDs, excerpts, URLs, and locations against retrieved hits.
- [ ] Implement explicit insufficient-evidence and ambiguous-product outcomes.
- [ ] Add the HTTP question route and ADK question tool over the same service.
- [ ] Add deterministic tests with fake retriever/generator plus 1-2 initial ADK eval
      cases for grounded answers and abstention.

### I. Vertical-slice verification

- [ ] Exercise `consumer_standard` as the first end-to-end integration slice.
- [ ] Cover API submit -> queued run -> worker claim -> pipeline -> publication -> run
      status using fakes/fixtures by default.
- [ ] Verify unchanged reruns are idempotent and produce no false changes.
- [ ] Verify one failing sibling produces family `PARTIAL_SUCCESS` without rolling back
      successful offerings.
- [ ] Verify a question uses the index only and never triggers acquisition.
- [ ] Keep live network/Gemini/PostgreSQL tests opt-in and clearly marked.

### J. Documentation and checklist reconciliation

- [ ] Update `docs/architecture.md` for new package boundaries, entry points, routes,
      models, scheduler behavior, queueing, and persistence responsibilities.
- [ ] Add/update focused docs for seed catalog, run lifecycle, snapshot lifecycle,
      indexing projection, and RAG answer contract.
- [ ] Reconcile `Project Documents/architecture-components-todo-list.md` with actual
      completed acquisition, normalization, discovery, extraction, indexing, and
      retrieval work.
- [ ] Mark newly completed items only after their tests and acceptance criteria pass.
- [ ] Update API/configuration examples without adding secrets.

### K. Quality gates

- [ ] Run formatting/lint checks configured by the project.
- [ ] Run `uv run pytest tests/unit tests/integration` and resolve regressions.
- [ ] Run `agents-cli run` smoke tests after the ADK tools are wired.
- [ ] Load the agents-cli evaluation guidance before evaluation.
- [ ] Start with 1-2 eval cases, inspect scores/traces, fix failures, and iterate before
      expanding the dataset.
- [ ] Do not deploy; deployment requires a separate explicit human approval.

## 9. Testing Strategy

### Unit tests

Cover catalog validation, domain invariants, run state transitions, idempotency
decisions, source/summary projection, stable IDs, canonical snapshot comparison,
candidate acceptance rules, answer citation validation, and error mapping.

### Repository integration tests

Use PostgreSQL/pgvector to verify queue claiming, multiple-worker safety, uniqueness,
atomic publication, rollback, document supersession, non-retirement on absence, latest
accepted snapshot selection, and retrieval filters.

### Pipeline integration tests

Use fake acquisition/model/embedding adapters and representative normalized fixtures.
Prove stage wiring and lifecycle behavior without asserting nondeterministic model prose.
The first concrete source slice is `consumer_standard`; all catalog entries still
receive validation and routing coverage.

### Agent evaluation

Behavioral checks belong in agents-cli eval rather than unit tests. Initial cases should
cover:

- natural-language consumer-loan/offering resolution followed by typed run submission;
- grounded answering with valid citations; and
- insufficient evidence producing abstention.

### Live tests

Live Ameria, Gemini, and database tests remain explicit opt-in checks because credentials,
network access, costs, and external content can vary. Failures caused only by unavailable
live dependencies must remain distinguishable from deterministic regressions.

## 10. In Scope

- All approved seed URLs and stable offering IDs.
- YAML-to-Pydantic catalog validation.
- Shared scheduled/API/ADK run submission.
- PostgreSQL-backed queueing, idempotency, locking, and durable run status.
- Existing-component orchestration through a concrete `TariffPipeline`.
- Per-offering source manifests and partial-success behavior.
- Source-faithful knowledge documents and deterministic offering summaries.
- Embedding/index publication using existing adapters/store behavior extended for
  per-offering atomicity.
- Candidate and accepted snapshot persistence.
- Canonical structured change detection.
- Thin run/status/question API routes, scheduler/worker, and ADK tools.
- Shared `RagAnswerService`, grounded citations, and abstention.
- One deterministic consumer-loan end-to-end integration slice.
- Unit, repository integration, pipeline integration, smoke, and initial eval coverage.
- Architecture/checklist/configuration documentation updates caused by this work.

## 11. Out of Scope

- Claim extraction/generation as a separate pipeline stage.
- Semantic claim verification, repair, or claim-level publishability decisions.
- Redesigning acquisition, normalization, source discovery, or semantic extraction.
- A new recursive crawler or changed source-classification policy.
- Automatic retirement solely because a source disappears from discovery.
- A full administrative source-retirement interface.
- A multi-agent topology, ADK graph workflow, Pub/Sub, Kafka, Celery, or another broker.
- Crawling during question answering.
- Replacing PostgreSQL/pgvector with a managed vector-search product.
- Full HITL review UI and end-to-end approval/resume workflow; this phase persists
  candidate/review-required state so that later work can resume safely.
- Production authentication/authorization for public review or operations endpoints.
- Changing configured Gemini model IDs unless explicitly requested.
- Deployment, Terraform/infrastructure changes, CI/CD, AWS provisioning, production
  secrets, monitoring infrastructure, or publication to Gemini Enterprise.
- Broad performance tuning or retrieval-weight optimization beyond what is necessary
  to make the vertical slice correct and testable.

## 12. Completion Criteria

This phase is complete when all of the following are true:

1. Every approved seed is present in the validated catalog with the agreed offering ID.
2. API, schedule, and ADK monitoring triggers submit the same typed application command.
3. The API returns durable `202` run IDs and the worker safely claims queued work.
4. Duplicate/idempotent and concurrent family submissions cannot duplicate work.
5. One consumer-loan offering passes the deterministic end-to-end integration slice.
6. A family run can publish successful offerings and report `PARTIAL_SUCCESS` for failed
   siblings while preserving their last known-good state.
7. Every run exposes persisted per-offering/source manifests and controlled failures.
8. The index contains both source-faithful content and deterministic offering summaries,
   with official evidence traceable to original source locators.
9. Every extraction attempt is auditable, but only complete valid results become the
   current accepted snapshot.
10. Canonically equivalent snapshots produce no tariff changes; meaningful value or
    condition changes do.
11. Per-offering publication is transactional and failure leaves the prior current state
    intact.
12. HTTP and ADK question paths use the same answer service, produce validated citations,
    and abstain when evidence is insufficient.
13. The deterministic unit/integration suite passes, with live-dependency skips/failures
    documented separately.
14. Initial agents-cli eval cases have been run and their results reviewed.
15. `docs/architecture.md` and the architecture component checklist accurately reflect
    the implemented system.

## 13. Implementation Guardrails

- Never expose raw network, filesystem, shell, database, or SQL tools to Gemini.
- Preserve generated ADK/A2A plumbing in `app/app_utils/` unless explicitly required.
- Preserve existing model IDs and environment configuration unless explicitly asked to
  change them.
- Use `uv` for Python commands and the project-approved test commands.
- Keep model calls bounded, cached where already supported, and outside database
  transactions.
- Do not hold database transactions open across network, browser, embedding, or Gemini
  calls.
- Do not fabricate missing values or convert candidate/review results into accepted data.
- Do not cite deterministic summaries as official evidence.
- Keep logs bounded and free of secrets, full source bodies, and hidden chain-of-thought.
- Update this plan when an approved decision changes; record material deviations before
  implementing them.
