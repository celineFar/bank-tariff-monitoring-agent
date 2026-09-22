# Structured Tariff Retrieval Implementation Plan

## 1. Purpose and outcome

Replace the current broad summary plus source-chunk answer path with an accepted-snapshot
read model built from typed, evidence-linked extraction. The read model must answer
single-offering questions, comparisons, family-wide extrema, and accepted change history
without asking vector search to perform numeric reasoning. Bounded retrieval remains
available for product descriptions, nuanced conditions, and exact source quotations.

This plan covers the 25 questions in the design discussion. It changes the query read
side, not the monitoring trigger policy: ordinary questions never start acquisition.
Both FastAPI and ADK must use the same application service. The model receives no raw
SQL, database, filesystem, shell, or network tool. Do not change configured Gemini
model IDs or generated `app/app_utils/` integration code.

## 2. Current baseline and invariants

- `LoanProduct` already has names, variants, category, purpose, conditional amounts,
  rates, terms, fees, eligibility, special conditions, and product-specific details.
- `tariff_snapshots.normalized_tariff` stores the canonical values, while
  `semantic_extraction` and `evidence` retain the extraction/evidence records. The
  canonical value tree omits provenance, so projection must reconnect each value to
  its validated citation. Reviewer overrides update both snapshot values and the
  semantic extraction record.
- `knowledge_chunks` contains rendered source text and embeddings, not original PDF
  bytes or HTML files. Original artifacts remain in content-addressed artifact storage.
- `knowledge_documents` carries bank, product family, offering ID, document kind,
  publication state, and version. Current hybrid SQL joins it to `knowledge_chunks`.
- Pending, rejected, superseded, and retired material must never answer ordinary
  questions. An accepted older snapshot remains current while a newer review is pending.
- Every non-missing tariff fact used in an answer must have verifiable official-source
  evidence. Keep exact quotes, source URLs, document version/checksum, and locators.
- Source artifacts remain available for audit/reprocessing under an explicit retention
  policy; artifact references alone are insufficient when remote pages can change.

## 3. Target read model

Create forward-only migrations and typed domain/repository contracts for these
versioned projections. `tariff_snapshots` remains the authority; projections are
rebuildable and never become independent accepted data.

| Projection | Required data | Query role |
|---|---|---|
| `offering_profiles` | Snapshot ID; bank, family, offering ID; catalog and extracted names/aliases; category, purpose, variants, market, applicability; accepted time; active state; schema version | Resolution aid, family filters, high-level description |
| `tariff_facts` | Snapshot ID; stable fact/field path; status; typed JSON value; one row per conditional variant; normalized numeric bounds, unit/currency/rate basis/type and fee scope where applicable; conditions JSON; active state | Exact lookup, deterministic comparisons and extrema |
| `fact_evidence` | Fact ID; evidence ID; exact quote; source item/document version/checksum; URL, page/section/locator; authority | Citation and audit join |
| `retrieval_units` | Snapshot ID; offering ID; kind (`profile` or `field_detail`); canonical field tags; supporting fact/evidence IDs; language; deterministic clean text; content hash; weighted search vector; nullable 768-dimension embedding; active state | Bounded lexical/vector search |

Use typed columns for the dimensions used in predicates and sorting, and JSONB for
nested values/conditions that do not have a stable scalar shape. Index bank, family,
offering, snapshot, field, currency, active state, and relevant numeric bounds; add
GIN/pgvector indexes for retrieval units. Constrain joins so fact evidence and units
cannot cross snapshot/offer scopes. Preserve all non-scalar forms such as salary
multiples, property-value percentages, formulas, indefinite terms, and conditional
rates. Never coerce them into comparable absolute numbers.

Define projection versioning and stable IDs from accepted snapshot ID, field path,
variant identity, and projection version. Reprojection must be idempotent and must not
turn historical or pending records active. Record why a field is `not_stated`,
ambiguous, or conflicting; do not convert missing values to zero.

