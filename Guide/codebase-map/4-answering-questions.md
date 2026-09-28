# 4 · Answering questions (read model and RAG)

[← Guide](README.md) · Deep dives: [rag-retrieval.md](../../docs/rag-retrieval.md), [tariff-query-services.md](../../docs/tariff-query-services.md), [knowledge-store.md](../../docs/knowledge-store.md), [indexing-projection.md](../../docs/indexing-projection.md)

Questions are answered **only from accepted typed facts**. No LLM does arithmetic and no free-text RAG answer path exists. Retrieval units (text chunks tied to evidence) are used only to *find which field* a free-form question is about.

```text
question → resolve_request → ResolutionPlan (read grant) → TariffAnswerRouter
        → StructuredTariffQueryService.answer → typed facts (+ lexical/vector retrieval units) → cited answer
```

## Answer path

| What | Where |
|---|---|
| The single answer entry (chat tool, post-monitoring, `/questions`) | [TariffAnswerRouter](../../app/services/answer_read_model.py#L118), [answer_plan](../../app/services/answer_read_model.py#L136), [answer_question](../../app/services/answer_read_model.py#L142) |
| Query engine: lookup, compare, rank, overview, history | [StructuredTariffQueryService.answer](../../app/services/structured_tariff_query.py#L252) |
| The plan it executes | [ResolutionPlan](../../app/domain/structured_tariffs.py#L490), [QueryOperation](../../app/domain/structured_tariffs.py#L452) |
| Default fields for an overview | [CORE_FIELDS](../../app/services/structured_query_planning.py#L28) |
| Typed plan for API callers | [issue_typed_plan](../../app/services/structured_query_planning.py#L114) |
| Comparable / rankable fields, reasons not ranked | [RANKABLE_PATHS](../../app/domain/tariff_comparison.py#L26), [comparison_issue](../../app/domain/tariff_comparison.py#L65), [IncomparabilityReason](../../app/domain/tariff_comparison.py#L14) |
| Result → answer + citations | [structured_to_answer_result](../../app/services/answer_read_model.py#L56) |
| What the model sees (trimmed) | [model_facing_query_result](../../app/services/tariff_queries.py#L374) |

## The typed read model

| What | Where |
|---|---|
| Canonical field paths (e.g. `rate.nominal.maximum`) | [FieldPath](../../app/domain/structured_tariffs.py#L19) |
| Human labels (EN/HY) for each path | [FIELD_LABELS](../../app/domain/structured_tariffs.py#L92) |
| Extraction field → field paths | [SOURCE_FIELD_PATHS](../../app/domain/structured_tariffs.py#L341) |
| Fee description → fee path | [fee_field_path](../../app/domain/structured_tariffs.py#L438) |
| Models | [TariffFact](../../app/domain/structured_tariffs.py#L570), [FactEvidence](../../app/domain/structured_tariffs.py#L552), [OfferingProfile](../../app/domain/structured_tariffs.py#L614), [RetrievalUnit](../../app/domain/structured_tariffs.py#L632) |
| Extraction → facts + units (fail-closed) | [StructuredTariffProjector.project](../../app/services/structured_projection.py#L168); per type [_amounts](../../app/services/structured_projection.py#L455), [_rates](../../app/services/structured_projection.py#L542), [_terms](../../app/services/structured_projection.py#L584), [_units](../../app/services/structured_projection.py#L661) |
| Written in the publication transaction | [publish_structured_projection](../../app/repositories/structured_projection.py#L19) |
| Tables (`offering_profiles`, `tariff_facts`, `fact_evidence`, `retrieval_units`) | [011_structured_tariff_read_model.sql](../../migrations/011_structured_tariff_read_model.sql) |

## Retrieval (the RAG layer)

| What | Where |
|---|---|
| SQL reads: facts, lexical + vector units | [PostgresStructuredTariffQueryRepository](../../app/repositories/structured_tariff_query.py#L227) |
| Lexical query builder (stop words, Armenian marks, stemming, prefix OR) | [lexical_search_terms](../../app/repositories/structured_tariff_query.py#L180), [_STOPWORDS](../../app/repositories/structured_tariff_query.py#L67), [_stem](../../app/repositories/structured_tariff_query.py#L209) |
| Fusion lexical + vector (RRF k=60, vector weight 0.7) | [RANK_FUSION_VERSION](../../app/services/structured_tariff_query.py#L47), [FIELD_FINDER_MAX_PATHS](../../app/services/structured_tariff_query.py#L49) |
| Unit text rendering version | [RENDERER_VERSION](../../app/services/structured_projection.py#L57) |
| Embeddings (Gemini, retries, quota) | [GeminiEmbeddingProvider](../../app/services/embedding_providers.py#L71), [GeminiQueryEmbeddingProvider](../../app/services/embedding_providers.py#L168) |
| Embed units missing a vector (worker sweep) | [StructuredUnitEmbeddingService.embed_missing](../../app/services/structured_unit_embeddings.py#L127) |
| Embedding cache (content-addressed) | [PostgresEmbeddingCache](../../app/repositories/embedding_cache.py#L12) |
| Per-query step trace (`RETRIEVAL_TRACE_LEVEL`) | [retrieval_trace](../../app/services/retrieval_trace.py#L105) |

**Evidence documents / chunks.** The selected sources are stored as text chunks with page, section and language metadata. Reviewers read them, and they are what facts cite. They are not searched.
Chunking: [KnowledgeProjectionService.project_sources](../../app/services/knowledge_projection.py#L70), size `CHUNK_SIZE_CHARS` ([RagSettings](../../app/config/models.py#L283)); models [KnowledgeChunk](../../app/domain/knowledge.py#L34), [KnowledgeDocument](../../app/domain/knowledge.py#L73).

## Current tariffs and history

| What | Where |
|---|---|
| Latest accepted + freshness (7 days) | [CurrentTariffService.get_current](../../app/services/tariff_queries.py#L38), setting `TARIFF_FRESHNESS_DAYS` ([TariffQuerySettings](../../app/config/models.py#L308)) |
| Snapshots and changes over time | [TariffHistoryService.query](../../app/services/tariff_queries.py#L129) |
| Compact citation per value (≤300 chars) | [field_citations](../../app/services/tariff_queries.py#L325), [QUOTE_CHARS](../../app/services/tariff_queries.py#L322) |
| Payload returned to the model | [current_tariffs_payload](../../app/tools/reads.py#L163), [tariff_history_payload](../../app/tools/reads.py#L191) |
