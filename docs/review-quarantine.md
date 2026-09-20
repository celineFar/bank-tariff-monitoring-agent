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
corresponding terminal publication state. Approval alone does not activate documents;
the later deterministic decision service will revalidate and atomically activate the
snapshot, change set, and eligible documents.

Reviewer choices and native ADK pause/resume are added in the later workflow phases. The
ordinary conversational agent never receives a review-decision tool.
