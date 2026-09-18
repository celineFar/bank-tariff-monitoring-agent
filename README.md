# Ameria Tariff Monitor

An evidence-backed Google ADK prototype for monitoring Ameria Bank consumer-loan
and mortgage tariffs. Gemini handles intent resolution, bounded cache-aware source
classification, native PDF structure transcription, and evidence-bound extraction;
security controls, ingestion, validation, persistence, comparison, scheduling, and
HITL routing are deterministic.

The repository contains the project scaffold, deterministic acquisition, structural
normalization, cache-aware source discovery, secure PDF retrieval and bounded Gemini PDF extraction,
a transactional PostgreSQL/pgvector knowledge store, hybrid retrieval, and bounded
evidence-linked semantic extraction. Claim generation, verification, and snapshot
comparison remain later implementation phases; unimplemented HTTP operations return
`501` rather than fabricating results.

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
[knowledge-store design](docs/knowledge-store.md), and
[.agents-cli-spec.md](.agents-cli-spec.md).

## Local setup

1. Copy `.env.example` to `.env` and set `GEMINI_API_KEY`.
2. Install dependencies: `agents-cli install`.
3. Install the local acquisition browser: `uv run playwright install chromium`.
4. Run deterministic tests: `uv run pytest tests/unit`.
5. Start the full stack: `docker compose up --build`.
6. Open API documentation at `http://localhost:8080/docs`.

The ADK playground can be started with `agents-cli playground` after dependencies are
installed. Behavioral evaluation uses `agents-cli eval run` after live pipeline tools
are implemented.

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
