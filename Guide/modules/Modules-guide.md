# Modules Guide — Ameria Tariff Monitor

A navigation map of `app/` for the technical interview. Every file, symbol and variable
below is a link that opens the file at the line where it is defined.

- Line numbers were checked against the working tree on **2026-09-28** (branch
  `chore/pre-main-merge`). If code above a symbol changes, its link drifts by a few
  lines; the symbol name is always next to the link, so search for it.
- A link with no line number (`file.py`) points to a class or function defined further
  down a large file; open the file and search for the name.
- Paths are relative to this file: `../../app/...` is the repository's `app/` folder.

**The system in one paragraph.** One ADK agent ([agent.py](../../app/agent.py)) talks to
the user and calls seven narrow tools ([tools/](../../app/tools/)). Scope is decided by
code, not the model: [`resolve_request`](../../app/tools/resolution.py#L48) issues a
per-turn *read grant* and, only for an explicit request, a *spend grant*. A monitoring
run executes the deterministic pipeline
([`TariffPipeline`](../../app/services/monitoring_pipeline.py#L570) →
[`IndexingPipeline.refresh`](../../app/services/monitoring_pipeline.py#L226)):
acquisition → PDF link selection → normalization (PDF transcription + OCR fallback) →
source discovery → semantic extraction → validation / review signals → change detection
→ one-transaction publication. Reviews pause the chat natively
([monitoring_node.py](../../app/services/monitoring_node.py#L316)). Questions are answered
from accepted typed facts ([structured_tariff_query.py](../../app/services/structured_tariff_query.py)).
Gemini is called in six prompt-bearing places, plus embeddings (see [§2.3](#23-prompts-the-model-sees)).

---

## Contents

- [1. Directory tree of `app/`](#1-directory-tree-of-app)
- [2. Variables you may be asked to tweak](#2-variables-you-may-be-asked-to-tweak)
  - [2.1 How configuration works](#21-how-configuration-works)
  - [2.2 Environment variables / settings](#22-environment-variables--settings)
    - [Models and secrets](#models-and-secrets)
    - [Database and ADK sessions](#database-and-adk-sessions)
    - [Source allowlist and HTTP](#source-allowlist-and-http)
    - [Acquisition](#acquisition)
    - [PDF transcription and OCR](#pdf-transcription-and-ocr)
    - [Source discovery](#source-discovery)
    - [Semantic extraction](#semantic-extraction)
    - [HITL, change detection, queries](#hitl-change-detection-queries)
    - [Scheduler and run lease](#scheduler-and-run-lease)
    - [Application, logging, tracing](#application-logging-tracing)
    - [Catalog (data file)](#catalog-data-file)
  - [2.3 Prompts the model sees](#23-prompts-the-model-sees)
  - [2.4 Hard-coded constants (code changes)](#24-hard-coded-constants-code-changes)
    - [Agent and tools](#agent-and-tools)
    - [Pipeline, retries, runs](#pipeline-retries-runs)
    - [Validation, acceptance, change detection](#validation-acceptance-change-detection)
    - [Review display and answering](#review-display-and-answering)
- [3. Module summaries](#3-module-summaries)
  - [Entry points](#entry-points)
  - [plugins / tools](#plugins--tools)
  - [config](#config)
  - [services: run orchestration](#services-run-orchestration)
  - [services: acquisition](#services-acquisition)
  - [services: document processing](#services-document-processing)
  - [services: source discovery and extraction](#services-source-discovery-and-extraction)
  - [services: projection and answering](#services-projection-and-answering)
  - [services: HITL](#services-hitl)
  - [services: cross-cutting](#services-cross-cutting)
  - [domain](#domain)
  - [repositories](#repositories)
  - [security / app_utils](#security--app_utils)
- [4. Assignment brief → code map](#4-assignment-brief--code-map)
- [5. Glossary and data model](#5-glossary-and-data-model)
  - [5.1 Glossary](#51-glossary)
  - [5.2 Assignment fields → schema](#52-assignment-fields--schema)
  - [5.3 Key models](#53-key-models)
  - [5.4 Database tables](#54-database-tables)
- [6. Symbol index and test map](#6-symbol-index-and-test-map)
  - [6.1 Symbol index (A–Z)](#61-symbol-index-az)
  - [6.2 API routes](#62-api-routes)
  - [6.3 Test map](#63-test-map)

---

## 1. Directory tree of `app/`

- [app/](../../app/)
  - [`__init__.py`](../../app/__init__.py) — exports `app`, the ADK App, so `adk web` / agents-cli can find the agent.
  - [`agent.py`](../../app/agent.py) — **the agent**: model, 25-line instruction, 7 tools, `ToolPolicyPlugin`, resumable App.
  - [`plugins.py`](../../app/plugins.py) — `ToolPolicyPlugin`: rejects business tools not preceded by `resolve_request`; turns tool exceptions into typed envelopes.
  - [`runtime.py`](../../app/runtime.py) — **composition root**: builds every repository, service, model fallback chain, the pipeline and the monitoring node (`ApplicationContainer`).
  - [`worker.py`](../../app/worker.py) — background worker: claims queued runs, daily 06:00 scheduler, lease recovery, embedding sweep. No ADK.
  - [`fast_api_app.py`](../../app/fast_api_app.py) — FastAPI app: ADK web/dev-UI routes, A2A routes, and the project routes; builds the container in `lifespan`.
  - [`cli.py`](../../app/cli.py) — the interactive product (`./tariff-chat`): one ADK invocation per message, progress rendering, review prompts, Ctrl-C/rewind, crash recovery.
  - [`cli_entry.py`](../../app/cli_entry.py) — quiet CLI entry point: filters ADK experimental warnings, sets up logging/telemetry, calls `cli.main`.
  - [api/](../../app/api/)
    - [`__init__.py`](../../app/api/__init__.py) — package marker ("project-specific FastAPI routes").
    - [`routes.py`](../../app/api/routes.py) — `/api/v1` routes: runs, questions, tariffs (query/current/history), reviews (read-only + admin abort), healthz.
  - [app_utils/](../../app/app_utils/) — generated ADK/A2A plumbing (keep intact per AGENTS.md).
    - [`services.py`](../../app/app_utils/services.py) — process-wide ADK session/artifact services (`shared://`), PostgreSQL session schema check.
    - [`a2a.py`](../../app/app_utils/a2a.py) — attaches the A2A agent card and JSON-RPC endpoint to FastAPI.
  - [config/](../../app/config/)
    - [`__init__.py`](../../app/config/__init__.py) — re-exports settings groups, `get_settings`, `load_seed_catalog`.
    - [`environment.py`](../../app/config/environment.py) — **flat env/.env reader** (`EnvironmentSettings`): one field per environment variable, with defaults.
    - [`loader.py`](../../app/config/loader.py) — maps the flat env fields into grouped `Settings`; `get_settings()` is cached.
    - [`models.py`](../../app/config/models.py) — **typed settings groups** with validation bounds (HTTP, OCR, HITL, scheduler, models...).
    - [`seed_catalog.py`](../../app/config/seed_catalog.py) — loads and validates the YAML catalog; checks every seed URL against the allowlist.
    - [`seed_catalog.yaml`](../../app/config/seed_catalog.yaml) — **the product catalog**: 2 families, 13 offerings, seed URLs, EN/HY names, aliases, transliterations.
    - `normalization_baseline.json` — per-page structural baseline used to score normalization quality (see [normalization_baseline.py](../../app/services/normalization_baseline.py)).
  - [domain/](../../app/domain/) — Pydantic models and pure rules (no I/O).
    - [`__init__.py`](../../app/domain/__init__.py) — package marker.
    - [`acquisition.py`](../../app/domain/acquisition.py) — `PageArtifact`, `DocumentArtifact`, `SourceLocator`, acquisition warnings/inventory.
    - [`catalog.py`](../../app/domain/catalog.py) — frozen catalog models (`SeedCatalog`, `SeedCatalogEntry`, `OfferingCategory`) and their validation.
    - [`effective_periods.py`](../../app/domain/effective_periods.py) — effective-date period parsing/status (current, historical, future).
    - [`extraction_terms.py`](../../app/domain/extraction_terms.py) — label words per extraction field, used only by the budgeted evidence mode.
    - [`intent.py`](../../app/domain/intent.py) — `RequestIntent`, `IntentResolution`, conversation state, freshness and history query models.
    - [`interpretation.py`](../../app/domain/interpretation.py) — the interpreter's proposal (`RequestInterpretation`), `PendingOffer`, `route_for`.
    - [`knowledge.py`](../../app/domain/knowledge.py) — `KnowledgeDocument` (versioned evidence documents/chunks) and version ids.
    - [`models.py`](../../app/domain/models.py) — `ProductType`, the 13 `OfferingId`s, and the assignment-shaped `LoanTariff`.
    - [`monitoring.py`](../../app/domain/monitoring.py) — run lifecycle: `RunCommand`, `MonitoringRun`, statuses, **all failure codes**, `SnapshotAttempt`, `SnapshotChangeSet`, `OfferingPublication`.
    - [`normalization.py`](../../app/domain/normalization.py) — `NormalizedSourceBundle`, blocks, tables, warnings codes, text normalizers.
    - [`pdf_extraction.py`](../../app/domain/pdf_extraction.py) — PDF admission, input probe, link selection, transcription and OCR result models.
    - [`pipeline.py`](../../app/domain/pipeline.py) — `IndexingRefreshResult`, `SourceManifest`, `StageTiming`.
    - [`query_shape.py`](../../app/domain/query_shape.py) — `QueryShape`, `Currency`, `ReplyKind` (what a question asks for).
    - [`review.py`](../../app/domain/review.py) — HITL models: `ReviewReason`, `ReviewTask`, `ReviewDecision`, prompt views.
    - [`semantic_extraction.py`](../../app/domain/semantic_extraction.py) — **the tariff schema** (`LoanProduct`, `Rate`, `TermRange`, `LoanFee`...) and extraction batch/result models.
    - [`source_discovery.py`](../../app/domain/source_discovery.py) — `OfferingContext`, `SourceAssessment`, authority / association / temporal enums.
    - [`structured_tariffs.py`](../../app/domain/structured_tariffs.py) — **the read model**: `FieldPath`, bilingual labels, `ResolutionPlan` (read grant), `TariffFact`, `RetrievalUnit`.
    - [`tariff_comparison.py`](../../app/domain/tariff_comparison.py) — comparability rules for ranking/comparing facts (`RANKABLE_PATHS`, `ComparableMeasure`).
    - [`tariff_queries.py`](../../app/domain/tariff_queries.py) — current-tariff and history result models.
  - [repositories/](../../app/repositories/) — PostgreSQL persistence (SQLAlchemy async, raw SQL).
    - [`__init__.py`](../../app/repositories/__init__.py) — package marker.
    - [`contracts.py`](../../app/repositories/contracts.py) — repository **Protocols** (`RunRepository`, `ReviewRepository`, snapshot/cache repos).
    - [`monitoring.py`](../../app/repositories/monitoring.py) — runs queue (submit/claim/heartbeat/finish), snapshots, and the atomic offering publication.
    - [`reviews.py`](../../app/repositories/reviews.py) — review tasks: create, list, decide, supersede; `StaleReviewError`.
    - [`review_supersession.py`](../../app/repositories/review_supersession.py) — SQL helpers that supersede older pending reviews/candidates.
    - [`review_memory.py`](../../app/repositories/review_memory.py) — remembered reviewer decisions (reuse on later runs); `result_fingerprint`.
    - [`knowledge_publication.py`](../../app/repositories/knowledge_publication.py) — the only writer of document versions; snapshot document sets; publication locks.
    - [`knowledge_records.py`](../../app/repositories/knowledge_records.py) — table mirror for `knowledge_documents`/`knowledge_chunks`.
    - [`structured_projection.py`](../../app/repositories/structured_projection.py) — writes profiles, facts, evidence, retrieval units in the publication transaction.
    - [`structured_tariff_query.py`](../../app/repositories/structured_tariff_query.py) — typed reads for answering: profiles, facts, lexical/vector retrieval units.
    - [`embedding_cache.py`](../../app/repositories/embedding_cache.py) — content-addressed embedding cache.
    - [`acquisition_baselines.py`](../../app/repositories/acquisition_baselines.py) — last passing acquisition inventory per URL (regression gate).
    - [`acquisition_snapshots.py`](../../app/repositories/acquisition_snapshots.py) — latest acquisition per URL (freshness reuse window).
    - [`pdf_extraction.py`](../../app/repositories/pdf_extraction.py) — cache of Gemini PDF transcriptions.
    - [`pdf_link_selection.py`](../../app/repositories/pdf_link_selection.py) — cache of PDF link decisions.
    - [`semantic_extraction.py`](../../app/repositories/semantic_extraction.py) — cache of extraction batch answers.
    - [`source_discovery.py`](../../app/repositories/source_discovery.py) — cache of source-discovery assessments.
  - [security/](../../app/security/)
    - [`__init__.py`](../../app/security/__init__.py) — package marker.
    - [`urls.py`](../../app/security/urls.py) — `validate_source_url`: HTTPS, allowlisted host, no IP literal, no credentials, port 443 only.
    - *(Download size/MIME/signature and redirect checks live in [pdf_downloader.py](../../app/services/pdf_downloader.py), `html_retriever.py` and `browser_renderer.py`.)*
  - [services/](../../app/services/) — application services (deterministic unless marked **Gemini**).
    - [`acquisition.py`](../../app/services/acquisition.py) — fetch page (static + Playwright render), completeness floor, download linked PDFs, store artifacts, content hashes.
    - [`acquisition_completeness.py`](../../app/services/acquisition_completeness.py) — gate: fail an acquisition whose tables/PDF links/main text dropped vs. baseline.
    - [`acquisition_errors.py`](../../app/services/acquisition_errors.py) — `AcquisitionError` / `AcquisitionFailure` reasons.
    - [`acquisition_freshness.py`](../../app/services/acquisition_freshness.py) — gate: reuse a recent acquisition within `ACQUISITION_FRESHNESS_HOURS`.
    - [`adk_logging.py`](../../app/services/adk_logging.py) — log filters that silence handled ADK noise.
    - [`answer_read_model.py`](../../app/services/answer_read_model.py) — `TariffAnswerRouter`: the single answer path (tool, post-run answer, `/questions`).
    - [`artifact_store.py`](../../app/services/artifact_store.py) — content-addressed filesystem store for raw HTML/PDF bytes.
    - [`block_normalizer.py`](../../app/services/block_normalizer.py) — normalizes one HTML content block.
    - [`browser_renderer.py`](../../app/services/browser_renderer.py) — Playwright renderer with allowlist, request blocking, interaction cap.
    - [`contracts.py`](../../app/services/contracts.py) — `TariffPipeline` protocol shared by chat node and worker.
    - [`discovery_classifier.py`](../../app/services/discovery_classifier.py) — **Gemini**: generic tool-free structured classifier + source-discovery prompt; retry/fallback helpers.
    - [`discovery_prefilter.py`](../../app/services/discovery_prefilter.py) — builds bounded classification candidates from the normalized bundle.
    - [`embedding_providers.py`](../../app/services/embedding_providers.py) — **Gemini** embeddings (document and query side) with quota-aware retries.
    - [`extraction_evidence.py`](../../app/services/extraction_evidence.py) — builds the evidence catalog (`EvidenceItem`s with stable `ev_` ids).
    - [`extraction_planner.py`](../../app/services/extraction_planner.py) — groups fields into 3 extraction calls; full vs. budgeted evidence packets.
    - [`failure_mapping.py`](../../app/services/failure_mapping.py) — exception → stable failure code; human-readable failure text.
    - [`gemini_pdf_extractor.py`](../../app/services/gemini_pdf_extractor.py) — **Gemini**: sends PDF bytes, gets page-structured blocks/tables.
    - [`html_parser.py`](../../app/services/html_parser.py) — parses HTML into blocks, tables, links (with allowlist flags), chrome detection.
    - [`html_retriever.py`](../../app/services/html_retriever.py) — static HTML fetch with allowlist, redirect, size and retry controls.
    - [`intent_resolution.py`](../../app/services/intent_resolution.py) — **Gemini**: request interpreter + `RequestResolver` (catalog-validated turn resolution).
    - [`interpretation_validation.py`](../../app/services/interpretation_validation.py) — rules V1–V10: turns the interpreter's proposal into an authoritative resolution.
    - [`knowledge_projection.py`](../../app/services/knowledge_projection.py) — projects selected sources into versioned knowledge documents/chunks.
    - [`logging_setup.py`](../../app/services/logging_setup.py) — console + rotating file logging, Yerevan timestamps.
    - [`model_call_usage.py`](../../app/services/model_call_usage.py) — redacted per-call model usage and cost ledger; ADK callbacks; run attribution.
    - [`model_pricing.py`](../../app/services/model_pricing.py) — model price catalog, fallback model sequence, price-cap enforcement.
    - [`monitoring_node.py`](../../app/services/monitoring_node.py) — **the ADK node** that runs/follows a run inside the chat and pauses per review.
    - [`monitoring_pipeline.py`](../../app/services/monitoring_pipeline.py) — **`TariffPipeline` and `IndexingPipeline`**: the stage order for every run.
    - [`monitoring_progress.py`](../../app/services/monitoring_progress.py) — progress events, sinks, `stream_progress`.
    - [`normalization.py`](../../app/services/normalization.py) — `StructuralNormalizationService`: page + PDFs → one evidence bundle.
    - [`normalization_baseline.py`](../../app/services/normalization_baseline.py) — loads the baseline JSON and scores a page's structure.
    - [`normalized_renderer.py`](../../app/services/normalized_renderer.py) — renders a bundle as Markdown (reviewer `?`, audit).
    - [`ocr_transcriber.py`](../../app/services/ocr_transcriber.py) — Tesseract OCR fallback (`hye+eng`), confidence floor, timeouts.
    - [`pdf_admission.py`](../../app/services/pdf_admission.py) — pre-model PDF admission from link metadata (irrelevant / historical).
    - [`pdf_downloader.py`](../../app/services/pdf_downloader.py) — secure PDF download: allowlist per redirect hop, retries, size/MIME/`%PDF-` checks.
    - [`pdf_extraction.py`](../../app/services/pdf_extraction.py) — `GeminiPdfExtractionService`: admission, probe, cache, Gemini transcription, OCR fallback.
    - [`pdf_input_probe.py`](../../app/services/pdf_input_probe.py) — pypdf probe: each page machine-readable / image-only / mixed / unknown.
    - [`pdf_link_selection.py`](../../app/services/pdf_link_selection.py) — **Gemini**: decides which linked PDFs belong to the offering, before transcription.
    - [`pdf_rasterizer.py`](../../app/services/pdf_rasterizer.py) — renders PDF pages to images for OCR (pypdfium2).
    - [`pipeline_audit.py`](../../app/services/pipeline_audit.py) — renders per-stage Markdown audit overlays.
    - [`pipeline_audit_archive.py`](../../app/services/pipeline_audit_archive.py) — writes those overlays to `PIPELINE_AUDIT_DIR/run_<id>/<offering>/`.
    - [`retrieval_trace.py`](../../app/services/retrieval_trace.py) — per-retrieval step trace on the `tariff.retrieval` logger.
    - [`review_decisions.py`](../../app/services/review_decisions.py) — applies a decision to the candidate snapshot; activates it when all reviews pass.
    - [`review_evidence.py`](../../app/services/review_evidence.py) — which passages a review shows (bounded display units); `ReviewDisplayService`.
    - [`review_input.py`](../../app/services/review_input.py) — parses reviewer plain-text answers ("15-21%", "up to AMD 15 million").
    - [`review_resolution.py`](../../app/services/review_resolution.py) — validates/applies replies, per-reason policy, run completion after review, admin abort.
    - [`run_lease.py`](../../app/services/run_lease.py) — heartbeat lease while executing; stop requests; stale run recovery.
    - [`run_metrics.py`](../../app/services/run_metrics.py) — SQL-derived run metrics (duration, failures, HITL rate...).
    - [`run_service.py`](../../app/services/run_service.py) — `RunService.submit/get`: the one submission boundary for API, scheduler, chat.
    - [`scalar_normalizer.py`](../../app/services/scalar_normalizer.py) — finds scalar candidates (numbers, currencies, percentages) in text.
    - [`semantic_extraction.py`](../../app/services/semantic_extraction.py) — **Gemini**: evidence-bound field extraction, validation, repair, caching, review items.
    - [`snapshot_lifecycle.py`](../../app/services/snapshot_lifecycle.py) — **acceptance rules, review signals, large-rate guard, change detection**.
    - [`source_discovery.py`](../../app/services/source_discovery.py) — rules + cache + Gemini classification of page sections/PDFs; model fallback.
    - [`source_selection.py`](../../app/services/source_selection.py) — builds the selected-sources bundle from discovery decisions.
    - [`structured_backfill.py`](../../app/services/structured_backfill.py) — backfills the typed read model from historical accepted snapshots.
    - [`structured_projection.py`](../../app/services/structured_projection.py) — accepted snapshot → offering profile, typed facts, citations, retrieval units.
    - [`structured_projection_audit.py`](../../app/services/structured_projection_audit.py) — compares stored facts with accepted extraction (no model calls).
    - [`structured_query_planning.py`](../../app/services/structured_query_planning.py) — issues the read grant (`ResolutionPlan`); default core fields.
    - [`structured_tariff_query.py`](../../app/services/structured_tariff_query.py) — answers single/compare/overview/rank/history from typed facts; field finder.
    - [`structured_unit_embeddings.py`](../../app/services/structured_unit_embeddings.py) — lazily embeds retrieval units (worker sweep).
    - [`table_normalizer.py`](../../app/services/table_normalizer.py) — rebuilds rectangular tables from rowspan/colspan; headers, sections, footnotes.
    - [`tariff_queries.py`](../../app/services/tariff_queries.py) — `CurrentTariffService` (freshness), `TariffHistoryService`, citation helpers.
    - [`telemetry.py`](../../app/services/telemetry.py) — OpenTelemetry setup; redacting span exporter; trace context through the run row.
  - [tools/](../../app/tools/) — the ADK tools (thin adapters).
    - [`__init__.py`](../../app/tools/__init__.py) — exports the 7 tools and `configure_services`.
    - [`_services.py`](../../app/tools/_services.py) — the service slots tools use (`services`), bound by `configure_services`.
    - [`_state.py`](../../app/tools/_state.py) — ADK session-state keys for grants, and helpers (`issued_this_turn`, `current_user_text`).
    - [`resolution.py`](../../app/tools/resolution.py) — `resolve_request`: interprets the turn, issues read/spend grants, pending-review counts.
    - [`reads.py`](../../app/tools/reads.py) — `answer_tariff_query`, `get_current_tariffs`, `get_tariff_history` (scope from the read grant only).
    - [`monitoring.py`](../../app/tools/monitoring.py) — `run_tariff_monitoring`, `review_pending_candidates`, `get_monitoring_status`.

Outside `app/` but referenced a lot: [migrations/](../../migrations/) (SQL schema, applied by Compose on first start),
[docs/](../../docs/) ([architecture.md](../../docs/architecture.md), [agent-and-tool-architecture.md](../../docs/agent-and-tool-architecture.md)),
[tests/](../../tests/), [scripts/](../../scripts/), [pyproject.toml](../../pyproject.toml), [README.md](../../README.md).

---

## 2. Variables you may be asked to tweak

### 2.1 How configuration works

1. [`EnvironmentSettings`](../../app/config/environment.py#L10) reads the process environment and `.env`
   (case-insensitive). **The env var name is the field name in UPPER CASE**, e.g. field
   `hitl_large_rate_change_percentage_points` ← `HITL_LARGE_RATE_CHANGE_PERCENTAGE_POINTS`.
   Comma-separated lists are split by [`parse_csv_tuple`](../../app/config/environment.py#L159).
2. [`load_settings`](../../app/config/loader.py#L28) copies each flat field into a typed group in
   [models.py](../../app/config/models.py), where **bounds are validated** (e.g. `timeout_seconds` must be 0–120).
3. [`get_settings`](../../app/config/loader.py#L202) is `lru_cache`d: **restart the process** (CLI, API or worker) after changing `.env`.
4. **Defaults come from `environment.py`**, because the loader always passes a value. When the two files
   disagree, the `environment.py` value wins. Example:
   `SEMANTIC_EXTRACTION_FALLBACK_MODEL_NAMES` defaults to `("gemini-3.8-flash",)` in
   [environment.py:123](../../app/config/environment.py#L123) but `()` in [models.py:371](../../app/config/models.py#L371).
   To change a default, edit **both** files, or just set the env var.
5. Settings are consumed in [runtime.py `build_application_container`](../../app/runtime.py#L123). That's the place to see what reads each group.

### 2.2 Environment variables / settings

Format: **ENV VAR** — default — effect. The first link goes to the env default and the second to the typed field (with its bounds).

#### Models and secrets

| Env var | Default | Where | Effect |
|---|---|---|---|
| `GEMINI_API_KEY` | none | [env:25](../../app/config/environment.py#L25) · [ModelSettings.api_key](../../app/config/models.py#L62) | Gemini key; required when `ENVIRONMENT=production` ([check](../../app/config/models.py#L529)). |
| `MODEL_NAME` | `gemini-3.7-flash` | [env:26](../../app/config/environment.py#L26) · [generation_model](../../app/config/models.py#L63) | Chat agent model ([agent.py:24](../../app/agent.py#L24)), request interpreter, primary extraction model. |
| `EMBEDDING_MODEL_NAME` | `gemini-embedding-001` | [env:27](../../app/config/environment.py#L27) · [embedding_model](../../app/config/models.py#L64) | Retrieval-unit embeddings. |
| `ENVIRONMENT` | `development` | [env:21](../../app/config/environment.py#L21) · [Environment](../../app/config/models.py#L35) | `production` requires an API key. |
| `REVIEW_ADMIN_TOKEN` | none | [env:128](../../app/config/environment.py#L128) · [HitlSettings](../../app/config/models.py#L413) | Enables `POST /api/v1/reviews/abort-pending` ([route](../../app/api/routes.py#L310)). |

#### Database and ADK sessions

| Env var | Default | Where | Effect |
|---|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://tariff:tariff@localhost:5432/tariff_monitor` | [env:28](../../app/config/environment.py#L28) · [validator](../../app/config/models.py#L90) | Business DB (must be PostgreSQL). |
| `SESSION_SERVICE_URI` | same as above | [env:31](../../app/config/environment.py#L31) · also read directly in [app_utils/services.py:47](../../app/app_utils/services.py#L47) | ADK conversation store. |
| `LOGS_BUCKET_NAME` | unset | [app_utils/services.py:99](../../app/app_utils/services.py#L99) | Use GCS for ADK artifacts instead of in-memory. |

#### Source allowlist and HTTP

Group: [HttpSettings](../../app/config/models.py#L112)

| Env var | Default | Where | Effect |
|---|---|---|---|
| `ALLOWED_SOURCE_HOSTS` | `ameriabank.am,www.ameriabank.am` | [env:34](../../app/config/environment.py#L34) · [field](../../app/config/models.py#L113) · [host validation](../../app/config/models.py#L135) | **Domain allowlist** for pages, PDFs, redirects, browser subrequests and catalog seed URLs. |
| `ALLOWED_DOWNLOAD_MIME_TYPES` | `application/pdf,text/html` | [env:38](../../app/config/environment.py#L38) · [field](../../app/config/models.py#L114) | Allowed content types. |
| `HTTP_USER_AGENT` | `ameria-tariff-monitor/0.1` | [env:42](../../app/config/environment.py#L42) | User-Agent header. |
| `DOWNLOAD_TIMEOUT_SECONDS` | `20` (0–120) | [env:43](../../app/config/environment.py#L43) · [timeout_seconds](../../app/config/models.py#L116) | HTTP timeout (shared httpx client [runtime.py:130](../../app/runtime.py#L130)). |
| `HTTP_MAX_ATTEMPTS` | `3` (1–5) | [env:44](../../app/config/environment.py#L44) · [field](../../app/config/models.py#L117) | Retries for timeouts/transport/429/5xx ([pdf_downloader.py:170](../../app/services/pdf_downloader.py#L170)). |
| `HTTP_BACKOFF_BASE_SECONDS` | `0.5` | [env:45](../../app/config/environment.py#L45) · [field](../../app/config/models.py#L118) | Exponential backoff base ([_backoff](../../app/services/pdf_downloader.py#L309)). |
| `HTTP_RETRY_JITTER_RATIO` | `0.25` | [env:46](../../app/config/environment.py#L46) | Backoff jitter. |
| `HTTP_MAX_RETRY_DELAY_SECONDS` | `120` | [env:47](../../app/config/environment.py#L47) | Caps any delay incl. `Retry-After`. |
| `MAX_REDIRECTS` | `5` (0–10) | [env:48](../../app/config/environment.py#L48) · [field](../../app/config/models.py#L121) | Redirect hops ([check](../../app/services/pdf_downloader.py#L140)). |
| `MAX_DOWNLOAD_BYTES` | `26214400` (25 MB) | [env:49](../../app/config/environment.py#L49) · [field](../../app/config/models.py#L122) | Download size cap ([header check](../../app/services/pdf_downloader.py#L268), [streaming check](../../app/services/pdf_downloader.py#L281)). |
| `ALLOW_ORIGINS` | `http://localhost:3000` | [env:147](../../app/config/environment.py#L147) · [field](../../app/config/models.py#L123) | FastAPI CORS origins. |

#### Acquisition

Group: [AcquisitionSettings](../../app/config/models.py#L191)

| Env var | Default | Where | Effect |
|---|---|---|---|
| `ACQUISITION_BROWSER_ENABLED` | `true` | [env:50](../../app/config/environment.py#L50) · [field](../../app/config/models.py#L192) | Render every page in Playwright; if false, static HTML only ([acquisition.py:123](../../app/services/acquisition.py#L123)). |
| `ACQUISITION_MIN_MAIN_CONTENT_CHARS` | `1500` | [env:51](../../app/config/environment.py#L51) · [field](../../app/config/models.py#L197) | Completeness floor ([completeness_floor_failures](../../app/services/acquisition.py#L58)). |
| `ACQUISITION_MIN_MAIN_CONTENT_CHARS_WITHOUT_STRUCTURE` | `3000` | [env:52](../../app/config/environment.py#L52) · [field](../../app/config/models.py#L200) | Floor for a page with no table/PDF link. |
| `ACQUISITION_BROWSER_NAVIGATION_TIMEOUT_SECONDS` | `30` | [env:53](../../app/config/environment.py#L53) · [field](../../app/config/models.py#L203) | Browser navigation timeout. |
| `ACQUISITION_BROWSER_SETTLE_MILLISECONDS` | `750` | [env:54](../../app/config/environment.py#L54) | Wait after load before reading. |
| `ACQUISITION_MAX_INTERACTIONS` | `100` | [env:55](../../app/config/environment.py#L55) | Accordion/tab clicks cap. |
| `ACQUISITION_MAX_LINKED_DOCUMENTS` | `40` | [env:56](../../app/config/environment.py#L56) · [cap](../../app/services/acquisition.py#L251) | Max linked PDFs downloaded per page. |
| `ACQUISITION_FRESHNESS_HOURS` | `1.0` (0 = off) | [env:57](../../app/config/environment.py#L57) · [field](../../app/config/models.py#L211) | Reuse a recent fetch instead of re-fetching. |
| `ACQUISITION_BASELINE_MAX_PDF_LINK_DROP` / `..._MAIN_CONTENT_DROP` | `0.5` / `0.6` | [env:58-59](../../app/config/environment.py#L58) · [fields](../../app/config/models.py#L215) | Regression gate vs. last good acquisition. |

#### PDF transcription and OCR

Groups: [PdfExtractionSettings](../../app/config/models.py#L219), [OcrSettings](../../app/config/models.py#L248)

| Env var | Default | Where | Effect |
|---|---|---|---|
| `PDF_EXTRACTION_MODEL_NAME` | `gemini-3.1-flash-lite` | [env:62](../../app/config/environment.py#L62) · [field](../../app/config/models.py#L223) | PDF transcription model. |
| `PDF_EXTRACTION_FALLBACK_MODEL_NAMES` | empty | [env:63](../../app/config/environment.py#L63) | Next models to try. |
| `PDF_EXTRACTION_MAX_PRICE_PER_MILLION_TOKENS_USD` | `1.5` | [env:64](../../app/config/environment.py#L64) · [enforced](../../app/services/pdf_extraction.py#L176) | Refuses to start with pricier models. |
| `PDF_EXTRACTION_MAX_ATTEMPTS` / `_BACKOFF_BASE_SECONDS` / `_MAX_BACKOFF_SECONDS` / `_RETRY_JITTER_RATIO` | `3` / `5` / `60` / `0.25` | [env:65-68](../../app/config/environment.py#L65) | Gemini PDF retries ([extract loop](../../app/services/gemini_pdf_extractor.py#L118)). |
| `PDF_EXTRACTION_PROBE_TEXT_THRESHOLD` | `20` chars | [env:69](../../app/config/environment.py#L69) · [probe](../../app/services/pdf_input_probe.py#L22) | Below this a page counts as having no text layer (image-only ⇒ OCR). |
| `PDF_EXTRACTION_SKIP_HISTORICAL` | `true` | [env:70](../../app/config/environment.py#L70) | Skip PDFs whose link metadata says historical. |
| `PDF_EXTRACTION_SCHEMA_VERSION` / `_PROMPT_VERSION` | `3` / `3` | [env:60-61](../../app/config/environment.py#L60) | Cache keys; **bump after editing the PDF prompt**. |
| `OCR_ENABLED` | `true` | [env:71](../../app/config/environment.py#L71) · [check](../../app/services/ocr_transcriber.py#L55) | OCR fallback on/off. |
| `OCR_LANGUAGES` | `hye+eng` | [env:72](../../app/config/environment.py#L72) · [validator](../../app/config/models.py#L262) | Tesseract languages (Armenian + English). |
| `OCR_RENDER_DPI` | `200` | [env:73](../../app/config/environment.py#L73) | Rasterization DPI. |
| `OCR_MAX_PAGES` | `20` | [env:74](../../app/config/environment.py#L74) | Pages OCR'd per document. |
| `OCR_MAX_PIXELS_PER_PAGE` | `40,000,000` | [env:75](../../app/config/environment.py#L75) | Pixel budget. |
| `OCR_MIN_CONFIDENCE` | `60.0` | [env:76](../../app/config/environment.py#L76) · [field](../../app/config/models.py#L256) | Below this a page yields **no** text (never a guess). |
| `OCR_TIMEOUT_SECONDS` | `60` | [env:77](../../app/config/environment.py#L77) | Per-page OCR timeout. |
| `OCR_TESSERACT_CMD` | unset | [env:78](../../app/config/environment.py#L78) | Tesseract binary path. |

#### Source discovery

Group: [SourceDiscoverySettings](../../app/config/models.py#L319). Also used by PDF link selection ([runtime.py:211](../../app/runtime.py#L211)).

| Env var | Default | Where | Effect |
|---|---|---|---|
| `SOURCE_DISCOVERY_MODEL_NAME` | `gemini-3.1-flash-lite` | [env:107](../../app/config/environment.py#L107) · [field](../../app/config/models.py#L336) | Classifier model. |
| `SOURCE_DISCOVERY_FALLBACK_MODEL_NAMES` | `gemini-3.5-flash-lite` | [env:108](../../app/config/environment.py#L108) · [field](../../app/config/models.py#L340) | Fallback chain ([FallbackSourceDiscoveryService](../../app/services/source_discovery.py#L422)). |
| `SOURCE_DISCOVERY_MAX_PRICE_PER_MILLION_TOKENS_USD` | `2.5` | [env:111](../../app/config/environment.py#L111) · [enforced](../../app/runtime.py#L173) | Price cap. |
| `SOURCE_DISCOVERY_MAX_ITEMS_PER_BATCH` / `_MAX_CHARS_PER_ITEM` / `_MAX_CHARS_PER_BATCH` | `8` / `3000` / `18000` | [env:96-98](../../app/config/environment.py#L96) · [fields](../../app/config/models.py#L323) | Batch size limits. |
| `SOURCE_DISCOVERY_MAX_CONCURRENT_BATCHES` | `3` | [env:99](../../app/config/environment.py#L99) · [semaphore](../../app/services/source_discovery.py#L336) | Parallel classifier calls. |
| `SOURCE_DISCOVERY_CLASSIFIER_MAX_ATTEMPTS` / `_BACKOFF_BASE_SECONDS` / `_MAX_BACKOFF_SECONDS` / `_RETRY_JITTER_RATIO` | `3` / `5` / `60` / `0.25` | [env:102-105](../../app/config/environment.py#L102) | Retries ([classify loop](../../app/services/discovery_classifier.py#L199)). |
| `SOURCE_DISCOVERY_CLASSIFIER_MAX_OUTPUT_TOKENS` | `8192` | [env:106](../../app/config/environment.py#L106) | Output cap. |
| `SOURCE_DISCOVERY_POLICY_VERSION` / `_PROMPT_VERSION` | `2` / `2` | [env:94-95](../../app/config/environment.py#L94) | Cache keys; **bump after editing the discovery prompt/rules**. |

#### Semantic extraction

Group: [SemanticExtractionSettings](../../app/config/models.py#L368)

| Env var | Default | Where | Effect |
|---|---|---|---|
| `SEMANTIC_EXTRACTION_FALLBACK_MODEL_NAMES` | `gemini-3.8-flash` (env) | [env:123](../../app/config/environment.py#L123) | Per-call fallback ([_call](../../app/services/semantic_extraction.py#L797)). |
| `SEMANTIC_EXTRACTION_EVIDENCE_MODE` | `full` | [env:114](../../app/config/environment.py#L114) · [field](../../app/config/models.py#L377) | `full` = whole evidence per call; `budgeted` = labelled units within a budget. |
| `SEMANTIC_EXTRACTION_MAX_PACKET_CHARS` | `200000` | [env:115](../../app/config/environment.py#L115) · [check](../../app/services/extraction_planner.py#L165) | Full mode fails above this (never truncates). |
| `SEMANTIC_EXTRACTION_BUDGET_CHARS` | `16000` | [env:116](../../app/config/environment.py#L116) | Budgeted mode per call. |
| `SEMANTIC_EXTRACTION_THINKING_BUDGET` | `0` | [env:117](../../app/config/environment.py#L117) · [used](../../app/services/semantic_extraction.py#L338) | Thinking tokens. |
| `SEMANTIC_EXTRACTION_MAX_OUTPUT_TOKENS` | `16384` | [env:118](../../app/config/environment.py#L118) | Truncated answer ⇒ asked once more ([L478](../../app/services/semantic_extraction.py#L478)). |
| `SEMANTIC_EXTRACTION_MAX_REPAIRS_PER_RUN` | `6` | [env:119](../../app/config/environment.py#L119) · [used](../../app/services/semantic_extraction.py#L1051) | Bounded one-field repair calls. |
| `SEMANTIC_EXTRACTION_MAX_CONCURRENT_CALLS` | `3` | [env:120](../../app/config/environment.py#L120) · [semaphore](../../app/services/semantic_extraction.py#L663) | Parallel extraction calls. |
| `SEMANTIC_EXTRACTION_SCHEMA_VERSION` / `_PROMPT_VERSION` | `6` / `7` | [env:112-113](../../app/config/environment.py#L112) | Cache namespace. (The cache key also hashes the instruction text itself: [prompt_fingerprint](../../app/services/semantic_extraction.py#L603).) |

#### HITL, change detection, queries

| Env var | Default | Where | Effect |
|---|---|---|---|
| `HITL_LARGE_RATE_CHANGE_PERCENTAGE_POINTS` | `3` | [env:127](../../app/config/environment.py#L127) · [field](../../app/config/models.py#L412) · [passed](../../app/runtime.py#L298) · [compared `>=`](../../app/services/snapshot_lifecycle.py#L522) | **Rate jump that forces a human review.** |
| `HITL_DOCUMENT_RANK_GAP` | `0.05` | [env:126](../../app/config/environment.py#L126) · [field](../../app/config/models.py#L411) | Second evidence unit shown if it ranks within this gap. |
| `TARIFF_FRESHNESS_DAYS` | `7` | [env:87](../../app/config/environment.py#L87) · [field](../../app/config/models.py#L309) | "Fresh" vs "stale" accepted data. |
| `TARIFF_RECENT_CHANGE_DAYS` / `TARIFF_DEFAULT_HISTORY_DAYS` / `TARIFF_MAX_HISTORY_RESULTS` | `60` / `30` / `100` | [env:88-90](../../app/config/environment.py#L88) | History windows. |
| `TARIFF_RUN_POLL_SECONDS` | `0.5` | [env:91](../../app/config/environment.py#L91) | Poll while following another process's run. |
| `RETRIEVAL_TRACE_LEVEL` / `RETRIEVAL_LOG_FILE` | `summary` / unset | [env:92-93](../../app/config/environment.py#L92) | Retrieval step tracing. |
| `INTENT_CLASSIFIER_MAX_ATTEMPTS` | `2` | [env:86](../../app/config/environment.py#L86) | Interpreter retries ([loop](../../app/services/intent_resolution.py#L243)). |
| `CHUNK_SIZE_CHARS` | `1500` (500–2000) | [env:79](../../app/config/environment.py#L79) · [field](../../app/config/models.py#L287) | Knowledge chunk size ([runtime.py:265](../../app/runtime.py#L265)). |
| `EMBEDDING_MAX_ATTEMPTS` / `_BACKOFF_BASE_SECONDS` / `EMBEDDING_QUOTA_*` | `3` / `10` / `4`, `30` | [env:80-83](../../app/config/environment.py#L80) | Embedding retries (5xx vs 429). |
| `EMBEDDING_SWEEP_BATCH` / `_INTERVAL_SECONDS` | `200` / `300` | [env:84-85](../../app/config/environment.py#L84) | Worker embedding sweep. |

#### Scheduler and run lease

Group: [SchedulerSettings](../../app/config/models.py#L416)

| Env var | Default | Where | Effect |
|---|---|---|---|
| `SCHEDULE_ENABLED` | `true` | [env:129](../../app/config/environment.py#L129) · [used](../../app/worker.py#L53) | Daily job on/off. |
| `SCHEDULE_TIMEZONE` / `SCHEDULE_HOUR` / `SCHEDULE_MINUTE` | `Asia/Yerevan` / `6` / `0` | [env:130-132](../../app/config/environment.py#L130) · [cron](../../app/worker.py#L56) | When the daily run fires. |
| `RUN_HEARTBEAT_SECONDS` | `5` | [env:133](../../app/config/environment.py#L133) | Lease renewal interval. |
| `RUN_LEASE_SECONDS` | `120` (≥ 4 heartbeats, [check](../../app/config/models.py#L433)) | [env:134](../../app/config/environment.py#L134) | Silent run ⇒ `run.abandoned`. |
| `RUN_RECOVERY_INTERVAL_SECONDS` | `60` | [env:135](../../app/config/environment.py#L135) | Worker's abandoned-run sweep. |

#### Application, logging, tracing

| Env var | Default | Where | Effect |
|---|---|---|---|
| `APP_NAME` | `ameria-tariff-monitor` | [env:20](../../app/config/environment.py#L20) | FastAPI title. |
| `ARTIFACT_TEMP_DIR` | `data/artifacts` | [env:22](../../app/config/environment.py#L22) | Raw HTML/PDF artifact store. |
| `PIPELINE_AUDIT_ENABLED` / `PIPELINE_AUDIT_DIR` | `true` / `artifacts/pipeline-audit` | [env:23-24](../../app/config/environment.py#L23) · [used](../../app/runtime.py#L269) | Per-stage Markdown audit overlays. |
| `LOG_LEVEL` / `LOG_FILE` / `LOG_TIMEZONE` / `LOG_MAX_BYTES` / `LOG_BACKUP_COUNT` | `INFO` / unset / `Asia/Yerevan` / 10 MB / 10 | [env:136-140](../../app/config/environment.py#L136) · [setup](../../app/services/logging_setup.py#L26) | Logging. |
| `OTEL_ENABLED` / `OTEL_TRACES_ENDPOINT` / `OTEL_SERVICE_NAME` / `OTEL_TO_CLOUD` / `OTEL_EXPORT_TIMEOUT_SECONDS` | off | [env:141-146](../../app/config/environment.py#L141) | Tracing export. |
| `OTEL_TRACE_CONTENT` | `none` | [env:145](../../app/config/environment.py#L145) · [TraceContentMode](../../app/config/models.py#L447) | `mapped` exports prompts/responses in spans; `none` keeps them out. |

#### Catalog (data file)

File: [seed_catalog.yaml](../../app/config/seed_catalog.yaml)

- Enable/disable an offering: its `enabled:` line, e.g. [consumer_standard](../../app/config/seed_catalog.yaml#L30).
- Change a seed URL: its `seed_url:` (must be HTTPS and allowlisted, [check](../../app/config/seed_catalog.py#L40)).
- Add a synonym/alias/Armenian name: the `localized_names` block of the offering (duplicates across offerings are rejected, [collision check](../../app/domain/catalog.py#L190)).
- Offerings: [consumer_standard L26](../../app/config/seed_catalog.yaml#L26), [overdraft L42](../../app/config/seed_catalog.yaml#L42), [credit_line L59](../../app/config/seed_catalog.yaml#L59), [online_consumer_finance L76](../../app/config/seed_catalog.yaml#L76), [mortgage_online L92](../../app/config/seed_catalog.yaml#L92), [mortgage_primary L108](../../app/config/seed_catalog.yaml#L108), [mortgage_diaspora L124](../../app/config/seed_catalog.yaml#L124), [mortgage_secondary_market L140](../../app/config/seed_catalog.yaml#L140), [mortgage_commercial L156](../../app/config/seed_catalog.yaml#L156), [mortgage_express L172](../../app/config/seed_catalog.yaml#L172), [mortgage_no_income_verification L188](../../app/config/seed_catalog.yaml#L188), [mortgage_renovation L204](../../app/config/seed_catalog.yaml#L204), [mortgage_construction L220](../../app/config/seed_catalog.yaml#L220).
- Adding a **new** offering also needs a new member in [`OfferingId`](../../app/domain/models.py#L12) (and its family in [`.product`](../../app/domain/models.py#L28)).

### 2.3 Prompts the model sees

| Prompt | Where | What it controls | Cache note |
|---|---|---|---|
| Chat agent instruction | [`INSTRUCTION` agent.py:28](../../app/agent.py#L28) | Language, honesty, how to report tool statuses, when monitoring may be called. | — |
| Request interpreter | [`INTERPRETER_INSTRUCTION` intent_resolution.py:98](../../app/services/intent_resolution.py#L98) (message wrapper [L274](../../app/services/intent_resolution.py#L274)) | Intents ([L105](../../app/services/intent_resolution.py#L105)), offer replies ([L123](../../app/services/intent_resolution.py#L123)), scope rules ([L139](../../app/services/intent_resolution.py#L139)), query fields/operations ([L163](../../app/services/intent_resolution.py#L163)). | No cache. |
| PDF link selection | [`PDF_LINK_INSTRUCTION` pdf_link_selection.py:46](../../app/services/pdf_link_selection.py#L46) (user msg [build_link_prompt](../../app/services/pdf_link_selection.py#L77)) | Which linked PDFs belong to the offering. | Bump [`PDF_LINK_PROMPT_VERSION`](../../app/services/pdf_link_selection.py#L43). |
| Source discovery | [`SOURCE_DISCOVERY_INSTRUCTION` discovery_classifier.py:27](../../app/services/discovery_classifier.py#L27) (user msg [build_classifier_prompt](../../app/services/discovery_classifier.py#L295)) | product_association categories ([L39](../../app/services/discovery_classifier.py#L39)), temporal status ([L80](../../app/services/discovery_classifier.py#L80)). | Bump `SOURCE_DISCOVERY_PROMPT_VERSION`. |
| PDF transcription | [`PDF_EXTRACTION_INSTRUCTION` gemini_pdf_extractor.py:38](../../app/services/gemini_pdf_extractor.py#L38) (user msg [L150](../../app/services/gemini_pdf_extractor.py#L150)) | Page-faithful blocks/tables, no interpretation. | Bump `PDF_EXTRACTION_PROMPT_VERSION`. |
| Semantic extraction | [`SEMANTIC_EXTRACTION_INSTRUCTION` semantic_extraction.py:92](../../app/services/semantic_extraction.py#L92) (user msg [build_extraction_prompt](../../app/services/semantic_extraction.py#L1174), evidence rendering [render_evidence_packet](../../app/services/semantic_extraction.py#L1223)) | Field rules: percentages as points ([L149](../../app/services/semantic_extraction.py#L149)), fee scope ([L157](../../app/services/semantic_extraction.py#L157)), term subranges ([L167](../../app/services/semantic_extraction.py#L167)), value shapes ([L184](../../app/services/semantic_extraction.py#L184)). | Auto: the instruction text is part of the cache key ([L615](../../app/services/semantic_extraction.py#L615)). |
| Review pause text | [`review_policy` review_resolution.py:608](../../app/services/review_resolution.py#L608) | Guidance and allowed decisions per review reason (shown to the reviewer and the model). | — |

All model calls use temperature 0 and strict output schemas ([agent](../../app/agent.py#L71) disables automatic function calling; classifiers: [discovery_classifier.py:145](../../app/services/discovery_classifier.py#L145); extraction: [semantic_extraction.py:336](../../app/services/semantic_extraction.py#L336)).

### 2.4 Hard-coded constants (code changes)

#### Agent and tools

| Constant | Value | Where | Effect |
|---|---|---|---|
| Agent model retries | `attempts=3` | [agent.py:68](../../app/agent.py#L68) | SDK retries for chat calls. |
| `TOOLS` | 7 tools | [agent.py:55](../../app/agent.py#L55) | Tools registered on the agent. |
| `BUSINESS_TOOLS` | 6 names | [plugins.py:22](../../app/plugins.py#L22) | Tools that require `resolve_request` first. |
| History page size clamp | `1..100` | [reads.py:154](../../app/tools/reads.py#L154) | `get_tariff_history` limit. |
| `PLAN_LIFETIME` | 30 min | [structured_query_planning.py:24](../../app/services/structured_query_planning.py#L24) | Read grant expiry. |
| `CORE_FIELDS` | amount, rates, term, 5 fee types | [structured_query_planning.py:28](../../app/services/structured_query_planning.py#L28) | What "tell me about X" answers with. |
| Catalog intro size | first 3 offerings | [intent_resolution.py:426](../../app/services/intent_resolution.py#L426) | Greeting listing. |
| `_ARMENIAN_SUFFIXES` | `ը, ն, ի, ին…` | [intent_resolution.py:73](../../app/services/intent_resolution.py#L73) | Exact-match cross-check of inflected Armenian names. |

#### Pipeline, retries, runs

| Constant | Value | Where | Effect |
|---|---|---|---|
| Page acquisition retry | 1 retry after 10 s | [monitoring_pipeline.py:146](../../app/services/monitoring_pipeline.py#L146) · transient set [L133](../../app/services/monitoring_pipeline.py#L133) | Retries only browser failure / incomplete content. |
| Bank id | `"ameria"` | [monitoring_pipeline.py:404](../../app/services/monitoring_pipeline.py#L404) | Snapshot lookup scope. |
| Run status decision | succeeded / partial / failed | [monitoring_pipeline.py:771](../../app/services/monitoring_pipeline.py#L771) | Family run outcome. |
| Worker poll interval | `2.0 s` | [worker.py:104](../../app/worker.py#L104) | Queue polling. |
| Scheduled families | consumer_loan, mortgage | [worker.py:36](../../app/worker.py#L36) | What the daily job submits. |
| Follow timeout | `1800 s` | [monitoring_node.py:76](../../app/services/monitoring_node.py#L76) | Max time a chat follows another process's run. |
| `_RETRYABLE_STATUS_CODES` | 429, 500, 502, 503, 504 | [discovery_classifier.py:99](../../app/services/discovery_classifier.py#L99) | Which Gemini errors are retried (all model stages). |
| PDF signature / redirects | `%PDF-`, 301/302/303/307/308 | [pdf_downloader.py:19](../../app/services/pdf_downloader.py#L19) | Download validation. |
| Port rule | only 443 | [urls.py:28](../../app/security/urls.py#L28) | URL validation. |
| `_MAX_LINKS_PER_BATCH` | 40 | [pdf_link_selection.py:44](../../app/services/pdf_link_selection.py#L44) | PDF link classifier batch. |
| `_OCR_MEMO_PAGES` | 500 | [pdf_extraction.py:71](../../app/services/pdf_extraction.py#L71) | In-process OCR memo size. |
| PDF admission word lists | relevant / historical / irrelevant | [pdf_admission.py:17](../../app/services/pdf_admission.py#L17), [L30](../../app/services/pdf_admission.py#L30), [L39](../../app/services/pdf_admission.py#L39) | Which PDFs are skipped before any model call. |

#### Validation, acceptance, change detection

These are the most likely live changes.

| Constant | Value | Where | Effect |
|---|---|---|---|
| `_REQUIRED_TARIFF_FIELDS` | product_name, loan_amount, interest_rate, effective_rate, term, fees, repayment, eligibility, required_documents | [snapshot_lifecycle.py:46](../../app/services/snapshot_lifecycle.py#L46) | A required field `not_stated` ⇒ `missing_required_field` review. |
| `_OFFICIAL_EVIDENCE_AUTHORITIES` | 4 official authorities | [snapshot_lifecycle.py:37](../../app/services/snapshot_lifecycle.py#L37) | Non-official evidence ⇒ `source_applicability` review. |
| `_RATE_FIELDS` | interest_rate, effective_rate | [snapshot_lifecycle.py:59](../../app/services/snapshot_lifecycle.py#L59) | Fields checked for large jumps. |
| Large-rate comparison | `largest >= threshold` | [snapshot_lifecycle.py:522](../../app/services/snapshot_lifecycle.py#L522) | Change to `>` to make the threshold exclusive. |
| `_RATE_ENTRY_MATCH_FLOOR` | 0.3 | [snapshot_lifecycle.py:574](../../app/services/snapshot_lifecycle.py#L574) | Pairing rate entries across snapshots by condition words. |
| `_PROVENANCE_KEYS` | quote, source_url, locator… | [snapshot_lifecycle.py:64](../../app/services/snapshot_lifecycle.py#L64) | Ignored when comparing snapshots (no false changes). |
| Accepted currencies | `AMD`, `USD`, `EUR` | [MoneyRange.currency](../../app/domain/semantic_extraction.py#L165), [LoanFee.currency](../../app/domain/semantic_extraction.py#L254), [_condition_dimension](../../app/services/semantic_extraction.py#L1541), [review_input `_CURRENCIES`](../../app/services/review_input.py#L31) | Adding a currency means editing all four. |
| Range rules | min ≤ max, ≥ 0, rates/pct ≤ 100 | [MoneyRange](../../app/domain/semantic_extraction.py#L162), [Rate](../../app/domain/semantic_extraction.py#L228), [TermRange](../../app/domain/semantic_extraction.py#L270), [PercentagePoint](../../app/domain/semantic_extraction.py#L22) | Schema validation of values. |
| Fraction → percentage points | `0 < x < 1 ⇒ x*100` | [_normalize_percentage](../../app/services/semantic_extraction.py#L1607) | Down payment / LTV normalization. |
| `_GROUNDED_FIELDS` | rates, amounts, term, fees… | [semantic_extraction.py:1815](../../app/services/semantic_extraction.py#L1815) | Every number must appear in the cited quote. |
| `_MULTIPLIERS` | million/billion/thousand | [semantic_extraction.py:1839](../../app/services/semantic_extraction.py#L1839) | "AMD 3-150 million" number reading. |
| `_REPAIR_PRIORITY` | rates first | [semantic_extraction.py:1791](../../app/services/semantic_extraction.py#L1791) | Which fields get the repair budget. |
| `_EXPLICIT_INCOME` | regex | [semantic_extraction.py:2216](../../app/services/semantic_extraction.py#L2216) | Income verification needs explicit wording. |
| Field groups / calls | 3 calls | [_GROUPS](../../app/services/extraction_planner.py#L18), [FULL_MODE_CALLS](../../app/services/extraction_planner.py#L80), [CATEGORY_FIELDS](../../app/services/extraction_planner.py#L115) | Which fields are extracted per category. |
| `FIELD_TERMS` | label words | [extraction_terms.py:22](../../app/domain/extraction_terms.py#L22) | Budgeted-mode evidence selection only. |
| `_FEE_TERMS` | EN+HY fee phrases | [structured_tariffs.py:428](../../app/domain/structured_tariffs.py#L428) | Maps a fee description to application/disbursement/service/... |
| `_SALARY_WORD` | salary / payroll / աշխատավարձ | [structured_projection.py:58](../../app/services/structured_projection.py#L58) | Produces `privilege.salary_customer` facts. |

#### Review display and answering

| Constant | Value | Where |
|---|---|---|
| Review display bounds (`TABLE_WHOLE_ROWS`, `SECTION_MAX_CHARS`, `UNITS_PER_REVIEW`, `MODEL_SEED_PASSAGES`, `MODEL_EXCERPT_CHARS`...) | 30 rows, 3000 chars, 2 units, 5 passages, 600 chars | [review_evidence.py:34-45](../../app/services/review_evidence.py#L34) |
| `_REVIEW_PAGE` | 100 | [review_resolution.py:57](../../app/services/review_resolution.py#L57) |
| Reviewer words (`_TRUE_WORDS`, `_FALSE_WORDS`, `_MULTIPLIERS`, `_RATE_TYPES`) | — | [review_input.py:39-55](../../app/services/review_input.py#L39) |
| `RANK_FUSION_VERSION`, `FIELD_FINDER_MAX_PATHS`, `OVERVIEW_MAX_*` | rrf k60, 3, 6, 240 | [structured_tariff_query.py:47-53](../../app/services/structured_tariff_query.py#L47) |
| `MODEL_PRICE_CATALOG` | $/M tokens per model and date | [model_pricing.py:18](../../app/services/model_pricing.py#L18) |
| CLI flags `--user --session --new --verbose` | — | [cli.py:1077](../../app/cli.py#L1077) |
| API input bounds (query 2–1000 chars, Idempotency-Key ≤ 200) | — | [routes.py:50](../../app/api/routes.py#L50), [L107](../../app/api/routes.py#L107) |

---

## 3. Module summaries

### Entry points
- **[agent.py](../../app/agent.py)**: defines `root_agent` (Gemini `MODEL_NAME`, the instruction, 7 tools, AFC disabled) and the resumable `App` with `ToolPolicyPlugin`. Resumability is required so a review pause can replay the original monitoring tool call. Both the CLI and ADK Web load this app.
- **[cli.py](../../app/cli.py)** / **[cli_entry.py](../../app/cli_entry.py)**: `./tariff-chat`. `ChatSession` runs one invocation per message. It renders progress from `custom_metadata`, turns each `adk_request_input` pause into a Rich review panel, and resumes the same invocation with the validated reply. It also handles Ctrl-C (cancel + rewind) and closes runs a crashed CLI left running.
- **[fast_api_app.py](../../app/fast_api_app.py)**: builds the ADK FastAPI app (dev UI, A2A), wires the container into `app.state` and the tool services, and mounts [api/routes.py](../../app/api/routes.py).
- **[worker.py](../../app/worker.py)**: `MonitoringWorker` claims queued runs (`FOR UPDATE SKIP LOCKED`), executes `TariffPipeline` under a lease with progress logged, recovers abandoned runs, completes reviewed runs and sweeps embeddings. APScheduler submits both families daily. It owns no ADK objects.
- **[runtime.py](../../app/runtime.py)**: the composition root shared by CLI, API and worker. It wires settings into repositories, model fallback chains (with price caps), gates, the pipeline, the review services and the monitoring node. Read this file to see which config value feeds which class.

### plugins / tools
- **[plugins.py](../../app/plugins.py)**: tool order is enforced in code, not the prompt. A business tool without a same-invocation resolution returns `policy.resolve_first`, and a tool exception becomes `{"status":"error"}`.
- **[tools/resolution.py](../../app/tools/resolution.py)**: `resolve_request()` reads the user's message itself, calls `RequestResolver`, clears the old grants, and issues the read grant (`ResolutionPlan`) and/or the spend grant (explicit monitoring request, or a yes to the previous turn's offer). It's idempotent per turn.
- **[tools/reads.py](../../app/tools/reads.py)**: read tools take no scope argument. `answer_tariff_query` (one use per grant) routes through `TariffAnswerRouter`. `get_current_tariffs` returns freshness only and writes a monitoring *offer* when data is missing. `get_tariff_history` returns cited history.
- **[tools/monitoring.py](../../app/tools/monitoring.py)**: `run_tariff_monitoring` checks that the spend grant matches the requested scope and asks for confirmation before a family-wide run, then calls `tool_context.run_node(monitoring_node)`. `review_pending_candidates` runs the same node in review-only mode.
- **[tools/_state.py](../../app/tools/_state.py)** / **[_services.py](../../app/tools/_services.py)**: session-state keys for the grants, and the service slots tools read from.

### config
- **[environment.py](../../app/config/environment.py) → [loader.py](../../app/config/loader.py) → [models.py](../../app/config/models.py)**: the environment is read flat, then mapped into frozen, validated groups. Consumers depend only on their group.
- **[seed_catalog.py](../../app/config/seed_catalog.py) + [seed_catalog.yaml](../../app/config/seed_catalog.yaml)**: the runtime source of truth for supported offerings. It is validated at startup (unique ids and URLs, HTTPS, allowlisted host, no name collisions).

### services: run orchestration
- **[monitoring_pipeline.py](../../app/services/monitoring_pipeline.py)**: `TariffPipeline.execute` loops over the run's offerings and isolates failures per offering (`partial_success`). It creates review tasks and pauses or finishes the run. `IndexingPipeline.refresh` runs the stages for one offering: acquisition → pdf_selection → normalization → source_discovery → semantic_extraction → previous_snapshot → snapshot build/validation → projection → publication. Each stage maps exceptions to a stable failure code in `_stage`.
- **[monitoring_node.py](../../app/services/monitoring_node.py)**: the ADK `FunctionNode` (`rerun_on_resume=True`). It submits or finds the run, claims and executes it in-process (streaming partial progress events) or follows another process's run. It yields one `RequestInput` per pending review, applies decisions on resume, and returns a `MonitoringResult` with the answer.
- **[run_service.py](../../app/services/run_service.py)** / **[run_lease.py](../../app/services/run_lease.py)** / **[monitoring_progress.py](../../app/services/monitoring_progress.py)**: submission, heartbeat lease plus stop requests, and progress events.
- **[contracts.py](../../app/services/contracts.py)**: the `TariffPipeline` protocol both executors depend on.

### services: acquisition
- **[acquisition.py](../../app/services/acquisition.py)**: fetches the page (static, then Playwright render when enabled). It enforces the completeness floor, downloads same-host linked PDFs (capped), stores raw bytes, and computes `page_content_hash` and `content_hash`.
- **[acquisition_freshness.py](../../app/services/acquisition_freshness.py)** wraps **[acquisition_completeness.py](../../app/services/acquisition_completeness.py)**, which wraps `AcquisitionService`. The outer gate reuses a recent fetch; the inner gate fails a sharp drop against the last good acquisition.
- **[pdf_downloader.py](../../app/services/pdf_downloader.py)**, **[html_retriever.py](../../app/services/html_retriever.py)**, **[browser_renderer.py](../../app/services/browser_renderer.py)**, **[html_parser.py](../../app/services/html_parser.py)**, **[artifact_store.py](../../app/services/artifact_store.py)**: secure fetchers (allowlist on every hop, bounded retries, size/MIME/signature checks), the parser, and content-addressed storage.

### services: document processing
- **[normalization.py](../../app/services/normalization.py)**: `StructuralNormalizationService` turns the page plus PDFs into one `NormalizedSourceBundle` (blocks, rectangular tables, notes, scalar candidates, source references, warnings). It uses [block_normalizer.py](../../app/services/block_normalizer.py), [table_normalizer.py](../../app/services/table_normalizer.py), [scalar_normalizer.py](../../app/services/scalar_normalizer.py) and [normalization_baseline.py](../../app/services/normalization_baseline.py).
- **[pdf_extraction.py](../../app/services/pdf_extraction.py)**: per PDF, it runs admission ([pdf_admission.py](../../app/services/pdf_admission.py)) and the input probe ([pdf_input_probe.py](../../app/services/pdf_input_probe.py)), checks the cache, then transcribes with Gemini ([gemini_pdf_extractor.py](../../app/services/gemini_pdf_extractor.py)). Pages with no text layer that Gemini left empty, or every page when all models fail, go to OCR ([pdf_rasterizer.py](../../app/services/pdf_rasterizer.py) + [ocr_transcriber.py](../../app/services/ocr_transcriber.py)).
- **[pdf_link_selection.py](../../app/services/pdf_link_selection.py)**: before paying for transcription, Gemini decides from link metadata alone which admitted PDFs are the offering's own, shared terms, another product's, or bank-wide. The decisions are cached.

### services: source discovery and extraction
- **[source_discovery.py](../../app/services/source_discovery.py)**: builds candidates ([discovery_prefilter.py](../../app/services/discovery_prefilter.py)), applies deterministic rules, reuses cached assessments, and sends only the unresolved candidates to the Gemini classifier ([discovery_classifier.py](../../app/services/discovery_classifier.py)). Children inherit their container's decision. [source_selection.py](../../app/services/source_selection.py) builds the selected bundle.
- **[semantic_extraction.py](../../app/services/semantic_extraction.py)**: [extraction_evidence.py](../../app/services/extraction_evidence.py) builds the evidence catalog and [extraction_planner.py](../../app/services/extraction_planner.py) creates 3 batched calls. The service calls Gemini per batch (cache first, fallback models per call), then validates every field deterministically: evidence ids, verbatim quotes, numbers present in quotes, condition-distinct alternatives, category vs. catalog. It spends a bounded number of one-field repair calls, reuses remembered review decisions, and produces a `LoanProduct` or a partial product plus review items.
- **[snapshot_lifecycle.py](../../app/services/snapshot_lifecycle.py)**: the acceptance decision (`extraction_is_acceptable`) and review signals (`detect_review_signals`: OCR, applicability, conflict, missing required, invalid; plus `detect_large_rate_changes`). It builds the canonical, provenance-free tariff payload and hash, and the field-by-field change set (`compare_accepted_snapshots`).

### services: projection and answering
- **[knowledge_projection.py](../../app/services/knowledge_projection.py)**: selected sources become versioned knowledge documents/chunks (text evidence anchors). **[structured_projection.py](../../app/services/structured_projection.py)**: an accepted snapshot becomes typed `TariffFact`s with verified citations and retrieval units.
- **[structured_query_planning.py](../../app/services/structured_query_planning.py)**: builds the read grant from a validated resolution. **[structured_tariff_query.py](../../app/services/structured_tariff_query.py)**: answers from accepted facts (single/compare/overview/rank/history), abstains when values aren't comparable, and uses lexical + vector retrieval only to *find fields*. **[answer_read_model.py](../../app/services/answer_read_model.py)**: `TariffAnswerRouter`, the one answer path.
- **[intent_resolution.py](../../app/services/intent_resolution.py)** + **[interpretation_validation.py](../../app/services/interpretation_validation.py)**: one tool-free Gemini call per chat turn proposes intent, scope, standalone question and query shape. Code validates it against the catalog, decides clarification and the route, and derives conversation state.
- **[tariff_queries.py](../../app/services/tariff_queries.py)**: current tariffs with freshness and a "newer pending review" flag, and bounded history.
- **[structured_unit_embeddings.py](../../app/services/structured_unit_embeddings.py)** / **[embedding_providers.py](../../app/services/embedding_providers.py)**: lazy embedding of retrieval units (worker sweep) and query embedding.

### services: HITL
- **[review_resolution.py](../../app/services/review_resolution.py)**: validates a reply per reason (`review_policy`) and applies it idempotently. A `reject_all` supersedes the snapshot's other reviews. It completes paused runs, closes orphaned reviews, and handles the admin abort.
- **[review_decisions.py](../../app/services/review_decisions.py)**: applies a decision to the candidate snapshot. Once every review is approved, it accepts, records changes and publishes in one transaction. It also remembers decisions.
- **[review_evidence.py](../../app/services/review_evidence.py)** / **[review_input.py](../../app/services/review_input.py)**: which passages a reviewer sees (bounded units), and deterministic parsing of typed answers.

### services: cross-cutting
- **[failure_mapping.py](../../app/services/failure_mapping.py)**: exception → `SourceFailureCode`, with bounded, safe details.
- **[model_call_usage.py](../../app/services/model_call_usage.py)** / **[model_pricing.py](../../app/services/model_pricing.py)**: per-call usage/cost ledger (no prompts logged), price catalog, fallback sequences, price caps.
- **[telemetry.py](../../app/services/telemetry.py)** / **[logging_setup.py](../../app/services/logging_setup.py)** / **[retrieval_trace.py](../../app/services/retrieval_trace.py)** / **[run_metrics.py](../../app/services/run_metrics.py)** / **[pipeline_audit_archive.py](../../app/services/pipeline_audit_archive.py)**: OTel with a redacting exporter, one trace per run, logs, retrieval traces, SQL metrics, and Markdown stage audits.

### domain
- **[semantic_extraction.py](../../app/domain/semantic_extraction.py)**: the extraction contract. `ExtractedValue` enforces "found needs value + evidence, not_stated has neither". Value models validate ranges. The `LoanProduct` details vary by category.
- **[structured_tariffs.py](../../app/domain/structured_tariffs.py)**: the read model (canonical `FieldPath`s with EN/HY labels), the `ResolutionPlan` read grant, and `TariffFact`/`RetrievalUnit`.
- **[monitoring.py](../../app/domain/monitoring.py)**: run lifecycle and every failure-code enum. **[review.py](../../app/domain/review.py)**: HITL contracts. **[catalog.py](../../app/domain/catalog.py)**: catalog contracts. **[models.py](../../app/domain/models.py)**: product/offering ids.

### repositories
- **[monitoring.py](../../app/repositories/monitoring.py)**: run queue (advisory-locked submit, idempotency keys, claim, heartbeat, recovery) and the **single-transaction publication** (documents, snapshot, change set, manifests, projection, audit event).
- **[reviews.py](../../app/repositories/reviews.py)**: review CRUD under publication locks. It supersedes older pending reviews and refuses stale approvals (`StaleReviewError`).
- **[knowledge_publication.py](../../app/repositories/knowledge_publication.py)**: immutable document versions and activating a snapshot's document set. The cache repositories store model answers keyed by content fingerprints.

### security / app_utils
- **[security/urls.py](../../app/security/urls.py)**: the host allowlist check used by the catalog loader, downloaders and renderer.
- **[app_utils/](../../app/app_utils/)**: generated ADK plumbing. It provides a shared PostgreSQL session service and the A2A routes.

---

## 4. Assignment brief → code map

The requirements are from [System Description](../../Project%20Documents/System%20Description.md).

| Requirement | Where it's implemented |
|---|---|
| **§4 End-to-end flow** | [`IndexingPipeline.refresh`](../../app/services/monitoring_pipeline.py#L226): stages at [L271](../../app/services/monitoring_pipeline.py#L271) (acquisition), [L304](../../app/services/monitoring_pipeline.py#L304) (PDF selection), [L309](../../app/services/monitoring_pipeline.py#L309) (normalization), [L329](../../app/services/monitoring_pipeline.py#L329) (discovery), [L354](../../app/services/monitoring_pipeline.py#L354) (extraction), [L400](../../app/services/monitoring_pipeline.py#L400) (previous snapshot), [L411](../../app/services/monitoring_pipeline.py#L411) (validation / HITL signals), [L479](../../app/services/monitoring_pipeline.py#L479) (compare), [L493](../../app/services/monitoring_pipeline.py#L493) (publish). |
| **5.1 ADK agent**: role, instructions | [agent.py `INSTRUCTION`](../../app/agent.py#L28), [`root_agent`](../../app/agent.py#L65) |
| 5.1 tools | [`TOOLS`](../../app/agent.py#L55); [tools table in docs](../../docs/agent-and-tool-architecture.md#L74) |
| 5.1 state/session | [grant keys `_state.py`](../../app/tools/_state.py#L15); PostgreSQL ADK sessions [app_utils/services.py:45](../../app/app_utils/services.py#L45) |
| 5.1 stopping/error conditions | typed statuses: [resolve_request](../../app/tools/resolution.py#L88), [reads](../../app/tools/reads.py#L41), [run_tariff_monitoring](../../app/tools/monitoring.py#L76), [plugin envelopes](../../app/plugins.py#L57) |
| 5.1 Gemini vs deterministic | [docs §4](../../docs/agent-and-tool-architecture.md#L134); Gemini sites in [§2.3](#23-prompts-the-model-sees) |
| No unrestricted LLM access | [ToolPolicyPlugin](../../app/plugins.py#L34); tools get only services [_services.py](../../app/tools/_services.py#L14) |
| **5.2 Tool design** | [tools/resolution.py](../../app/tools/resolution.py), [tools/reads.py](../../app/tools/reads.py), [tools/monitoring.py](../../app/tools/monitoring.py) |
| **5.3 Official source discovery**: fuzzy/semantic product matching | [INTERPRETER_INSTRUCTION scope rules](../../app/services/intent_resolution.py#L139), [RequestResolver.resolve_turn](../../app/services/intent_resolution.py#L330), catalog synonyms/transliterations [seed_catalog.yaml](../../app/config/seed_catalog.yaml#L25), Armenian suffix matching [L547](../../app/services/intent_resolution.py#L547) |
| 5.3 relevant page / document discovery | seed URLs; [pdf_link_selection.py](../../app/services/pdf_link_selection.py#L46); [source_discovery.py](../../app/services/source_discovery.py#L313) |
| 5.3 domain allowlist | [`validate_source_url`](../../app/security/urls.py#L9), [`ALLOWED_SOURCE_HOSTS`](../../app/config/models.py#L113), [per-redirect check](../../app/services/pdf_downloader.py#L138) |
| **5.4 Digital PDF parsing** | [probe_pdf_input](../../app/services/pdf_input_probe.py#L10), [GeminiPdfExtractionService.plan](../../app/services/pdf_extraction.py#L183), [AdkGeminiPdfExtractor](../../app/services/gemini_pdf_extractor.py#L54) |
| 5.4 OCR fallback | [`_pages_needing_ocr`](../../app/services/pdf_extraction.py#L230), [`_transcribe_pages`](../../app/services/pdf_extraction.py#L249), [TesseractOcrTranscriber](../../app/services/ocr_transcriber.py#L39), [PdfiumPageRasterizer](../../app/services/pdf_rasterizer.py#L60), OCR ⇒ review [snapshot_lifecycle.py:268](../../app/services/snapshot_lifecycle.py#L268) |
| 5.4 cleaning/structuring | [normalization.py](../../app/services/normalization.py), [table_normalizer.py](../../app/services/table_normalizer.py), [block_normalizer.py](../../app/services/block_normalizer.py), chrome removal in [page hash](../../app/services/acquisition.py#L328) |
| **5.5 Chunking and RAG** | chunks: [KnowledgeProjectionService](../../app/services/knowledge_projection.py) ([`CHUNK_SIZE_CHARS`](../../app/config/models.py#L287)); retrieval units + field finder: [structured_projection.py](../../app/services/structured_projection.py), [structured_tariff_query.py](../../app/services/structured_tariff_query.py#L47) (RRF lexical + vector), [docs/rag-retrieval.md](../../docs/rag-retrieval.md) |
| 5.5 evidence to the model | [render_evidence_packet](../../app/services/semantic_extraction.py#L1223), [build_extraction_prompt](../../app/services/semantic_extraction.py#L1174) |
| **5.6 Structured extraction schema** | [LoanProduct](../../app/domain/semantic_extraction.py#L419), [ExtractionField](../../app/domain/semantic_extraction.py#L444), [see §5.2](#52-assignment-fields--schema) |
| 5.6 missing = NOT_FOUND | [ExtractionStatus.NOT_STATED](../../app/domain/semantic_extraction.py#L42), [ExtractedValue.validate_state](../../app/domain/semantic_extraction.py#L367) |
| **5.7 Evidence and provenance** | [EvidenceCitation](../../app/domain/semantic_extraction.py#L349) (url, locator, page, section, quote), [quote must be in evidence](../../app/services/semantic_extraction.py#L2237), [`source_span`](../../app/services/semantic_extraction.py#L1851), [FactEvidence](../../app/domain/structured_tariffs.py#L552) |
| **5.8 Deterministic validation**: schema/required | [_validate_field_result](../../app/services/semantic_extraction.py#L2379), [_validate_semantic_completeness](../../app/services/semantic_extraction.py#L2049), [extraction_is_acceptable](../../app/services/snapshot_lifecycle.py#L189) |
| 5.8 currency/value normalization | [normalize_extraction_field_value](../../app/services/semantic_extraction.py#L1341), [MoneyRange](../../app/domain/semantic_extraction.py#L162) |
| 5.8 rate/amount checks | [Rate](../../app/domain/semantic_extraction.py#L228), [numbers grounded in quotes](../../app/services/semantic_extraction.py#L2135) |
| 5.8 term formats | [TermRange](../../app/domain/semantic_extraction.py#L270), [term threshold rule](../../app/services/semantic_extraction.py#L2153) |
| 5.8 domain / file type / size | [urls.py](../../app/security/urls.py#L9), [MIME check](../../app/services/pdf_downloader.py#L241), [size](../../app/services/pdf_downloader.py#L253), [signature](../../app/services/pdf_downloader.py#L288) |
| **5.9 Change detection** | [compare_accepted_snapshots](../../app/services/snapshot_lifecycle.py#L674), normalization before compare [`_canonicalize`](../../app/services/snapshot_lifecycle.py#L724), [SnapshotChangeSet](../../app/domain/monitoring.py#L352); scheduled trigger [worker.py:51](../../app/worker.py#L51) |
| **5.10 HITL** | signals [detect_review_signals](../../app/services/snapshot_lifecycle.py#L237) + [large rate](../../app/services/snapshot_lifecycle.py#L497); pause [monitoring_node.py:316](../../app/services/monitoring_node.py#L316); CLI prompt [_ask_review_decision](../../app/cli.py#L793); policy [review_policy](../../app/services/review_resolution.py#L608); apply [ReviewDecisionService.apply](../../app/services/review_decisions.py#L57) |
| **5.11 Error handling** | timeouts/retries [pdf_downloader](../../app/services/pdf_downloader.py#L170); 404 ⇒ warning [acquisition.py:273](../../app/services/acquisition.py#L273); Gemini retries [discovery_classifier.py:199](../../app/services/discovery_classifier.py#L199), model fallback [source_discovery.py:422](../../app/services/source_discovery.py#L422); invalid output [parse_batch_response](../../app/services/semantic_extraction.py#L2647); failure codes [domain/monitoring.py:78-162](../../app/domain/monitoring.py#L78); mapping [failure_mapping.py](../../app/services/failure_mapping.py#L49); page retry [acquire_with_retry](../../app/services/monitoring_pipeline.py#L142); product not found ⇒ clarification [interpretation_validation.py](../../app/services/interpretation_validation.py#L143); previous snapshot missing ⇒ empty change set [L680](../../app/services/snapshot_lifecycle.py#L680) |
| **5.12 Security** | secrets via env [`SecretStr`](../../app/config/models.py#L62); input validation [routes](../../app/api/routes.py#L47), [ReviewDecision](../../app/domain/review.py#L91); download limits [config](../../app/config/models.py#L122); least privilege [ToolPolicyPlugin](../../app/plugins.py#L34) + grants; admin token [compare_digest](../../app/api/routes.py#L320); logging without content [telemetry.py](../../app/services/telemetry.py#L1), [model_call_usage.py](../../app/services/model_call_usage.py#L1) |
| **5.13 Observability** | spans per stage [monitoring_pipeline.py:259](../../app/services/monitoring_pipeline.py#L259); trace across processes [worker.py:147](../../app/worker.py#L147); audit events `record_audit` [contracts.py:98](../../app/repositories/contracts.py#L98); metrics [run_metrics.py](../../app/services/run_metrics.py); cost [model_call_usage.py](../../app/services/model_call_usage.py#L50); stage audit [pipeline_audit_archive.py](../../app/services/pipeline_audit_archive.py) |
| **5.14 Tests and evaluation** | [§6.3 test map](#63-test-map); eval [tests/eval/RESULTS.md](../../tests/eval/RESULTS.md) |
| **5.15 Python engineering** | [pyproject.toml](../../pyproject.toml), typed config [config/models.py](../../app/config/models.py), [README.md](../../README.md) |

---

## 5. Glossary and data model

### 5.1 Glossary

| Term | Meaning | Defined in |
|---|---|---|
| **Family / product** | `consumer_loan` or `mortgage`. | [ProductType](../../app/domain/models.py#L7) |
| **Offering** | One concrete bank product page (13 of them). | [OfferingId](../../app/domain/models.py#L12), [seed_catalog.yaml](../../app/config/seed_catalog.yaml#L25) |
| **Category** | consumer_loan / overdraft / credit_line / mortgage; decides which detail fields are extracted. | [OfferingCategory](../../app/domain/catalog.py#L85), [CATEGORY_FIELDS](../../app/services/extraction_planner.py#L115) |
| **Seed URL** | The approved official page of an offering. | [SeedCatalogEntry](../../app/domain/catalog.py#L111) |
| **Run** | One monitoring execution for a family or one offering; queued → running → awaiting_review → succeeded / partial_success / failed. | [MonitoringRun](../../app/domain/monitoring.py#L208), [RunStatus](../../app/domain/monitoring.py#L33) |
| **Trigger** | Who started the run: api / schedule / adk (chat). | [RunTrigger](../../app/domain/monitoring.py#L26) |
| **Offering execution** | The per-offering part of a run with its current stage. | [OfferingExecution](../../app/domain/monitoring.py#L260) |
| **Claim / lease / heartbeat** | The executing process owns a run and renews `heartbeat_at`; a silent run is closed `run.abandoned`. | [run_lease.py](../../app/services/run_lease.py#L49), [LeaseState](../../app/domain/monitoring.py#L93) |
| **PageArtifact** | Immutable acquisition output: HTML, blocks, tables, links, PDFs, hashes. | [domain/acquisition.py](../../app/domain/acquisition.py) |
| **Completeness / freshness gate** | Reject thin pages / reuse recent fetch. | [acquisition.py:58](../../app/services/acquisition.py#L58), [acquisition_freshness.py](../../app/services/acquisition_freshness.py) |
| **Admission / input probe** | Deterministic pre-model PDF checks: relevance/historical from metadata; per-page text-layer mode. | [pdf_admission.py:100](../../app/services/pdf_admission.py#L100), [pdf_input_probe.py:10](../../app/services/pdf_input_probe.py#L10) |
| **PDF link selection** | Gemini decision per linked PDF: current_product / shared_terms / related_product / generic / unclear. | [pdf_link_selection.py:57](../../app/services/pdf_link_selection.py#L57) |
| **NormalizedSourceBundle** | Page + PDFs in one evidence schema. | [domain/normalization.py](../../app/domain/normalization.py) |
| **Source discovery / assessment** | Classification of each section/table/PDF: product_association, role, relevance, authority, temporal status. | [SOURCE_DISCOVERY_INSTRUCTION](../../app/services/discovery_classifier.py#L27), [domain/source_discovery.py](../../app/domain/source_discovery.py) |
| **Authority** | e.g. official_terms, official_product_content; only official authorities can support accepted values. | [_OFFICIAL_EVIDENCE_AUTHORITIES](../../app/services/snapshot_lifecycle.py#L37) |
| **Evidence item / evidence_id** | One citable passage (`ev_` + 24 hex), content-addressed. | [EvidenceItem](../../app/domain/semantic_extraction.py#L475) |
| **Batch / call** | One extraction call over a field group with an evidence packet. | [ExtractionBatch](../../app/domain/semantic_extraction.py#L527), [FULL_MODE_CALLS](../../app/services/extraction_planner.py#L80) |
| **Repair** | A bounded one-field re-ask that fixes schema/citation only. | [_repair_batch](../../app/services/semantic_extraction.py#L1944) |
| **Review memory** | A remembered reviewer decision reused when the same call/result recurs. | [_apply_review_memory](../../app/services/semantic_extraction.py#L905), [RememberedReviewDecision](../../app/domain/semantic_extraction.py#L588) |
| **Snapshot / candidate** | One extraction attempt; `accepted` or `review_required` (a *candidate*, inert until reviewed). | [SnapshotAttempt](../../app/domain/monitoring.py#L311), [SnapshotStatus](../../app/domain/monitoring.py#L58) |
| **Canonical payload / hash** | Normalized tariff JSON without provenance keys; used for change detection. | [canonical_tariff_payload](../../app/services/snapshot_lifecycle.py#L83) |
| **Change set** | Field-level diffs between previous and current accepted snapshots. | [SnapshotChangeSet](../../app/domain/monitoring.py#L352) |
| **Review signal / reason** | Why a human is needed: large_rate_change, official_source_conflict, source_applicability, missing_required_field, ocr_evidence, extraction_invalid. | [ReviewReason](../../app/domain/review.py#L17) |
| **Review task / decision** | Durable HITL record; decisions approve / select_candidate / override / confirm_not_stated / reject_all. | [ReviewTask](../../app/domain/review.py#L188), [ReviewDecisionType](../../app/domain/review.py#L74) |
| **Publication** | One DB transaction: documents, snapshot, changes, manifests, facts, audit event. | [OfferingPublication](../../app/domain/monitoring.py#L368) |
| **Tariff fact / FieldPath** | Typed accepted value at a canonical path (e.g. `rate.nominal.minimum`) with citations. | [TariffFact](../../app/domain/structured_tariffs.py#L570), [FieldPath](../../app/domain/structured_tariffs.py#L19) |
| **Retrieval unit / field finder** | Searchable text for an offering's facts; used only to find which fields a question means. | [RetrievalUnit](../../app/domain/structured_tariffs.py#L632) |
| **Read grant** | `ResolutionPlan` in session state: the scope/fields a read tool may touch this turn (30 min). | [ResolutionPlan](../../app/domain/structured_tariffs.py#L490), [issue_read_grant](../../app/services/structured_query_planning.py#L51) |
| **Spend grant** | Authorization for a paid monitoring run, bound to the invocation. | [resolution.py:121-149](../../app/tools/resolution.py#L121), [MONITOR_AUTHORIZATION_KEY](../../app/tools/_state.py#L23) |
| **Monitoring offer / scope confirmation** | The assistant's one-turn offer to refresh; a family-wide run needs an explicit yes. | [MONITOR_OFFER_KEY](../../app/tools/_state.py#L26), [tools/monitoring.py:87](../../app/tools/monitoring.py#L87) |
| **Monitoring node / RequestInput / interrupt id** | ADK node that pauses per review; ids `review:<run>:<review>[:n]`. | [review_interrupt_id](../../app/services/monitoring_node.py#L143) |
| **Failure codes** | Stable namespaced strings (`source.timeout`, `run.cancelled`...). | [domain/monitoring.py:78](../../app/domain/monitoring.py#L78), [failure_mapping.py](../../app/services/failure_mapping.py) |

### 5.2 Assignment fields → schema

There are two schemas. The **extraction schema** is what Gemini fills and what gets validated ([LoanProduct](../../app/domain/semantic_extraction.py#L419)). The **read model** is what questions are answered from ([FieldPath](../../app/domain/structured_tariffs.py#L19)). [`SOURCE_FIELD_PATHS`](../../app/domain/structured_tariffs.py#L341) maps one to the other.

| Assignment field | Extraction schema | Read model (FieldPath) |
|---|---|---|
| Արժույթ — Currency | Not a standalone field. It is carried inside values: [MoneyRange.currency](../../app/domain/semantic_extraction.py#L165), [LoanFee.currency](../../app/domain/semantic_extraction.py#L254), and condition dimension [`currency`](../../app/domain/semantic_extraction.py#L89) | [TariffFact.currency](../../app/domain/structured_tariffs.py#L580) |
| Ժամկետ — Term | [`term`](../../app/domain/semantic_extraction.py#L428) → [TermRange](../../app/domain/semantic_extraction.py#L270) (months, or indefinite/on_demand) | [`term.*`](../../app/domain/structured_tariffs.py#L39) |
| Գումար — Amount | [`loan_amount`](../../app/domain/semantic_extraction.py#L425) → [LoanAmount](../../app/domain/semantic_extraction.py#L222) (absolute / salary multiple / % of property / formula) | [`amount.*`](../../app/domain/structured_tariffs.py#L26) |
| Անվանական տոկոսադրույք — Nominal rate | [`interest_rate`](../../app/domain/semantic_extraction.py#L426) → [Rate](../../app/domain/semantic_extraction.py#L228) | [`rate.nominal.*`](../../app/domain/structured_tariffs.py#L33) |
| Փաստացի տոկոսադրույք — Effective rate | [`effective_rate`](../../app/domain/semantic_extraction.py#L427) | [`rate.effective.*`](../../app/domain/structured_tariffs.py#L36) |
| Ապահովվածություն — Collateral | `details.collateral` ([consumer](../../app/domain/semantic_extraction.py#L382), [mortgage](../../app/domain/semantic_extraction.py#L392)) → [CollateralTerm](../../app/domain/semantic_extraction.py#L338) | [`collateral.*`](../../app/domain/structured_tariffs.py#L59) |
| Հայտի ուսումնասիրության վճար — Application fee | [`fees`](../../app/domain/semantic_extraction.py#L429) list of [LoanFee](../../app/domain/semantic_extraction.py#L250) (description tells which fee) | [`fee.application`](../../app/domain/structured_tariffs.py#L43), classified by [fee_field_path](../../app/domain/structured_tariffs.py#L438) |
| Տրամադրման վճար — Disbursement fee | same `fees` list | [`fee.disbursement`](../../app/domain/structured_tariffs.py#L44) |
| Սպասարկման վճար — Service fee | same `fees` list | [`fee.service`](../../app/domain/structured_tariffs.py#L45) |
| Աշխատավարձը բանկով ստանալիս արտոնություններ — Salary privileges | No dedicated extraction field. It shows up as conditions (e.g. `borrower_type`/`program`) or [`special_conditions`](../../app/domain/semantic_extraction.py#L438) | [`privilege.salary_customer`](../../app/domain/structured_tariffs.py#L58), derived by [`_SALARY_WORD`](../../app/services/structured_projection.py#L58) |

The bilingual labels for these paths are in [`FIELD_LABELS`](../../app/domain/structured_tariffs.py#L92) (e.g. [fee labels](../../app/domain/structured_tariffs.py#L185)).
There is also a simple assignment-shaped model, [`LoanTariff`](../../app/domain/models.py#L64), with exactly these 10 fields and `FOUND/NOT_FOUND` ([ValueStatus](../../app/domain/models.py#L44)). The live pipeline uses `LoanProduct`.

**How "missing" is represented:** every field is an [`ExtractedValue`](../../app/domain/semantic_extraction.py#L361) with a status of `found | not_stated | ambiguous | conflicting` ([ExtractionStatus](../../app/domain/semantic_extraction.py#L40)). `not_stated` must have no value and no evidence ([validator](../../app/domain/semantic_extraction.py#L372)). A required field that is `not_stated` blocks acceptance ([L202](../../app/services/snapshot_lifecycle.py#L202)) and raises a `missing_required_field` review ([L327](../../app/services/snapshot_lifecycle.py#L327)). A reviewer can answer `confirm_not_stated` ([ReviewDecisionType](../../app/domain/review.py#L80)). The answer path reports `not_stated_in_source` ([TariffQueryResult.reason_code](../../app/domain/structured_tariffs.py#L680)).

### 5.3 Key models

| Model | Where | Purpose |
|---|---|---|
| `Settings` (+ 15 groups) | [config/models.py:511](../../app/config/models.py#L511) | All configuration. |
| `SeedCatalog`, `SeedCatalogEntry` | [domain/catalog.py:158](../../app/domain/catalog.py#L158), [L111](../../app/domain/catalog.py#L111) | Catalog. |
| `RunCommand`, `MonitoringRun`, `OfferingExecution` | [domain/monitoring.py:184](../../app/domain/monitoring.py#L184), [L208](../../app/domain/monitoring.py#L208), [L260](../../app/domain/monitoring.py#L260) | Run lifecycle. |
| `LoanProduct`, `ExtractedValue`, `EvidenceCitation`, `EvidenceItem` | [domain/semantic_extraction.py:419](../../app/domain/semantic_extraction.py#L419), [L361](../../app/domain/semantic_extraction.py#L361), [L349](../../app/domain/semantic_extraction.py#L349), [L475](../../app/domain/semantic_extraction.py#L475) | Extraction contract. |
| `SemanticExtractionResult` | [domain/semantic_extraction.py:632](../../app/domain/semantic_extraction.py#L632) | What extraction returns. |
| `SnapshotAttempt`, `SnapshotChange`, `SnapshotChangeSet`, `OfferingPublication` | [domain/monitoring.py:311](../../app/domain/monitoring.py#L311), [L342](../../app/domain/monitoring.py#L342), [L352](../../app/domain/monitoring.py#L352), [L368](../../app/domain/monitoring.py#L368) | Snapshot & publication. |
| `ReviewTask`, `ReviewDecision`, `ReviewPromptView` | [domain/review.py:188](../../app/domain/review.py#L188), [L91](../../app/domain/review.py#L91), [L176](../../app/domain/review.py#L176) | HITL. |
| `ResolutionPlan`, `TariffFact`, `TariffQueryResult` | [domain/structured_tariffs.py:490](../../app/domain/structured_tariffs.py#L490), [L570](../../app/domain/structured_tariffs.py#L570), [L667](../../app/domain/structured_tariffs.py#L667) | Read side. |
| `MonitoringResult` | [monitoring_node.py:121](../../app/services/monitoring_node.py#L121) | What the monitoring tool returns to the model. |

### 5.4 Database tables

The schema is in [migrations/](../../migrations/) (applied in numeric order on first start). Table names are from [architecture.md](../../docs/architecture.md#L803).

| Table | Created in | Written/read by | Holds |
|---|---|---|---|
| `monitoring_runs` | [001_initial.sql](../../migrations/001_initial.sql#L3), reshaped in `006` | [repositories/monitoring.py](../../app/repositories/monitoring.py) | The run queue: scope, status, claim, heartbeat, summary, idempotency. |
| `offering_executions` | `006` | repositories/monitoring.py | Per-offering stage, counts and failure code. |
| `tariff_snapshots` | [001_initial.sql](../../migrations/001_initial.sql#L14), extended in `006` | repositories/monitoring.py, reviews.py | Every extraction attempt (accepted or candidate), evidence, validation, canonical hash. |
| `tariff_changes` | `006` | repositories/monitoring.py | Field changes between snapshots. |
| `source_manifests` | `006` | repositories/monitoring.py | Which sources a run saw and selected. |
| `knowledge_documents`, `knowledge_chunks` | `002`, `023`, `027` | [knowledge_publication.py](../../app/repositories/knowledge_publication.py) | Versioned evidence documents (text). |
| `snapshot_documents` | `023` | knowledge_publication.py | Which document versions a snapshot was built from. |
| `offering_profiles`, `tariff_facts`, `fact_evidence`, `retrieval_units`, `model_call_usage` | `011_structured_tariff_read_model.sql` | [repositories/structured_projection.py](../../app/repositories/structured_projection.py), [structured_tariff_query.py](../../app/repositories/structured_tariff_query.py), [model_call_usage.py](../../app/services/model_call_usage.py) | The typed read model and the model call ledger. |
| embedding cache / unit vectors | `012`, `013` | [embedding_cache.py](../../app/repositories/embedding_cache.py) | Content-addressed vectors. |
| semantic extraction cache, `review_decision_memory` | `004_semantic_extraction.sql`, `021_...review_memory.sql` | [repositories/semantic_extraction.py](../../app/repositories/semantic_extraction.py), [review_memory.py](../../app/repositories/review_memory.py) | Batch answers and remembered decisions. |
| `pdf_link_selections` | `020` | [repositories/pdf_link_selection.py](../../app/repositories/pdf_link_selection.py) | Cached PDF link decisions. |
| source discovery cache | scoped per offering in `019` | [repositories/source_discovery.py](../../app/repositories/source_discovery.py) | Cached assessments. |
| `acquisition_baselines`, `acquisition_snapshots` | — | [acquisition_baselines.py](../../app/repositories/acquisition_baselines.py), [acquisition_snapshots.py](../../app/repositories/acquisition_snapshots.py) | Completeness baseline and freshness reuse. |
| review tasks, audit events | see migrations | [repositories/reviews.py](../../app/repositories/reviews.py), `record_audit` in repositories/monitoring.py | HITL records and the audit trail. |

Other notable migrations: `009` (`_yerevan` timestamp columns), `010_offering_scoped_active_runs.sql`, `016_drop_review_workflow_correlation.sql`, `018` (acquisition time/reuse on executions), `022` (pending review unique per field + reason), `024` (cancel requests), `026_awaiting_review_does_not_block.sql`, `027` (dropped the old RAG vectors).

---

## 6. Symbol index and test map

### 6.1 Symbol index (A–Z)

- [`acquire_with_retry`](../../app/services/monitoring_pipeline.py#L142): one retry for transient page failures
- [`AcquisitionService`](../../app/services/acquisition.py#L89) · [`.acquire`](../../app/services/acquisition.py#L109)
- [`AdkGeminiPdfExtractor`](../../app/services/gemini_pdf_extractor.py#L54)
- [`AdkPdfLinkClassifier`](../../app/services/pdf_link_selection.py#L84)
- [`AdkRequestInterpreter`](../../app/services/intent_resolution.py#L206)
- [`AdkSemanticExtractor`](../../app/services/semantic_extraction.py#L317)
- [`AdkSourceDiscoveryClassifier`](../../app/services/discovery_classifier.py#L266)
- [`answer_tariff_query`](../../app/tools/reads.py#L56) (tool)
- [`ApplicationContainer`](../../app/runtime.py#L90)
- [`assemble_loan_product`](../../app/services/semantic_extraction.py#L2760)
- [`assess_pdf_metadata`](../../app/services/pdf_admission.py#L100)
- [`build_acquisition_service`](../../app/services/acquisition.py#L413)
- [`build_application_container`](../../app/runtime.py#L123)
- [`build_extraction_batches`](../../app/services/extraction_planner.py#L143)
- [`build_extraction_prompt`](../../app/services/semantic_extraction.py#L1174)
- [`build_monitoring_node`](../../app/services/monitoring_node.py#L160)
- [`build_review_view`](../../app/services/review_resolution.py#L574)
- [`build_snapshot_attempt`](../../app/services/snapshot_lifecycle.py#L107)
- [`canonical_sha256`](../../app/services/snapshot_lifecycle.py#L97) · [`canonical_tariff_payload`](../../app/services/snapshot_lifecycle.py#L83)
- [`ChatSession`](../../app/cli.py#L386) · [`.converse`](../../app/cli.py#L463) · [`.answer_reviews`](../../app/cli.py#L516) · [`.interrupt`](../../app/cli.py#L414)
- [`cited_evidence_set`](../../app/services/review_evidence.py#L88)
- [`compare_accepted_snapshots`](../../app/services/snapshot_lifecycle.py#L674)
- [`completeness_floor_failures`](../../app/services/acquisition.py#L58)
- [`configure_application_logging`](../../app/services/logging_setup.py#L26)
- [`configure_services`](../../app/tools/_services.py#L30)
- [`CurrentTariffService`](../../app/services/tariff_queries.py#L24)
- [`detect_large_rate_changes`](../../app/services/snapshot_lifecycle.py#L497)
- [`detect_review_signals`](../../app/services/snapshot_lifecycle.py#L237)
- [`EnvironmentSettings`](../../app/config/environment.py#L10)
- [`estimate_cost`](../../app/services/model_call_usage.py#L50)
- [`execute_with_lease`](../../app/services/run_lease.py#L49)
- [`ExtractedValue`](../../app/domain/semantic_extraction.py#L361) · [`ExtractionField`](../../app/domain/semantic_extraction.py#L444) · [`ExtractionStatus`](../../app/domain/semantic_extraction.py#L40)
- [`extraction_is_acceptable`](../../app/services/snapshot_lifecycle.py#L189)
- [`FallbackSemanticExtractionService`](../../app/services/semantic_extraction.py#L2994)
- [`FallbackSourceDiscoveryService`](../../app/services/source_discovery.py#L422)
- [`fee_field_path`](../../app/domain/structured_tariffs.py#L438)
- [`FIELD_LABELS`](../../app/domain/structured_tariffs.py#L92) · [`FieldPath`](../../app/domain/structured_tariffs.py#L19)
- [`get_current_tariffs`](../../app/tools/reads.py#L91) (tool)
- [`get_monitoring_status`](../../app/tools/monitoring.py#L185) (tool)
- [`get_settings`](../../app/config/loader.py#L202)
- [`get_tariff_history`](../../app/tools/reads.py#L128) (tool)
- [`GeminiPdfExtractionService`](../../app/services/pdf_extraction.py#L150)
- [`IndexingPipeline`](../../app/services/monitoring_pipeline.py#L189) · [`.refresh`](../../app/services/monitoring_pipeline.py#L226) · [`._stage`](../../app/services/monitoring_pipeline.py#L541)
- [`InterpretationValidator`](../../app/services/interpretation_validation.py#L115) · [`.validate`](../../app/services/interpretation_validation.py#L143)
- [`is_model_fallback_error`](../../app/services/discovery_classifier.py#L315) · [`is_retryable_api_error`](../../app/services/discovery_classifier.py#L303)
- [`issue_read_grant`](../../app/services/structured_query_planning.py#L51) · [`issue_typed_plan`](../../app/services/structured_query_planning.py#L114)
- [`load_seed_catalog`](../../app/config/seed_catalog.py#L19) · [`load_settings`](../../app/config/loader.py#L28)
- [`LoanProduct`](../../app/domain/semantic_extraction.py#L419) · [`LoanTariff`](../../app/domain/models.py#L64)
- [`main` (CLI)](../../app/cli.py#L1077) · [`main` (worker)](../../app/worker.py#L313)
- [`MonitoringResult`](../../app/services/monitoring_node.py#L121) · [`MonitoringRun`](../../app/domain/monitoring.py#L208)
- [`MonitoringWorker`](../../app/worker.py#L85) · [`.process_next`](../../app/worker.py#L133)
- [`normalize_extraction_field_value`](../../app/services/semantic_extraction.py#L1341)
- [`OfferingId`](../../app/domain/models.py#L12)
- [`OfferingPipelineError`](../../app/services/monitoring_pipeline.py#L171)
- [`parse_batch_response`](../../app/services/semantic_extraction.py#L2647)
- [`parse_review_field_text`](../../app/services/review_input.py#L91)
- [`PdfDownloader`](../../app/services/pdf_downloader.py#L103) · [`.download`](../../app/services/pdf_downloader.py#L121)
- [`probe_pdf_input`](../../app/services/pdf_input_probe.py#L10)
- [`ProgressRenderer`](../../app/cli.py#L241)
- [`render_evidence_packet`](../../app/services/semantic_extraction.py#L1223)
- [`RequestResolver`](../../app/services/intent_resolution.py#L308) · [`.resolve_turn`](../../app/services/intent_resolution.py#L330) · [`.shape_for`](../../app/services/intent_resolution.py#L376)
- [`ResolutionPlan`](../../app/domain/structured_tariffs.py#L490)
- [`resolve_request`](../../app/tools/resolution.py#L48) (tool)
- [`review_pending_candidates`](../../app/tools/monitoring.py#L148) (tool)
- [`review_policy`](../../app/services/review_resolution.py#L608)
- [`ReviewDecisionService`](../../app/services/review_decisions.py#L44)
- [`ReviewReason`](../../app/domain/review.py#L17) · [`ReviewTask`](../../app/domain/review.py#L188)
- [`ReviewResolutionService`](../../app/services/review_resolution.py#L97) · [`.validate`](../../app/services/review_resolution.py#L143) · [`.apply`](../../app/services/review_resolution.py#L182) · [`.complete_run`](../../app/services/review_resolution.py#L256)
- [`run_tariff_monitoring`](../../app/tools/monitoring.py#L37) (tool)
- [`RunCommand`](../../app/domain/monitoring.py#L184) · [`RunRepository`](../../app/repositories/contracts.py#L42) · [`RunService`](../../app/services/run_service.py#L45)
- [`schedule_daily_monitoring`](../../app/worker.py#L51)
- [`SeedCatalog`](../../app/domain/catalog.py#L158)
- [`SemanticExtractionService`](../../app/services/semantic_extraction.py#L508) · [`.extract`](../../app/services/semantic_extraction.py#L621) · [`.plan`](../../app/services/semantic_extraction.py#L532)
- [`Settings`](../../app/config/models.py#L511)
- [`SnapshotAttempt`](../../app/domain/monitoring.py#L311)
- [`source_failure_code`](../../app/services/failure_mapping.py#L49)
- [`source_span`](../../app/services/semantic_extraction.py#L1851)
- [`SourceDiscoveryService`](../../app/services/source_discovery.py#L195) · [`.discover`](../../app/services/source_discovery.py#L313)
- [`StructuredAdkClassifier`](../../app/services/discovery_classifier.py#L117)
- [`structured_to_answer_result`](../../app/services/answer_read_model.py#L56)
- [`tariff_fields`](../../app/services/snapshot_lifecycle.py#L657)
- [`TariffFact`](../../app/domain/structured_tariffs.py#L570)
- [`TariffPipeline`](../../app/services/monitoring_pipeline.py#L570) · [`.execute`](../../app/services/monitoring_pipeline.py#L584)
- [`TesseractOcrTranscriber`](../../app/services/ocr_transcriber.py#L39)
- [`ToolPolicyPlugin`](../../app/plugins.py#L34)
- [`validate_source_url`](../../app/security/urls.py#L9)

Defined further down their files (open the file and search for the name): `TariffAnswerRouter` ([answer_read_model.py](../../app/services/answer_read_model.py)), `StructuredTariffQueryService` ([structured_tariff_query.py](../../app/services/structured_tariff_query.py)), `TariffHistoryService` ([tariff_queries.py](../../app/services/tariff_queries.py)), `StructuralNormalizationService` ([normalization.py](../../app/services/normalization.py)), `PdfLinkSelectionService` ([pdf_link_selection.py](../../app/services/pdf_link_selection.py)), `ReviewDisplayService` ([review_evidence.py](../../app/services/review_evidence.py)), `stop_run` / `recover_stale_runs` ([run_lease.py](../../app/services/run_lease.py)), `explain_failure_code` ([failure_mapping.py](../../app/services/failure_mapping.py)), `PostgresRunRepository` / `PostgresOfferingPublicationRepository` ([repositories/monitoring.py](../../app/repositories/monitoring.py)), `PostgresReviewRepository` ([repositories/reviews.py](../../app/repositories/reviews.py)), `configure_telemetry` ([telemetry.py](../../app/services/telemetry.py)).

### 6.2 API routes

| Method + path | Handler |
|---|---|
| `GET /api/v1/healthz` | [health](../../app/api/routes.py#L65) |
| `POST /api/v1/runs` | [create_run](../../app/api/routes.py#L104) |
| `GET /api/v1/runs/{run_id}` | [get_run](../../app/api/routes.py#L156) |
| `POST /api/v1/questions` | [answer_question](../../app/api/routes.py#L172) |
| `POST /api/v1/tariffs/query` | [query_structured_tariffs](../../app/api/routes.py#L188) |
| `GET /api/v1/tariffs/current` | [get_current_tariffs](../../app/api/routes.py#L230) |
| `GET /api/v1/tariffs/history` | [get_tariff_history](../../app/api/routes.py#L252) |
| `GET /api/v1/reviews` | [list_reviews](../../app/api/routes.py#L283) |
| `POST /api/v1/reviews/abort-pending` | [abort_pending_reviews](../../app/api/routes.py#L311) |
| `GET /api/v1/reviews/{review_id}` | [get_review](../../app/api/routes.py#L334) |

### 6.3 Test map

These test files were confirmed to exist. Tests generally follow `tests/unit/test_<module>.py`.

| Module you changed | Run this test file |
|---|---|
| [snapshot_lifecycle.py](../../app/services/snapshot_lifecycle.py) (acceptance, rate guard, change detection) | [tests/unit/test_snapshot_lifecycle.py](../../tests/unit/test_snapshot_lifecycle.py) |
| [semantic_extraction.py](../../app/services/semantic_extraction.py) (validation, normalization, repair) | [tests/unit/test_semantic_extraction.py](../../tests/unit/test_semantic_extraction.py) |
| [monitoring_pipeline.py](../../app/services/monitoring_pipeline.py) | [tests/unit/test_monitoring_pipeline.py](../../tests/unit/test_monitoring_pipeline.py) |
| [monitoring_node.py](../../app/services/monitoring_node.py) | [tests/unit/test_monitoring_node.py](../../tests/unit/test_monitoring_node.py) (fixtures: `tests/fixtures/monitoring_node.py`) |
| [review_resolution.py](../../app/services/review_resolution.py) | [tests/unit/test_review_resolution.py](../../tests/unit/test_review_resolution.py) |
| [review_input.py](../../app/services/review_input.py) | [tests/unit/test_review_input.py](../../tests/unit/test_review_input.py) |
| [intent_resolution.py](../../app/services/intent_resolution.py) | [tests/unit/test_intent_resolution.py](../../tests/unit/test_intent_resolution.py) |
| [interpretation_validation.py](../../app/services/interpretation_validation.py) | [tests/unit/test_interpretation_validation.py](../../tests/unit/test_interpretation_validation.py) |
| [config/](../../app/config/) | [tests/unit/test_config.py](../../tests/unit/test_config.py) |
| [seed_catalog.yaml](../../app/config/seed_catalog.yaml) / [catalog.py](../../app/domain/catalog.py) | [tests/unit/test_seed_catalog.py](../../tests/unit/test_seed_catalog.py) |
| [acquisition.py](../../app/services/acquisition.py) | [tests/unit/test_acquisition.py](../../tests/unit/test_acquisition.py) |
| [normalization.py](../../app/services/normalization.py) | [tests/unit/test_normalization.py](../../tests/unit/test_normalization.py) |
| [pdf_extraction.py](../../app/services/pdf_extraction.py) OCR path / [ocr_transcriber.py](../../app/services/ocr_transcriber.py) | [tests/unit/test_ocr_fallback.py](../../tests/unit/test_ocr_fallback.py) |
| [source_discovery.py](../../app/services/source_discovery.py) | [tests/unit/test_source_discovery.py](../../tests/unit/test_source_discovery.py) |
| [structured_projection.py](../../app/services/structured_projection.py) | [tests/unit/test_structured_projection.py](../../tests/unit/test_structured_projection.py) |
| [structured_tariff_query.py](../../app/services/structured_tariff_query.py) | [tests/unit/test_structured_tariff_query.py](../../tests/unit/test_structured_tariff_query.py) |
| [tariff_queries.py](../../app/services/tariff_queries.py) | [tests/unit/test_tariff_queries.py](../../tests/unit/test_tariff_queries.py) |
| [failure_mapping.py](../../app/services/failure_mapping.py) | [tests/unit/test_failure_mapping.py](../../tests/unit/test_failure_mapping.py) |
| [plugins.py](../../app/plugins.py) | [tests/unit/test_plugins.py](../../tests/unit/test_plugins.py) |
| [cli.py](../../app/cli.py) | [tests/unit/test_cli.py](../../tests/unit/test_cli.py) |
| [pdf_downloader.py](../../app/services/pdf_downloader.py), [urls.py](../../app/security/urls.py), [worker.py](../../app/worker.py), [tools/](../../app/tools/) | Test file not located yet. Search with `grep -rl "validate_source_url\|PdfDownloader\|MonitoringWorker\|resolve_request" tests/` |

Test data: `tests/fixtures/interpretation_cases.py`, `tests/fixtures/recorded_interpretations.json`, and `tests/fixtures/target_questions.py` (the 25 target questions).
Evaluation: [tests/eval/RESULTS.md](../../tests/eval/RESULTS.md) (scores and how to reproduce), `tests/eval/datasets/README.md`, `tests/eval/structured_metrics.py`.

**Commands**

```bash
uv run pytest tests/unit                                  # all unit tests
uv run pytest tests/unit tests/integration                # pre-deploy suite (AGENTS.md)
uv run pytest tests/unit/test_snapshot_lifecycle.py       # one file
uv run pytest tests/unit/test_snapshot_lifecycle.py -k rate   # tests matching a name
uv run pytest -m "not live and not postgres and not browser"  # skip tests needing services
uv run python scripts/structured_eval_metrics.py          # model-free structured eval (25 questions)
agents-cli eval run                                       # agent eval
```

Markers (defined in [pyproject.toml:118](../../pyproject.toml#L118)): `live` needs real services or model credentials; `postgres` needs `TEST_DATABASE_URL` pointing at an isolated test database; `browser` starts a local headless Chromium (fixture pages only).
