# Agent Intent, Native HITL, and Reliability Implementation Plan

## 1. Purpose

This plan extends the completed monitoring-pipeline foundation with three connected
capabilities:

1. bilingual intent, product-family, and offering resolution;
2. native Google ADK human-in-the-loop pause and resume; and
3. explicit, testable safe-failure behavior across acquisition, extraction, RAG,
   persistence, and concurrency.

The implementation must preserve the modular-monolith boundary. The monitoring stages,
scheduler, validation, persistence, change detection, and publication remain deterministic.
A coarse-grained ADK workflow wraps the existing `TariffPipeline` only at meaningful
control boundaries: execute, route outcome, request human input, resume, apply a validated
decision, and report the final state.

The governing specification is `.agents-cli-spec.md`. If this plan and the specification
ever differ, update them together before implementation continues.

## 2. Inspection Baseline

### 2.1 Verified current state

- Unit baseline on 2026-09-20: `194 passed`, with four existing warnings.
- Git worktree was clean before the specification and this plan were written.
- Installed Google ADK version: `2.9.0`.
- Latest approved stable Google ADK version at planning time: `2.9.2`.
- `ProductType` has two families: `consumer_loan` and `mortgage`.
- `OfferingId` and `seed_catalog.yaml` define thirteen offerings: four consumer-loan
  offerings and nine mortgage offerings.
- Snapshots, runs, source manifests, knowledge documents, and retrieval already carry
  offering identity.
- FastAPI, ADK tools, and the scheduler submit through the shared run service; the worker
  invokes the concrete `TariffPipeline`.
- Per-offering publication is transactional and accepted snapshots are offering-scoped.
- Hybrid RAG supports product, offering, and document-kind filters and rejects candidates
  below a configured relevance threshold.
- Extraction validates structured fields and citations, attempts bounded repair, and can
  preserve valid sibling fields when one batch fails.
- `human_reviews` exists in the first migration, but no concrete review repository or
  native workflow integration exists.
- `/api/v1/reviews` routes return `501`.
- `HitlSettings.document_rank_gap` and
  `HitlSettings.large_rate_change_percentage_points` are configured but unused.

### 2.2 Central gaps

- `resolve_product()` is a small family-only substring matcher. It does not resolve intent,
  offering, aliases, fuzzy candidates, or session clarification.
- The agent instruction names only two families and does not describe the thirteen
  configured offerings or first-interaction behavior.
- “Current tariffs” is answered through general RAG rather than a latest-accepted-snapshot
  service with freshness semantics.
- Run status does not represent a paused, resumable review state.
- `REVIEW_REQUIRED` snapshots do not create actionable review records or ADK interrupts.
- Semantic `conflicting` is currently a valid extraction status and is not guaranteed to
  block acceptance.
- Review-pending source documents can be published into the active knowledge store even
  when the snapshot is not accepted.
- RAG answer generation exceptions are not converted into controlled answer failures.
- Failure codes are often collapsed to broad offering-stage errors, losing useful causes
  such as timeout, MIME rejection, or malformed model output.

## 3. Agreed Product and Interaction Policy

### 3.1 Explicit intent taxonomy

Use the following typed intents:

- `LIST_SUPPORTED_PRODUCTS`
- `ANSWER_INDEXED_TARIFF_QUESTION`
- `GET_CURRENT_TARIFFS`
- `START_MONITORING_RUN`
- `GET_RUN_STATUS`
- `GET_CHANGE_HISTORY`
- `UNSUPPORTED_OR_GENERAL`
- `CLARIFICATION_RESPONSE`

An indexed question never starts acquisition. A history request never starts acquisition.
Only an explicit monitoring/refresh request or the user's affirmative response to a stale
data offer submits a run.

### 3.2 Catalog presentation

On the first assistant response in a chat session:

- briefly name consumer loans and mortgages;
- name a few representative offerings from each family;
- offer to show the complete catalog; and
- call them configured/supported offerings, not offerings proven to have indexed data.

Do not repeat the introduction on every turn.

### 3.3 Resolution cascade

Resolve intent and scope in this order:

1. Unicode normalization, case folding, punctuation/space normalization, and reviewed
   transliteration normalization.
2. Canonical ID, exact localized display name, reviewed alias, and synonym lookup.
3. Conservative fuzzy matching with configurable minimum score and minimum top-candidate
   gap.
4. Gemini classification constrained to enumerated catalog and intent IDs.
5. Clarification with two or three concrete choices if the result remains ambiguous.

Gemini must never generate a new offering ID. Store English and Armenian names, aliases,
synonyms, and optional transliterations in the versioned seed catalog rather than agent
prompt constants.

### 3.4 Family-only requests

- Family-wide monitoring runs every enabled offering in the family.
- A broad overview question summarizes all indexed offerings in the family.
- A question expecting one value, such as “What is the mortgage rate?”, asks the user to
  choose an offering.

