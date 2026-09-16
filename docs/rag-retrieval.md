# RAG retrieval

The retrieval component returns a small, typed, evidence-bearing chunk set for
structured tariff extraction. It is a deterministic application service and is not
exposed to Gemini as a database or SQL tool.

## Query contract

`RetrievalRequest` requires a bank, product, natural-language query, and at least one
tariff field. Supported fields cover amount, term, nominal/effective rates,
application/disbursement/service fees, collateral, and salary-customer privileges.
The service deterministically expands each field with Armenian and English search
terms. The enriched text is embedded with Gemini's configured embedding model using
the `RETRIEVAL_QUERY` task, paired with the store's `RETRIEVAL_DOCUMENT` vectors.

Both lexical and vector SQL branches require exact bank and product matches and only
consider active documents and chunks. The final select repeats those predicates as a
defense-in-depth guard. Callers cannot request an unscoped search.

## Hybrid ranking

PostgreSQL returns the union of the best lexical and vector candidates:

- lexical score: `ts_rank_cd / (ts_rank_cd + 1)`, bounded to `[0, 1]`;
- vector score: cosine similarity `1 - cosine_distance`, bounded to `[0, 1]`;
- candidate pool: `max(20, top_k * 4)`, capped at 200 per branch.

The service applies weighted reciprocal-rank fusion with lexical weight `0.45`,
vector weight `0.55`, and `k = 60`. It normalizes that value against the theoretical
rank-one maximum. Absolute relevance is the same weighted combination of the two
normalized source scores. The final score is:

```text
0.70 * weighted_relevance + 0.30 * normalized_weighted_rrf
```

The absolute-score term prevents a merely first-ranked but irrelevant vector from
passing solely because it leads a weak candidate set. Results below
`RETRIEVAL_MIN_SCORE` are rejected. Ties are stable: final score, vector score,
lexical score, then chunk ID.

## Deduplication and result contract

After thresholding, chunks from the same document are overlap-deduplicated in rank
order using a Unicode token overlap coefficient of `0.85`. This removes ingestion
overlap while retaining similarly worded evidence from different documents. The
first `top_k` surviving chunks are returned.

Every `RetrievalHit` contains chunk content/ID, lexical/vector/final scores, a typed
rank explanation, document version UUID and checksum, source/final URL, page range,
section, language, retrieval time, extraction method, and quality. If no candidate
passes the threshold, the result status is explicitly `INSUFFICIENT_EVIDENCE` with
an empty hit tuple and reason; downstream extraction must stop rather than infer.

