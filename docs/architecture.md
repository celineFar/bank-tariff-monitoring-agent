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
  services. `AcquisitionService` combines restricted static HTML retrieval, faithful
  structural parsing, conditional Playwright rendering, bounded same-domain network
  capture, content-addressed artifact storage, and linked-PDF retrieval. `PdfDownloader`
  uses an injected, caller-owned HTTP client and returns
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

## Acquisition boundary

Acquisition is deterministic and does not decide what a loan field means. Initial URLs,
HTTP redirects, browser subrequests, and the final browser URL must pass the same exact
HTTPS host allowlist. Browser rendering is used only when static content is insufficient
or the DOM advertises interactive/client-rendered content. It blocks non-GET requests,
forms, downloads, cross-domain traffic, service workers, and unnecessary heavy assets.

The output is an immutable `PageArtifact` containing raw/rendered HTML, Markdown,
structural blocks, span-aware tables, linked FAQ questions and answers, inline links,
image/control metadata, downloaded PDFs, bounded textual XHR/fetch payloads, source
locators, timestamps, and a deterministic content hash. Raw bytes are stored
under SHA-256-derived paths; source-controlled strings never become filesystem paths.
See `docs/acquisition.md` for the complete contract.

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
