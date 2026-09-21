# Native ADK tariff review

Tariff review uses Google ADK's native durable `request_input` pause/resume contract.
For runs created in a user chat, the root `app` session pauses for each review item in
that same conversation. The worker's `tariff_monitoring_workflow` stays durable in its
run-scoped ADK session; the root chat submits the human's native input to resume it.
PostgreSQL owns the review, snapshot, run, and audit state. The model cannot directly
write any of those records.

For API and scheduled runs, the run-scoped ADK Web session remains the decision UI
because those triggers have no originating user conversation.

- `GET /api/v1/reviews` lists durable review records.
- `GET /api/v1/runs/{run_id}/review-handoff` provides the saved workflow session link.
- `POST /api/v1/reviews/abort-pending` rejects pending reviews through their saved
  ADK workflows. It requires `X-Review-Admin-Token` matching `REVIEW_ADMIN_TOKEN`.
  It reports completed and failed runs separately and leaves failures pending.
  If an original chat is already displaying a native input prompt, that prompt can
  remain on screen until the user returns; a later reply is told the run was
  aborted and cannot publish the candidate.

## Interactive CLI for long monitoring runs

Use `./tariff-chat` on the EC2 host. The CLI prints its ADK session ID.
If the terminal closes, restart with `./tariff-chat --session-id <saved-session-id>`.
The API and worker containers must be running, since the worker owns the actual
monitoring pipeline.

The CLI uses a dedicated `app_cli` ADK session and a long-running start tool. Its
initial tool response contains the durable monitoring run ID. The CLI polls the
PostgreSQL run until it is terminal or awaiting review, then supplies a final
function response with the same ADK invocation and tool-call IDs. No HTTP chat
request stays open for the pipeline's duration, and the 120-second web chat wait
is not used. If ADK asks for review input, the CLI displays the field and
its matching source passages and accepts a plain field value or a numbered
candidate selection. For example, a term review accepts
`Indefinite term (until requested back)` or `12-24 months`; JSON remains
available for advanced structured overrides. The CLI builds the typed decision and evidence reference
before resuming the saved ADK invocation. It can recover the pending tool call
from saved ADK events after a restart. If no root input call remains but the
business run still awaits review, the CLI loads the saved review from PostgreSQL,
uses the same guided prompt, and submits the human decision through the saved
ADK monitoring workflow. This recovery path does not start another monitoring run or require Gemini to display the
review. After approval, the CLI asks the chat agent to answer the original
question from accepted data.

The saved review can hold the whole candidate snapshot's evidence catalog. Before
presenting a review, the workflow ranks passages matching that field and candidate
references ahead of general context, then limits the prompt to 20 passages. The CLI
shows matching passages by default; `?` shows the full prompt context.

If a review decision fails validation, the PostgreSQL review and worker
interruption remain pending. The next request for a review in the same CLI
session discards the uncommitted chat choice and prompts again; the worker
pipeline is not rerun. Do not delete `human_reviews` rows to recover a
paused workflow, because the run, evidence, and ADK correlation must agree.

## Chat review flow

1. A product question first resolves intent and checks accepted snapshot availability.
   If the snapshot is missing, the agent explains that monitoring is needed and asks
   for confirmation. Only an offered scope or an explicit monitoring request can
   authorize submission.
2. On confirmation, the chat tool queues the run and stores its ID in that ADK
   session. The worker acquires and extracts asynchronously. If it is still running
   after the bounded wait, the user returns to the same chat to check again. There
   is no push message after a chat turn ends.
3. When review is ready, the chat shows one field, captured candidate values, official
   URL, page/section, and a bounded evidence excerpt. The root ADK app calls native
   `request_input` and durably pauses the original conversation.
4. The user responds to that input in the same conversation. The tool reads the actual
   ADK function response, checks the review ID and allowed decision against saved
   evidence, then asks for the next field. A rejection ends the review set. After
   all approvals or selections, the tool resumes the saved worker workflow, whose
   deterministic review service revalidates the complete snapshot before publication.
5. The agent answers the original question from the accepted index. If the user
   rejects the candidate or validation still fails, it says no new tariff was activated.