### 3.5 Language

Respond in Armenian for Armenian input, English for English input, and the dominant
language for mixed input. Default to English only when the language is genuinely unclear.
Canonical IDs remain language-neutral.

### 3.6 Current data and history

- Read current tariffs from the latest accepted snapshot, not from an arbitrary newest
  RAG chunk.
- Default freshness threshold: seven days.
- A stale accepted snapshot may be displayed only with its as-of time and a clear warning.
- Ask whether to refresh stale data unless the user explicitly requested a fresh run.
- With no accepted snapshot, return no tariff values and offer monitoring.
- “What changed?” reports accepted changes within sixty days; otherwise state that no
  change was detected in the last sixty days and optionally report the older last-change
  date.
- “Show history” defaults to thirty days and supports bounded explicit filters.

### 3.7 Bounded monitoring wait

In chat, after submitting a monitoring request:

- say that monitoring has started;
- wait on persisted run state for at most two minutes;
- return the final result if available;
- return the durable run ID and current state if still queued, running, or awaiting review;
- never describe a queued or pending candidate as fresh accepted data.

The typed HTTP API remains asynchronous and returns `202` without holding the request for
the conversational wait period.

## 4. Target Architecture

### 4.1 Entry paths

```text
ADK chat ───────────────┐
                       │
POST /api/v1/runs ─────┼─> RunService queue ─> worker ─> ADK MonitoringWorkflow
                       │                             └─> TariffPipeline
daily scheduler ───────┘
```

- Chat resolves free-form language before submitting a canonical `RunCommand`.
- The typed API and scheduler already have canonical IDs and make no intent-classification
  model call.
- All monitoring commands use the same queue, worker, durable workflow, and concrete
  `TariffPipeline`.
- Do not add a second “direct pipeline” monitoring endpoint that bypasses native HITL.

### 4.2 Coarse-grained ADK workflow

Implement a graph with only meaningful control/resume boundaries:

```text
START
  -> resolve_scope
  -> execute_monitoring
  -> route_outcome
       ACCEPTED -> build_final_result
       FAILED -> build_failure_result
       REVIEW_REQUIRED -> request_human_input
                            [ADK RequestInput; invocation pauses]
                         -> apply_review_decision
                         -> route_decision
                              APPROVED -> build_final_result
                              REJECTED -> build_rejection_result
                              UNRESOLVED -> request_human_input or safe stop
```

`execute_monitoring` calls the existing deterministic `TariffPipeline`. Acquisition,
normalization, discovery, PDF extraction, semantic extraction, embedding, and publication
do not become separate graph nodes merely to make the system appear more agentic.

### 4.3 Native HITL contract

- Configure the ADK `App` with `ResumabilityConfig(is_resumable=True)`.
- Persist ADK sessions/events in PostgreSQL through the existing shared session-service
  registration; do not use in-memory sessions for reviewable workflows.
- Emit a typed `RequestInput` payload containing `review_id`, reason code, offering scope,
  candidate choices, bounded evidence summaries, and allowed decision types.
- Treat an unanswered `adk_request_input` event as the native pending-approval signal.
- Resume with a function response tied to the exact interrupt and invocation.
- Reload the business review row on resume; never trust stale workflow state as current
  publication authority.
- Return control to the worker when the workflow pauses. Do not hold a worker loop or HTTP
  request open waiting for a reviewer.

### 4.4 State ownership

PostgreSQL business tables own:

- monitoring and offering run state;
- candidates, source evidence, and validation results;
- review reason, choices, status, reviewer, and decision;
- accepted snapshots, active documents, and changes.

ADK persisted sessions/events own:

- node progress;
- paused invocation and interrupt identity;
- native resume input;
- workflow completion events.

Link them with `run_id`, `offering_execution_id`, `review_id`, `session_id`,
`invocation_id`, and `interrupt_id`. Neither store is allowed to infer the other's terminal
state silently.

### 4.5 Reference patterns to reuse

From `core/python/ambient-expense-agent`:

- `Workflow` function-node routing;
- `RequestInput` as the pause boundary;
- pending review discovery from an unanswered `adk_request_input` event;
- resume through a matching function response;
- integration testing of trigger -> pause -> resume -> decision;
- immediate return from a headless trigger once the workflow pauses.

Do not copy its in-memory-session default, duplicated threshold constant, Pub/Sub,
Terraform, notification, or custom frontend.

From `core/python/long-horizon-harness`:

- `ResumabilityConfig(is_resumable=True)`;
- a runner built over an injected durable session service;
- explicit result envelopes that distinguish completed, failed, timed out, and paused;
- tagged sessions for headless/scheduled execution;
- resuming from stored function responses without rerunning completed work.

Do not adopt sub-agents, sandboxing, memory-bank behavior, or its broad web application.

From `core/python/rag-vector-search`:

