# Review and Candidate Quarantine

Review records are durable business state. `ReviewTask` binds one review reason and issue
scope to a run, offering execution, candidate snapshot, bounded candidate choices, and
captured evidence references: the review's evidence set (`evidence.set`, units of
evidence IDs decided when the signal was raised), never a copy of the evidence. Rows
written before migration `022` carry a copy (`evidence.items`) and still work. The repository creates tasks idempotently, serializes
decisions with row locks, stores ADK workflow correlation separately, and supports
approved, rejected, superseded, and failed terminal states.

A newer review for the same product, offering, and issue scope deterministically
supersedes the older pending review from an earlier snapshot. Reviews of the same field
with different reasons in one snapshot (an OCR reading that is also a large rate change)
are siblings and both stay pending (migration `022`); each decision removes only its own
signal. Repeated creation and repeated identical decisions
are idempotent; a conflicting late decision is rejected.

Documents published with a `candidate` or `review_required` snapshot are stored as
text only (no embedding is paid for content a reviewer may reject), inactive, with
`publication_state=pending_review`, and linked to the snapshot (`snapshot_documents`).
Existing accepted documents stay active and are never rewritten: the same source bytes
projected into other chunks are another version. A rejected, failed, or superseded
review deletes the snapshot's never-published versions that no other snapshot names.
The deterministic decision service validates native ADK input against the field schema
and captured evidence. Once every review for a snapshot is approved, the repository
atomically activates the snapshot, its change set, its structured projection and its
whole document set, which replaces the offering's evidence documents. A rejection
preserves the preceding accepted publication.

An accepted publication supersedes pending reviews of the offering's older snapshots
(`review.superseded`, reason `newer_accepted_snapshot`): approving one would roll the
offering back. An approval that races such a publication is refused with
`StaleReviewError` and the review is superseded (`review.superseded_stale`).

Reviewer choices enter through native ADK pause/resume: the monitoring node pauses the
chat invocation on each pending review and applies the answer through
`ReviewResolutionService` when the invocation resumes. Runs the scheduler or the API
started are reviewed from the CLI the same way. `POST /api/v1/reviews/abort-pending` is
a protected admin operation that rejects every pending review and closes those runs. The
model never receives a raw database or review repository tool, and never relays a
decision. See `docs/native-hitl-review.md`.

## Deterministic routing

Snapshot validation blocks unresolved `ambiguous` and `conflicting` fields. Conflicting
web/PDF citations are preserved as distinct candidates with their evidence references,
source types, quoted values, and conditions. A required field the extraction did not
state (or left out of its answer) routes to `missing_required_field`, showing the
passages its extraction call read. The reviewer can enter the value with its passage,
confirm the sources do not state it (`confirm_not_stated`, with a reason), or reject the
candidate. A value Gemini proposed that failed a check, for any
field, routes to `extraction_invalid` with that value as the candidate and the failed
checks named. A model execution failure without a valid response fails the offering
without creating a human task. A `found` empty or inapplicable value
with official evidence is distinct from unsupported `not_stated` output.

Nominal and effective rate endpoints are compared entry by entry, and an absolute change
of at least the configured three percentage points quarantines the candidate. Multiple
agreeing official citations remain attached to the accepted value and do not create a
review signal.

The check runs on **every** candidate that has a previous accepted snapshot, including
one that already needs a field review. It used to run only on otherwise-clean
candidates, so a reviewer answering an unrelated field review could activate a snapshot
whose rate had jumped without ever being shown the jump. Each signal is its own review
and activation waits for all of them, so the rate change is now always put in front of
someone.

Entries are paired by what they describe, not by where they sit in the sorted list. The
extractor rewords conditions between runs over the same page, and even renames their
dimensions (`card_type` one run, `card_tier` the next), which moves entries to different
positions. Pairing by position compared one card tier's rate with another's and raised
large changes on rates that had not moved. An entry's identity is therefore the set of
words in its condition values; it pairs with its mutual best match above a similarity
floor, which sits well inside the gap measured on real Overdraft snapshots (correct pairs
0.60–0.88, wrong pairs 0.00–0.15). An entry with no counterpart is a structural change,
reported by change detection rather than as a rate jump.

## OCR evidence

A `found` value whose supporting citation resolves to a block produced by the OCR
fallback raises an `ocr_evidence` signal and quarantines the candidate. This is the
§5.10 scenario "OCR or extraction quality is insufficient".

The reasoning is that a value read off a page image is not the same evidence as one
read from a text layer, even after clearing the confidence floor: OCR can turn `13.5`
into `135` without any of the deterministic checks noticing, because both are
well-formed rates. The deterministic stages cannot tell those apart, so a human does.

Provenance survives to the reviewer because the evidence `source_item_id` carries an
`:ocr:` marker — evidence records keep the item id, not the extraction method, so the
id is what transports it. The reviewer is shown the quoted text and the PDF page it
came from, and may approve, reject all candidates, or supply an evidence-linked
structured override. Approval is permitted here, unlike most reasons, because the
reviewer is confirming a reading against a page they were shown rather than inventing
a value.