## API and scheduled reviewer flow

1. Submit a typed monitoring run from Swagger with `POST /api/v1/runs`, or let the daily
   scheduler submit it. The HTTP call remains asynchronous and returns `status_url`
   and `review_handoff_url` with the run ID.
2. Read `GET /api/v1/runs/{run_id}`. A reviewable result has status
   `awaiting_review`; its summary contains the durable review IDs. Chat-initiated
   runs include status and saved review-session links immediately. When the bounded
   chat wait observes a pause, its result includes the pending review scopes, a
   direct link to the persisted ADK Web session, and a link to the review records.
   If the wait ends
   while work is still running, use the status link to check later; the chat
   cannot send a later push notification after that turn has ended.
3. Open ADK Web at `/dev-ui/` and select `tariff_monitoring_workflow`. Use the user and
   session identifiers stored on the review record. API-originated runs use
   `monitoring-api` and `monitoring-run-{run_id}`; scheduled runs use
   `monitoring-schedule` and the same run-scoped session pattern.
4. Inspect the native input request. It shows the product family, offering, field/review
   scope, reason, allowed decisions, candidate values, evidence IDs, official source
   URLs, PDF page or section, and bounded captured excerpts.
5. Respond to the exact ADK interrupt. Depending on the reason, choose one captured
   candidate, approve an otherwise valid large change, reject the candidate snapshot,
   or provide a structured override. An override always requires a reason and a
   reference to captured evidence already shown in the request.
6. The workflow reloads the business review, validates that the ADK user/session owns
   the interrupt, validates the value and evidence, and applies the decision. Approval
   activates the revalidated snapshot and quarantined documents in one database
   transaction after every review for that snapshot is approved. Rejection preserves
   the previous accepted snapshot and active documents.
7. Read the run again. It is terminal only after the resumed workflow has applied all
   decisions. The deterministic pause/resume test proves the pipeline executes once;
   resumption does not repeat acquisition or extraction.

## Decision shapes

The response belongs inside the native ADK function response and must target the exact
interrupt and invocation emitted by ADK.

```json
{
  "decisions": [{
    "review_id": "00000000-0000-0000-0000-000000000000",
    "decision": {
      "decision_type": "select_candidate",
      "candidate_id": "ev_0123456789abcdef01234567"
    }
  }]
}
```

```json
{
  "decisions": [{
    "review_id": "00000000-0000-0000-0000-000000000000",
    "decision": {
      "decision_type": "override",
      "override_value": [{
        "value": {"min": "12.5", "max": "12.5", "rate_type": "fixed", "basis": "annual"},
        "conditions": []
      }],
      "reason": "The captured current-period table explicitly applies to this offering.",
      "evidence_reference": "ev_0123456789abcdef01234567"
    }
  }]
}
```

Reviewer identity is taken from the persisted ADK session boundary, never from a
self-asserted reviewer field in the response. Production authentication and reviewer
authorization remain a deployment gap; do not expose ADK Web publicly without an
authenticated ingress.

## Deterministic reviewer demonstration

Render the same bounded request model used by the workflow without starting Gemini,
writing to PostgreSQL, or making a decision:

```bash
uv run python scripts/demonstrate_native_hitl.py --scenario large-change
uv run python scripts/demonstrate_native_hitl.py --scenario source-conflict
```

The first scenario shows an evidence-backed 3.6 percentage-point nominal-rate change and
the `approve`, `reject_all`, and evidence-linked `override` choices. The second keeps the
official PDF and webpage fee candidates distinct and permits `select_candidate`,
`reject_all`, or evidence-linked `override`. `--scenario all` renders both reviews in one
native request. These are reviewer-training fixtures, not an alternate decision path; use
the ADK Web flow above to exercise a real persisted pause and resume.

## Production gaps

- ADK Web currently needs authenticated ingress and a role-to-review-scope authorization
  policy before it can be exposed beyond local development.
- Review creation has durable audit events but no email, chat, or paging notification
  adapter. Reviewers must currently discover pending work through run/review reads or ADK
  Web.
- No production deployment has been performed. Deployment, secret wiring, ingress, and
  reviewer identity integration require a separate approved deployment phase.
