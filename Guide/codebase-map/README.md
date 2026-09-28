# Codebase map (start here)

Open this in the Markdown preview (`Ctrl+Shift+V`). Every link opens the file at the line.

The app has **one ADK agent** (chat) and **one deterministic pipeline** (monitoring runs).
Gemini does only four jobs: it interprets the request, picks and classifies sources,
transcribes PDFs, and extracts fields with cited evidence. Everything else is plain Python:
downloads, validation, change detection, review routing, storage and scheduling.

## Pages

| Page | Open it for |
|---|---|
| [1 Agent and chat](1-agent-and-chat.md) | ADK agent, its 7 tools, the prompt, intent resolution, grants, the CLI, the monitoring node |
| [2 Monitoring pipeline](2-monitoring-pipeline.md) | acquisition → PDF → OCR → normalization → source discovery → extraction → validation |
| [3 Review and change detection](3-review-and-change-detection.md) | snapshots, change detection, HITL review reasons, reviewer input, publication |
| [4 Answering questions](4-answering-questions.md) | the structured read model, the RAG/retrieval units, embeddings, current/history reads |
| [5 Config, security, ops](5-config-security-ops.md) | settings/env vars, URL allowlist and download limits, API, worker/scheduler, DB, logging, tracing |
| [6 Tests, evals, demos](6-tests-evals-demos.md) | which test covers what, the eval datasets, demo scripts |
| [Recipes](recipes.md) | step-by-step for the most likely "change X" tasks |
| [Debug and run →](../debug/README.md) | run your edit without a rebuild, logs/SQL/audit files, symptom table, traces, practice drills |

## The flow on one screen

```text
chat message ──► resolve_request (Gemini interprets, code validates) ──► tool
                                                     │
          ┌──────────── answer_tariff_query ◄────────┤  (question: read accepted facts)
          │                                          │
          │            run_tariff_monitoring ◄───────┘  (monitoring: spend grant needed)
          │                     │
          │              monitoring node ──► TariffPipeline.execute (per offering: IndexingPipeline.refresh)
          │                                   1 acquisition        (HTML + browser + linked PDFs, allowlisted)
          │                                   2 pdf_selection      (Gemini: which PDFs belong to the offering)
          │                                   3 normalization      (tables, blocks; Gemini PDF transcription; OCR fallback)
          │                                   4 source_discovery   (rules + cache + Gemini classifier)
          │                                   5 semantic_extraction(Gemini, evidence-bound; Python validates)
          │                                   6 previous_snapshot → build snapshot → review signals
          │                                   7 projection → change set → publication (one DB transaction)
          │                     │
          │              review pending? ──► RequestInput pause ──► CLI review panel ──► resume
          └──────────────► answer from typed facts ◄──────────────┘
Worker (daily 06:00 Asia/Yerevan) and POST /api/v1/runs submit the same RunCommand → same TariffPipeline.
```