- keep write-side document state and read-side retrieval filters symmetrical;
- preserve deterministic IDs and idempotent ingestion/publication;
- evaluate answer quality separately from deterministic unit contracts.

Retain PostgreSQL/pgvector; do not adopt Vertex Vector Search, KFP, or Terraform.

## 5. Native HITL Policy

### 5.1 Complete review scenarios

Create a native ADK review pause for:

1. an otherwise valid nominal or effective interest-rate change of at least three absolute
   percentage points;
2. incompatible values from a current official PDF and current official webpage for the
   same field and conditions;
3. captured official documents whose offering/effective-period applicability cannot be
   deterministically resolved; and
4. a missing required field after bounded repair when usable official evidence remains
   available for human inspection.

Do not create review solely because multiple official documents exist if they agree.

### 5.2 Fail without HITL

Fail the offering, preserve the previous accepted snapshot, and create no review for:

- unusable PDF extraction;
- low-quality PDF/OCR output;
- page parsing failure without trustworthy evidence;
- exhausted infrastructure/network/Gemini failures;
- unsafe URL, redirect, MIME, signature, or size rejection;
- database failure; or
- any condition where a reviewer has no trustworthy evidence choice to make.

### 5.3 Reviewer choices

For a conflict, native human input may:

- select one captured evidence-backed candidate;
- reject every candidate; or
- propose a value with a reason and a reference to existing captured evidence.

The decision service must reject unsupported values, nonexistent evidence IDs, evidence
outside the review scope, mismatched offering/conditions, malformed values, and decisions
against superseded or terminal reviews.

### 5.4 Publication behavior

- Candidate snapshots and documents are quarantined and excluded from ordinary RAG.
- Approval revalidates the complete snapshot and atomically activates the snapshot,
  eligible change set, and documents.
- Rejection keeps the previous accepted snapshot/documents active and retains the rejected
  candidate for audit.
- Duplicate resume inputs return the already-recorded decision and cannot publish twice.
- A newer candidate or accepted observation for the same offering and issue scope marks
  the older pending review `SUPERSEDED`.
- Resuming a superseded interrupt returns a safe terminal result and performs no write.

### 5.5 Run states

Add nonterminal `AWAITING_REVIEW`:

- `QUEUED`: submitted, not claimed;
- `RUNNING`: workflow/pipeline executing;
- `AWAITING_REVIEW`: native ADK invocation is paused;
- `SUCCEEDED`: every targeted offering accepted;
- `PARTIAL_SUCCESS`: at least one offering accepted and at least one failed/rejected;
- `FAILED`: no targeted offering accepted.

Do not use top-level `COMPLETED_WITH_REVIEW`; a resumable invocation is not complete.

## 6. Persistence Design

### 6.1 Review model

Replace the underspecified `human_reviews` contract with a typed forward migration that
retains or safely extends existing data. The final record needs:

- `id`, `run_id`, `offering_execution_id`, `product`, and `offering_id`;
- typed `reason_code` and `issue_scope`;
- `PENDING`, `APPROVED`, `REJECTED`, `SUPERSEDED`, and `FAILED` statuses;
- candidate values and allowed choices as bounded JSON;
- evidence references, not duplicate unrestricted source bodies;
- candidate snapshot ID and previous accepted snapshot ID;
- ADK app, user, session, invocation, and interrupt identifiers;
- reviewer identity, decision payload, reason/comment, and timestamps;
- replacement/supersession link;
- optimistic version or uniqueness constraints for idempotent decision application.

### 6.2 Candidate document visibility

Current knowledge rows need explicit publication visibility or equivalent staging:

- `candidate`/inactive documents are persisted for review but excluded from hybrid search;
- accepted documents become active only with accepted snapshot publication;
- rejected/superseded documents remain inactive and auditable;
- previous active versions are not retired until the replacement is accepted.

Update retrieval SQL and indexes so every normal answer path enforces accepted visibility,
not merely `is_active` if that flag can currently be set during candidate publication.

### 6.3 ADK session persistence

- Set `SESSION_SERVICE_URI` to the PostgreSQL SQLAlchemy URI in local/docker runtime.
- Keep the `shared://session` indirection so ADK Web, A2A, FastAPI, and worker runners use
  the same service instance/contract.
- Add an explicit session-schema migration/startup procedure compatible with ADK 2.9.2.
- Use in-memory sessions only in deterministic tests that do not claim restart durability.
- Add restart integration coverage against PostgreSQL for a paused workflow.

### 6.4 Reconciliation

Implement a bounded reconciliation service and worker startup check for:

- pending business review with no stored ADK interrupt;
- paused ADK interrupt with no live business review;
- business-terminal review with a still-resumable interrupt;
- superseded review whose workflow has not been safely terminated;
- run stuck in `AWAITING_REVIEW` after every review became terminal.

