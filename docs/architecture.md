# Architecture

```text
FastAPI user trigger ----+
                         +--> ADK intent/product resolution
Daily worker trigger ----+              |
                                        v
                           deterministic pipeline
 discovery -> secure retrieval -> PDF/HTML parse -> OCR fallback
 -> clean/chunk -> PostgreSQL + pgvector -> hybrid retrieval
 -> Gemini evidence-bound extraction -> deterministic validation
 -> snapshot comparison -> HITL routing -> report
```

Gemini is restricted to language-dependent intent resolution and structured extraction.
All security, persistence, validation, comparison, scheduling, and review routing controls
are deterministic application services. The ADK agent receives no raw network, filesystem,
shell, or SQL tool.

## Package boundaries

- `app/agent.py`: ADK root agent and stable instructions.
- `app/config/`: one environment adapter plus nested typed groups shared by API,
  agent, and worker; consumers depend only on the relevant group.
- `app/tools.py`: narrow ADK adapters that call application services.
- `app/api/`: user-trigger, run-status, and HITL review HTTP contracts.
- `app/domain/`: validated tariff/evidence models and pure business rules.
- `app/services/`: pipeline orchestration interfaces and deterministic application
  services. `PdfDownloader` uses an injected, caller-owned HTTP client and returns
  immutable PDF artifacts only after URL/redirect, status, size, MIME, and signature
  checks complete.
- `app/repositories/`: persistence interfaces and PostgreSQL implementations,
  including the transactional pgvector knowledge store.
- `app/security/`: URL, download, redirect, and logging guardrails.
- `app/worker.py`: daily Asia/Yerevan scheduler entry point.
- `migrations/`: PostgreSQL/pgvector schema.
- `tests/unit/`: deterministic logic tests.
- `tests/eval/`: non-deterministic agent/RAG behavioral evaluation.

## PDF retrieval boundary

Official-source discovery hands a typed `PdfCandidate` to `PdfDownloader`; the
downloader is an application service and is not exposed directly to Gemini. It uses
a caller-owned `httpx.AsyncClient`, manually validates the initial URL and every
redirect target, and retries only timeouts, transport failures, HTTP 429, and HTTP
5xx responses with bounded exponential backoff, proportional jitter, and bounded
`Retry-After` support for both delta-seconds and HTTP-date values.

The service returns an immutable `DownloadedPdf` only after the complete stream has
passed the configured byte limit, `application/pdf` MIME check, and `%PDF-`
signature check. The result contains the source/final URLs, bytes, SHA-256 checksum,
size, retrieval timestamps, and only the bounded provenance headers ETag,
Last-Modified, and Content-Disposition. Failed or interrupted attempts return a
typed `PdfDownloadError` and never expose a partial document.

## Website / HTML retrieval boundary

`RestrictedHttpTransport` now owns the allowlist, manual redirect, transient retry,
`Retry-After`, MIME, streamed-size, checksum, and safe-header behavior shared by PDF
and HTML retrieval. `HtmlRetriever` adds the narrower `text/html` contract and the
independent `MAX_HTML_BYTES` ceiling.

The retriever parses without a browser runtime, removes executable/form content and
common navigation, footer, cookie, chat, and repeated boilerplate elements,
then returns immutable structured headings, main text, tables, language hints, and
same-allowlist links. Canonical URLs and extracted links are independently validated;
unsafe values are ignored rather than trusted from the page. Protected, unavailable,
empty, non-HTML, and oversized responses fail with typed outcomes and no partial page.
Raw HTML remains an untrusted artifact and is never supplied directly to Gemini. See
`docs/html-retrieval.md` for the complete contract.

## Product source-crawl boundary

`ProductCrawler` starts only from the typed, hard-coded Phase-1 registry of five
consumer-loan and nine mortgage subproducts. For each seed it retrieves English and
verified Armenian product pages, discovers literal links from the unmodified HTML,
classifies them deterministically, follows at most one relevant supporting-page level,
downloads validated PDF/Word/Excel attachments, and returns a typed
`ProductSourceInventory`.

Discovery and retrieval remain separate: `source_discovery` inspects DOM attributes
and literal script strings without executing JavaScript, while `HtmlRetriever`,
`DocumentDownloader`, and `RestrictedHttpTransport` enforce network and byte-level
policy. Pages whose public DNN modules are empty in static HTML use a restricted,
allowlisted Playwright rendered-DOM fallback. A shared per-run task cache, semaphore,
and per-host limiter bound traffic.
Sibling products and global navigation are excluded, external/calculator references
are recorded but never followed, failures are isolated per product, and documents are
deduplicated first by normalized URL and then by SHA-256. See
`docs/product-source-crawler.md`.

