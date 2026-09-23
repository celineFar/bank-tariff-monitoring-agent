# RAG answer contract

After the Phase F cutover this is the **rollback** answer path, selected by
`TARIFF_ANSWER_READ_MODEL=legacy`. With the default `structured` setting the
same surfaces answer from accepted typed facts through
`StructuredTariffQueryService`; see `docs/tariff-query-services.md`. Both read
models are reached through `TariffAnswerRouter`, so the switch changes the
evidence source without changing the authorized scope, and `POST
/api/v1/questions` keeps returning an `AnswerResult` either way. Under the
structured setting its citations carry the evidence ID, the exact quote, and the
source locator instead of a chunk ID.

`RagAnswerService` answers only from the active PostgreSQL/pgvector corpus; it never
invokes acquisition. A `QuestionCommand` supplies the query and optional typed
product/offering filters. Missing product scope returns `ambiguous_product`.

Retrieval searches deterministic offering summaries for precision and official source
chunks for coverage, with bank/product/offering/document-kind filters. The service
builds a bounded evidence packet and makes exactly one structured generation call.
Only official `source` chunks may be cited. Repository predicates require active documents
and active chunks, so pending, rejected, superseded, or failed review candidates are not
retrievable. The current-tariff service may disclose that a newer review exists, but neither
it nor RAG discloses candidate values before atomic approval. Citation IDs must be retrieved IDs and each
excerpt must occur exactly in its chunk; URL, document, page, and section are restored
server-side from the hit rather than trusted from model output. Invalid or absent
evidence returns `insufficient_evidence`.

Both adapters use the same service:

```bash
curl -X POST http://localhost:8080/api/v1/questions \
  -H 'Content-Type: application/json' \
  -d '{"query":"What is the nominal rate?","product":"consumer_loan","offering_id":"consumer_standard"}'
```

`AnswerResult` contains status, resolved scope, answer text when answered, verified
citations, and the newest cited source time as `as_of`. Retrieval diagnostics remain in
audit metadata rather than the prose answer.

## Inspect one question end to end

With PostgreSQL and Gemini credentials configured in `.env`, run:

```bash
uv run python -m scripts.trace_rag_answer \
  "What is the nominal interest rate?" \
  --product consumer_loan --offering-id consumer_standard
```

The script uses the production retriever and answer service. It prints the query
embedding input, scoped hybrid SQL search and candidates, selected chunks with
scores and full text, the evidence prompt and structured model draft, then the
final answer or failure code after citation validation. The product scope is
required; the offering filter is optional. It reads active published chunks and
does not write to the knowledge store.

Chunks are stored in PostgreSQL table `knowledge_chunks`, linked by `document_id`
to `knowledge_documents`. `knowledge_chunks.content` holds the text,
`search_vector` supports lexical search, and `embedding` stores the 768-dimensional
pgvector. Both the document and chunk must have `is_active = true` to be retrieved.


## Shadow comparison

`app/services/structured_shadow_read.py` runs both read models over a
checked-in set of representative queries and reports statuses, fact and citation
counts, latency, and evidence-source overlap. It logs only a question hash,
never question text, source text, excerpts, or generated wording. Its cutover
gate stays closed until both paths ran, the structured model answered at least
one query, and every divergence was audited:

```bash
uv run python scripts/shadow_read_report.py            # structured only, no model call
uv run python scripts/shadow_read_report.py --with-legacy  # spends Gemini credits
```