Reconciliation reports and safely repairs status linkage; it never invents or auto-approves
a decision.

## 7. Intent and Catalog Design

### 7.1 Catalog extensions

Extend each seed entry with reviewed fields such as:

- `display_names.en` and `display_names.hy`;
- `aliases.en` and `aliases.hy`;
- `transliterations`;
- optional family-level aliases stored in a catalog-level section.

Validate nonblank normalized aliases, uniqueness within an ambiguity scope, supported
language keys, and collisions that would make deterministic resolution unsafe.

### 7.2 Domain contracts

Add typed models for:

- `IntentType`;
- `ResolutionStatus` (`RESOLVED`, `AMBIGUOUS`, `UNSUPPORTED`);
- family/offering `ResolutionCandidate` with method and deterministic score;
- `ResolvedRequest` with intent, family, offering, language, confidence source, and
  clarification choices;
- session clarification state;
- current-tariff query/result with freshness;
- history query/result;
- workflow outcome and review resume payload.

Do not expose raw similarity scores as business confidence or let the LLM provide an
unvalidated floating-point confidence.

### 7.3 Deterministic matcher

- Normalize once through a single tested function.
- Prefer exact ID/name/alias matches over fuzzy candidates.
- Scope offering candidates by an already-resolved family where available.
- Require both a minimum fuzzy score and a minimum gap over the runner-up.
- Return ranked candidates and reasons without resolving ties.
- Keep thresholds configurable and calibrate them from the bilingual resolution dataset.

### 7.4 Gemini fallback

- Use a strict Pydantic output schema.
- Supply only bounded user text and enumerated candidates.
- Use temperature zero and the existing configured generation model.
- Validate returned IDs against the supplied candidate set.
- On API failure, malformed output, low discriminative result, or multiple candidates,
  return clarification rather than retrying indefinitely or guessing.
- Cache only safe normalized classifier inputs if a cache is justified by evaluation;
  do not cache session-dependent clarification state as a global answer.

### 7.5 Session behavior

Use ADK session state for:

- `catalog_intro_shown`;
- pending intent;
- pending candidate IDs;
- last resolved family/offering.

Clear pending candidates after successful clarification, cancellation, unsupported input,
or a new request that replaces the pending intent. Do not add cross-session personal
memory.

## 8. Current Tariff, Status, and History Services

### 8.1 Current tariff service

Add a deterministic repository/service that returns latest accepted snapshots by family
and optional offering, including:

- accepted timestamp and age;
- `FRESH`, `STALE`, or `MISSING` freshness state;
- evidence-bearing normalized tariff;
- pending newer review indicator without exposing quarantined values.

Do not infer “current” from document retrieval rank.

### 8.2 Run wait/status service

- Reuse `RunService.get` under a bounded asynchronous wait helper.
- Use a configurable two-minute maximum and bounded poll interval.
- Stop immediately on terminal status or `AWAITING_REVIEW`.
- Return an explicit incomplete envelope at timeout.
- Do not block the worker, scheduler, typed run API, or database transaction.

### 8.3 Change/history repository

Add offering/family-scoped reads for accepted snapshots and change sets with bounded date
ranges and result limits. Return explicit states for first observation, unchanged within
window, last change outside the sixty-day window, and unavailable history.

## 9. Failure-Handling Audit and Target Behavior

