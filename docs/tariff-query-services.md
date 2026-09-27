# Current Tariff, History, and Run-Wait Services

The read side is deterministic. It never uses retrieval rank or model output to decide
which tariff is current.

## Current tariffs

`CurrentTariffService` reads the latest `accepted` snapshot for each requested configured
offering. The default freshness threshold is seven days:

- `fresh`: accepted no more than seven days ago;
- `stale`: accepted more than seven days ago; the accepted value and timestamp remain
  visible so callers can warn and offer a refresh;
- `missing`: no accepted snapshot exists, so no tariff or evidence is returned.

A newer `candidate` or `review_required` snapshot is represented only by
`pending_newer_review=true`. Its values and evidence are not returned.

`GET /api/v1/tariffs/current` returns the full typed result. The `get_current_tariffs`
ADK tool returns what the model needs to decide on monitoring: per offering, freshness,
`accepted_at`, `age_seconds`, `snapshot_id`, `pending_newer_review` and each field's
status (`found`, `not_stated`, ...), never values or evidence. Values reach the model
only through `answer_tariff_query`, with their citations.

## Accepted history and changes

`TariffHistoryService` reads only accepted snapshots and persisted accepted change sets.
“What changed?” defaults to a sixty-day window. With no change in that window it reports
one of `first_observation`, `unchanged_in_window`, or `unavailable`, and includes the most
recent older change timestamp when one exists. “Show history” defaults to thirty days.
Explicit date bounds and result limits remain bounded by configuration.

`GET /api/v1/tariffs/history` returns the full typed result. The `get_tariff_history`
ADK tool returns the same result without each snapshot's evidence catalog, extraction
record and validation (hundreds of kB per snapshot); values, times and change sets stay.
Each value carries compact citations instead: up to three per field, each with source
URL, section, page and a quote of at most 300 characters, read from the snapshot that
accepted it (`field_citations`). A snapshot gets `citations: {field: [...]}`, and
`TariffHistoryService` fills each change item's `previous_evidence` and
`current_evidence` the same way. A changed value whose non-missing side has no citation
is left out of the payload and listed under `omitted_changes`; no history value reaches
the model uncited.

## Read scope in chat

The ADK adapters take no scope argument. `get_current_tariffs()` and
`get_tariff_history(kind, start_at, end_at, limit)` read the product family and
offerings from the turn's read grant — the `ResolutionPlan` that `resolve_request`
issued — and `limit` is clamped to 1-100 rather than refused. When the resolver named
no family (a broad "what changed recently?"), the grant covers both families. A subset
of a family's offerings is read per offering and merged in the service. See
[agent-and-tool-architecture.md](agent-and-tool-architecture.md) §3.

There is no chat-side wait any more: a chat-initiated monitoring run executes inside
the chat turn and streams its own progress; `get_monitoring_status()` summarises runs
executing elsewhere. `POST /api/v1/runs` remains asynchronous and does not wait.


## Structured tariff queries

`StructuredTariffQueryService` answers ordinary tariff questions from accepted
typed facts. It has five deterministic branches — `single`, `compare`, `overview`,
`family_rank`, and `history` — and performs all filtering, alignment, ordering,
and abstention itself; Gemini never does the arithmetic. The answer is the
evidence-backed facts of the plan's fields. Only when the question named no field
does retrieval run, to find the fields (the *field finder*, see
[rag-retrieval.md](rag-retrieval.md)); with none found, the core fields answer.
`metadata.fields_source` says which (`question`, `retrieval`, `core`).

Scope comes from a per-turn `ResolutionPlan`, which is an authorization boundary,
not routing metadata. The plan carries session and turn identity, the normalized
question hash, the resolved family and offering set, the permitted operation and
canonical fields, any currency condition, and a 30-minute validity window. A plan
that is absent, replayed, stale, cross-session, cross-family, or widened is
rejected before any repository call. The operation, fields, rank and currency are
the request interpreter's proposal, validated and bounded by code
(`issue_read_grant`); nothing is parsed from the question's words. The plan also
holds the standalone question of record, and `answer_tariff_query` answers exactly
that. ADK stores the plan in server-held session state; the typed HTTP route builds
an equivalent plan from its own validated product and offering scope through
`issue_typed_plan`, with the shape from `RequestResolver.shape_for`.

A ranking ranks by group: values are grouped by unit, currency, rate basis and fee
scope, each offering is represented in a group by its best variant whatever that
variant's conditions, and the conditions travel with the value
(`metadata.groups`). A percentage fee is never ranked against a fixed amount, and
AMD and USD rank separately; `metadata.winner` is set only when exactly one group
ranks. When no two offerings share a group the result is `incomparable`, with a
reason naming what differs. An `overview` lists the requested fields for 1–9
offerings side by side (at most six variants per offering and field, 240 facts in
all) with no comparability verdict, and names the offerings without facts. A
comparison reports each field's comparability with a reason. A currency condition
drops only facts that name another currency; a term or repayment method stays.
Accepted history returns each change item with verified evidence for every side
that has a value (an added field has no previous value); an item without it is
left out and listed under `metadata.omitted`.

### Which read model answers

Every ordinary question is answered from accepted typed facts: the ADK
`answer_tariff_query` tool, the post-monitoring answer, and `POST /api/v1/questions`
all go through `TariffAnswerRouter`. The HTTP route returns fact-evidence citations
carrying the evidence ID, exact quote, and locator. (The RAG answer path that
`TARIFF_ANSWER_READ_MODEL=legacy` once restored was removed.)

`POST /api/v1/tariffs/query` always uses the structured service and returns the
full typed result.