### 3.1 Canonical field-path registry

Use a checked-in, versioned `FieldPath` registry shared by projection, resolver,
repository, query planner, answer formatter, and evaluation fixtures. The registry
maps every current `ExtractionField` to the paths below. Reject unknown paths rather
than allowing free-form extractor names. A path denotes one semantic measure; repeated
conditional variants are separate rows with the **same** path and a stable
`variant_key`. Do not encode array indexes, currencies, or offering names into paths.
Those belong in typed columns and conditions. A range produces separate lower/upper
fact rows tied by `variant_key`; retain the original structured value and evidence on
both. `minimum`/`maximum` mean the disclosed bounds for that variant, not a global
product-wide bound across incompatible conditions.

| Canonical path or family | Extraction source and meaning |
|---|---|
| `identity.product_name`, `identity.formal_terms_name`, `identity.category`, `identity.variant_name`, `identity.variant_purpose`, `identity.purpose` | `product_name`, `formal_terms_names`, `category`, `variants`, `purpose`; one fact per repeated name/purpose/variant |
| `amount.minimum`, `amount.maximum`, `amount.salary_multiple.minimum`, `amount.salary_multiple.maximum`, `amount.property_value_pct.minimum`, `amount.property_value_pct.maximum`, `amount.formula` | `loan_amount`; preserve the amount union discriminator and currency |
| `rate.nominal.minimum`, `rate.nominal.maximum`, `rate.nominal.formula`, `rate.effective.minimum`, `rate.effective.maximum`, `rate.effective.formula` | `interest_rate` and `effective_rate`; preserve rate type, basis, currency/conditions where given |
| `term.minimum_months`, `term.maximum_months`, `term.indefinite`, `term.end_condition` | `term`; never rank indefinite terms as a numeric maximum |
| `fee.application`, `fee.disbursement`, `fee.service`, `fee.origination`, `fee.early_repayment`, `fee.insurance`, `fee.other` | Each `fees` item, with fee category, original description, fee scope, amount/currency or percentage, and conditions in separate columns |
| `repayment.method`, `eligibility.requirement`, `eligibility.residency`, `eligibility.age.minimum`, `eligibility.age.maximum`, `application.channel`, `document.required`, `condition.special`, `privilege.salary_customer` | Shared repayment, eligibility, age, application, document, and special-condition fields; salary privilege requires an explicit supported extraction/tagging rule |
| `collateral.requirement`, `collateral.alternative`, `income_verification.required`, `creditworthiness_assessment.required` | Shared consumer/mortgage details and conditional policy exceptions |
| `mortgage.property_market`, `mortgage.down_payment.minimum_pct`, `mortgage.down_payment.maximum_pct`, `mortgage.ltv.minimum_pct`, `mortgage.ltv.maximum_pct`, `mortgage.property_requirement` | Mortgage-only details; preserve property and alternative-security conditions |
| `revolving.credit_limit.minimum`, `revolving.credit_limit.maximum`, `revolving.credit_limit.salary_multiple.minimum`, `revolving.credit_limit.salary_multiple.maximum`, `revolving.credit_limit.property_value_pct.minimum`, `revolving.credit_limit.property_value_pct.maximum`, `revolving.credit_limit.formula`, `revolving.grace_period_days`, `revolving.enabled`, `revolving.linked_account_or_card` | Overdraft/credit-line details; credit-limit amounts use the same amount-form discriminators as `loan_amount` |

The table is the initial vocabulary. Amount and credit-limit union variants
must map to their matching paths; unsupported shapes fail projection rather than
being silently dropped. Fee category is **not** currently typed by `LoanFee`:
classify only from explicit, validated source wording using a versioned deterministic
mapping. Unclear fees remain `fee.other`, retain their exact description,
and cannot be used as a named fee in comparisons. `privilege.salary_customer` is a
planned extraction extension, not a claim that current extraction supplies it.
Unknown conditions must remain attached as raw structured conditions and block a
comparison that would otherwise erase them. Document path version and source-field
mapping on each projected row so a taxonomy migration can be backfilled and audited.

