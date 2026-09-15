# Architecture Components To-do List

This list contains the components that need to be implemented. The order should remain as specified unless a dependency requires us to change it. After each step is completed, it should be marked as done.

Each item defines its responsibility, implementation contract, important boundaries, and completion criteria. Ameria Bank, consumer loans, mortgages, Gemini Developer API, PostgreSQL/pgvector, FastAPI, and the daily `06:00 Asia/Yerevan` schedule are the initial scope.

- [ ]  1. Configuration Component

  - **Responsibility:** Provide one typed source of runtime configuration for the API, worker, ADK agent, repositories, and processing pipeline.
  - **Implement:** Use `pydantic-settings` for model names, `GEMINI_API_KEY`, PostgreSQL URL, Ameria host allowlist, HTTP timeout/retries, download/MIME limits, OCR thresholds/languages, chunk/retrieval settings, HITL thresholds, schedule, and logging. Supply a secret-free `.env.example`; use environment variables or AWS Secrets Manager for real secrets.
  - **Boundaries:** Normalize allowlist entries as hostnames, validate settings at startup, inject settings into services, and do not scatter environment reads through business logic.
  - **Done when:** API and worker use the same validated settings, invalid values fail before startup, configuration tests pass, and no credential is committed.

- [ ]  2. PDF Downloader

  - **Responsibility:** Retrieve official candidate PDFs safely as untrusted binary content.
  - **Implement:** Build a focused async downloader using the shared HTTP client. Validate HTTPS and the exact Ameria allowlist before requesting and after every redirect; enforce status handling, redirect/timeout/retry limits, streamed byte limits, MIME and PDF-signature checks, SHA-256 hashing, and retrieval timestamps.
  - **Contract:** Accept only a discovered candidate URL and return a typed document containing content/artifact reference, final URL, MIME type, size, checksum, timestamps, and safe provenance headers. Do not expose generic downloading to Gemini.
  - **Done when:** Tests cover valid PDF, timeout, 404, 429/5xx retry, oversized content, spoofed MIME/signature, disallowed redirect, redirect loop, and controlled failure without partial output.

- [ ]  3. RAG Index / Knowledge Store

  - **Responsibility:** Persist evidence-bearing chunks for lexical and semantic retrieval.
  - **Implement:** Use PostgreSQL and pgvector tables/repositories for document versions, chunks, metadata, full-text `tsvector`, and embeddings. Upsert deterministic chunk IDs derived from document checksum and location; retire stale chunks when a version changes. Generate embeddings through the configured Gemini embedding model outside the LLM tool loop.
  - **Boundaries:** Keep bank, product, document, URL, page, section, language, retrieval time, checksum, extraction method, and quality filterable. Writes must be transactional and idempotent. This consumes component 7 output despite appearing earlier in the list.
  - **Done when:** Unchanged re-ingestion creates no duplicates, changed versions remain distinguishable, search uses indexes, and PostgreSQL/pgvector integration tests pass.

- [ ]  4. RAG Retrieval Component

  - **Responsibility:** Return the smallest relevant set of verifiable chunks for tariff extraction.
  - **Implement:** Combine pgvector similarity and PostgreSQL full-text search with mandatory bank/product filters, documented rank fusion, overlap deduplication, top-k limits, and minimum relevance thresholds. Support field-oriented queries for amounts, terms, rates, fees, collateral, and privileges.
  - **Contract:** Return typed hits with chunk content/ID, lexical/vector/final scores, rank explanation, document version, page/section, and URL. Return explicit insufficient evidence below threshold.
  - **Done when:** Armenian/English tests cover both products, metadata isolation, irrelevant-query rejection, deterministic ordering, deduplication, and complete provenance.

- [ ]  5. Website Scraper / HTML Retriever

  - **Responsibility:** Retrieve usable public content and links from official Ameria webpages.
  - **Implement:** Reuse the restricted HTTP transport and URL validator. Enforce redirects, timeouts, size, status, and HTML type limits. Extract canonical URL, title, headings, main text, tables, language hints, and same-allowlist links while removing scripts, styles, navigation, cookie banners, and repeated boilerplate.
  - **Boundaries:** Never execute scripts, submit forms, or bypass authentication, CAPTCHA, access restrictions, or anti-bot measures. Retain checksums and retrieval metadata; treat HTML as untrusted data.
  - **Done when:** Fixtures preserve Armenian text/tables and official links, unsafe/non-HTML/oversized responses fail closed, and unavailable/protected pages produce controlled errors.

