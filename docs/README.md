# Documentation index

Start here. [`../README.md`](../README.md) covers setup and the commands; this
folder covers how the system is built and why.

## Read first

| Document | What it answers |
|---|---|
| [agent-and-tool-architecture.md](agent-and-tool-architecture.md) | What the agent is, which tools it has, and the major design decisions behind them |
| [architecture-diagram.md](architecture-diagram.md) | The same system as diagrams: components, pipeline, HITL, trust boundary |
| [architecture.md](architecture.md) | The detailed, boundary-by-boundary reference for every package |
| [configuration.md](configuration.md) | Every environment variable, grouped by the settings group that reads it |

## The pipeline, stage by stage

In the order one monitoring run executes them:

| Document | Stage |
|---|---|
| [source-discovery.md](source-discovery.md) | Which normalized material belongs to the requested product (stage 3) |
| [acquisition.md](acquisition.md) | Retrieving the page, its linked PDFs, and its captured payloads (stage 1) |
| [normalization.md](normalization.md) | One uniform evidence schema, including PDF admission and transcription (stage 2) |
| [semantic-extraction.md](semantic-extraction.md) | Evidence into typed tariff fields (stage 4); operational guide |
| [semantic-extraction-maintenance-guide.md](semantic-extraction-maintenance-guide.md) | The same subsystem in depth: guarantees, limits, and how to extend it |
| [indexing-projection.md](indexing-projection.md) | Turning accepted extraction into knowledge documents and chunks |
| [knowledge-store.md](knowledge-store.md) | Versioned chunk persistence in PostgreSQL/pgvector |
| [snapshot-lifecycle.md](snapshot-lifecycle.md) | Acceptance, comparison, and change detection |

Read acquisition before normalization; the table above is in pipeline order, not
reading order.

## The read side

| Document | What it answers |
|---|---|
| [intent-resolution.md](intent-resolution.md) | How an imprecise, bilingual product name becomes a canonical offering |
| [tariff-query-services.md](tariff-query-services.md) | How an ordinary question is answered from accepted typed facts |
| [rag-retrieval.md](rag-retrieval.md) | Ranking: structured retrieval units, and the legacy chunk path |
| [rag-answering.md](rag-answering.md) | The legacy answer path kept for rollback |

## Running it, reviewing it, operating it

| Document | What it answers |
|---|---|
| [run-lifecycle.md](run-lifecycle.md) | Trigger, durable queue, worker claim, terminal states |
| [review-quarantine.md](review-quarantine.md) | What makes a candidate need a human, and what stays inactive meanwhile |
| [native-hitl-review.md](native-hitl-review.md) | The reviewer's flow in chat, in the CLI, and in ADK Web |
| [failure-behavior.md](failure-behavior.md) | Every stable failure code and what it does to the run |
| [observability.md](observability.md) | Traces, SQL metrics, logs, and what was deliberately not built |
| [model-cost-monitoring.md](model-cost-monitoring.md) | The redacted model call and cost ledger |
| [seed-catalog.md](seed-catalog.md) | The thirteen approved offerings and their validation rules |
| [demonstrations.md](demonstrations.md) | The assignment demonstrations and their machine-checked criteria |

## Elsewhere in the repository

- [`../tests/eval/RESULTS.md`](../tests/eval/RESULTS.md) — the evaluation
  datasets, the measured scores, and how to reproduce them.
- [`../tests/eval/datasets/README.md`](../tests/eval/datasets/README.md) — the
  eval dataset schema.
- [adk-2.9.2-upgrade.md](adk-2.9.2-upgrade.md) — a point-in-time upgrade record,
  kept for its compatibility notes rather than as current design.