## 4. Product profile and retrieval text

The profile is a consistent, deterministic template, not a second tariff source:

1. Official/catalog display name, extracted name, formal terms names, aliases, and ID.
2. Family, extracted category, variant names, and property market when applicable.
3. Source-supported purpose/use cases and applicability or eligibility boundaries.
4. Distinguishing characteristics and high-level constraints with evidence links.
5. Accepted snapshot time and profile schema version.

Do not invent suitability advice or a “when to use” claim from a generic product name.
If purpose is not stated, mark it missing. Define an explicit salary-customer privilege
field or tagged condition if current generic special conditions cannot reliably answer
question 6. The profile is useful for orientation and recall; numeric tariffs remain
in `tariff_facts`.

Every factual profile sentence and field-detail unit must carry supporting accepted
fact IDs and exact official evidence IDs/locators. Catalog names and aliases may help
search, but catalog text alone is not citable evidence for a product claim. Units with
no verified source locator may aid internal routing only; exclude them from Gemini's
factual evidence packet and from answer citations. For descriptive answers, retrieve
the supporting official excerpt through those IDs, verify it against the stored
source/evidence record, and supply both excerpt and locator to Gemini. If no such
excerpt exists, abstain from that claim. A generated profile sentence is never itself
the citation of record.

Render field detail deterministically from accepted typed facts: canonical offering
name/ID, field label, value with unit/currency, every condition, applicability, and
source section. Preserve Armenian/English source wording and approved catalog aliases;
do not generate unsupported translations. Do not embed raw HTML, whole PDFs, raw API
payloads, or provenance JSON. Preserve exact source quotes separately in
`fact_evidence`. Normalize markup before rendering retrieval text, retaining meaningful
superscripts, links, and table relations as plain text.

Create one small profile embedding per offering snapshot and separate embeddings for
field-detail units. Group values only when their conditions remain clear in isolation;
keep different currencies, rate types, fee scopes, and product variants separate.
Split long units at fact/condition boundaries with stable IDs. Set initial text size
limits from corpus measurements, then tune against the evaluation set rather than an
arbitrary character target. Reuse embeddings by `(model, dimensions, normalized text
hash)` across unchanged content and reruns. Pending-review facts may be embedded in
advance for atomic activation, but must remain invisible until approval.

## 5. Query planning and answer contract

Extend resolution from one optional offering ID to a typed scope that can hold one,
several, or all offerings in a family. The resolver must return a bounded operation:
`single`, `compare`, `family_rank`, or `history`, plus requested fields and any
currency/condition constraints. Clarify only when the requested comparison or single
value cannot be interpreted safely. The application service validates all IDs and
scope against the catalog and saved resolution state.

The saved `ResolutionPlan` is an **authorization boundary for data scope**, not just
routing metadata. Persist it in server-controlled ADK session state with session/turn
identity, normalized question hash, resolved family and offering set, permitted
operation and fields, clarification state, and a short validity window. A question
answer call must consume or validate the plan for that exact turn; reject absent,
stale, changed-query, cross-session, cross-family, or widened offering/field scope
before any repository call. The model may narrow the question, but may not add an
offering or field outside the plan. Re-resolution creates a new plan. For multi-offering
comparisons, the resolver must authorize the full explicit set or a named family-wide
ranking; a single-offering plan never silently expands to a family. This is a
business-scope guard, not a replacement for API authentication or user permissions.
The HTTP adapter constructs an equivalent validated plan from its typed request and
the catalog, then uses the same service checks.

Implement one `TariffQueryService` with deterministic branches:

1. **Single offering:** load latest accepted snapshot and matching facts; retrieve
   profile/detail units only for description or unresolved wording; join exact evidence.