| Stage | Entry point |
|---|---|
| Stage runner (all stages, in order) | [IndexingPipeline.refresh](../../app/services/monitoring_pipeline.py#L226) |
| Family run, per-offering isolation | [TariffPipeline.execute](../../app/services/monitoring_pipeline.py#L584) |
| 1 Acquisition | [AcquisitionService.acquire](../../app/services/acquisition.py#L109) |
| 2 PDF link selection | [PdfLinkSelectionService.select](../../app/services/pdf_link_selection.py#L184) |
| 3 Normalization | [StructuralNormalizationService.normalize](../../app/services/normalization.py#L126) |
| 3a PDF transcription + OCR | [GeminiPdfExtractionService.extract](../../app/services/pdf_extraction.py#L456) |
| 4 Source discovery | [SourceDiscoveryService.discover](../../app/services/source_discovery.py#L313) |
| 5 Semantic extraction | [SemanticExtractionService.extract](../../app/services/semantic_extraction.py#L621) |
| 6 Snapshot + review signals | [build_snapshot_attempt](../../app/services/snapshot_lifecycle.py#L107) |
| 7 Change detection | [compare_accepted_snapshots](../../app/services/snapshot_lifecycle.py#L674) |
| 7 Publication (one transaction) | [PostgresOfferingPublicationRepository.publish](../../app/repositories/monitoring.py#L1388) |
| Everything is wired together in | [build_application_container](../../app/runtime.py#L123) |

## Quick lookup: "change …" → go here

| They ask about… | Go to |
|---|---|
| The agent's prompt / behaviour | [INSTRUCTION](../../app/agent.py#L28) |
| Which tools the agent has | [TOOLS](../../app/agent.py#L55), code in [app/tools/](../../app/tools/) |
| "Tool X must be called first" policy | [ToolPolicyPlugin](../../app/plugins.py#L34) |
| How a message is understood (intent, product) | [INTERPRETER_INSTRUCTION](../../app/services/intent_resolution.py#L98), [InterpretationValidator.validate](../../app/services/interpretation_validation.py#L143) |
| Products / offerings / synonyms / seed URLs | [seed_catalog.yaml](../../app/config/seed_catalog.yaml) |
| Allowed domains | [HttpSettings.allowed_source_hosts](../../app/config/models.py#L113), [validate_source_url](../../app/security/urls.py#L9) |
| Download size / MIME / timeout / retries | [HttpSettings](../../app/config/models.py#L112), [PdfDownloader](../../app/services/pdf_downloader.py#L103) |
| Which extracted fields exist | [ExtractionField](../../app/domain/semantic_extraction.py#L444), per category [CATEGORY_FIELDS](../../app/services/extraction_planner.py#L115) |
| The extraction prompt | [SEMANTIC_EXTRACTION_INSTRUCTION](../../app/services/semantic_extraction.py#L92) |
| Validation of extracted values | [_validate_individual_fields](../../app/services/semantic_extraction.py#L2252), [_validate_field_result](../../app/services/semantic_extraction.py#L2379) |
| Required fields (missing → review) | [_REQUIRED_TARIFF_FIELDS](../../app/services/snapshot_lifecycle.py#L46) |
| Large rate change threshold (3 pp) | [HitlSettings](../../app/config/models.py#L410), [detect_large_rate_changes](../../app/services/snapshot_lifecycle.py#L497) |
| When a human review is triggered | [detect_review_signals](../../app/services/snapshot_lifecycle.py#L237), reasons in [ReviewReason](../../app/domain/review.py#L17) |
| What the reviewer sees / types | [_show_review](../../app/cli.py#L666), [_ask_review_decision](../../app/cli.py#L793), [review_input.py](../../app/services/review_input.py#L488) |
| What counts as a change | [compare_accepted_snapshots](../../app/services/snapshot_lifecycle.py#L674), [_canonicalize](../../app/services/snapshot_lifecycle.py#L724) |
| "10 000 000" vs "10,000,000" normalization | [normalize_money_text](../../app/domain/normalization.py#L42), [scalar_normalizer.py](../../app/services/scalar_normalizer.py#L117) |
| OCR fallback | [GeminiPdfExtractionService._apply_ocr](../../app/services/pdf_extraction.py#L355), [TesseractOcrTranscriber](../../app/services/ocr_transcriber.py#L39), [OcrSettings](../../app/config/models.py#L248) |
| Error → failure code / message | [source_failure_code](../../app/services/failure_mapping.py#L49), [_FAILURE_EXPLANATIONS](../../app/services/failure_mapping.py#L152) |
| How answers are built | [TariffAnswerRouter](../../app/services/answer_read_model.py#L118), [StructuredTariffQueryService.answer](../../app/services/structured_tariff_query.py#L252) |
| RAG chunking / retrieval | [KnowledgeProjectionService](../../app/services/knowledge_projection.py#L64), [lexical_search_terms](../../app/repositories/structured_tariff_query.py#L180), [RANK_FUSION_VERSION](../../app/services/structured_tariff_query.py#L47) |
| Which Gemini model each stage uses | [ModelSettings](../../app/config/models.py#L61), [runtime.py model wiring](../../app/runtime.py#L169) |
| Schedule (06:00 daily) | [SchedulerSettings](../../app/config/models.py#L416), [schedule_daily_monitoring](../../app/worker.py#L51) |
| HTTP routes | [routes.py](../../app/api/routes.py#L104) |
| DB schema | [migrations/](../../migrations/) |
| Logs, traces, metrics, cost | [5 Config, security, ops](5-config-security-ops.md#observability) |

## Run, rebuild, test

| Task | Command |
|---|---|
| Start the stack (api, worker, db) | `docker compose up --build -d` |
| Chat with the agent | `./tariff-chat` (`--session name`, `--new`) — runs [cli_entry.py](../../app/cli_entry.py) inside the `api` container ([launcher](../../tariff-chat)) |
| **After editing `app/`** | `docker compose up --build -d api worker`. The code is copied into the image at build time and not mounted, so without a rebuild the old code keeps running. |
| Unit tests | `uv run pytest tests/unit` (or one file: `uv run pytest tests/unit/test_snapshot_lifecycle.py -q`) |
| Integration tests | `docker compose --profile test up -d db-test`, apply migrations to it (loop in [demonstrations.md → Setup](../../docs/demonstrations.md#setup)), then `TEST_DATABASE_URL=postgresql+asyncpg://tariff:tariff@localhost:5433/tariff_monitor_test uv run pytest tests/integration`. Without the variable they are skipped. |
| Lint | `agents-cli lint` (or `uv run ruff check app tests`) |
| Watch a run | `docker compose logs -f --tail=200 worker api`; files in [logs/](../../logs/) |
| Per-run audit reports | `artifacts/pipeline-audit/run_<id>/<offering>/` (see [2 Monitoring pipeline](2-monitoring-pipeline.md#audit-trail)) |
| Apply a new migration to the running DB | `docker compose exec -T db psql -U tariff -d tariff_monitor < migrations/0NN_x.sql` (the files in `migrations/` run automatically only when the DB volume is new) |

## Layout

```text
app/agent.py            the ADK App + root agent (prompt, tools)
app/plugins.py          tool policy: resolve_request first; errors become typed envelopes
app/tools/              the 7 ADK tools (thin adapters, no scope arguments)
app/cli.py              ./tariff-chat: chat loop, progress rendering, review panel
app/runtime.py          composition root: builds every service
app/fast_api_app.py     FastAPI app (+ ADK web / A2A); app/api/routes.py = project routes
app/worker.py           queue worker + daily scheduler (no ADK)
app/config/             settings (env → typed groups), seed catalog, normalization baseline
app/domain/             Pydantic models and pure rules (no I/O)
app/services/           pipeline stages + application services
app/repositories/       PostgreSQL persistence (and file/in-memory variants for scripts)
app/security/urls.py    HTTPS + host allowlist check
migrations/             SQL schema 001–027
scripts/                demos, reports, backfills, eval helpers
tests/unit | integration | eval | fixtures
docs/                   deep-dive docs per component (architecture.md is the master)
Presentation-demonstrations/   the live interview demos
```

Background: [assignment](../../Project%20Documents/System%20Description.md) ·
[architecture.md](../../docs/architecture.md) · [agent-and-tool-architecture.md](../../docs/agent-and-tool-architecture.md) ·
[docs index](../../docs/README.md)