`OfficialSourceDiscovery` converts validated inventories into explicit source
candidates and supplements them with bounded, allowlisted sitemap matches. A sitemap
match is only a proposal with `not_retrieved` status; it is not silently promoted to
an authoritative source. Product aliases and deterministic match signals remain part
of the candidate record for later source ranking.

`SourceIngestionService` persists raw HTML and validated document bytes before
parsing. `LocalArtifactStore` uses immutable SHA-256-addressed keys under the
configured artifact directory and writes one JSON provenance manifest per ingestion
run. API and worker containers mount the same local Docker volume.
`PostgresSourceIngestionRepository` separately persists run and product summaries,
the complete candidate inventory, unique artifact metadata, and per-run URL origins.
Migration `003_source_ingestion.sql` owns that metadata schema. A deterministic
artifact UUID and transactional run-level advisory lock make retries idempotent;
checksum metadata conflicts roll back the complete metadata write. Parser and
chunking components resolve artifact keys from this repository and consume bytes
through the storage interface rather than depending on absolute filesystem paths.
This deterministic storage boundary is never exposed to Gemini as a filesystem or
database tool.

## Document content-extraction boundary

`DocumentContentExtractor` accepts an `IngestedSource`, never an arbitrary local
path or live URL. It reloads bytes through `ArtifactStore`, verifies their SHA-256
digest and size against ingestion metadata, and dispatches only on the normalized,
validated MIME type. Unsupported formats stop with a typed error; PDF dispatch stays
unsupported until the dedicated PDF parser component is implemented.

The deterministic HTML extractor parses the persisted rendered/static artifact. It
selects the narrowest known main-content container, removes executable, navigation,
form, footer, hidden, and common boilerplate elements, and walks the remaining DOM in
document order. Its immutable output retains heading hierarchy, paragraphs, list
items, label/value facts, table rows, HTTP(S) link text and targets, language, source
URLs, and CSS locators. Stable block IDs derive from the source checksum, ordinal,
type, locator, label, and exact extracted text; this stage does not interpret tariff
amounts, currencies, rates, or terms.

The canonical JSON representation excludes processing timestamps, is addressed by
its own SHA-256 key under `extracted/`, and is therefore reused byte-for-byte on an
unchanged rerun. `PostgresContentExtractionRepository` records the relationship from
the ingested source artifact to the extracted representation, extractor/version,
statistics, warnings, and processing time. Migration
`004_content_extraction.sql` owns this schema, and an advisory lock plus deterministic
extraction ID make metadata writes idempotent. Neither artifact storage nor the
repository is exposed to Gemini.

`scripts/extract_ingested_sources.py` is the operator entry point. It can read an
explicit or latest local ingestion manifest, optionally filter products, or reload
known product sources from PostgreSQL. It prints each generated JSON path. Normal
runs record metadata in PostgreSQL; `--artifact-only` is an explicit local diagnostic
mode that writes immutable JSON without a metadata row. Non-HTML artifacts are
reported as skipped until their dedicated extractors exist.

## RAG index / knowledge-store boundary

`KnowledgeIndexer` accepts page-aware chunks from the future chunking component,
requests `RETRIEVAL_DOCUMENT` embeddings through an injected embedding provider, and
passes only validated 768-dimensional vectors to `PostgresKnowledgeStore`. Neither
the embedding client nor the repository is exposed as an ADK tool.

Document-version UUIDs are derived from bank, product, stable document identity, and
source checksum. Chunk IDs are SHA-256 digests of the document checksum and stable
location fields. Re-ingesting unchanged input therefore upserts the same rows. A
per-document PostgreSQL advisory transaction lock serializes concurrent ingestion;
new versions retire prior active versions and their chunks while retaining history.
Re-chunking the same version also retires chunks absent from the new input.

`knowledge_documents` retains source/version metadata, active state, retrieval time,
extraction method, and quality. `knowledge_chunks` retains page/section/language,
content, extraction metadata, a generated `tsvector`, and a `vector(768)` embedding.
GIN and HNSW indexes support the lexical/vector retrieval component implemented in a
later checklist item. Migration `002_rag_knowledge_store.sql` owns this schema.

## RAG retrieval boundary

`RagRetriever` accepts an already resolved bank, product, query, and tariff-field
scope. It creates a `RETRIEVAL_QUERY` embedding and calls only the narrow
`HybridRetrievalRepository`; no database handle or SQL operation crosses into the
agent/tool layer. `PostgresRagRetrievalRepository` unions full-text and cosine
candidates while enforcing bank/product and active-version predicates in every SQL
branch.

The application service performs documented weighted reciprocal-rank fusion,
absolute relevance scoring, threshold rejection, deterministic tie-breaking,
same-document overlap deduplication, and top-k limiting. It returns immutable typed
hits with complete document/chunk provenance, or an explicit
`INSUFFICIENT_EVIDENCE` result. See `docs/rag-retrieval.md` for the exact formula and
query contract.