2. **Compare:** load the same requested fields for each resolved offering, align units,
   currencies, rate bases, variants, and conditions, then produce a typed comparison.
3. **Family rank:** filter accepted facts and calculate an extremum only over comparable
   values. Report conditional minima/maxima and conditions; abstain from a single winner
   when currencies, fee types, formulas, or bases make comparison invalid.
4. **History:** read accepted `tariff_changes`/snapshots and return old/new values and
   evidence. Distinguish the previous accepted snapshot from the previous run, which
   might be pending or failed.

Use exact fact lookup first for known fields. For descriptive retrieval, use
PostgreSQL full-text search as the lexical baseline: a stored `tsvector` using the
`simple` configuration, with `setweight` for identity/field labels (`A`), approved
aliases and purpose terms (`B`), and clean detail text (`C`). Use
`websearch_to_tsquery('simple', ...)` and `ts_rank_cd` within the authorized offering
and field scope; GIN-index the vector. Keep Armenian and English aliases as explicit
lexical terms. Keep the existing resolver's bounded string-similarity fallback
for misspelled names; consider `pg_trgm` there only if measured catalog scale warrants
it. Do not use trigram matching as the main tariff-content ranker or add BM25 or an
extension dependency until evaluation shows a concrete FTS failure.

Vector search is a bounded fallback or supplement for descriptive questions and uses
the same hard SQL scope/active/evidence predicates. Candidate selection starts with
exact field matches and ranked FTS hits; add vector candidates when lexical coverage
is insufficient or the query is semantic. The initial hybrid baseline is the current
service's rank fusion, recorded as an explicit configuration/version; tune its weights,
threshold, and candidate limits on held-out retrieval cases. Do not combine raw FTS
and cosine scores as though they share a scale. Neither similarity branch overrides
metadata filters, accepted state, typed values, or evidence checks. Keep profile and
detail budgets separate so profiles cannot crowd out citable evidence.

Return a typed result with operation, resolved scope, freshness/accepted time,
facts/comparison rows, conditions, verified citations, and explicit unavailable or
incomparable reasons. Gemini may phrase an evidence-bound response where useful, but
the service performs filtering, arithmetic, ordering, citation validation, and
abstention deterministically. No answer may cite a profile or unsupported generated
sentence as the source of a tariff value.

## 6. ADK, API, and compatibility boundary

Replace `answer_tariff_question` with a narrow `answer_tariff_query(query,
tool_context)` adapter. It reads the typed, saved resolution plan; the model cannot
expand the offering scope by supplying its own IDs. Keep `resolve_request` as the
first ordinary-turn boundary and update both `app/agent.py` and `app/cli.py` to route
single, comparison, ranking, and history questions through the shared service.
Preserve native monitoring and HITL routes. Keep `POST /api/v1/questions` and define
an explicit typed API scope for callers that do not have ADK session state; validate it
through the same service. Preserve existing current/history endpoints or adapt them
through shared read methods without duplicating business logic.

Retain the old RAG query path for read-only shadow comparison during migration. Do
not expose it as an independent truth source after cutover. Deprecate old summary and
source chunk embeddings only after the new read model, citations, and corpus coverage
are verified. Historical rows and artifact references remain available for audit.

## 6.1 Model-call usage and cost monitoring

Instrument every Gemini boundary used by monitoring and answering: intent fallback,
PDF transcription, source classification, semantic extraction/repair, document/query
embeddings, and answer generation. Record **each actual API attempt**, including
retries and failures, with an idempotent call/attempt ID, UTC time, operation/stage,
model ID, run/offering or request correlation IDs, input/output token counts when the
provider returns them, embedding input size/count when tokens are unavailable,
latency, outcome, cache hit/miss, and error class. Never log raw prompts, responses,
source text, API keys, or personal data. Cache hits have no API charge but retain
avoided-call counters separately.