| Scenario | Current state | Target behavior |
|---|---|---|
| Website unavailable/timeout | Handled in `HtmlRetriever` with bounded transient retries; pipeline records a broad acquisition failure | Preserve retries; persist the precise cause and fail the offering without review |
| 404/missing page or PDF | Non-success status is rejected; linked PDF failure becomes a warning and processing may continue | Do not retry 404; preserve a per-source manifest reason; accept only if remaining evidence independently satisfies validation |
| Invalid MIME type | HTML and PDF retrievers reject unsupported content | Keep fail-closed behavior and expose stable source-level reason codes |
| Oversized download | Header and streaming byte limits exist | Keep behavior; prove no model/parser call occurs after rejection |
| Redirect problems | Allowlist, loop, missing-location, and maximum-redirect checks exist | Keep behavior; persist the specific redirect reason and final safe URL when available |
| HTML parsing failure | Exceptions propagate to acquisition/normalization stage failure | Add stable parse reason; fail without HITL unless usable independently captured evidence remains |
| PDF extraction failure | PDF model retries/fallback exist; exhaustion fails normalization | Preserve bounded fallback; fail offering without HITL and keep previous accepted state |
| OCR/image-only failure | Input probe distinguishes page modes and Gemini consumes original PDF, but no complete quality gate/failure contract exists | Treat unusable or low-quality result as offering failure without review; add fixture coverage for scanned pages |
| Gemini/API failure | Bounded retries exist in PDF/discovery/extraction paths; RAG answer generation is not safely mapped | Normalize retryability and stable failure codes; map RAG generation failure to controlled answer failure |
| Malformed structured output | Extraction validates and repairs; discovery validates IDs; RAG parses directly and may raise | Keep bounded repair; add controlled RAG failure and never accept unresolved output |
| Missing required fields | Extraction can create review items and a review-required snapshot, but no durable task exists; `not_stated` can be accepted too broadly | Require evidence for explicit inapplicability/absence; otherwise quarantine and enter native HITL when usable evidence exists |
| Conflicting values | `conflicting` can be a valid semantic status and may not block acceptance | Preserve separate candidates/evidence, block acceptance, and enter native HITL |
| Multiple candidate documents | Relevant sources are included, but rank-gap settings and document-selection HITL are unused | Accept agreeing sources; review unresolved applicability; never let Gemini silently decide authority |
| Product/sub-product not found | Basic family substring matcher returns ambiguous; offering resolution is absent | Use the resolution cascade and conversational clarification; invoke no business tool until resolved |
| Irrelevant RAG retrieval | Minimum score and explicit insufficient-evidence result exist | Preserve abstention; test irrelevant bilingual queries and candidate-only exclusion |
| Invalid RAG citation | Citation ID and exact excerpt validation exist | Preserve; return insufficient evidence rather than model prose |
| RAG generator failure | Exception can escape | Return typed `GENERATION_FAILED`/controlled failure without fabricated answer |
| Previous snapshot unavailable | Correctly treated as first observation | Preserve and expose clearly in history/current responses |
| Database/persistence failure | Atomic publication rollback and worker catch exist; API/service mappings are incomplete | Preserve rollback; use stable typed errors/HTTP mapping; no review task for infrastructure failure |
| Duplicate/concurrent runs | Idempotency key, advisory locks, unique active-family index, and safe queue claiming exist | Preserve; extend tests through the ADK workflow wrapper |
| Review-pending data visibility | Candidate snapshot is not accepted, but source documents may still become active | Quarantine all candidate documents until approval |
| Stale review resume | No workflow/review implementation exists | Reject superseded/terminal resumes idempotently and publish nothing |
| ADK process restart during review | Default local session service may be in memory | Use PostgreSQL session/event persistence and prove restart-safe resume |

## 10. API and Agent Surface Changes

### 10.1 Preserve typed non-chat APIs

- Keep `POST /api/v1/runs` as the canonical machine trigger.
- Keep `GET /api/v1/runs/{run_id}` and extend its response/status for workflow linkage and
  `AWAITING_REVIEW`.
- Keep `POST /api/v1/questions`, but route current/history operations to their dedicated
  deterministic services rather than pretending every request is generic RAG.
- Add typed current-tariff and change-history endpoints if needed for non-chat parity.

### 10.2 Review routes

- Implement optional read-only `GET /api/v1/reviews` and
  `GET /api/v1/reviews/{review_id}` for diagnostics.
- Remove, deprecate, or leave unavailable `POST /reviews/{review_id}/decision`.
- The only assignment decision path is native ADK human input through ADK Web/session
  resume.

### 10.3 Agent tools and instructions

- Replace `resolve_product` with the typed resolver boundary.
- Add focused catalog, current snapshot, run status/wait, and history tools.
- Keep monitoring submission thin; it must not execute the pipeline inside the LLM tool
  call.
- Update agent instructions with intent distinctions, first-interaction behavior,
  clarification rules, bilingual response policy, stale-data language, and strict
  non-fabrication rules.
- Do not expose the review-decision tool to the ordinary conversational agent unless the
  active invocation is the constrained review workflow.

## 11. Concrete To-Do List

Work in this order. Do not combine phases merely to reduce commit count; each phase has a
separate correctness boundary.

### A. Baseline and ADK upgrade

- [x] Record `agents-cli info`, Python version, installed ADK version, and clean test
      baseline.
- [x] Change the ADK dependency constraint/lock to approved stable `2.9.2` without changing
      Gemini model IDs.
- [x] Run `uv sync` and import/smoke tests for App, Runner, Workflow, `RequestInput`, ADK
      Web, A2A, and current shared service registration.
- [x] Run the full deterministic suite and resolve only upgrade-caused regressions.
- [x] Record migration/compatibility notes before feature work.

### B. Intent and catalog contracts

- [x] Add intent, resolution, candidate, clarification, language, freshness, and history
      domain models.
- [x] Extend the YAML/Pydantic seed catalog with localized names, aliases, synonyms, and
      transliterations for all thirteen offerings and both families.
- [x] Add collision, uniqueness, family/offering compatibility, and normalized-empty-value
      validation.
- [x] Add bilingual catalog fixtures reviewed against the current Ameria offering names.
- [x] Update `docs/seed-catalog.md`.

### C. Deterministic and Gemini resolution

