<p align="center">
  <img src="docs/assets/tariff-monitor-logo.png" alt="Ameria Tariff Monitor logo" width="320">
</p>

# Ameria Tariff Monitor

An evidence-backed Google ADK prototype for monitoring Ameria Bank consumer-loan and mortgage tariffs.

Gemini is used for intent resolution, bounded cache-aware source classification, native PDF structure transcription, and evidence-grounded extraction. Security controls, ingestion, validation, persistence, comparison, scheduling, and Human-in-the-Loop (HITL) routing remain deterministic.

The system includes:

* deterministic source acquisition and structural normalization;
* cache-aware source discovery and secure PDF retrieval;
* bounded Gemini-based PDF and semantic extraction;
* dual source and summary knowledge projections;
* transactional PostgreSQL/pgvector persistence;
* hybrid retrieval;
* durable monitoring runs and snapshots;
* tariff change detection; and
* Human-in-the-Loop review workflows.

Standard tariff questions are answered from accepted, typed facts with per-value citations.


## Setup

Everything runs in Docker. You need only:

- Docker Engine with Compose v2 (`docker compose version`)
- A Gemini API key

No Python, `uv`, Playwright, or Tesseract installation on the host — the image
carries them.

### 1. Configure the environment

```bash
cp .env.example .env
```

Set `GEMINI_API_KEY` in `.env`. Every other value has a working default for local
use; the defaults already point `DATABASE_URL` and `SESSION_SERVICE_URI` at the
Compose `db` service.

### 2. Start the stack

```bash
docker compose up --build -d
```

This builds the image and starts three containers: `db` (PostgreSQL 17 with
pgvector), `api` (FastAPI and the ADK surface on `http://localhost:8080`), and
`worker` (the daily 06:00 `Asia/Yerevan` trigger). The SQL files in
[migrations/](migrations/) are applied automatically the first time the database
volume is created.

Wait for the database to report healthy before continuing:

```bash
docker compose ps
```

### 3. Prepare the ADK session schema

The conversation is durable, so ADK needs its session tables:

```bash
docker compose exec api uv run python scripts/check_adk_session_schema.py
```

It prints `ADK session schema is ready` and is safe to re-run.

## Talking to the agent

Start a conversation:

```bash
./tariff-chat
```

The script runs the ADK CLI inside the `api` container, so the agent shares the
same database, configuration, and monitoring runs as the rest of the stack.

From there you can ask tariff questions in plain language, trigger a monitoring
run, and answer human-review prompts when the agent pauses for one. A run you ask
for executes inside that turn: each stage is printed as it happens, any review is
asked right there, and the answer to your question follows in the same turn.
Candidates from scheduled or API runs wait for you too — the agent mentions them,
and "review them" walks you through each one.

Conversations are named and durable. `./tariff-chat` opens the conversation called
`default`; closing the terminal, even mid-review, loses nothing — reopening it
continues where you left off.

```bash
./tariff-chat --session pricing   # open or continue a named conversation
./tariff-chat --new               # start a new conversation (its name is printed)
```

Ctrl-C cancels a running turn, including a monitoring run in progress. Other flags:
`--user <name>` to separate reviewers' conversations, `--verbose` to also show tool
calls and run ids.

If `tariff-chat` reports that the container does not have this CLI version, the
image is older than your checkout:

```bash
docker compose up --build -d api
```

### Stopping

```bash
docker compose down        # stop containers, keep the database
docker compose down -v     # also discard the database and re-run migrations next start
```


## Demonstrations



### Data Extraction Pipeline

A step-by-step demonstration of the extraction pipeline is available in:

`docs/assets/demonstrations/extraction_pipeline`

The pipeline has four stages: **acquisition**, **normalization**, **source discovery**, and **semantic extraction**. Each numbered PDF visualizes the changes and decisions made at that stage.

1. [`1_acquired_content.pdf`](docs/assets/demonstrations/extraction_pipeline/1_acquired_content.pdf)  
   — **Acquisition.** The source page as retrieved, captured as Markdown with links, menus, and other rendered content intact.

2. [`2_acquired_content_normalized.pdf`](docs/assets/demonstrations/extraction_pipeline/2_acquired_content_normalized.pdf)  
   — **Normalization.** The acquired content after deterministic cleanup, with removals and additions shown as an annotated diff.

