# IXS05: a review older than an accepted snapshot (IX4)

**Checks.**
1. An accepted publication supersedes pending reviews of older snapshots of the
   offering.
2. A review raised for an older snapshot after a newer one was accepted (a race)
   cannot be approved.

**Run.** `test_ix4_accepted_publication_supersedes_older_pending_reviews`,
`test_ix4_approval_is_refused_when_a_newer_snapshot_was_accepted`.

**Pass when.** (1) the older review is `superseded`; (2) approval raises
`ReviewConflictError("... newer accepted snapshot ...")` and the newer documents stay
active.

**Result.** _Filled in Phase 6._
