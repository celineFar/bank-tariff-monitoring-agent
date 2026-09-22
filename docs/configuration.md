# Configuration

`app.config.Settings` is the immutable, nested configuration contract shared by
FastAPI, the ADK agent, and the scheduled worker. `EnvironmentSettings` reads the
existing flat process environment variables and, for local development, `.env`
once; `load_settings` then validates and groups them. Copy `.env.example` to
`.env` and never commit a real API key.

The service-facing groups are `application`, `models`, `database`, `http`,
`acquisition`, `pdf_extraction`, `rag`, `intent_resolution`, `tariff_queries`,
`source_discovery`, `semantic_extraction`, `hitl`,
`scheduler`, and `observability`. A component should receive only the group it needs—for example, a
downloader receives `settings.http` and the PDF extraction service receives
`settings.pdf_extraction`.

## Setting groups

- **Application:** `APP_NAME`, `ENVIRONMENT` (`development`, `test`, or
  `production`). Production requires `GEMINI_API_KEY`.
  `PIPELINE_AUDIT_ENABLED` (default `true`) and `PIPELINE_AUDIT_DIR` (default
  `artifacts/pipeline-audit`) control the stage-numbered Markdown audit trail
  written by every pipeline run; see `docs/architecture.md`.
- **Models:** `GEMINI_API_KEY`, `MODEL_NAME`, `EMBEDDING_MODEL_NAME`.
- **Persistence:** `DATABASE_URL`, `SESSION_SERVICE_URI`, `ARTIFACT_TEMP_DIR`.
  Application storage must use PostgreSQL; the ADK session URI may also use
  `shared://`.
- **Network policy:** `ALLOWED_SOURCE_HOSTS`,
  `ALLOWED_DOWNLOAD_MIME_TYPES`, `HTTP_USER_AGENT`,
  `DOWNLOAD_TIMEOUT_SECONDS`, `HTTP_MAX_ATTEMPTS`,
  `HTTP_BACKOFF_BASE_SECONDS`, `HTTP_RETRY_JITTER_RATIO`,
  `HTTP_MAX_RETRY_DELAY_SECONDS`, `MAX_REDIRECTS`, and `MAX_DOWNLOAD_BYTES`.
- **Acquisition:** `ACQUISITION_BROWSER_ENABLED`,
  `ACQUISITION_MIN_STATIC_TEXT_CHARS`,
  `ACQUISITION_BROWSER_NAVIGATION_TIMEOUT_SECONDS`,
  `ACQUISITION_BROWSER_SETTLE_MILLISECONDS`, `ACQUISITION_MAX_INTERACTIONS`,
  `ACQUISITION_MAX_NETWORK_PAYLOADS`,
  `ACQUISITION_MAX_NETWORK_PAYLOAD_BYTES`, and
  `ACQUISITION_MAX_LINKED_DOCUMENTS`.
- **PDF extraction:** `PDF_EXTRACTION_SCHEMA_VERSION`,
  `PDF_EXTRACTION_PROMPT_VERSION`, `PDF_EXTRACTION_MODEL_NAME`, and the
  comma-separated `PDF_EXTRACTION_FALLBACK_MODEL_NAMES`. Retry behavior uses
  `PDF_EXTRACTION_MAX_ATTEMPTS`, `PDF_EXTRACTION_BACKOFF_BASE_SECONDS`,
  `PDF_EXTRACTION_MAX_BACKOFF_SECONDS`, and
  `PDF_EXTRACTION_RETRY_JITTER_RATIO`. `PDF_EXTRACTION_PROBE_TEXT_THRESHOLD`
  affects only the deterministic input-mode diagnostic.
  `PDF_EXTRACTION_MAX_PRICE_PER_MILLION_TOKENS_USD` rejects any configured model
  whose input or output rate exceeds the ceiling before a live call.
- **RAG:** `CHUNK_SIZE_CHARS`, `CHUNK_OVERLAP_CHARS`, `RETRIEVAL_TOP_K`, and
  `RETRIEVAL_MIN_SCORE`.
- **Intent resolution:** `INTENT_FUZZY_MIN_SCORE`, `INTENT_FUZZY_MIN_GAP`,
  `INTENT_MAX_CANDIDATES`, and `INTENT_CLASSIFIER_MAX_ATTEMPTS`. These bound the
  deterministic fuzzy acceptance rule and the candidate/model fallback surface; they do
  not change the configured Gemini model.
- **Tariff queries:** `TARIFF_FRESHNESS_DAYS`, `TARIFF_RECENT_CHANGE_DAYS`,
  `TARIFF_DEFAULT_HISTORY_DAYS`, and `TARIFF_MAX_HISTORY_RESULTS` bound accepted-data
  reads. `TARIFF_ANSWER_READ_MODEL` is the reversible cutover switch: `structured`
  (default) answers from accepted typed facts, `legacy` restores the old RAG
  answer path without a code change. `TARIFF_RUN_WAIT_SECONDS` (at most 120) and `TARIFF_RUN_POLL_SECONDS` bound
  chat-side persisted run polling; HTTP submission remains asynchronous.
