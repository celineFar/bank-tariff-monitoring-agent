# Retrieval

Ordinary questions are answered from accepted, typed facts
(`docs/tariff-query-services.md`). Retrieval here is the *field finder*: when a
question names no tariff field, it finds which fields the question is about by
searching the active offering's retrieval units. It is a deterministic application
service and is never exposed to Gemini as a database or SQL tool.

The earlier chunk retrieval (hybrid search over `knowledge_chunks` for a RAG answer
path) was removed together with that path; migration `027` dropped its vectors and
search indexes.

## Retrieval units

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
the typed facts with their verified citations.
