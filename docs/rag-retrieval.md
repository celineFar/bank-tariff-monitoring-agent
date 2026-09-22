# RAG retrieval

The retrieval component returns a small, typed, evidence-bearing chunk set for
structured tariff extraction. It is a deterministic application service and is not
exposed to Gemini as a database or SQL tool.

This document describes the **legacy chunk retrieval** used by monitoring and by
the rollback answer path (`TARIFF_ANSWER_READ_MODEL=legacy`). Ordinary questions
are answered from the structured read model; see
[Structured retrieval units](#structured-retrieval-units) below and
`docs/tariff-query-services.md`.

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



## Structured retrieval units

Ordinary tariff questions no longer rank source chunks. `retrieval_units` holds
deterministic, versioned text rendered from accepted typed facts, and each unit
must name the facts and verified citations that support it. Units with no
verified locator can aid internal routing but never reach Gemini's evidence
packet or an answer citation.

**Renderer version 2** writes a human field label next to the canonical path, so
a field-detail line reads `minimum nominal interest rate (rate.nominal.minimum):
14 AMD (percent)`. The labels come from the checked-in bilingual
`FIELD_LABELS` registry in `app/domain/structured_tariffs.py`, which must cover
every `FieldPath`. They are our own canonical vocabulary, not a translation of
source wording; the Armenian label is written into the unit's weight-`B` search
text only, never into the text handed to the model. Version 1 rendered the bare
path, which full-text search could not match against natural wording. Publishing
re-renders any unit still at a lower renderer version and clears its stale
embedding so the vector is recomputed for the new text.

### Lexical baseline

The lexical branch is weighted PostgreSQL full-text search over the `simple`
configuration: `setweight` puts identity text at `A`, aliases and the Armenian
field label at `B`, and clean detail text at `C`, ranked with `ts_rank_cd` inside
the authorized offering scope.

`simple` has no stopword list and `websearch_to_tsquery` joins bare terms with
AND, so passing a question through verbatim required every filler word to appear
in a unit and matched nothing. `lexical_search_terms` (version
`simple-or-v1`) therefore builds the query deterministically: casefold, strip the
Armenian intra-word question, exclamation, and emphasis marks so `որքա՞ն`
normalizes to the stopword `որքան`, split on non-word characters, drop a
checked-in bilingual function-word list and single characters, keep the first
twelve distinct terms, and join them with `or`. `ts_rank_cd` then supplies
precision, and the service still admits only units whose facts and evidence are
within the answered scope.

### Vector supplement

Vector search runs only when lexical recall is sparse (fewer than four hits),
uses the same hard scope, active-state, and evidence predicates, and is fused
with the lexical ranking as `rrf-v1-k60-lex1-vector0.7`. Over the 25 target
questions it fired on 1 of 15 single-offering questions, so those fusion weights
have not been tuned; see `tests/eval/RESULTS.md`.

### Tracing

`uv run python -m scripts.trace_structured_answer "<question>" --no-vector`
prints resolution, the issued authorization plan, the typed facts with their
verified citations, the admitted explanatory units, and the ranking version,
without any model call. `scripts/trace_rag_answer.py` still traces the legacy
chunk path for rollback comparison.