- **Retrieval trace:** `RETRIEVAL_TRACE_LEVEL` controls the `tariff.retrieval`
  logger — `off`, `summary` (default, one closing line per answer), `steps`
  (one line per stage with identifiers, counts, and scores), or `verbose`
  (also the derived search terms and the rendered unit text). `verbose` prints
  text projected from bank source documents, so it is for local debugging
  only. `RETRIEVAL_LOG_FILE` adds a dedicated rotating file for that logger,
  separate from `LOG_FILE`, reusing `LOG_MAX_BYTES` and `LOG_BACKUP_COUNT`.
- **Source discovery:** `SOURCE_DISCOVERY_POLICY_VERSION`,
  `SOURCE_DISCOVERY_PROMPT_VERSION`, `SOURCE_DISCOVERY_MAX_ITEMS_PER_BATCH`,
  `SOURCE_DISCOVERY_MAX_CHARS_PER_ITEM`, and
  `SOURCE_DISCOVERY_MAX_CHARS_PER_BATCH`. Preflight cost assumptions use
  `SOURCE_DISCOVERY_ESTIMATED_CHARS_PER_INPUT_TOKEN` and
  `SOURCE_DISCOVERY_ESTIMATED_OUTPUT_TOKENS_PER_ITEM`. Classifier resilience uses
  `SOURCE_DISCOVERY_CLASSIFIER_MAX_ATTEMPTS`,
  `SOURCE_DISCOVERY_CLASSIFIER_BACKOFF_BASE_SECONDS`,
  `SOURCE_DISCOVERY_CLASSIFIER_MAX_BACKOFF_SECONDS`, and
  `SOURCE_DISCOVERY_CLASSIFIER_RETRY_JITTER_RATIO`. Whole-run fallback order is
  configured by the comma-separated `SOURCE_DISCOVERY_FALLBACK_MODEL_NAMES`.
  `SOURCE_DISCOVERY_MAX_PRICE_PER_MILLION_TOKENS_USD` is a hard ceiling applied
  independently to both input and output rates before any live model call.
  Model-specific paid-tier
  rates and effective periods live in `app/services/model_pricing.py`. Policy,
  prompt, model, product, and
  content fingerprints jointly define exact cache reuse. Changing either version
  deliberately invalidates the corresponding cached assessments.
- **Semantic extraction:** `SEMANTIC_EXTRACTION_SCHEMA_VERSION`,
  `SEMANTIC_EXTRACTION_PROMPT_VERSION`,
  `SEMANTIC_EXTRACTION_MAX_EVIDENCE_CHARS_PER_ITEM`,
  `SEMANTIC_EXTRACTION_MAX_CHARS_PER_BATCH`, and
  `SEMANTIC_EXTRACTION_MAX_ITEMS_PER_BATCH`. Schema, prompt, model, product, and
  selected-evidence fingerprints jointly define exact extraction-batch cache reuse.
  The demonstration command uses the source-discovery retry, fallback-model, and
  price-ceiling settings for live calls.
- **HITL:** `HITL_DOCUMENT_RANK_GAP` and
  `HITL_LARGE_RATE_CHANGE_PERCENTAGE_POINTS`. The latter defaults to three percentage
  points. These settings create deterministic review reasons; they do not authorize or
  apply a decision.
- **Scheduling:** `SCHEDULE_TIMEZONE`, `SCHEDULE_HOUR`, and
  `SCHEDULE_MINUTE`.
- **Serving/telemetry:** `LOG_LEVEL`, `LOG_FILE`, `LOG_TIMEZONE`,
  `LOG_MAX_BYTES`, `LOG_BACKUP_COUNT`, `OTEL_TO_CLOUD`, and `ALLOW_ORIGINS`.
  Compose sets a separate `LOG_FILE` for API and worker; `./tariff-chat` writes
  its own `logs/cli.log` through the shared log volume. The other values can be set in
  `.env`. File timestamps use the configured IANA timezone with an explicit UTC offset.
  The default is `Asia/Yerevan`, independently of the EC2 host timezone. Each service
  keeps ten 10 MiB backup files by default under the host `logs/` directory.

Comma-separated values are used for hosts, MIME types, fallback models, and CORS
origins. Allowlisted sources must be exact DNS hostnames; schemes, paths,
wildcards, credentials, ports, and IP literals are rejected. Redirect targets
must later be checked against the same normalized tuple.

`DATABASE_URL`, `SESSION_SERVICE_URI`, and `GEMINI_API_KEY` use Pydantic secret
types so their values are masked in object representations. Services should
receive the narrow nested group they need rather than reading environment
variables directly.

## Stored database timestamps

Migration `009_yerevan_wall_times.sql` adds stored `<timestamp>_yerevan` columns to
project-owned tables. These hold the `Asia/Yerevan` wall-clock value, including for
existing rows. The original `timestamptz` columns remain the authoritative,
timezone-aware instants for ordering and comparisons. Generated columns update with
each insert or timestamp change; application code does not set them separately.

