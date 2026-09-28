# 1 · Settings (no code)

[← Change recipes](README.md)

How settings flow: `.env` → flat [EnvironmentSettings](../../app/config/environment.py#L10) →
[load_settings](../../app/config/loader.py#L28) → typed groups in [models.py](../../app/config/models.py#L511)
(validated, frozen) → handed to services in [build_application_container](../../app/runtime.py#L123).

> **Your `.env` overrides the code default.** Changing a default in `models.py` does nothing for a
> variable that `.env` sets. `.env` already sets the HITL threshold, the schedule and the extraction
> schema/prompt versions. Edit `.env`, then run
> `docker compose up -d --force-recreate api worker` (with `COMPOSE_FILE` exported, see the [cheat sheet](README.md#cheat-sheet-one-screen)).

## Settings-only changes

| Change | `.env` line | Typed field (validation / bounds) | Used in |
|---|---|---|---|
| Large rate change → review (default 3 pp) | `HITL_LARGE_RATE_CHANGE_PERCENTAGE_POINTS=1` | [HitlSettings.large_rate_change_percentage_points](../../app/config/models.py#L412) (`> 0`) | [runtime.py:298](../../app/runtime.py#L298) → [IndexingPipeline](../../app/services/monitoring_pipeline.py#L419) → [detect_large_rate_changes](../../app/services/snapshot_lifecycle.py#L497) (`>=` threshold) |
| Allowed domains | `ALLOWED_SOURCE_HOSTS=ameriabank.am,www.ameriabank.am` | [HttpSettings.allowed_source_hosts](../../app/config/models.py#L113) (no IPs, no wildcards, no scheme) | [validate_source_url](../../app/security/urls.py#L9) (HTTPS, port 443, no credentials) |
| Max download size (25 MB) | `MAX_DOWNLOAD_BYTES=5242880` | [HttpSettings.max_download_bytes](../../app/config/models.py#L122) | [PdfDownloader](../../app/services/pdf_downloader.py#L103) (checks `Content-Length` and the streamed bytes) |
| Allowed MIME types | `ALLOWED_DOWNLOAD_MIME_TYPES=application/pdf,text/html` | [HttpSettings.allowed_download_mime_types](../../app/config/models.py#L114) | PDFs must also start with [`%PDF-`](../../app/services/pdf_downloader.py#L19) |
| HTTP timeout / retries / backoff | `DOWNLOAD_TIMEOUT_SECONDS`, `HTTP_MAX_ATTEMPTS` (1–5), `HTTP_BACKOFF_BASE_SECONDS` | [HttpSettings](../../app/config/models.py#L112) | which statuses retry: [5 Pipeline](5-pipeline-and-retrieval.md#change-which-http-errors-are-retried) |
| Schedule time / on-off | `SCHEDULE_HOUR=9`, `SCHEDULE_MINUTE=30`, `SCHEDULE_ENABLED=true` (currently **false** in `.env`) | [SchedulerSettings](../../app/config/models.py#L416) | [schedule_daily_monitoring](../../app/worker.py#L51), timezone at [worker.py:330](../../app/worker.py#L330) |
| Chat / extraction model | `MODEL_NAME` | [ModelSettings.generation_model](../../app/config/models.py#L63) | must be in [MODEL_PRICE_CATALOG](../../app/services/model_pricing.py#L18) or startup refuses it |
| Discovery / PDF model | `SOURCE_DISCOVERY_MODEL_NAME`, `PDF_EXTRACTION_MODEL_NAME` | [SourceDiscoverySettings](../../app/config/models.py#L319), [PdfExtractionSettings](../../app/config/models.py#L219) | each has a `*_MAX_PRICE_PER_MILLION_TOKENS_USD` cap |
| Re-fetch every run (no 1 h reuse) | `ACQUISITION_FRESHNESS_HOURS=0` | [AcquisitionSettings.freshness_hours](../../app/config/models.py#L211) | |
| "Stale" after N days | `TARIFF_FRESHNESS_DAYS=7` | [TariffQuerySettings](../../app/config/models.py#L308) | |
| OCR on/off, confidence floor | `OCR_ENABLED`, `OCR_MIN_CONFIDENCE=60` | [OcrSettings](../../app/config/models.py#L248) | [5 Pipeline: OCR](5-pipeline-and-retrieval.md#change-when-ocr-runs) |
| RAG chunk size | `CHUNK_SIZE_CHARS=1500` (500–2000) | [RagSettings.chunk_size_chars](../../app/config/models.py#L287) | the upper bound keeps a chunk inside the embedding model's 2,048 tokens |

**Test:** `uv run pytest tests/unit/test_config.py -q -p no:cacheprovider`. A bad value fails at startup
with a Pydantic error that names the field, not in the middle of a run.

**See it live:** `docker compose exec api uv run python -c "from app.config import get_settings; print(get_settings().hitl)"`

---

## Add a new setting
📖 Example: make the rate plausibility cap from [recipe A](2-validation-review-changes.md#a--add-a-deterministic-validation-rule) configurable.

1. **Flat env field**, next to its neighbours in [EnvironmentSettings](../../app/config/environment.py#L127):
   ```python
   hitl_max_annual_rate_pct: float = 60
   ```
2. **Typed field** in the right group, with bounds, in [HitlSettings](../../app/config/models.py#L410):
   ```python
   max_annual_rate_pct: float = Field(default=60, gt=0, le=100)
   ```
3. **Map it** in [load_settings → hitl=HitlSettings(...)](../../app/config/loader.py#L172):
   ```python
   max_annual_rate_pct=raw.hitl_max_annual_rate_pct,
   ```
4. **Document it** in [.env.example](../../.env.example) (`HITL_MAX_ANNUAL_RATE_PCT=60`).
5. **Pass it** where the service is built in [build_application_container](../../app/runtime.py#L123).
   Follow `settings.hitl.large_rate_change_percentage_points` at [runtime.py:298](../../app/runtime.py#L298),
   which travels as a constructor argument into [IndexingPipeline.\_\_init\_\_](../../app/services/monitoring_pipeline.py#L202).
   Do not call `get_settings()` inside domain/service code: services receive their settings.
6. **Test:** [test_config.py](../../tests/unit/test_config.py). `load_settings(_env_file=None, hitl_max_annual_rate_pct=5)` builds settings without reading `.env`.
