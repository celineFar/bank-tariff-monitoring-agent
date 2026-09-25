# Native ADK tariff review

A review is a native ADK pause inside the conversation that needs it. When a
monitoring run finds a value a human must decide, the monitoring node — running
inside the chat's own invocation — yields an ADK `RequestInput`. The invocation
pauses; the CLI shows the evidence and takes the decision; the answer resumes the
*same* invocation, the node applies the decision, and the agent answers the original
question in the same turn.

PostgreSQL owns the review, snapshot, run and audit state. The ADK session owns only
the conversation and its pause. Nothing correlates the two stores: every time the
node runs it re-reads the review state from PostgreSQL. The model never sees
candidate values before they are decided and never relays a decision.

The CLI (`./tariff-chat`) is the review console for every run, including runs the
scheduler or the API started. ADK Web (`/dev-ui/`) is a development surface.

## The flow in one conversation

1. A question about a tariff with no accepted snapshot: the agent says monitoring is
   needed and offers it. Only that offer (taken up in the very next turn) or an
   explicit monitoring request authorizes a run — see
   [agent-and-tool-architecture.md](agent-and-tool-architecture.md) §3 on the
   per-turn grants.
2. On "yes", the agent calls `run_tariff_monitoring`. The tool runs the monitoring
   node in the same invocation. The node submits the run, claims it, and executes the
   pipeline in this process; each stage's start and end streams to the terminal as a
   partial ADK event (shown, never persisted, never in the model's context).
3. If the pipeline finishes with candidates that need review, the node lists the
   run's pending reviews and yields one `RequestInput` for the first. The invocation
   pauses without calling the model. The CLI renders the review: field, reason,
   candidate values, and the captured passages that mention the field (ranked
   before general context, at most 20; `?` shows every passage).
4. The reviewer types a decision. The CLI validates it locally (a malformed reply is
   re-prompted and never sent) and resumes the invocation. ADK replays the original
   tool call; the node re-runs, finds the answer in `ctx.resume_inputs`, validates it
   against the review and its evidence, and applies it through
   `ReviewResolutionService`. If another review is pending it pauses again; a
   business-level rejection (e.g. an override citing evidence outside the review) is
   re-asked with the reason, and nothing is written.
5. With no review pending the node closes the run (`succeeded`, `partial_success` or
   `failed`), answers the original question from accepted facts, and returns. The
   model sees one call and one result and writes the reply.

The pipeline runs once. Re-running the node on each resume costs one PostgreSQL read
per review, not another acquisition or extraction.

## Reviews from runs started elsewhere

The daily scheduler and `POST /api/v1/runs` are executed by the worker, which has no
conversation. When such a run pauses for review it simply stays `awaiting_review`.
The next time anyone opens the CLI, `resolve_request` reports the pending count and
the agent mentions it; "review them" calls `review_pending_candidates`, which runs
the same node in review-only mode (no submit, no claim) through the same pause
and resume.

## Interactive CLI

```bash
./tariff-chat                    # the "default" conversation
./tariff-chat --session pricing  # a named conversation
./tariff-chat --new              # a new conversation named after the current time
./tariff-chat --verbose          # also show tool calls and run ids
```

Conversations are names, not UUIDs. Closing the terminal mid-review loses nothing:
the pause is in the conversation, and the next start prints "Continuing the review
of …" and asks again. Ctrl-C cancels the running turn: a run in progress is marked
`failed` with `run.cancelled` and the turn is rewound; Ctrl-C at a review prompt
postpones the review (it stays pending and reachable with "review them"). If the CLI
process dies mid-run, the next start marks that process's run `run.interrupted` and
says so in one sentence; the worker's lease recovery is the backstop.

A term review accepts `Indefinite term`, `Indefinite term (until requested back)`,
`12 months` or `12-24 months`; the short indefinite form is accepted only when a
captured passage states the "until requested back" end condition. Every field states
its accepted entry format before the reviewer types; JSON remains available for
structured overrides.

## Decision shape

The CLI answers the pause with the `ReviewDecisionInput` shape (the `RequestInput`
response schema). It is deliberately permissive — only field types are checked when
ADK resumes, because a reply that fails schema validation at that point can never be
retried — and every business rule is applied by the node, which re-asks instead of
failing.

```json
{"decision_type": "select_candidate", "candidate_id": "candidate-1"}
```

```json
{
  "decision_type": "override",
  "override_value": "12.5% fixed",
  "reason": "The captured current-period table explicitly applies to this offering.",
  "evidence_reference": "ev_0123456789abcdef01234567"
}
```

`approve` confirms a large rate change or an OCR reading; `reject_all` rejects the
candidate snapshot and supersedes the run's other pending reviews. The reviewer
recorded on the review is the CLI's `--user` (default `cli-user`).

## Operations

- `GET /api/v1/reviews[?run_id=]` and `GET /api/v1/reviews/{id}` are read-only
  diagnostics. `POST /api/v1/runs` returns `reviews_url` for the run.
- `POST /api/v1/reviews/abort-pending` rejects every pending review and closes those
  runs through `ReviewResolutionService.reject_all_pending`. It requires
  `X-Review-Admin-Token` matching `REVIEW_ADMIN_TOKEN` and reports completed and failed
  runs separately. A chat paused on one of those reviews learns on its next resume
  that the run was closed; it does not start a new run.
- On start, the worker completes any run left `awaiting_review` whose reviews are all
  decided (for example after a crash between the last decision and closing the run).
- Do not delete `human_reviews` rows to "unstick" a run; reject it instead.

## Deterministic reviewer demonstration

Render the payload the node puts on a `RequestInput` — without Gemini, PostgreSQL or a
decision:

```bash
uv run python scripts/demonstrate_native_hitl.py --scenario large-change
uv run python scripts/demonstrate_native_hitl.py --scenario source-conflict
```

The first scenario shows an evidence-backed 3.6 percentage-point nominal-rate change
with `approve`, `reject_all` and evidence-linked `override`. The second keeps the
official PDF and webpage fee candidates distinct and permits `select_candidate`,
`reject_all` or `override`. `--scenario all` renders both, positioned 1/2 and 2/2.

`uv run python scripts/probe_adk_runtime.py` re-demonstrates the ADK behaviours this
design relies on (streamed progress, pause without a model call, replay on resume,
cancel and rewind) against the installed google-adk.

## Production gaps

- Reviewer identity is the self-declared `--user`; an authenticated identity source
  and a role-to-review-scope policy are separate work.
- ADK Web runs monitoring in-process in the API worker; it needs authenticated ingress
  before being exposed beyond local development.
- Review creation has durable audit events but no email, chat or paging adapter;
  pending reviews are discovered when someone opens the CLI (which says so) or through
  the review reads.
- No production deployment has been performed.