- [ ]  6. Official Source Discovery

  - **Responsibility:** Find candidate product pages and official information documents within the configured Ameria domain.
  - **Implement:** Traverse configured seeds, public sitemap entries, navigation, and official page links under strict crawl budgets. Normalize/deduplicate URLs and match Armenian/English product synonyms plus official-document terms such as `տեղեկատվական ամփոփագիր` and `ամփոփաթերթիկ`.
  - **Contract:** Return candidates with URL, type, discovery path, anchor/title/context, match signals, and retrieval status. Discovery proposes candidates; it does not silently declare authority.
  - **Done when:** Consumer-loan and mortgage fixtures produce relevant same-domain candidates, off-domain/unsupported resources are excluded, budgets hold, and product-not-found is explicit.

- [ ]  7. Chunking & Metadata Builder

  - **Responsibility:** Convert cleaned, page-aware content into stable retrieval units without losing evidence locations.
  - **Implement:** Chunk by page, heading, subsection, and table before splitting oversized sections with configurable size/overlap. Keep table headings with rows where possible. Generate deterministic IDs and metadata for bank/product, document identity/version/checksum, source URL, language, time, page, section, order, extraction method, and quality.
  - **Boundaries:** Never mix documents; record any page range. Avoid tiny orphan chunks, repeated boilerplate, and overlap-driven duplicate evidence.
  - **Done when:** Repeated input creates identical chunks/IDs, Armenian text and tables survive, every chunk maps to its source, and boundary/overlap tests pass.

- [ ]  8. PDF Parser / Document Content Extractor

  - **Responsibility:** Extract structured, page-addressable content from digital PDFs before OCR.
  - **Implement:** Parse every page into text, blocks/tables, page dimensions, document metadata, warnings, and extraction statistics while preserving page boundaries and reading order. Detect encrypted, malformed, empty, and excessively complex documents.
  - **Boundaries:** Accept only downloader-approved bytes and never infer tariff values. Report extraction facts to the quality checker, which decides whether OCR is required.
  - **Done when:** Tests cover Armenian Unicode, normal/multi-page/table PDFs, empty pages, malformed/encrypted files, and page output usable by evidence references.

- [ ]  9. Relevant Document Recognition / Source Ranking

  - **Responsibility:** Rank candidates by authority, product relevance, recency, and extractability while exposing ambiguity.
  - **Implement:** Use explainable weighted signals: official-document terminology, canonical source, product match, link context, title, publication/effective date, type, checksum duplication, and quality. Penalize generic marketing, archived/expired, unrelated, and weakly matched sources. Gemini may assist semantic matching only after deterministic hard filters.
  - **HITL boundary:** Close scores, contradictory dates/values, or no result above threshold create a review case rather than a silent choice.
  - **Done when:** Ranking is reproducible, official summaries outrank generic pages, stale/irrelevant sources are penalized, and ambiguity routes to HITL.

- [ ]  10. Evaluation Harness

  - **Responsibility:** Measure nondeterministic agent, intent, retrieval, extraction, evidence, and response behavior separately from unit tests.
  - **Implement:** Use the Agents CLI/ADK evaluation format with versioned cases for both products, Armenian/English and imprecise requests, expected resolution, source/chunk evidence, tariff values, `NOT_FOUND`, ambiguity, and failures. Add rubric-based quality and task-specific programmatic metrics where supported.
  - **Boundaries:** Do not assert model wording in pytest. Record dataset/model/config versions and an acceptance threshold; keep generated traces/results free of secrets.
  - **Done when:** `agents-cli eval run` yields traceable stage-level results, both products are covered, a baseline is documented, and an expansion plan exists.

- [ ]  11. Structured Tariff Extraction

  - **Responsibility:** Convert retrieved evidence into the required loan-tariff schema without invention.
  - **Implement:** Use Gemini structured output with a strict Pydantic/JSON schema covering currency, term, amount, nominal rate, EIR, collateral, application fee, disbursement fee, service fee, and salary-customer privileges. Each field requires `FOUND`/`NOT_FOUND`, raw value, evidence chunk IDs, and extraction status/confidence.
  - **Boundaries:** Supply only retrieved chunks. Extraction does not normalize, validate, rank conflicting sources, save, or compare. Reject evidence IDs absent from supplied context and use only bounded schema-repair attempts.
  - **Done when:** Fixtures yield schema-valid output, absent data remains `NOT_FOUND`, invented evidence fails, conflicts remain visible, and API/schema failures are explicit.

