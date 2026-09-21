# Ameria Tariff Monitor

An evidence-backed Google ADK prototype for monitoring Ameria Bank consumer-loan
and mortgage tariffs. Gemini handles intent resolution, bounded cache-aware source
classification, native PDF structure transcription, and evidence-bound extraction;
security controls, ingestion, validation, persistence, comparison, scheduling, and
HITL routing are deterministic.

The repository contains deterministic acquisition, structural normalization,
cache-aware source discovery, secure PDF retrieval, bounded Gemini PDF extraction and
semantic extraction, dual source/summary knowledge projections, a transactional
PostgreSQL/pgvector store, hybrid retrieval, durable monitoring runs and snapshots,
change detection, and evidence-bound RAG answering. Claim generation and semantic
claim verification are intentionally deferred.

## Runtime

- ADK agent and standard ADK/A2A FastAPI surface
- Project API under `/api/v1`
- Daily worker at 06:00 `Asia/Yerevan`
- PostgreSQL 17 with pgvector
- Docker Compose for a single AWS compute instance

See [the architecture](docs/architecture.md), [configuration reference](docs/configuration.md),
[acquisition design](docs/acquisition.md), [normalization design](docs/normalization.md),
[source-discovery design](docs/source-discovery.md),
[semantic-extraction design](docs/semantic-extraction.md),
[knowledge-store design](docs/knowledge-store.md),
[seed catalog](docs/seed-catalog.md), [monitoring run lifecycle](docs/run-lifecycle.md),
[snapshot lifecycle](docs/snapshot-lifecycle.md),
[native ADK review](docs/native-hitl-review.md),
[indexing projections](docs/indexing-projection.md), [RAG answering](docs/rag-answering.md), and
[.agents-cli-spec.md](.agents-cli-spec.md).

## Local setup

1. Copy `.env.example` to `.env` and set `GEMINI_API_KEY`.
2. Install dependencies: `agents-cli install`.
3. Install the local acquisition browser: `uv run playwright install chromium`.
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