Maintain a versioned, dated price catalog by model, billing platform, operation, and
input/output unit. `app/services/model_pricing.py` covers some generation models but
needs embedding rates and an explicit platform/billing basis. Calculate an
**estimated** USD cost from provider-reported billable usage and the price record
valid on the call date; store rate version and arithmetic with the event. If usage or
rate is unavailable, store `unknown`, never zero. Reconcile estimates with provider
billing outside the answer path. Expose read-only aggregates by day, model, stage,
run, and offering, plus total calls, retries, tokens, estimated cost, unknown-cost
calls, and embedding cache savings. Add a configurable budget alert/threshold with
an operational status, without allowing the model to change budgets.

## 7. Coverage map for the 25 target questions

| Questions | Required behavior |
|---|---|
| 1–7, 9, 14–19 | Single-offering current facts, conditions, freshness, and citations |
| 8, 21, 22 | Explicit multi-offering comparison with aligned amount, term, rate, fee, purpose, down payment, and collateral fields |
| 10–12, 23–24 | Family extrema using comparable typed amounts/terms/rates; show currency, rate basis, and eligibility conditions |
| 13 | Fee inventory and comparison by compatible fee scope/type; no fabricated universal “highest fee” |
| 20 | Mortgage down-payment and alternative-security facts, including conditional exceptions |
| 25 | Accepted change set with previous/current value, affected field, source evidence, and clear previous-run semantics |

Include English and Armenian variants, incomplete/offering-missing cases, pending
review, stale accepted data, and source disagreement in evaluation. The result for
each target question must be judged for scope, field coverage, conditions, calculation,
freshness, citation validity, and appropriate abstention, not wording alone.

## 8. Ordered implementation to-do list

### A. Contracts and baseline

- [x] Record current schema, active snapshot counts, chunk counts, model/embedding
      configuration, RAG latency and embedding usage; keep identifiers/secrets out of logs.
- [x] Freeze representative accepted snapshot fixtures, including conditional rates,
      multiple currencies, formulas, fees, mortgage details, and reviewed overrides.
- [x] Define and version the complete `FieldPath` registry and source-field mappings,
      including bound/variant semantics, fee-category rules, and unsupported-shape errors.
- [x] Define typed scope/query/result contracts and evidence invariants in `app/domain/`.
- [x] Decide explicit comparable-field rules for every numeric ranking question and
      document required clarifications or abstentions.

#### Phase A implementation summary (2026-09-22)

Implemented the version-1 `FieldPath` registry and complete mapping from existing
`ExtractionField` values, conservative fee categorization, typed per-turn resolution
and evidence-bearing fact contracts, and pure numeric comparability rules. Added three
fully typed **synthetic** accepted snapshots for consumer, mortgage, and reviewer-
overridden cases. These fixtures are never production tariffs.

Baseline: PostgreSQL schema currently uses `tariff_snapshots`, `knowledge_documents`,
and `knowledge_chunks`; the running local database has 1 accepted snapshot, 8 active
knowledge documents, 446 active chunks, and 1,010 total chunks. Configured models are
`gemini-3.7-flash` and `gemini-embedding-001`; current RAG uses `top_k=8` and minimum
score `0.25`. The `.env` database host `db` resolves inside Compose, while host-side
read-only inspection used the published local PostgreSQL port. Historical RAG latency,
embedding-call totals, and USD spend are **unavailable** because no durable usage
ledger exists yet. Phase C adds that ledger and establishes a measurable post-change
baseline; do not report unknown usage as zero.

