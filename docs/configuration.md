# Configuration

`app.config.Settings` is the immutable, nested configuration contract shared by
FastAPI, the ADK agent, and the scheduled worker. `EnvironmentSettings` reads the
existing flat process environment variables and, for local development, `.env`
once; `load_settings` then validates and groups them. Copy `.env.example` to
`.env` and never commit a real API key.

The service-facing groups are `application`, `models`, `database`, `http`,
`acquisition`, `pdf_extraction`, `rag`, `intent_resolution`, `source_discovery`, `semantic_extraction`, `hitl`,
`scheduler`, and `observability`. A component should receive only the group it needs—for example, a
downloader receives `settings.http` and the PDF extraction service receives
`settings.pdf_extraction`.

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
  `HITL_LARGE_RATE_CHANGE_PERCENTAGE_POINTS`.
- **Scheduling:** `SCHEDULE_TIMEZONE`, `SCHEDULE_HOUR`, and
  `SCHEDULE_MINUTE`.
- **Serving/telemetry:** `LOG_LEVEL`, `OTEL_TO_CLOUD`, and `ALLOW_ORIGINS`.

Comma-separated values are used for hosts, MIME types, fallback models, and CORS
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