3. [`3_source_discovery.pdf`](docs/assets/demonstrations/extraction_pipeline/3_source_discovery.pdf)  
   — **Source discovery.** Each content block is classified and visually marked to show whether it is selected, uncertain, historical, future, or excluded.

4. [`4_semantic_extraction.pdf`](docs/assets/demonstrations/extraction_pipeline/4_semantic_extraction.pdf)  
   — **Semantic extraction.** Extracted field values and outcomes are shown alongside the exact source text cited as evidence.

### Agent Bot QA

Video demonstrations are available here:

[Google Drive — Agent Bot QA Demonstrations](https://drive.google.com/drive/folders/1n5gXFmCIvQ1T_ivSHAaV5l4NEwLNY44I?usp=sharing)

The folder currently includes a demonstration of how question answering with the bot works.

### Script-based Demonstrations

The corresponding demonstration scripts are available in:

`scripts/demonstrations`

They cover the following scenarios:

- **Question answering** — demonstrates the bot's standard question-answering workflow.
- **Tariff-change detection** — demonstrates how tariff changes are identified and surfaced.
- **Controlled failure scenarios** — demonstrates expected failure modes and how the system handles them.
- **Human-in-the-Loop (HITL)** — demonstrates a scenario in which human review or intervention is required.

Each run writes a markdown transcript. A captured set is committed in
[`docs/assets/demonstrations/run_001`](docs/assets/demonstrations/run_001) —
[document processing](docs/assets/demonstrations/run_001/document-processing.md),
[extraction](docs/assets/demonstrations/run_001/extraction.md),
[change detection](docs/assets/demonstrations/run_001/change-detection.md),
[failures](docs/assets/demonstrations/run_001/failures.md), and
[HITL](docs/assets/demonstrations/run_001/hitl.md) — so the output is readable
without running the scripts. See [demonstrations](docs/demonstrations.md) for setup.





## Documentation

[`docs/README.md`](docs/README.md) indexes everything. Start with:

- [agent and tool architecture](docs/agent-and-tool-architecture.md) — what the agent
  is, which tools it has, and the major design decisions;
- [architecture diagram](docs/architecture-diagram.md) — components, the pipeline,
  the human-review pause, and the read path;
- [architecture](docs/architecture.md) — the boundary-by-boundary reference;
- [configuration](docs/configuration.md) — every environment variable.

Per-stage designs live in [acquisition](docs/acquisition.md),
[normalization](docs/normalization.md), [source discovery](docs/source-discovery.md),
[semantic extraction](docs/semantic-extraction.md),
[knowledge store](docs/knowledge-store.md), [indexing projections](docs/indexing-projection.md),
[snapshot lifecycle](docs/snapshot-lifecycle.md), and [seed catalog](docs/seed-catalog.md).
Operating it is covered by [run lifecycle](docs/run-lifecycle.md),
[native ADK review](docs/native-hitl-review.md),
[review quarantine](docs/review-quarantine.md), [failure behavior](docs/failure-behavior.md),
[observability](docs/observability.md), and [demonstrations](docs/demonstrations.md).


## Local logs

Logging is the Python standard library `logging` module, configured once in
`app/services/logging_setup.py`: a console handler plus a `RotatingFileHandler`
(10 MB per file, 10 backups) and a formatter that stamps every record in
`Asia/Yerevan` rather than UTC. No logging framework is layered on top.

View live application logs with:

```bash
docker compose logs -f --tail=200 worker api
```

Persistent logs are also written to:

```text
logs/api.log
logs/worker.log
```

To inspect logs for a specific monitoring run:

```bash
rg '<run-id>' logs/
```

## Tracing and metrics

Tracing is **OpenTelemetry**. The SDK is set up in `app/services/telemetry.py`,
which exports over **OTLP/HTTP** when `OTEL_TRACES_ENDPOINT` is set and falls
back to the console exporter when it is not. Spans come from ADK's own
instrumentation (`invoke_workflow`, `invoke_agent`, `call_llm`, `execute_tool`),
the `google-genai` instrumentation library, and a span per offering and per
stage opened by the pipeline. Trace context is carried across the HTTP, worker,
and CLI process boundaries through PostgreSQL, so one run is one trace.

The trace backend is **Langfuse 4**, shipped as an opt-in Compose profile
(Langfuse plus its PostgreSQL, ClickHouse, Redis, and MinIO dependencies — six
containers next to the three-container application, which is why it is not in
the default stack).

Tracing is disabled by default. Enable it with:

```env
OTEL_ENABLED=true
```

To start the optional observability stack:

```bash
docker compose --profile observability up -d
```

The Langfuse UI is then at `http://localhost:3001`, and `OTEL_TRACES_ENDPOINT`
points at its OTLP receiver:

```env
OTEL_TRACES_ENDPOINT=http://langfuse:3000/api/public/otel/v1/traces
```

`OTEL_TRACE_CONTENT` controls whether prompts and model responses leave the
process at all; it defaults to `none`.

Metrics are **not** an OpenTelemetry metrics pipeline. They are SQL aggregates
computed on demand over the durable audit tables (`monitoring_runs`,
`offering_executions`, `tariff_facts`, `human_reviews`, `model_call_usage`, and
others), so they have no retention window. Generate a report with:

```bash
uv run python scripts/run_metrics_report.py --days 30
```

For tracing configuration, metrics definitions, and operational details, see [Observability](docs/observability.md).


## Main layout

```text
app/agent.py          ADK root agent
app/tools.py          constrained agent tool adapters
app/api/              user-trigger and HITL HTTP contracts
app/domain/           tariff/evidence schemas and pure rules
app/services/         application orchestration contracts
app/repositories/     persistence contracts
app/security/         network and content trust boundaries
app/worker.py         scheduled trigger
migrations/           PostgreSQL/pgvector schema
tests/unit/           deterministic tests
tests/eval/           agent/RAG evaluation scaffold
```

## Security notes

The prototype applies several safeguards around network access, retrieval, model usage, tracing, and administrative actions.

**Outbound access is allowlisted.**  
`app/security/urls.py` only accepts HTTPS URLs whose host exactly matches a configured allowlist entry, such as `ameriabank.am` or `www.ameriabank.am`. Subdomain wildcards are not allowed, and URLs containing credentials or IP-literal hosts are rejected.

**Redirects are validated explicitly.**  
Fetchers disable automatic redirects and validate every `Location` target before following it. Redirect chains are bounded by `max_redirects` (default: 5), loops are detected, and malformed redirects are treated as errors.

**Retrieval is bounded and validated.**  
Responses are streamed and stopped when they exceed `max_download_bytes` (default: 25 MB). Requests use fixed timeouts, an identifying user agent, and bounded jittered retries. HTML responses must use the expected content type and decode successfully.

**Browser rendering is restricted.**  
The Playwright renderer blocks non-`GET`/`HEAD` requests, images, media, fonts, downloads, and service workers. Every subresource URL is validated against the same outbound allowlist as the top-level page.

**Model access is constrained.**  
Gemini is exposed only through the typed tools in `app/tools.py`. It has no filesystem, shell, arbitrary network, or direct SQL access, and it cannot independently choose URLs to retrieve. Source discovery operates only on candidates already validated by the deterministic crawler.

Document content is treated as data rather than instructions, and accepted extracted values must include supporting source evidence.

**Trace content is disabled by default.**  
`OTEL_TRACE_CONTENT` defaults to `none`, preventing prompts and model responses from being exported unless explicitly enabled. Direct use of `OTEL_EXPORTER_OTLP_ENDPOINT` is rejected to avoid creating an additional unredacted exporter.

**Administrative operations are token-protected.**  
`POST /api/v1/reviews/abort-pending` requires an `X-Review-Admin-Token`, validated with `compare_digest`. If no token is configured, the operation is unavailable. Other `/api/v1` endpoints currently assume deployment within a trusted network.

**Production deployment.**  
Production environments should provide secrets through AWS Secrets Manager and place authenticated HTTPS ingress in front of the FastAPI service.

## AI-assisted development disclosure

OpenAI Codex and Google Agents CLI were used to refine the architecture, generate the
canonical ADK scaffold, and establish implementation and test boundaries. The project
owner remains responsible for reviewing, understanding, testing, and presenting all code.
