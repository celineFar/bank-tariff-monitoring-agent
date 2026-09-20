# Native ADK tariff review

Tariff review uses Google ADK's native `RequestInput` pause/resume contract. ADK Web is
the only decision interface in this prototype. The project HTTP routes are diagnostic:

- `GET /api/v1/reviews` lists durable business review records;
- `GET /api/v1/reviews/{review_id}` reads one record; and
- no project `POST /reviews/{review_id}/decision` route exists.

## Reviewer flow

1. Submit a typed monitoring run from Swagger with `POST /api/v1/runs`, or let the daily
   scheduler submit it. The HTTP call remains asynchronous.
2. Read `GET /api/v1/runs/{run_id}`. A reviewable result has status
   `awaiting_review`; its summary contains the durable review IDs.
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
