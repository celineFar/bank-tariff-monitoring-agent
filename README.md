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



## Runtime

- ADK agent and standard ADK/A2A FastAPI surface
- Project API under `/api/v1`
- Daily worker at 06:00 `Asia/Yerevan`
- PostgreSQL 17 with pgvector
- Docker Compose for a single AWS compute instance



## Demonstrations



### Data Extraction Pipeline

A step-by-step demonstration of the extraction pipeline is available in:

`artifacts/demonstrations/extraction_pipeline_demonstration`

The pipeline has four stages: **acquisition**, **normalization**, **source discovery**, and **semantic extraction**. Each numbered PDF visualizes the changes and decisions made at that stage.

1. [`1_acquired_content.pdf`](artifacts/demonstrations/extraction_pipeline_demonstration/1_acquired_content.pdf)  
   — **Acquisition.** The source page as retrieved, captured as Markdown with links, menus, and other rendered content intact.

2. [`2_acquired_content_normalized.pdf`](artifacts/demonstrations/extraction_pipeline_demonstration/2_acquired_content_normalized.pdf)  
   — **Normalization.** The acquired content after deterministic cleanup, with removals and additions shown as an annotated diff.

3. [`3_source_discovery.pdf`](artifacts/demonstrations/extraction_pipeline_demonstration/3_source_discovery.pdf)  
   — **Source discovery.** Each content block is classified and visually marked to show whether it is selected, uncertain, historical, future, or excluded.

4. [`4_semantic_extraction.pdf`](artifacts/demonstrations/extraction_pipeline_demonstration/4_semantic_extraction.pdf)  
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
The generated ADK integration surface is described in
[.agents-cli-spec.md](.agents-cli-spec.md).

## Local setup

1. Copy `.env.example` to `.env` and set `GEMINI_API_KEY`.
2. Install dependencies: `agents-cli install`.
3. Install the local acquisition browser: `uv run playwright install chromium`.
   For the scanned-PDF OCR fallback, also install the optional extra and a
   tesseract engine: `uv sync --extra ocr`, plus `tesseract-ocr`,
   `tesseract-ocr-hye`, and `tesseract-ocr-eng` (Linux), or the Tesseract
   installer with `hye.traineddata` and `OCR_TESSERACT_CMD` set (Windows). The
   pipeline runs without it; scanned pages simply stay empty rather than being
   guessed.
4. Verify/create the ADK session schema: `uv run python scripts/check_adk_session_schema.py`.
5. Run deterministic tests: `uv run pytest tests/unit`.
6. Start the full stack: `docker compose up --build`.
7. Open API documentation at `http://localhost:8080/docs`.

For a durable terminal conversation, run `./tariff-chat` after the Compose
stack is up. It shows monitoring stages while the worker runs and prints a
session ID. Reconnect with `./tariff-chat --session-id <id>`.

The ADK playground can be started with `agents-cli playground` after dependencies are
installed. Behavioral evaluation uses `agents-cli eval run`; it requires configured
model credentials and an indexed local corpus.


## Local logs

`docker compose logs -f --tail=200 worker api` shows live console output. Compose also
writes rotating, persistent host files under `logs/api.log` and `logs/worker.log`;
numbered files such as `worker.log.1` hold older entries across container recreation.
Use `rg '<run-id>' logs/` to inspect a past run. Each file entry has an ISO 8601 timestamp
with an explicit offset, defaulting to `Asia/Yerevan`. `LOG_TIMEZONE`, `LOG_LEVEL`,
`LOG_MAX_BYTES`, and `LOG_BACKUP_COUNT` are configurable in `.env`. Logs stay on the EC2
host disk and must be copied or shipped separately to survive host replacement.

## Tracing and metrics

Tracing is off by default. Set `OTEL_ENABLED=true` to print spans to the console,
which is enough to see a whole run end to end. For a UI, start the opt-in profile
with `docker compose --profile observability up -d` and point `OTEL_TRACES_ENDPOINT`
at Langfuse on `http://localhost:3001`.

One monitoring run is one trace even though it crosses processes: the trigger, the
worker that claims it, and the process that resolves a human review all contribute
spans. Prompts and model responses are kept out of exported spans unless
`OTEL_TRACE_CONTENT=mapped` is set explicitly.

`uv run python scripts/run_metrics_report.py --days 30` reports run duration,
failure taxonomies, per-field extraction completeness, evidence coverage, and HITL
rate from the audit tables. See [observability](docs/observability.md).

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

Only exact configured HTTPS hosts are accepted. Redirect targets must be checked with
the same validator when retrieval is implemented. The model is not given filesystem,
shell, arbitrary network, or SQL access. Production deployments should inject secrets
through AWS Secrets Manager and put authenticated HTTPS ingress in front of FastAPI.

## AI-assisted development disclosure

OpenAI Codex and Google Agents CLI were used to refine the architecture, generate the
canonical ADK scaffold, and establish implementation and test boundaries. The project
owner remains responsible for reviewing, understanding, testing, and presenting all code.
