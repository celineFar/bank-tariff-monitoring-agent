# Snapshot and change lifecycle

Every semantic-extraction attempt is stored. A result becomes `accepted` only when it is
complete and passes deterministic schema/evidence checks, including known evidence IDs and
evidence for every found value. Review-required, conflicting, or invalid attempts remain
candidates and never replace the last accepted snapshot.

Candidate visibility follows the review lifecycle:

- `pending` documents/chunks stay inactive while the prior accepted version remains active;
- `approved` candidates are revalidated and become active only when every review for their
  snapshot is approved in the same publication transaction;
- `rejected` candidates remain inactive and the prior accepted publication is unchanged;
- `superseded` candidates remain inactive when a newer same-scope observation wins the
  locked supersession rule; and
- failed decision or persistence work rolls back without partially activating a candidate.

Comparison uses the preceding accepted snapshot for the same bank, family, and stable
offering. Canonical payloads preserve business values, states, bounds, currencies, units,
and conditions while excluding timestamps, citation ordering, prose formatting, and
evidence locations. The first accepted observation has no field changes. Equal canonical
values with changed evidence create `snapshot.provenance_changed`, not a tariff change.

Current-tariff reads and normal RAG retrieval filter to accepted/active state. A newer
pending review is exposed only as a flag; its candidate values and chunks are not returned.
History and change reads likewise use accepted observations, so rejection and supersession
cannot appear as published tariff history.

Publication is atomic per offering: knowledge versions/chunks, extraction attempt,
snapshot decision, changes, manifest, offering status, and audit event commit together.
Rollback preserves the prior index and accepted snapshot.
