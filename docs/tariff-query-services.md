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

The same typed result is available through the `get_current_tariffs` ADK tool and
`GET /api/v1/tariffs/current`.

## Accepted history and changes

`TariffHistoryService` reads only accepted snapshots and persisted accepted change sets.
“What changed?” defaults to a sixty-day window. With no change in that window it reports
one of `first_observation`, `unchanged_in_window`, or `unavailable`, and includes the most
recent older change timestamp when one exists. “Show history” defaults to thirty days.
Explicit date bounds and result limits remain bounded by configuration.

The same typed result is available through the `get_tariff_history` ADK tool and
`GET /api/v1/tariffs/history`.

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
typed facts. It has four deterministic branches — `single`, `compare`,
`family_rank`, and `history` — and performs all filtering, alignment, ordering,
and abstention itself; Gemini never does the arithmetic.

Scope comes from a per-turn `ResolutionPlan`, which is an authorization boundary,
not routing metadata. The plan carries session and turn identity, the normalized
question hash, the resolved family and offering set, the permitted operation and
canonical fields, any currency condition, and a 30-minute validity window. A plan
that is absent, replayed, stale, cross-session, cross-family, or widened is
rejected before any repository call. ADK stores the plan in server-held session
state; the typed HTTP route builds an equivalent plan from its own validated
product and offering scope through `issue_typed_resolution_plan`.

A ranking abstains rather than naming a winner when the candidate values differ
in currency, unit, rate basis, or fee scope — a percentage fee is never ranked
against a fixed amount. A comparison reports each field's comparability with a
reason. Accepted history returns old and new values only when both carry verified
source evidence.

### Which read model answers

`TARIFF_ANSWER_READ_MODEL` selects the read model for every ordinary question and
is the reversible cutover switch:

- `structured` (default): the ADK `answer_tariff_query` tool, the
  post-monitoring answer, and `POST /api/v1/questions` all read accepted typed
  facts. The HTTP route returns fact-evidence citations carrying the evidence ID,
  exact quote, and locator.
- `legacy`: the same three surfaces fall back to `RagAnswerService` over chunk
  retrieval, within the same authorized scope, with no code change.

`POST /api/v1/tariffs/query` always uses the structured service and returns the
full typed result.
