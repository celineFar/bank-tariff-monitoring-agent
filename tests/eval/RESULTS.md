# Agent evaluation baseline

Recorded 2026-09-21 with `agents-cli` 1.6.1, Google ADK 2.9.2, agent model
`gemini-3.7-flash`, judge model `gemini-3.7-flash`, and temperature zero for the
judge. Generated traces and HTML/JSON result artifacts stay under ignored
`artifacts/`; this file records the reviewable aggregate.

Acceptance bar: every case must grade at least 4/5 and the suite mean must be at
least 4.5/5. A fabricated tariff/evidence value, an unauthorized monitoring
start, a wrong canonical offering, or publication of quarantined data caps a
case at 1/5.

| Suite | Cases | Valid | Mean | Minimum | Result |
|---|---:|---:|---:|---:|---|
| Core bilingual clarification/current-data | 2 | 2 | 5.00 | 5.00 | pass |
| Expanded baseline before resolver fixes | 22 | 22 | 3.64 | 1.00 | fail |
| Expanded candidate after resolver fixes | 22 | 22 | 5.00 | 5.00 | pass |

The expanded suite covers seven directly seedable intents, all thirteen
offerings, English/Armenian/mixed/transliterated/typo inputs, ambiguity,
stale accepted data, a newer quarantined review candidate, accepted history,
unsupported advice, and prompt/tool-routing safety. `CLARIFICATION_RESPONSE`
requires session state created by a preceding turn. ADK 2.9.2 rejects state
actions in session-initialization events, so `agents-cli eval generate` cannot
seed that eighth intent. Its real two-turn state transition remains covered by
`test_clarification_state_resolves_natural_follow_up_and_clears_pending` and
`test_resolve_request_tool_persists_only_session_clarification_state` rather
than by a fabricated stateless eval prompt.

The first live pass exposed an ADK integration defect: `ToolContext.state` does
not implement `pop()`. After the state-clearing fix, both core inference traces
completed. Expanded failure analysis then identified missing plural/status
phrases and Armenian suffix-aware matching. `agents-cli eval compare` confirmed
the mean improved from 3.64 to 5.00 with no case regression.

The local custom metric uses the Gemini API key. In this environment the
Agent Platform SDK also initialized a GCS client before running a local metric,
contrary to its documented no-GCP path; an ephemeral, nonfunctional local ADC
identity was used only to satisfy that constructor. No credential or trace is
committed.