- [x] Implement the single Unicode/transliteration normalization function.
- [x] Implement exact canonical/name/alias resolution.
- [x] Implement conservative fuzzy ranking with configurable minimum score and score gap.
- [x] Implement constrained Gemini fallback over supplied candidate IDs only.
- [x] Implement clarification choices and session continuation for replies such as “the
      express one.”
- [x] Implement the eight-intent classifier and ensure non-monitoring intents cannot call
      acquisition.
- [x] Add unit tests for Armenian, English, mixed language, aliases, typos, collisions,
      unsupported requests, ties, and Gemini failure.

### D. Current, status, wait, and history services

- [x] Add repositories for latest accepted snapshots and bounded accepted history/change
      reads.
- [x] Implement seven-day freshness classification.
- [x] Implement sixty-day “what changed?” and thirty-day history defaults.
- [x] Implement the bounded two-minute run wait helper with early stop on review/terminal
      state.
- [x] Add focused agent tools and typed HTTP parity where appropriate.
- [x] Test stale, missing, pending-newer-review, first observation, unchanged, old change,
      timeout, and terminal results.

### E. Review and quarantine domain

- [x] Define typed review reason, decision, choice, status, and correlation models.
- [x] Add a forward migration extending/replacing the legacy `human_reviews` shape safely.
- [x] Add review repository operations: create idempotently, list/get, attach workflow
      identifiers, claim/lock for decision, approve, reject, supersede, and fail.
- [x] Add candidate document visibility/staging state and supporting indexes.
- [x] Change publication so review-required documents remain inactive and prior accepted
      documents remain active.
- [x] Add deterministic supersession rules for newer same-scope observations.
- [x] Add PostgreSQL integration tests for duplicate create/decision, concurrent reviewers,
      rollback, supersession, and active-index isolation.

### F. Deterministic review routing

- [x] Add conflict detection that preserves distinct PDF/web candidates and conditions.
- [x] Ensure any unresolved `conflicting` field blocks snapshot acceptance.
- [x] Add the three-percentage-point nominal/effective rate-change rule.
- [x] Add unresolved document-applicability routing.
- [x] Distinguish evidence-backed explicit absence from unsupported missing required fields.
- [x] Route reviewable missing fields to review and non-reviewable extraction/quality
      failures to offering failure.
- [x] Prove agreeing official sources retain all evidence without creating review.

### G. Durable ADK monitoring workflow

- [x] Add typed workflow input/output/state schemas.
- [x] Implement coarse-grained execute, route, request-input, decision, and final-result
      nodes.
- [x] Configure `ResumabilityConfig(is_resumable=True)`.
- [x] Build the workflow Runner over the shared session service and existing application
      container; avoid new global repository access from nodes.
- [x] Create/tag one durable workflow session per monitoring run with stable user/session
      identity rules for API, schedule, and chat origins.
- [x] Store workflow correlation identifiers in the business review record.
- [x] Mark the business run `AWAITING_REVIEW` when `RequestInput` is emitted.
- [x] Return worker control immediately on pause.
- [x] Resume the same invocation from the native function response and do not rerun
      completed pipeline work.
- [x] Apply decisions through a narrow deterministic service and finalize run state.

### H. ADK session/event durability

- [x] Configure PostgreSQL `SESSION_SERVICE_URI` for FastAPI, ADK Web, A2A, and worker.
- [x] Document and automate the ADK 2.9.2 session schema migration/startup check.
- [x] Ensure every serving surface uses the existing `shared://session` registration.
- [x] Add a restart test: pause, dispose runner/process boundary, recreate services, resume,
      and verify exactly-once publication.
- [x] Add reconciliation for missing/mismatched review and workflow state.
- [x] Add audit events for pause, resume attempt, approved, rejected, superseded, failed
      resume, and reconciliation outcome.

### I. Native reviewer experience

- [x] Define bounded `RequestInput` message/payload schemas for large change, source
      conflict, applicability, and missing field.
- [x] Ensure ADK Web displays enough product, field, candidate, source URL, page/section,
      and excerpt information to decide.
- [x] Support select, reject, and evidence-linked override inputs.
- [x] Validate reviewer identity from the ADK/session boundary.
- [x] Keep any project review HTTP routes read-only and document ADK Web as the sole
      decision interface.
- [x] Demonstrate a paused scheduled/API-triggered run being resumed by a reviewer.

### J. Failure-code and adapter hardening

- [x] Introduce stable source-level codes for timeout, status, MIME, size, signature,
      redirect, parsing, PDF, model, and validation failures.
- [x] Preserve precise causes in manifests/audit while bounding user-visible detail.
- [x] Convert RAG generator/API and malformed-answer errors into typed controlled results.
- [x] Map validation, missing resource, active-run reuse, and persistence failures to
      stable HTTP responses.
- [x] Verify no failure path creates or activates a fabricated tariff value.

### K. Agent instruction and session integration