Comparison decisions: only identical canonical numeric paths with matching unit,
currency, rate basis, and fee scope can share a numeric ranking. Formula, salary-
multiple, property-value-percentage, indefinite-term, and unclassified-fee paths are
not rankable with absolute values. Conditional promotional values may be compared as
**disclosed** minima/maxima only when the answer carries every eligibility condition;
they are not unconditional customer offers. Cross-currency amounts require a user-
specified common currency and an approved conversion policy; none exists today, so
abstain. “Highest fees” requires a named comparable fee category and fixed-amount or
percentage basis. Missing or conflicting accepted values are never treated as zero.
History compares accepted snapshots, not merely consecutive monitoring runs.

Files added: `app/domain/structured_tariffs.py`,
`app/domain/tariff_comparison.py`, `tests/fixtures/structured_tariffs.py`, and
`tests/unit/test_structured_tariff_contracts.py`. File modified: this plan. Files
removed: none.

Handoff notes: Phase A contracts are additive and not yet wired to persistence or
ADK. `privilege.salary_customer` remains a planned extraction extension. The
synthetic fixture's reviewed case represents the **final accepted** extraction, with
a review-tagged validated rate; Phase B must test evidence reconstruction from real
review records as well. Keep the existing RAG path active until the Phase F cutover.

### B. Schema and deterministic projection

- [x] Add forward migrations for the four projections, constraints, and indexes.
- [x] Add a durable `model_call_usage` table and indexes for call/attempt identity,
      run/offering correlation, stage/model/day aggregates, rate version, and cost.
- [x] Implement a pure projector from the **final accepted** snapshot and validated
      semantic extraction into profile, fact, and evidence records.
- [x] Reconnect canonical values to per-field evidence; fail publication/projection if a
      non-missing fact loses required evidence or a review override is not reflected.
- [x] Add a deterministic, versioned renderer for clean profile and field-detail text.
- [x] Add tests for nested conditional values, rate/currency/fee variants, missing
      fields, evidence joins, stable IDs, markup cleanup, and taxonomy round trips.
- [x] Require verified locators on every explanatory unit admitted to Gemini's
      evidence packet; test that unsupported profile text cannot be cited.

**Phase B implementation summary (2026-09-22).** Added forward migration `011` for
accepted offering profiles, typed tariff facts, official fact evidence, weighted
lexical/vector retrieval units, and the model-call usage ledger. Added a pure
projector that checks the final accepted snapshot against the validated extraction,
projects typed values and conditions to versioned field paths, verifies each found
fact's quote and official source locator, and renders evidence-backed profile and
field-detail units with markup removed. Range bounds share a variant key; monetary
amounts retain currency and conditions. No live query or publication path uses these
new tables yet.

Files added: `migrations/011_structured_tariff_read_model.sql`,
`app/services/structured_projection.py`, and
`tests/unit/test_structured_projection.py`. Files modified:
`app/domain/structured_tariffs.py`, `docs/architecture.md`, and this plan.
Files removed: none.

Verification: 21 structured-contract/projector unit tests passed; 6 knowledge-store
PostgreSQL integration tests passed with the new migration applied to the isolated
test database; Ruff check passed. The reviewed fixture represents a final accepted
review result, but end-to-end reconstruction from persisted review records remains
for Phase C integration tests. Projection currently fails closed for missing or
mismatched evidence and is not yet published. Embeddings and model call ledger rows
are intentionally unpopulated until Phase C.

### C. Atomic publication and embedding cost

- [x] Publish/activate projections in the same transaction as accepted snapshot state;
      quarantine pending review and atomically activate approved projections.
- [x] Retire prior active projections for the same offering without deleting history.
- [x] Add content/model/dimension keyed embedding reuse and avoid re-embedding
      unchanged chunks on reruns.
- [x] Record the available pre-cutover text/call baseline and a controlled
      before/after cache measurement; measure live post-cutover tokens/calls in G.
- [x] Instrument direct Gemini and ADK logical-call boundaries, application
      retries/failures/cache hits; persist observed token usage, dated price basis,
      estimated USD cost or `unknown`, and latency without model inputs/outputs.
      Provider-internal HTTP retries remain folded into logical-call latency.
