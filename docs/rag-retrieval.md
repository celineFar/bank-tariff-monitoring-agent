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
defense-in-depth guard. Callers cannot request an unscoped search. The chunk predicates
are written exactly as the partial indexes' (`c.is_active`, and
`c.is_active AND c.embedding IS NOT NULL` for vectors), the vector side orders by the
bound query vector (pgvector uses the HNSW index only for a constant), and the search
runs with `hnsw.iterative_scan = relaxed_order`, so offering and product filters
applied after the approximate scan do not starve the result. A chunk still without a
vector is found by the lexical side only.

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

### The field finder

Retrieval units no longer rank an answer: the answer is the accepted facts of the
plan's fields. Retrieval runs only when a question named no field (the request
interpreter left `fields` empty, e.g. "what documents do I need?", "tell me about
the overdraft"). It then ranks the scoped offerings' units against the standalone
question and loads the facts of the field paths of the best field-detail units, at
most three (`metadata.fields_source = retrieval`).

### Lexical branch

Weighted PostgreSQL full-text search over the `simple` configuration: `setweight`
puts identity text at `A`, aliases and the Armenian field label at `B`, and clean
detail text at `C`, ranked with `ts_rank_cd` inside the authorized offering scope.

`simple` has no stopword list and no stemming. `lexical_search_terms` (version
`simple-prefix-v2`) therefore builds a `to_tsquery` deterministically:

1. casefold and strip the Armenian intra-word question, exclamation and emphasis
   marks;
2. split on non-word characters;
3. drop a checked-in bilingual function-word list, single characters, and the
   words of the scoped offering's own names and aliases (they match every one of
   its units);
4. keep the first twelve distinct terms;
5. trim terms of four or more characters to a stem — English plural `-s`, Armenian
   article and case endings — and match them as prefixes (`fee:*` finds "fee" and
   "fees", `տոկոսադրույք:*` finds its inflected forms);
6. join them with `|`.

### Vector branch

When a unit embedder is configured, the field finder also embeds the question (the
only embedding call on the request path) and fuses the vector hits with the lexical
ranking as `rrf-v1-k60-lex1-vector0.7`. Units themselves are embedded by the
worker's sweep (`CombinedEmbeddingSweep`), never while answering a question.

### Tracing

Set `RETRIEVAL_TRACE_LEVEL=steps` to have every stage of every retrieval write
one correlated line to the `tariff.retrieval` logger, in call order:

```text
trace=1f9f step=2  stage=plan.authorized   offerings=['overdraft'] fields=[] conditions={}
trace=1f9f step=3  stage=profiles.loaded   requested=1 active=1 snapshots=['c68e2d4c']
trace=1f9f step=4  stage=lexical.query     version=simple-prefix-v2 terms=2 limit=8
trace=1f9f step=5  stage=lexical.result    hits=8 top=[('0941b09c', 1.6), ...]
trace=1f9f step=6  stage=fusion.ranked     version=rrf-v1-k60-lex1-vector0.7 candidates=8 fields=[...]
trace=1f9f step=7  stage=fields.selected   source=retrieval fields=['document.required']
trace=1f9f step=8  stage=facts.loaded      loaded=6 after_conditions=6 evidence_backed=6 citations=6
trace=1f9f step=9  stage=branch.selected   branch=single
trace=1f9f steps=9 elapsed_ms=41.2 status=answered facts=6 units=0
```

A question that names its fields skips steps 4–6.

`summary` keeps only the closing line, `off` disables it, and `verbose` adds
`lexical.terms` (the derived `tsquery`) and one `unit.content` line per unit the
field finder used. A trace always closes, including on an exception, where the summary
carries `outcome=error` and the error type. `RETRIEVAL_LOG_FILE` routes the
logger to its own rotating file. At `steps` and below, neither the question text
nor any unit text is written; the question stays correlatable through the
`question_sha12` prefix.

`uv run python -m scripts.trace_structured_answer "<question>" --no-vector`
prints the resolution (one interpreter call), the issued authorization plan, and
the typed facts with their verified citations. `scripts/trace_rag_answer.py` still traces the legacy
chunk path for rollback comparison.
