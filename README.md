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
run, and answer human-review prompts when the agent pauses for one. While a run
is in progress the CLI prints each monitoring stage as it completes.

The session is durable. On start the CLI prints a session ID; reconnect to the
same conversation — including a run still waiting on your review — with:

```bash
./tariff-chat --session-id <id>
```

Optional flags: `--user-id <name>` to separate conversations, `--poll-seconds <n>`
to change how often the CLI checks a running monitoring job.

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


## Local logs

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

Tracing is disabled by default. Enable it with:

```env
OTEL_ENABLED=true
```

To start the optional observability stack:

```bash
docker compose --profile observability up -d
```

Generate a monitoring metrics report with:

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

Only exact configured HTTPS hosts are accepted. Redirect targets must be checked with
the same validator when retrieval is implemented. The model is not given filesystem,
shell, arbitrary network, or SQL access. Production deployments should inject secrets
through AWS Secrets Manager and put authenticated HTTPS ingress in front of FastAPI.

## AI-assisted development disclosure

OpenAI Codex and Google Agents CLI were used to refine the architecture, generate the
canonical ADK scaffold, and establish implementation and test boundaries. The project
owner remains responsible for reviewing, understanding, testing, and presenting all code.