- [x] Add read-only cost aggregates and budget-threshold status; test idempotent
      logging, pricing arithmetic, missing usage/rates, and secret redaction.
- [x] Test concurrent publication, rollback, rejection, supersession, and process
      restart with PostgreSQL integration tests.

**Phase C implementation summary (2026-09-22).** Accepted profiles, facts,
evidence, and retrieval units now publish in the same transaction as accepted
snapshots. Pending reviews create no projection rows, so the previous accepted
projection remains active. Reviewer approval projects the final reviewed extraction
in its acceptance transaction. Offering-scoped advisory locking serializes concurrent
publication; supersession retires old active read rows and retains history. New
acceptance validation routes nonofficial citations to review before publication.

Document embeddings use a content/model/dimension/task cache. Unchanged text is
not sent to Gemini again. Direct Gemini and ADK model boundaries write redacted
logical-call usage, application retry/failure and cache-hit records, dated paid-tier
list rates, known USD estimates or explicit unknown reasons, and latency. The
read-only cost report provides stage/model/day totals and budget status. No prompt,
source text, model response, key, or exception message is persisted in the ledger.

Measurements: the pre-cutover local accepted Overdraft run has 446 old chunks and
623,207 chunk characters; historical token/call/cost totals are unavailable. A
controlled two-version cache test made one provider call instead of two for identical
text. Synthetic projected fixture counts are 17 consumer and 20 mortgage retrieval
units; their content is not a live before/after cost comparison. The local legacy
accepted Overdraft snapshot cannot be strictly projected because one tariff-term
citation has `marketing_content` authority; Phase F must repair or quarantine it.
Live after-cutover token/call/latency comparison is moved to G because no production
cutover exists in Phase C. Google SDK internal HTTP retry attempts are not exposed
by ADK callbacks; a callback row covers the whole logical call. Embedding responses
may lack token counts, so their estimated cost remains unknown even though the
published per-token rate is retained. Budget status remains `incomplete` when unknown
calls exist below the threshold.

Files added: `app/repositories/structured_projection.py`,
`app/repositories/embedding_cache.py`, `app/services/model_call_usage.py`,
`migrations/012_embedding_cache.sql`, `scripts/model_cost_report.py`,
`docs/model-cost-monitoring.md`, `tests/unit/test_model_call_usage.py`,
`tests/integration/test_model_call_usage_postgres.py`, and
`tests/integration/test_embedding_cache_postgres.py`. Files modified:
`app/agent.py`, `app/cli.py`, `app/repositories/monitoring.py`,
`app/repositories/reviews.py`, `app/runtime.py`,
`app/services/discovery_classifier.py`, `app/services/gemini_pdf_extractor.py`,
`app/services/intent_resolution.py`, `app/services/knowledge_index.py`,
`app/services/model_pricing.py`, `app/services/pdf_extraction.py`,
`app/services/rag_answer.py`, `app/services/semantic_extraction.py`,
`app/services/snapshot_lifecycle.py`, `app/services/source_discovery.py`,
`tests/integration/test_monitoring_repository_postgres.py`,
`tests/unit/test_knowledge_index.py`, `docs/architecture.md`, and this plan.
Files removed: none.

Verification: 363 available unit tests passed; 27 focused PostgreSQL integration
tests passed, including concurrent publication, rollback, rejection, supersession,
review approval, and workflow restart. Ruff passed on changed Python files. The
full unit collection is blocked by a pre-existing obsolete test importing removed
`app.domain.discovery`; the full integration suite includes live-agent/server tests
that require external services and did not finish in this environment.

### D. Query services and repository

- [ ] Add typed repositories for latest accepted profile/facts/evidence, weighted
      PostgreSQL FTS (`simple` + `websearch_to_tsquery` + `ts_rank_cd`), bounded vector
      units, and accepted change history; benchmark Armenian/English retrieval.
