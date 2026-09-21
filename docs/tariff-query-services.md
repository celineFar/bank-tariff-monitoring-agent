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

## Bounded chat wait

`RunWaitService` polls persisted run state outside database transactions. It waits for at
most 120 seconds by default and stops immediately for a terminal status or
`awaiting_review`. For a paused run it waits for the durable review records to be
attached to the ADK interruption, then returns a compact list of required review scopes
and exact relative links to the saved ADK Web session and review records. If review
attachment is still incomplete at the wait deadline, the result marks the handoff as
not ready so the caller can check again. A timeout while monitoring is still running
returns the durable run and its current status; it is not reported as fresh data.
`POST /api/v1/runs` remains asynchronous and does not wait. A chat turn cannot
spontaneously send a later notification after its wait ends; the run ID remains the
lookup key for later status and review checks.