- [ ]  12. OCR Fallback

  - **Responsibility:** Recover page-level text from scanned/image PDFs when direct extraction is insufficient.
  - **Implement:** Render required pages at configured DPI; run Armenian/English OCR; return page text/blocks, engine/version, confidence where available, duration, and warnings. Bound page count, resolution, pixels, memory, concurrency, and execution time.
  - **Triggering:** Only deterministic quality results invoke OCR. Keep OCR provenance separate. Failed or low-confidence OCR routes to HITL/failure, never fabricated interpretation.
  - **Done when:** A committed scanned fixture exercises OCR, direct PDFs skip it, Armenian/numerical text is usable, limits hold, and low quality is explicit.

- [ ]  13. Document Cleaning & Structuring

  - **Responsibility:** Remove extraction noise while preserving financial meaning and coordinates.
  - **Implement:** Normalize Unicode/whitespace, safely repair line breaks/hyphenation, detect repeated headers/footers, remove standalone page numbers, deduplicate blocks, identify headings/sections, and represent tables consistently. Preserve Armenian, decimals, currencies, rates, ranges, conditions, footnotes, and page boundaries.
  - **Boundaries:** Map every cleaned block to original page/block coordinates, log transformations, and never rewrite numeric values or discard qualifications.
  - **Done when:** Golden fixtures remove noise without tariff mutation, tables stay understandable, and provenance survives cleaning.

- [ ]  14. Normalization Component

  - **Responsibility:** Convert extracted values to canonical typed forms for validation and comparison while retaining raw text.
  - **Implement:** Normalize currencies, grouped/decimal numbers, percentages, ranges/open bounds, AMD amounts, month/year durations, fee amount/basis, conditional privileges, and missing states. Represent compound values structurally, not only as display strings.
  - **Boundaries:** Be deterministic and locale-aware. Keep `NOT_FOUND`, zero, free/no-fee, and not-applicable distinct; preserve raw values and evidence.
  - **Done when:** Equivalent formats such as `10 000 000 AMD` and `10,000,000 AMD` normalize identically while material differences remain distinct.

- [ ]  15. Snapshot Storage / Repository

  - **Responsibility:** Persist accepted observations and retrieve the correct preceding snapshot.
  - **Implement:** Add SQLAlchemy/asyncpg repositories for runs, source documents, snapshots, and audit metadata. Store product identity, timestamps, full normalized/raw schema, validation status, source version/checksum, and evidence. Save atomically and provide `get_latest_accepted(bank, product, before_run)`.
  - **Boundaries:** Pending/rejected reviews cannot become accepted snapshots. Narrow injected repositories prevent Gemini from seeing SQL or handles. Identical observations must not create false changes.
  - **Done when:** PostgreSQL tests cover first observation, states, rollback, idempotency, concurrency, previous-selection correctness, and restart persistence.

- [ ]  16. Change Detection Component

  - **Responsibility:** Report only meaningful differences between accepted canonical snapshots.
  - **Implement:** Compare all fields including bounds, currencies, term units, rate types, fee bases, collateral conditions, and privileges. Return typed changes with prior/current raw/canonical values, evidence, severity, and review reason for large changes.
  - **Boundaries:** Missing prior data means `FIRST_OBSERVATION`. Ignore formatting-only differences. Treat found↔missing transitions as meaningful.
  - **Done when:** Tests cover equivalent formats, value/range changes, missing transitions, unchanged/first snapshots, and large-change HITL inputs.

- [ ]  17. Evidence / Provenance Component

  - **Responsibility:** Make every accepted non-missing tariff field independently verifiable.
  - **Implement:** Create immutable references containing final/source URL, document identity/version/checksum, page/section, chunk/block ID, bounded excerpt, retrieval time, extraction method, and quality. Resolve model-returned IDs against stored chunks server-side.
  - **Boundaries:** Reject model-authored locations/excerpts that cannot be matched. Preserve evidence throughout snapshots and change history.
  - **Done when:** Orphaned/mismatched evidence fails validation, every `FOUND` field is traceable, and both sides of a change remain verifiable.

- [ ]  18. Result / Report Builder

  - **Responsibility:** Produce stable business output without asking Gemini to restate validated facts.
  - **Implement:** Deterministically render JSON and readable Markdown/text with bank/product, retrieval time, statuses, all tariff fields including `NOT_FOUND`, sources, field evidence, uncertainty, review state, first observation, and changes. Support Armenian/English text safely.
  - **Boundaries:** Escape untrusted excerpts, use canonical formatters, keep ordering stable, and never hide validation failures or pending review.
  - **Done when:** Golden tests cover success, no prior snapshot, changes, missing fields, HITL, and controlled failure without fabricated values.