- [x] Update the agent instruction and tools without changing the configured model.
- [x] Add one-time short catalog introduction behavior.
- [x] Store and clear pending clarification state correctly.
- [x] Implement intent-sensitive family behavior.
- [x] Implement Armenian/English response selection.
- [x] Implement stale/current/review-pending wording that cannot imply unaccepted data is
      current.
- [x] Keep unsupported/general requests within the tariff-monitoring capability boundary.

### L. Deterministic tests

- [x] Unit-test every new domain invariant and resolver branch.
- [x] Unit-test review routing and decision validation with no live model.
- [x] Unit-test workflow routing with fake pipeline/decision services.
- [x] Integration-test native pause/resume using an in-memory service for fast coverage.
- [x] PostgreSQL-test durable pause/resume, restart, concurrency, supersession, and atomic
      activation.
- [x] Extend trigger-adapter tests to prove chat/API/schedule reach the same workflow and
      `TariffPipeline`.
- [x] Add controlled failure fixtures for every row in the failure matrix.
- [x] Run `uv run pytest tests/unit tests/integration` until green.

Phase L verification (2026-09-20): the deterministic command excludes the opt-in live
Gemini/server files with `--ignore tests/integration/test_agent.py --ignore
tests/integration/test_server_e2e.py`; it passes locally. PostgreSQL cases remain collected
and skip only when `TEST_DATABASE_URL` is absent. The unfiltered command still reports the
known missing Gemini credential and unavailable configured database host rather than a
deterministic regression.

### M. Agent evaluation loop

- [x] Load the agents-cli evaluation guidance immediately before evaluation.
- [x] Start with one bilingual resolution/clarification case and one grounded current-data
      case.
- [x] Run `agents-cli eval run`, inspect traces/scores, and fix the first failure class.
- [x] Repeat the eval/fix loop until the core cases meet the agreed bar.
- [x] Expand to all eight intents, all thirteen offerings, fuzzy aliases, ambiguity,
      stale-data behavior, unsupported requests, and tool-routing safety.
- [x] Add native HITL behavioral coverage using deterministic workflow integration tests;
      do not assert variable LLM prose in pytest.
- [x] Use `agents-cli eval compare` before merging later resolver/prompt changes.


Phase M verification (2026-09-21): core 2/2 mean 5.00; expanded 22/22 mean 5.00 after a 3.64 baseline. `agents-cli eval compare` confirmed improvement without a case regression. All eight intents are covered across live eval and deterministic session-continuation tests; ADK 2.9.2 rejects state-bearing initialization events, so `CLARIFICATION_RESPONSE` remains in the real two-turn deterministic suite. Native pause/resume and PostgreSQL restart coverage passed (18 tests).

### N. Documentation and demonstration

- [x] Update `docs/architecture.md` for the ADK workflow, persistence ownership, routes,
      run statuses, review lifecycle, and worker behavior.
- [x] Add focused docs for intent resolution, native HITL, failure behavior, and reviewer
      demonstration.
- [x] Update `docs/run-lifecycle.md`, `docs/snapshot-lifecycle.md`,
      `docs/rag-answering.md`, `docs/configuration.md`, and the architecture checklist.
- [x] Document the typed API as the non-chat monitoring entry point.
- [x] Document ADK Web as the local native review interface.
- [x] Provide one large-change and one PDF/web-conflict demonstration script/fixture.
- [x] Record known production gaps: reviewer authorization, notifications, and deployment.

Phase N verification (2026-09-21): architecture and lifecycle docs now define typed HTTP entry points, run/review state ownership, worker pause/resume, quarantine, and accepted-only RAG behavior. `scripts/demonstrate_native_hitl.py` renders validated large-change and official PDF/web-conflict request payloads; focused workflow/demo tests pass (8 passed). ADK Web is documented as the local decision interface, with production authorization, notification, and deployment gaps explicit.

### O. Final quality gates

- [x] Run project formatting, lint, type, and codespell checks.
- [x] Run the complete deterministic test suite.
- [x] Run `agents-cli run` smoke tests for catalog, resolution, current tariffs,
      monitoring, status, history, and unsupported requests.
- [x] Run the approved initial eval suite and record results.
- [x] Verify migrations against a fresh database and an existing migrated database.
- [x] Verify no pending/rejected/superseded document is returned by normal RAG.
- [x] Verify restart-safe native HITL end to end.
- [x] Do not deploy; deployment requires separate explicit approval.

Phase O verification (2026-09-21): `agents-cli lint` passed Ruff formatting/lint, ty, and codespell; 334 source-controlled deterministic tests passed with PostgreSQL (the ignored local legacy bundle test and two opt-in live tests were excluded); all seven `agents-cli run` scenarios routed safely; and the approved core eval rerun scored 2/2 at 5.00. Migration 001-007 -> 008 and fresh 001-008 paths passed, ADK session schema version 1 passed, normal RAG excluded pending/rejected/superseded documents, and PostgreSQL pause/dispose/resume completed without rerunning the pipeline. No deployment command was run.

