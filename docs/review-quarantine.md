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

Reviewer choices enter through native ADK pause/resume. Chat-originated runs pause
the original conversation with `request_input`; API and scheduled runs use their
run-scoped ADK Web session. `POST /api/v1/reviews/abort-pending` is a protected
admin operation that sends `reject_all` through pending workflows. The model
never receives a raw database or review repository tool. See `docs/native-hitl-review.md`.

## Deterministic routing

Snapshot validation blocks unresolved `ambiguous` and `conflicting` fields. Conflicting
web/PDF citations are preserved as distinct candidates with their evidence references,
source types, quoted values, and conditions. Missing core tariff fields route to review
when captured evidence remains usable; a model execution failure without a valid response
fails the offering without creating a human task. A `found` empty or inapplicable value
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
