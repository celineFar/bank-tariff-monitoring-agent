# Configuration

`app.config.Settings` is the immutable, nested configuration contract shared by
FastAPI, the ADK agent, and the scheduled worker. `EnvironmentSettings` reads the
existing flat process environment variables and, for local development, `.env`
once; `load_settings` then validates and groups them. Copy `.env.example` to
`.env` and never commit a real API key.

The service-facing groups are `application`, `models`, `database`, `http`,
`acquisition`, `ocr`, `rag`, `source_discovery`, `hitl`, `scheduler`, and
`observability`. A component should receive only the group it needs—for example, a
downloader receives `settings.http` and an OCR service receives `settings.ocr`.

## Setting groups

- **Application:** `APP_NAME`, `ENVIRONMENT` (`development`, `test`, or
  `production`). Production requires `GEMINI_API_KEY`.
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
- **OCR:** `OCR_LANGUAGES`, `OCR_MIN_TEXT_CHARS_PER_PAGE`, `OCR_DPI`,
  `OCR_MAX_PAGES`, and `OCR_TIMEOUT_SECONDS`.
- **RAG:** `CHUNK_SIZE_CHARS`, `CHUNK_OVERLAP_CHARS`, `RETRIEVAL_TOP_K`, and
  `RETRIEVAL_MIN_SCORE`.
- **Source discovery:** `SOURCE_DISCOVERY_POLICY_VERSION`,
  `SOURCE_DISCOVERY_PROMPT_VERSION`, `SOURCE_DISCOVERY_MAX_ITEMS_PER_BATCH`,
  `SOURCE_DISCOVERY_MAX_CHARS_PER_ITEM`, and
  `SOURCE_DISCOVERY_MAX_CHARS_PER_BATCH`. Preflight cost assumptions use
  `SOURCE_DISCOVERY_ESTIMATED_CHARS_PER_INPUT_TOKEN` and
  `SOURCE_DISCOVERY_ESTIMATED_OUTPUT_TOKENS_PER_ITEM`. Model-specific paid-tier
  rates and effective periods live in `app/services/model_pricing.py`. Policy,
  prompt, model, product, and
  content fingerprints jointly define exact cache reuse. Changing either version
  deliberately invalidates the corresponding cached assessments.
- **HITL:** `HITL_DOCUMENT_RANK_GAP` and
  `HITL_LARGE_RATE_CHANGE_PERCENTAGE_POINTS`.
- **Scheduling:** `SCHEDULE_TIMEZONE`, `SCHEDULE_HOUR`, and
  `SCHEDULE_MINUTE`.
- **Serving/telemetry:** `LOG_LEVEL`, `OTEL_TO_CLOUD`, and `ALLOW_ORIGINS`.

Comma-separated values are used for hosts, MIME types, OCR languages, and CORS
origins. Allowlisted sources must be exact DNS hostnames; schemes, paths,
wildcards, credentials, ports, and IP literals are rejected. Redirect targets
must later be checked against the same normalized tuple.

`DATABASE_URL`, `SESSION_SERVICE_URI`, and `GEMINI_API_KEY` use Pydantic secret
types so their values are masked in object representations. Services should
receive the narrow nested group they need rather than reading environment
variables directly.

## AWS deployment

Inject `GEMINI_API_KEY` and database credentials from AWS Secrets Manager into
the container environment. Do not store them in the image, Compose file, source
repository, application logs, or task definitions containing plaintext values.