- [ ]  19. Start / Trigger Component

  - **Responsibility:** Start the same pipeline from a user request or scheduled event.
  - **Implement:** Add a bounded FastAPI request endpoint with optional idempotency key, create a run record, invoke/enqueue `TariffPipeline.run`, and expose run/result status. Add a scheduled adapter that submits canonical consumer-loan and mortgage requests to the same service.
  - **Boundaries:** Record trigger, run/correlation ID, original request, requester when available, timestamps, and status. Keep HTTP/scheduling outside the agent tool layer and prevent duplicate submission.
  - **Done when:** Both triggers enter one pipeline, return stable IDs, validate input/idempotency, and expose pending/success/failure/review states.

- [ ]  20. Scheduler

  - **Responsibility:** Trigger both products daily at 06:00 `Asia/Yerevan`.
  - **Implement:** Run a timezone-aware scheduler in a separate worker with stable job identity, startup logs, graceful shutdown, misfire/coalescing policy, bounded concurrency, and database advisory lock/uniqueness preventing duplicate product/date runs. Provide a manual tick for demonstration.
  - **Boundaries:** No business/extraction logic; it calls the shared trigger/application service. One product failure must not suppress the other or future schedules.
  - **Done when:** Timezone behavior, duplicate-worker locking, missed runs, manual simulation, isolation, and failure recovery are tested/documented.

- [ ]  21. ADK Agent / Orchestrator

  - **Responsibility:** Interpret requests and coordinate a constrained workflow while deterministic services retain control.
  - **Implement:** Define one root ADK agent with explicit role, supported scope, no-fabrication rules, stopping conditions, and prompt-injection resistance. Expose focused typed tool adapters—not raw network, filesystem, shell, SQL, or database tools. Use session state only for conversational/run context; PostgreSQL owns durable state.
  - **Execution boundary:** Gemini handles intent/product understanding and evidence-bound extraction. The application service controls stage order, validation, retries, stopping, persistence, comparison, reporting, and HITL.
  - **Done when:** Smoke/eval cases cover both products and ambiguity, traces show only approved tools, document instructions cannot bypass controls, and generated ADK/A2A plumbing remains intact.

- [ ]  22. Deterministic Validation Component

  - **Responsibility:** Decide whether extraction is acceptable without relying on Gemini judgment.
  - **Implement:** Validate schema/statuses, required fields, supported currencies, numeric/range ordering, percentage bounds, duration/amount/fee formats, product compatibility, domains, file constraints, evidence existence/match, and missing-value rules. Return field errors/warnings and aggregate `ACCEPT`, `REVIEW`, or `REJECT`.
  - **Boundaries:** Do not silently coerce implausible data. Only `ACCEPT` may be stored as accepted; critical missing/evidence failures route according to explicit policy.
  - **Done when:** Parameterized boundary/invalid tests pass and storage cannot bypass the validation decision.

- [ ]  23. User Intent + Product Resolution

  - **Responsibility:** Convert natural language into a constrained Ameria consumer-loan or mortgage intent.
  - **Implement:** Define structured output for bank, canonical product enum, original query, language, requested fields/action, confidence, and ambiguity reason. Give Gemini Armenian/English synonyms/examples, then verify against supported enums and deterministic alias/fuzzy signals.
  - **Boundaries:** The model cannot introduce arbitrary banks, URLs, products, or actions. Low-confidence/conflicting/no-match input requests clarification or returns `PRODUCT_NOT_FOUND`; scheduled runs submit canonical products.
  - **Done when:** Evaluation covers exact names, synonyms, misspellings, vague/unrelated/conflicting requests, and attempts to redirect to another domain.

- [ ]  24. Security / Guardrails

  - **Responsibility:** Enforce least privilege at every trust boundary independently of prompts.
  - **Implement:** Centralize URL/redirect allowlisting, HTTPS-only and IP/private-host rejection, file limits/type checks, schema validation, prompt-injection treatment, secret isolation, database least privilege, container hardening, and API/HITL authentication hooks. Add ADK pre-tool callbacks that validate approved tool names and canonical arguments.
  - **Boundaries:** Gemini sees no secrets/raw clients and has no arbitrary network, filesystem, shell, database, or SQL access. Never bypass CAPTCHA/auth/access/anti-bot controls. Use non-root containers and AWS secret injection before exposure.
  - **Done when:** Tests block unsafe URLs/redirects/files, unauthorized reviews, injection attempts, unexpected tools, and secret leakage.

