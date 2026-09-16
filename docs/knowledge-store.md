# RAG knowledge store

The knowledge store persists versioned, evidence-bearing document chunks in
PostgreSQL with pgvector. Ingestion is deterministic except for embedding generation,
which is isolated behind `EmbeddingProvider` and invoked by application code outside
the ADK tool loop.

## Ingestion contract

`KnowledgeDocument` contains the run, bank/product, stable document key, source and
final URLs, checksum, retrieval metadata, and page-aware chunks. `KnowledgeIndexer`
embeds chunk content with the configured Gemini embedding model using the
`RETRIEVAL_DOCUMENT` task and validates count, dimensionality, and finite values
before opening a repository transaction.

The database schema fixes embeddings at 768 dimensions. Changing that value requires
a schema migration and a coordinated embedding-provider update.

## Idempotency and versioning

- Document-version IDs derive from bank, product, document key, and checksum.
- Chunk IDs derive from document checksum, ordinal, page range, and section.
- Unchanged re-ingestion updates last-seen metadata without creating duplicates.
- A new checksum creates a distinguishable version and retires the previous active
  version and chunks without deleting history.
- Missing chunks are retired when the same version is re-indexed with a smaller set.
- A transaction-level advisory lock serializes writes for the same document identity.

## Indexes

- B-tree indexes support bank/product/document/version metadata filters.
- A generated `tsvector` with a GIN index supports multilingual lexical matching via
  PostgreSQL's `simple` configuration.
- A pgvector HNSW index with cosine operators supports semantic candidate retrieval.

Hybrid ranking and result contracts belong to the separate RAG Retrieval Component.

## PostgreSQL integration tests

The live tests deliberately require an isolated database whose name ends in `_test`:

```powershell
docker compose --profile test up -d db-test
$env:TEST_DATABASE_URL = `
  "postgresql+asyncpg://tariff:tariff@localhost:5433/tariff_monitor_test"
uv run pytest tests/integration/test_knowledge_store_postgres.py
```

The suffix guard prevents the test fixture from resetting a development or production
database. The Compose test service uses temporary storage and binds only to loopback.
The fixture applies all SQL migrations, verifies idempotency and retirement, and checks
that PostgreSQL plans vector ordering through the HNSW index.