## 12. Testing Strategy

### 12.1 Pytest responsibilities

Use pytest for deterministic contracts:

- normalization and matching;
- typed model validation;
- catalog collision detection;
- workflow routing with fake services;
- review repository transitions;
- transaction rollback and exactly-once publication;
- URL/download/model failure mapping;
- native interrupt/resume event shape;
- accepted-only retrieval filtering.

Do not assert nondeterministic response wording in pytest.

### 12.2 Evaluation responsibilities

Use `agents-cli eval` for:

- intent classification;
- Armenian/English response quality;
- imprecise/fuzzy offering interpretation;
- appropriate clarification;
- correct tool choice and absence of forbidden tool calls;
- evidence-grounded answers and abstention;
- stale/current communication quality.

### 12.3 Initial evaluation dataset

Begin with two cases, then expand:

1. Armenian or imprecise offering request that must resolve or ask a constrained
   clarification.
2. Current-tariff question that must use accepted data, cite evidence, and communicate
   freshness correctly.

The expanded set should contain at least:

- one positive and one ambiguous example for every intent;
- every offering ID at least once;
- Armenian, English, mixed, transliterated, alias, and typo variants;
- stale, missing, review-pending, first-observation, and insufficient-evidence cases;
- unsupported financial-advice and general requests.

## 13. Implementation Slices

### Slice 1: Resolution and read-only user experience

Deliver catalog extensions, intent/offering resolution, clarification state, current
snapshot freshness, run status/wait, and history reads. This slice changes no publication
or review behavior and can be evaluated independently.

### Slice 2: Review domain and quarantine

Deliver review persistence, deterministic routing, candidate-document quarantine,
supersession, and decision services without exposing a custom decision endpoint. Verify
all state transitions and atomic publication with direct service tests.

### Slice 3: Native ADK HITL

Deliver the durable workflow, PostgreSQL session persistence, `RequestInput`, ADK Web
review, native resume, and restart/reconciliation tests. Demonstrate large-change approval
first, then the PDF/web conflict workflow.

### Slice 4: Reliability completion and evaluation

Complete failure-code mapping, RAG error containment, all failure fixtures, documentation,
smoke tests, and the iterative ADK evaluation suite.

## 14. Completion Criteria

This phase is complete only when:

1. All thirteen offerings resolve through reviewed bilingual catalog data, with ambiguity
   producing clarification rather than a guessed tool call.
2. Every one of the eight intents has passing behavioral coverage.
3. Current tariffs come only from latest accepted snapshots and enforce seven-day
   freshness communication.
4. API, chat, and schedule triggers reach the same durable ADK workflow and deterministic
   `TariffPipeline`.
5. A large rate change and a PDF/web field conflict both pause through native ADK
   `RequestInput`, survive restart, and resume the same invocation.
6. The run remains `AWAITING_REVIEW` while paused and reaches the correct terminal status
   after decisions.
7. Reviewer choices are evidence-bound, validated, idempotent, and fully audited.
8. Pending, rejected, failed, and superseded data never enters ordinary RAG results.
9. Every requested failure scenario has a deterministic test and the agreed controlled
   outcome.
10. No failure or review path fabricates or silently promotes a tariff value.
11. Unit/integration tests, lint/type checks, smoke tests, and the initial eval loop pass.
12. Architecture, configuration, lifecycle, reviewer, and demonstration documentation
    accurately describe the implemented system.

## 15. Explicitly Out of Scope

- Decomposing every monitoring stage into an ADK graph node.
- Letting Gemini control downloads, validation, authority, review approval, SQL, or
  publication.
- A custom reviewer decision API or bespoke reviewer frontend.
- Push/email/Slack review notifications.
- Production authentication/authorization implementation.
- Additional banks, families, or non-rate anomaly thresholds.
- Replacing PostgreSQL/pgvector with managed vector search.
- Deployment, Terraform, CI/CD, or infrastructure changes.
- Changing Gemini generation or embedding model IDs.

## 16. Implementation Guardrails

- Modify only the packages and documents directly required by this phase.
- Preserve generated ADK/A2A plumbing unless the shared durable workflow/session boundary
  requires a narrowly documented change.
- Keep model calls outside database transactions.
- Keep reviewer payloads bounded and refer to stored evidence by ID.
- Never hold a transaction, worker poll loop, or HTTP request open across human review.
- Treat ADK session state as workflow execution state, not business publication authority.
- Recheck business review status on every resume.
- Preserve the prior accepted snapshot/index until replacement approval commits.
- Use `uv` for Python execution and the project-approved test commands.
- Stop after three repetitions of the same error and diagnose the root cause.
- Do not deploy without explicit human approval.
