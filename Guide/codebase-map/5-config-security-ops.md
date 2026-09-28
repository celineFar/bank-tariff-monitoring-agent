# 5 · Config, security, API, worker, persistence, observability

[← Guide](README.md) · Deep dives: [configuration.md](../../docs/configuration.md), [observability.md](../../docs/observability.md), [model-cost-monitoring.md](../../docs/model-cost-monitoring.md), [run-lifecycle.md](../../docs/run-lifecycle.md)

## Configuration

Flow: `.env` → [EnvironmentSettings](../../app/config/environment.py#L10) (flat env names) → [load_settings](../../app/config/loader.py#L28) (maps them into groups) → [Settings](../../app/config/models.py#L511) → [get_settings](../../app/config/loader.py#L203).
To add a setting, change all three files. Sample values: [.env.example](../../.env.example).

| Group | Key env vars | Class |
|---|---|---|
| Models | `GEMINI_API_KEY`, `MODEL_NAME`, `EMBEDDING_MODEL_NAME` | [ModelSettings](../../app/config/models.py#L61) |
| HTTP / security | `ALLOWED_SOURCE_HOSTS`, `MAX_DOWNLOAD_BYTES`, `DOWNLOAD_TIMEOUT_SECONDS`, `HTTP_MAX_ATTEMPTS`, `MAX_REDIRECTS` | [HttpSettings](../../app/config/models.py#L112) |
| Acquisition | `ACQUISITION_BROWSER_ENABLED`, `ACQUISITION_FRESHNESS_HOURS`, `ACQUISITION_MIN_MAIN_CONTENT_CHARS` | [AcquisitionSettings](../../app/config/models.py#L191) |
| PDF transcription | `PDF_EXTRACTION_MODEL_NAME`, `PDF_EXTRACTION_PROMPT_VERSION`, `PDF_EXTRACTION_SKIP_HISTORICAL` | [PdfExtractionSettings](../../app/config/models.py#L219) |
| OCR | `OCR_ENABLED`, `OCR_LANGUAGES`, `OCR_MIN_CONFIDENCE`, `OCR_MAX_PAGES` | [OcrSettings](../../app/config/models.py#L248) |
| Source discovery | `SOURCE_DISCOVERY_MODEL_NAME`, `SOURCE_DISCOVERY_PROMPT_VERSION`, batch limits | [SourceDiscoverySettings](../../app/config/models.py#L319) |
| Extraction | `SEMANTIC_EXTRACTION_EVIDENCE_MODE`, `…_FALLBACK_MODEL_NAMES`, `…_MAX_REPAIRS_PER_RUN` | [SemanticExtractionSettings](../../app/config/models.py#L368) |
| HITL | `HITL_LARGE_RATE_CHANGE_PERCENTAGE_POINTS`, `REVIEW_ADMIN_TOKEN` | [HitlSettings](../../app/config/models.py#L410) |
| Scheduler / lease | `SCHEDULE_ENABLED`, `SCHEDULE_HOUR`, `RUN_LEASE_SECONDS` | [SchedulerSettings](../../app/config/models.py#L416) |
| Answers | `TARIFF_FRESHNESS_DAYS`, `RETRIEVAL_TRACE_LEVEL` | [TariffQuerySettings](../../app/config/models.py#L308) |
| RAG / embeddings | `CHUNK_SIZE_CHARS`, `EMBEDDING_SWEEP_*` | [RagSettings](../../app/config/models.py#L283) |
| Logging / tracing | `LOG_LEVEL`, `OTEL_ENABLED`, `OTEL_TRACE_CONTENT` | [ObservabilitySettings](../../app/config/models.py#L460) |

Which model each stage uses is decided in [runtime.py](../../app/runtime.py#L169). Discovery and link selection use `SOURCE_DISCOVERY_MODEL_NAME`. Extraction, the interpreter and chat use `MODEL_NAME`. PDF transcription uses `PDF_EXTRACTION_MODEL_NAME`. A price cap is checked at startup: [enforce_model_price_cap](../../app/services/model_pricing.py#L150), prices in [MODEL_PRICE_CATALOG](../../app/services/model_pricing.py#L18).

Other config files: [seed_catalog.yaml](../../app/config/seed_catalog.yaml) (loaded and validated by [load_seed_catalog](../../app/config/seed_catalog.py#L19)), [normalization_baseline.json](../../app/config/normalization_baseline.json).

## Security controls (assignment §5.12)

| Control | Where |
|---|---|
| HTTPS + host allowlist, no IPs, no credentials, port 443 only | [validate_source_url](../../app/security/urls.py#L9) |
| Allowlist also validated at config load | [HttpSettings.validate_source_hosts](../../app/config/models.py#L135) |
| Every redirect hop re-checked | [HtmlRetriever](../../app/services/html_retriever.py#L98), [PdfDownloader._request_with_retries](../../app/services/pdf_downloader.py#L170) |
| Browser: cross-domain / non-GET / forms blocked | [PlaywrightBrowserRenderer](../../app/services/browser_renderer.py#L443) |
| Size limit (header and streamed) | [PdfDownloader](../../app/services/pdf_downloader.py#L268), [HtmlRetriever](../../app/services/html_retriever.py#L194) |
| MIME + `%PDF-` signature | [PdfDownloader](../../app/services/pdf_downloader.py#L242), [signature](../../app/services/pdf_downloader.py#L288) |
| Bounded retries with backoff, only for transient errors | [PdfDownloader._request_with_retries](../../app/services/pdf_downloader.py#L170), [_parse_retry_after](../../app/services/pdf_downloader.py#L346) |
| Secrets as `SecretStr`; API key required in production | [ModelSettings.api_key](../../app/config/models.py#L62), [require_production_secret](../../app/config/models.py#L529) |
| Least-privilege tools (no URL/SQL/FS args; grants) | [ToolPolicyPlugin](../../app/plugins.py#L34), [app/tools/](../../app/tools/__init__.py) |
| Model content kept out of exported traces | [TariffSpanExporter](../../app/services/telemetry.py#L98) |
| Bounded error detail in logs/audit | [bounded_failure_detail](../../app/services/failure_mapping.py#L138) |
| Admin token for the one mutating review route | [abort_pending_reviews](../../app/api/routes.py#L311) |

## HTTP API ([routes.py](../../app/api/routes.py), prefix `/api/v1`)

| Route | Handler |
|---|---|
| `POST /runs` (202, `Idempotency-Key`) | [create_run](../../app/api/routes.py#L104) |
| `GET /runs/{id}` | [get_run](../../app/api/routes.py#L156) |
| `POST /questions` | [answer_question](../../app/api/routes.py#L172) |
| `POST /tariffs/query` | [query_structured_tariffs](../../app/api/routes.py#L188) |
| `GET /tariffs/current`, `/tariffs/history` | [get_current_tariffs](../../app/api/routes.py#L230), [get_tariff_history](../../app/api/routes.py#L252) |
| `GET /reviews`, `/reviews/{id}` | [list_reviews](../../app/api/routes.py#L283), [get_review](../../app/api/routes.py#L334) |
| `POST /reviews/abort-pending` | [abort_pending_reviews](../../app/api/routes.py#L311) |
| `GET /healthz` | [health](../../app/api/routes.py#L66) |

The app, startup and service injection (`app.state`) live in [lifespan](../../app/fast_api_app.py#L49). The router is mounted at [fast_api_app.py:113](../../app/fast_api_app.py#L113).

## Worker and scheduler ([worker.py](../../app/worker.py), no ADK)

| What | Where |
|---|---|
| Daily job (06:00 Asia/Yerevan, both families) | [schedule_daily_monitoring](../../app/worker.py#L51), [run_scheduled_monitoring](../../app/worker.py#L70), [PRODUCTS](../../app/worker.py#L36) |
| Claim and execute queued runs | [MonitoringWorker.process_next](../../app/worker.py#L133) |
| Fail runs with expired lease | [MonitoringWorker.recover_abandoned](../../app/worker.py#L121) |
| Embedding sweep loop | [MonitoringWorker.sweep_embeddings](../../app/worker.py#L224) |
| Main loop | [MonitoringWorker.run_forever](../../app/worker.py#L268), [main](../../app/worker.py#L313) |
| Submit path shared by chat, API and scheduler | [RunService.submit](../../app/services/run_service.py#L51) |

## Persistence

- Repository interfaces: [contracts.py](../../app/repositories/contracts.py#L42). Main implementations: [PostgresRunRepository](../../app/repositories/monitoring.py#L222), [PostgresSnapshotRepository](../../app/repositories/monitoring.py#L1138), [PostgresOfferingPublicationRepository](../../app/repositories/monitoring.py#L1384), [PostgresReviewRepository](../../app/repositories/reviews.py#L76).
- `File*`/`InMemory*` repositories exist only for scripts and tests.
- Schema: [migrations/](../../migrations/). Key files: [006 runs, snapshots, changes](../../migrations/006_monitoring_pipeline_foundation.sql), [007 reviews](../../migrations/007_review_quarantine.sql), [011 typed facts](../../migrations/011_structured_tariff_read_model.sql), [024 lease/cancel](../../migrations/024_run_lease_and_cancel_requests.sql).
- The migrations run through `docker-entrypoint-initdb.d` ([docker-compose.yml](../../docker-compose.yml#L42)), and only on a **fresh** volume.

## Observability

| What | Where |
|---|---|
| Console + rotating file logs (`logs/api.log`, `worker.log`, `cli.log`) | [configure_application_logging](../../app/services/logging_setup.py#L26) |
| OpenTelemetry setup, span redaction | [configure_telemetry](../../app/services/telemetry.py#L171), [TariffSpanExporter](../../app/services/telemetry.py#L98) |
| One span per pipeline stage | [refresh → stage](../../app/services/monitoring_pipeline.py#L259) |
| Trace context across API → worker | [inject_trace_context](../../app/services/telemetry.py#L243), [extract_trace_context](../../app/services/telemetry.py#L254) |
| Model calls, tokens, cost (per run) | [observe_model_call](../../app/services/model_call_usage.py#L288), [estimate_cost](../../app/services/model_call_usage.py#L50), [pipeline_usage_scope](../../app/services/model_call_usage.py#L353) |
| Run metrics (duration, failures, completeness, HITL rate) | [RunMetricsRepository.collect](../../app/services/run_metrics.py#L317) |
| Reports | `uv run python scripts/run_metrics_report.py --days 30` ([script](../../scripts/run_metrics_report.py)), `uv run python scripts/model_cost_report.py --days 7` ([script](../../scripts/model_cost_report.py)) |
| Audit events per run | [PostgresRunRepository.record_audit](../../app/repositories/monitoring.py#L862) |