- [ ] Implement deterministic single-offering answer, comparison, family ranking,
      and history branches in one application service.
- [ ] Reject invalid cross-family IDs and requests that try to read inactive,
      pending, rejected, or superseded data.
- [ ] Test currency/rate-basis separation, conditional promotional minima,
      incomparable fees/formulas, salary privileges, and missing evidence.
- [ ] Keep exact source quote validation and immutable document provenance in all
      returned citations.

### E. Resolution, tools, and API

- [ ] Extend resolver output/session state for multiple offering IDs and bounded
      operation/field/condition selection; add bilingual comparison tests.
- [ ] Enforce per-turn `ResolutionPlan` scope authorization before repository access;
      test absent, stale, replayed, changed-query, and widened-scope calls.
- [ ] Replace the ADK RAG adapter with `answer_tariff_query` backed by trusted
      resolution state; update root and CLI agent instructions without changing models.
- [ ] Wire FastAPI and ADK to the same application service in `app/runtime.py`.
- [ ] Preserve monitoring/HITL flow and add route/tool tests for no acquisition on
      ordinary questions, scope integrity, and controlled insufficient-evidence results.

### F. Backfill and cutover

- [ ] Backfill accepted snapshots in batches using stored semantic extraction and
      evidence; identify legacy snapshots that cannot be projected reliably.
- [ ] Compare projected facts to canonical snapshots and old answer outputs; audit
      every mismatch before using the new path for answers.
- [ ] Shadow-read old and new retrieval paths on representative queries, logging
      aggregate diagnostics without source text or sensitive payloads.
- [ ] Cut over after acceptance gates pass; retain a reversible application-level
      switch until production observation is stable.
- [ ] Remove or stop updating obsolete summary/source embeddings only after proving
      all required source evidence remains available through `fact_evidence` and
      artifact retention. Plan physical cleanup separately.

### G. Evaluation and documentation

- [ ] Create fixtures and expected structured outcomes for all 25 questions; start
      the agent eval loop with 1–2 cases, then expand with held-out cases.
- [ ] Measure exact fact accuracy, conditional coverage, valid citation rate,
      unsupported-answer rate, scope leakage, comparison correctness, FTS/vector
      recall, latency, model calls, tokens, cache savings, and estimated cost; tune
      hybrid fusion only on held-out retrieval cases.
- [ ] Run `uv run pytest tests/unit tests/integration`; run applicable `agents-cli`
      evals and inspect scores/traces, not just process exit codes.
- [ ] Update `docs/architecture.md`, knowledge-store/retrieval/answering docs,
      API contracts, migration notes, and the RAG trace script to show the new stages.
- [ ] Do not deploy as part of this plan; dev deployment requires separate explicit
      human approval under `AGENTS.md`.

## 9. Completion criteria

- All 25 target questions have a defined typed route and evaluation result; every
  answer either cites accepted official evidence or gives a specific abstention.
- Exact and comparative numeric answers come from typed accepted facts, not vector
  similarity or model arithmetic.
- A pending or rejected review cannot affect current answers. Approved overrides and
  their evidence appear atomically; old accepted versions remain auditable.
- Product/offer scope from the per-turn authorized resolution plan is enforced by
  the service and SQL. Explicit multi-offering questions work without broadening to
  unrelated offerings; stale or widened calls fail before data access.
- Canonical paths are stable across extractors and review overrides. Explanatory text
  reaches Gemini only with verified official evidence and locators.
- Profile and field-detail retrieval are versioned, consistently rendered, and free
  of raw artifact dumps. Unchanged text does not trigger a new embedding call.
- Every actual model API attempt has a correlated usage record and dated price basis;
  missing billable usage/rates are reported as unknown, not free. Read-only cost
  aggregates reveal spend and cache savings without logging sensitive content.
- Backfill discrepancies are resolved or explicitly excluded with safe abstention;
  the old path can be disabled without losing required citation evidence.
