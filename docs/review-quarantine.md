# Review and Candidate Quarantine

Review records are durable business state. `ReviewTask` binds one review reason and issue
scope to a run, offering execution, candidate snapshot, bounded candidate choices, and
captured evidence references. The repository creates tasks idempotently, serializes
decisions with row locks, stores ADK workflow correlation separately, and supports
approved, rejected, superseded, and failed terminal states.

A newer review for the same product, offering, and issue scope deterministically
supersedes the older pending review. Repeated creation and repeated identical decisions
are idempotent; a conflicting late decision is rejected.

Documents published with a `candidate` or `review_required` snapshot are inserted with
`publication_state=pending_review`, with inactive chunks. Existing accepted documents stay
active. Rejected, failed, or superseded review documents remain inactive and receive the
corresponding terminal publication state. The deterministic decision service validates
native ADK input against the field schema and captured evidence. Once every review for a
snapshot is approved, the repository atomically activates the snapshot, change set, and
eligible documents. A rejection preserves the preceding accepted publication.

Reviewer choices enter only through native ADK pause/resume in ADK Web. Project review
HTTP routes are read-only, and the ordinary conversational agent never receives a
review-decision tool. See `docs/native-hitl-review.md`.

## Deterministic routing

Snapshot validation blocks unresolved `ambiguous` and `conflicting` fields. Conflicting
web/PDF citations are preserved as distinct candidates with their evidence references,
source types, quoted values, and conditions. Missing core tariff fields route to review
when captured evidence remains usable; a model execution failure without a valid response
fails the offering without creating a human task. A `found` empty or inapplicable value
with official evidence is distinct from unsupported `not_stated` output.

Nominal and effective rate endpoints are compared by their canonical conditional paths.
An absolute change of at least the configured three percentage points quarantines the
otherwise valid candidate. Multiple agreeing official citations remain attached to the
accepted value and do not create a review signal.
