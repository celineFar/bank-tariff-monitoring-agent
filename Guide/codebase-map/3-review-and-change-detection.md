# 3 · Snapshots, change detection, human review

[← Guide](README.md) · Deep dives: [snapshot-lifecycle.md](../../docs/snapshot-lifecycle.md), [review-quarantine.md](../../docs/review-quarantine.md), [native-hitl-review.md](../../docs/native-hitl-review.md), [run-lifecycle.md](../../docs/run-lifecycle.md)

Most of the logic is in one file: [snapshot_lifecycle.py](../../app/services/snapshot_lifecycle.py).

## Snapshot: accept or send to review

| What | Where |
|---|---|
| Build the snapshot from the extraction result | [build_snapshot_attempt](../../app/services/snapshot_lifecycle.py#L107) |
| Canonical JSON used for hashing and comparing | [canonical_tariff_payload](../../app/services/snapshot_lifecycle.py#L83), [canonical_sha256](../../app/services/snapshot_lifecycle.py#L97) |
| Accepted without review? | [extraction_is_acceptable](../../app/services/snapshot_lifecycle.py#L189) |
| Fails instead of review (nothing a person could answer) | [non_reviewable_extraction_failure](../../app/services/snapshot_lifecycle.py#L223) |
| A linked PDF failed and fields vanished → fail, don't record "withdrawn" | [check in refresh](../../app/services/monitoring_pipeline.py#L425), [_fields_lost](../../app/services/monitoring_pipeline.py#L905) |
| Signals → `ReviewTask` rows | [_review_tasks](../../app/services/monitoring_pipeline.py#L922) |
| Statuses | [SnapshotStatus](../../app/domain/monitoring.py#L58), model [SnapshotAttempt](../../app/domain/monitoring.py#L311) |

## When a human review is triggered

All signals come from [detect_review_signals](../../app/services/snapshot_lifecycle.py#L237). Reasons are listed in [ReviewReason](../../app/domain/review.py#L17).

| Reason | Trigger | Code |
|---|---|---|
| `ocr_evidence` | a found value cites OCR text | [L262](../../app/services/snapshot_lifecycle.py#L262) |
| `source_applicability` | a found value cites non-official evidence ([_OFFICIAL_EVIDENCE_AUTHORITIES](../../app/services/snapshot_lifecycle.py#L37)), or the field is `AMBIGUOUS` | [L291](../../app/services/snapshot_lifecycle.py#L291), [L319](../../app/services/snapshot_lifecycle.py#L319) |
| `official_source_conflict` | field status `CONFLICTING` (two official sources disagree) | [L305](../../app/services/snapshot_lifecycle.py#L305), candidates [_conflict_candidates](../../app/services/snapshot_lifecycle.py#L536) |
| `missing_required_field` | a required field was not found | [L327](../../app/services/snapshot_lifecycle.py#L327), list [_REQUIRED_TARIFF_FIELDS](../../app/services/snapshot_lifecycle.py#L46) |
| `extraction_invalid` | Gemini's value failed validation | [_review_item_signal](../../app/services/snapshot_lifecycle.py#L366) |
| `large_rate_change` | rate moved ≥ `HITL_LARGE_RATE_CHANGE_PERCENTAGE_POINTS` (3) vs last accepted | [detect_large_rate_changes](../../app/services/snapshot_lifecycle.py#L497), threshold [HitlSettings](../../app/config/models.py#L412) |

The evidence shown for each review is chosen when the signal is raised:
[field_evidence_set](../../app/services/review_evidence.py#L123), [cited_evidence_set](../../app/services/review_evidence.py#L88), limits [UNITS_PER_REVIEW / PASSAGE_MAX_CHARS / MODEL_SEED_PASSAGES](../../app/services/review_evidence.py#L34).

## Resolving a review

| What | Where |
|---|---|
| Allowed decisions + guidance per reason | [review_policy](../../app/services/review_resolution.py#L608) |
| Decision types (approve, reject, override, select candidate) | [ReviewDecisionType](../../app/domain/review.py#L74) |
| What the pause carries to the CLI | [build_review_view](../../app/services/review_resolution.py#L574), [ReviewPromptView](../../app/domain/review.py#L176) |
| Validate the reviewer's reply | [ReviewResolutionService.validate](../../app/services/review_resolution.py#L143) |
| Apply it | [ReviewResolutionService.apply](../../app/services/review_resolution.py#L182) → [ReviewDecisionService.apply](../../app/services/review_decisions.py#L57) |
| Close the run when nothing is pending | [ReviewResolutionService.complete_run](../../app/services/review_resolution.py#L256) |
| Admin "reject all pending" | [reject_all_pending](../../app/services/review_resolution.py#L353) (route `POST /api/v1/reviews/abort-pending`) |
| Remember a decision so the same result isn't asked again | [PostgresReviewDecisionMemory](../../app/repositories/review_memory.py#L99), [result_fingerprint](../../app/repositories/review_memory.py#L26) |
| Older pending reviews superseded by a newer snapshot | [supersede_reviews_older_than](../../app/repositories/review_supersession.py#L21) |
| Review DB rows (create, approve + accept snapshot, reject) | [PostgresReviewRepository](../../app/repositories/reviews.py#L76), [approve_with_snapshot](../../app/repositories/reviews.py#L301), [reject](../../app/repositories/reviews.py#L425) |

**Reviewer input format** (e.g. `15-21%`, `up to AMD 15 million`) is parsed deterministically, with no model involved:
[review_field_format](../../app/services/review_input.py#L86), [parse_review_field_text](../../app/services/review_input.py#L91), per-field table [_FORMATS](../../app/services/review_input.py#L488).
The CLI side: [_show_review](../../app/cli.py#L666), [_ask_review_decision](../../app/cli.py#L793), full-evidence display [ReviewDisplayService](../../app/services/review_evidence.py#L477).

## Change detection

| What | Where |
|---|---|
| Compare accepted snapshots, field by field | [compare_accepted_snapshots](../../app/services/snapshot_lifecycle.py#L674) |
| Which fields are compared (provenance keys stripped) | [tariff_fields](../../app/services/snapshot_lifecycle.py#L657), [_PROVENANCE_KEYS](../../app/services/snapshot_lifecycle.py#L64) |
| Canonical form (so formatting differences don't count) | [_canonicalize](../../app/services/snapshot_lifecycle.py#L724), [_stable_json](../../app/services/snapshot_lifecycle.py#L741) |
| How a changed value is displayed | [_display](../../app/services/snapshot_lifecycle.py#L751) |
| Evidence changed but values didn't | [evidence_changed](../../app/services/snapshot_lifecycle.py#L715) |
| Models | [SnapshotChange](../../app/domain/monitoring.py#L342), [SnapshotChangeSet](../../app/domain/monitoring.py#L352) |
| Stored | [_insert_changes](../../app/repositories/monitoring.py#L1720) (`tariff_changes` table) |
| Read back (history tool / API) | [TariffHistoryService](../../app/services/tariff_queries.py#L117) |

Numbers are normalized before comparison, e.g. "10 000 000" becomes 10000000. That happens when values are parsed into typed models ([MoneyRange](../../app/domain/semantic_extraction.py#L162), [normalize_extraction_field_value](../../app/services/semantic_extraction.py#L1341)), so the comparison only sees typed values.

[compare_snapshots](../../app/domain/change_detection.py#L4) is an older, simpler comparer. Only [test_change_detection.py](../../tests/unit/test_change_detection.py) uses it. The pipeline does not.

## Publication (one transaction per offering)

| What | Where |
|---|---|
| Publish documents, manifest, snapshot, changes, projection, status | [PostgresOfferingPublicationRepository.publish](../../app/repositories/monitoring.py#L1388) |
| Per-offering advisory lock | [lock_offering_publication](../../app/repositories/knowledge_publication.py#L286) |
| Evidence document versions (immutable) | [store_document_version](../../app/repositories/knowledge_publication.py#L38), [activate_snapshot_set](../../app/repositories/knowledge_publication.py#L182) |
| Typed facts written for answering | [publish_structured_projection](../../app/repositories/structured_projection.py#L19) |
| Last accepted snapshot (the "previous") | [PostgresSnapshotRepository.get_latest_accepted](../../app/repositories/monitoring.py#L1167) |

## Run lifecycle

`queued → running → awaiting_review → succeeded | partial_success | failed` ([RunStatus](../../app/domain/monitoring.py#L33)).
Queue and claims: [PostgresRunRepository.submit](../../app/repositories/monitoring.py#L226), [claim](../../app/repositories/monitoring.py#L394), [claim_next](../../app/repositories/monitoring.py#L352), [heartbeat](../../app/repositories/monitoring.py#L588), [recover_abandoned](../../app/repositories/monitoring.py#L519).