- [ ]  25. Document Quality Check

  - **Responsibility:** Decide whether extraction is usable, needs OCR, needs review, or is unusable.
  - **Implement:** Measure per-page/document characters, printable/letter/digit ratios, replacement/control characters, blank pages, table/text coverage, repeated noise, OCR confidence, and expected tariff-term/numeric coverage. Return `USABLE`, `NEEDS_OCR`, `NEEDS_REVIEW`, or `UNUSABLE` with metrics/reason codes.
  - **Boundaries:** Use configured deterministic thresholds and retain metrics for audit; Gemini cannot override a failed hard threshold.
  - **Done when:** Digital, scanned, mixed, empty, garbled, and low-confidence fixtures take the expected route, including threshold boundaries.

- [ ]  26. Log Sanitizer

  - **Responsibility:** Keep secrets, credentials, sensitive headers, and excessive content out of logs/traces.
  - **Implement:** Add a recursive structured logging filter for configured secrets, keys/tokens, authorization/cookie headers, database URLs, signed query strings, and oversized source/model/tool payloads. Log safe IDs, hashes, sizes, counts, and bounded excerpts instead.
  - **Boundaries:** Sanitize before every console/JSON/telemetry handler, including exception/HTTP logging. Never log chain-of-thought; fail closed on suspect fields.
  - **Done when:** Nested data, exceptions, headers, URLs, and long Armenian content tests prove secrets/full bodies never reach captured logs.

- [ ]  27. Logging / Observability

  - **Responsibility:** Make each run diagnosable without unsafe payloads or chain-of-thought.
  - **Implement:** Emit structured events with run/request/product/source/document/snapshot/review IDs; stage timing/status; HTTP attempts; parsing/OCR quality; chunk/index counts; retrieval scores; extraction completeness/model usage; validation; HITL; changes; and final status. Define stable event names/reason codes and counters/histograms.
  - **Boundaries:** All events pass through sanitization. Keep OpenTelemetry vendor-neutral/configurable so AWS/local startup does not require Google ADC. Persist key audit events separately in PostgreSQL.
  - **Done when:** Normal and controlled-failure runs can be reconstructed by correlation ID, metrics are documented, and telemetry can be disabled safely.

- [ ]  28. HITL / Human Review Component

  - **Responsibility:** Prevent acceptance of ambiguous/risky results until an authorized reviewer decides.
  - **Implement:** Persist review cases for close-ranked/conflicting documents, low OCR/quality, missing critical evidence, invalid extraction after bounded repair, and large changes. Store reasons, candidate/prior/current values, source evidence, quality/validation details, and proposed action. Expose FastAPI list/detail/approve/reject endpoints with identity, comments, time, and optimistic concurrency.
  - **Boundaries:** Pending results cannot become accepted. Approval resumes from stored validated artifacts rather than re-running nondeterministic work; rejection is terminal. Development identity must be clearly marked and replaced before public exposure.
  - **Done when:** Tests cover creation, evidence display, authorization, decisions, double-decision conflict, restart persistence, snapshot gating, and the demonstration scenario.

- [ ]  29. Automated Test Suite

  - **Responsibility:** Verify deterministic correctness and integration boundaries independently of live Gemini output.
  - **Implement:** Add unit tests for settings, normalization, validation, comparison, URLs, quality, cleaning/chunking, evidence, ranking, and error classification. Add integration tests for mocked HTTP, digital/OCR fixtures, PostgreSQL/pgvector and hybrid retrieval, FastAPI/HITL, scheduler locking, log redaction, and the deterministic pipeline with fake Gemini/embedding adapters.
  - **Boundaries:** Offline and reproducible by default; mark live model/network tests. Never assert natural-language model content in pytest. Include small generated/licensed digital and scanned Armenian/numeric fixtures.
  - **Done when:** `uv run pytest tests/unit tests/integration` passes cleanly, critical failures are covered, gaps are documented, and live tests require explicit opt-in.

- [ ]  30. Error Handling & Retry Component

  - **Responsibility:** Produce stable outcomes, retry only transient work, and prevent partial/fabricated results.
  - **Implement:** Define typed errors/reason codes for configuration, product/source failures, unsafe URLs, HTTP status/timeouts, invalid/large files, parse/OCR/quality, embedding/retrieval, irrelevant evidence, Gemini/schema, validation, database, missing prior snapshot, and HITL conflicts. Centralize capped exponential backoff/jitter for transient HTTP, Gemini, embedding, and database disconnects.
  - **Boundaries:** Never retry deterministic 4xx, validation, allowlist, unsupported-file, or permanent parsing failures. Update run/audit state, roll back, clean temporary resources, stop downstream persistence/reporting, and treat missing prior data as `FIRST_OBSERVATION`.
  - **Done when:** Tests verify retry classification/limits, cleanup/rollback, terminal state/API mapping, and at least two controlled failure demonstrations.
