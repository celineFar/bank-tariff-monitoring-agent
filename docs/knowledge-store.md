# RAG knowledge store

The knowledge store persists versioned, evidence-bearing document chunks in
PostgreSQL with pgvector. Ingestion is deterministic except for embedding generation,
which is isolated behind `EmbeddingProvider` and invoked by application code outside
the ADK tool loop.

## Ingestion contract

`KnowledgeDocument` contains the run, bank/product/offering, document kind, stable
document key, source and final URLs, checksum, retrieval metadata, and page-aware
chunks. `KnowledgeIndexer.embed` embeds chunk content with the configured Gemini
embedding model using the `RETRIEVAL_DOCUMENT` task (content-addressed cache first)
and validates count, dimensionality, and finite values. A chunk may also be stored
without a vector (`EmbeddedKnowledgeDocument.text_only`): content under review, or a
run published during a provider quota refusal.

The database schema fixes embeddings at 768 dimensions. Changing that value requires
a schema migration and a coordinated embedding-provider update.

## Versions, sets and activation

Writes happen only inside the offering publication transaction
(`app/repositories/monitoring.py`) and the review repository, through
`app/repositories/knowledge_publication.py`:

- **Versions are immutable.** The version ID derives from bank, product, offering,
  document kind, document key, the source checksum and the projection hash; a chunk ID
  from the version ID and ordinal. Storing a version again only refreshes bookkeeping
  (last seen, retrieval time, document metadata) and fills a vector that is still
  missing. New versions start inactive (`publication_state = pending_review`).
- **A snapshot owns its set** (`snapshot_documents`, migration `023`): the versions it
  was built from. Fact evidence links to documents through it.
- **Activation replaces the offering's whole index.** An accepted publication, or the
  final approval of a review-required snapshot, activates the snapshot's set and
  retires every other active document of the offering: a changed page's old version,
  a PDF no longer linked, the previous summary. History is kept (`retired`).
- **Discarded versions are deleted.** Rejecting or superseding a review deletes the
  snapshot's set and every `pending_review` version no other snapshot names.
- States: `pending_review`, `active`, `retired`.
- Every path that changes an offering's index or its pending reviews takes the
  offering's publication advisory lock first (`lock_offering_publication`).

`KnowledgeIndexer.embed_missing` embeds active chunks stored without a vector
(`PostgresChunkEmbeddingRepository`); the approval path calls it after committing, and
the worker runs it every `EMBEDDING_SWEEP_INTERVAL_SECONDS` for up to
`EMBEDDING_SWEEP_BATCH` chunks (usage stage `indexing.embedding_sweep`).

## Indexes

- B-tree indexes support bank/product/offering/document/version metadata filters.
- A generated `tsvector` with a GIN index supports multilingual lexical matching via
  PostgreSQL's `simple` configuration.
- A pgvector HNSW index with cosine operators supports semantic candidate retrieval.
- Both chunk indexes are **partial** (migration `023`): GIN `WHERE is_active`, HNSW
  `WHERE is_active AND embedding IS NOT NULL`, so retired and unembedded rows never
  fill the approximate scan. Queries must repeat these predicates verbatim. A retired
  row's entry leaves the partial index at the next (auto)vacuum.

Hybrid ranking and result contracts are implemented by the separate RAG Retrieval
Component and documented in `docs/rag-retrieval.md`.

## PostgreSQL integration tests

The live tests deliberately require an isolated database whose name ends in `_test`:

```powershell
docker compose --profile test up -d db-test
$env:TEST_DATABASE_URL = `
  "postgresql+asyncpg://tariff:tariff@localhost:5433/tariff_monitor_test"
uv run pytest tests/integration/test_knowledge_retrieval_postgres.py `
  tests/integration/test_indexing_fixes_postgres.py
```

The suffix guard prevents the test fixture from resetting a development or production
database. The Compose test service uses temporary storage and binds only to loopback.
The fixtures apply all SQL migrations; the tests check publication, activation,
review quarantine, evidence links, the partial indexes, and that PostgreSQL can plan
vector ordering through the HNSW index.
