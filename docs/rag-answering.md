# RAG answer contract

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