For example, inspect both representations in PostgreSQL:

```sql
SELECT id, queued_at, queued_at_yerevan
FROM monitoring_runs
ORDER BY queued_at DESC
LIMIT 20;
```

The `_yerevan` suffix identifies the local timezone because PostgreSQL's `timestamp
without time zone` type does not carry an offset. To inspect another timezone, use the
original instant, for example `queued_at AT TIME ZONE 'Europe/London'`. `LOG_TIMEZONE`
and `SCHEDULE_TIMEZONE` configure logs and scheduling independently; they do not
change stored timestamp instants or the fixed Yerevan companion columns. ADK-owned
session/event timestamps are managed by the SDK and have no companion columns.

On an existing Compose database, apply the new migration explicitly; SQL files in
`docker-entrypoint-initdb.d` only run when PostgreSQL initializes a new volume:

```bash
docker compose exec -T db psql -U tariff -d tariff_monitor -v ON_ERROR_STOP=1 \
  -f /docker-entrypoint-initdb.d/009_yerevan_wall_times.sql
```

## AWS deployment

Inject `GEMINI_API_KEY` and database credentials from AWS Secrets Manager into
the container environment. Do not store them in the image, Compose file, source
repository, application logs, or task definitions containing plaintext values.


## Secret-free local example

Use placeholders locally and inject real values through the environment; do not commit
the resulting `.env` file.

```dotenv
ENVIRONMENT=development
DATABASE_URL=postgresql+asyncpg://tariff:replace-me@localhost:5432/tariff_monitor
SESSION_SERVICE_URI=postgresql+asyncpg://tariff:replace-me@localhost:5432/tariff_monitor
GEMINI_API_KEY=replace-me
ALLOWED_SOURCE_HOSTS=ameriabank.am,www.ameriabank.am
SCHEDULE_TIMEZONE=Asia/Yerevan
SCHEDULE_HOUR=6
SCHEDULE_MINUTE=0
```

The checked-in seed catalog is loaded from `app/config/seed_catalog.yaml`; it is not an
environment variable and accepts only HTTPS URLs on the configured source hosts.

## ADK session schema startup and migration

`SESSION_SERVICE_URI` must be a PostgreSQL SQLAlchemy async URI in every local/docker
runtime that can start or resume monitoring. `shared://session` remains an internal ADK
registry URI used by ADK Web, A2A, FastAPI, and the worker; it is not the value to put in
the deployment environment.

FastAPI and the worker run an eager startup gate that calls ADK 2.9.2's idempotent
`DatabaseSessionService.prepare_tables()` and requires JSON session schema version `1`.
The same check can be run independently before starting either process:

```powershell
uv run python scripts/check_adk_session_schema.py
```

For a new database, the check creates ADK-owned session/event tables and records schema
version `1`. Do not copy those SDK-owned tables into this project's numbered business
migrations. If an existing database contains ADK's legacy pickle schema, migrate to a
separate destination database with the SDK command, verify it, then change
`SESSION_SERVICE_URI` during a coordinated cutover; ADK 2.9.2 does not support in-place
migration:

```powershell
uv run adk migrate session --source_db_url <legacy-sync-uri> --dest_db_url <new-sync-uri>
```

Only use the migration command's unsafe-unpickling option for a fully trusted legacy
database. The application never logs either URI.

For local native review, run the normal application services and open ADK Web at
`/dev-ui/`, select `tariff_monitoring_workflow`, and use the persisted run-scoped user
and session IDs. `shared://session` ensures all local ADK surfaces resolve the injected
session service; PostgreSQL remains the cross-process store. See
`docs/native-hitl-review.md` for the decision flow.

Production still requires authenticated ingress, reviewer authorization, a notification
adapter, and an explicitly approved deployment. None is enabled merely by setting the
HITL thresholds or session URI.

## Durable CLI chat

For monitoring runs that take several minutes, start the custom CLI inside the
API container:

```bash
./tariff-chat
```

The CLI prints a session ID. After an interrupted terminal session, run
`./tariff-chat --session-id <id>` to recover any pending ADK long-running function
or review input. It reports each persisted offering stage and a heartbeat while
the worker runs. A Gemini 402 means the configured Google AI project has no
prepaid credits; add credits and retry in the same session.
The CLI uses the same PostgreSQL session service and run repository as the API
and worker. Run the CLI within the container because the Compose `.env` database
host is `db`.

## Review abort administration

Set `REVIEW_ADMIN_TOKEN` to a long random secret before using
`POST /api/v1/reviews/abort-pending`. Pass it as `X-Review-Admin-Token`. If unset,
the route returns `503`; an incorrect token returns `403`. The route resumes each
paused workflow with `reject_all`, preserving review and audit history. It does not
delete PostgreSQL rows. Example after configuring the secret:

```bash
curl -X POST http://localhost:8080/api/v1/reviews/abort-pending \
  -H "X-Review-Admin-Token: $REVIEW_ADMIN_TOKEN"
```
