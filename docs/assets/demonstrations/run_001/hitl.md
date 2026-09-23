# Deliverable 12 — Human-in-the-loop: a large rate change is quarantined until approved

**PASS — 6/6 criteria**

## Steps

1. An accepted snapshot publishes a 12% minimum nominal rate (snapshot 64438e4f).
2. Monitoring run 2 extracted an AMD nominal rate of 19-22%, up from 12-15%. Deterministic change detection raised 1 large-rate-change signal(s) against the 3pp threshold.
3.     signal: {'reason': 'large_rate_change', 'issue_scope': 'interest_rate', 'field': 'interest_rate', 'previous': '12', 'current': '19', 'absolute_percentage_point_change': '7'}
4. The candidate was stored as review_required, not accepted (snapshot 3f8dcb15).
5. A review task was opened (534a6477, reason=large_rate_change) carrying the previous value, the candidate value, the source URL, and the evidence reference the reviewer needs.
6. While the review is pending, the same question still answers from the older accepted snapshot: AMD minimum nominal rate ['12']%, not the quarantined 19%.
7. A reviewer approved the candidate: status=approved, reviewer=reviewer@example.test.

## Success criteria

| | Criterion | Expected | Observed |
| --- | --- | --- | --- |
| PASS | large change is detected deterministically | a jump beyond the threshold raises a signal without asking the model | 1 signal(s) at a 3pp threshold |
| PASS | candidate is quarantined | the new snapshot is review_required, never auto-accepted | status=review_required, accepted_at=None |
| PASS | reviewer receives source evidence | the task carries candidate value, previous value, and an evidence link | 1 candidate(s), evidence keys ['candidate', 'previous', 'source_url', 'threshold_percentage_points'] |
| PASS | pending value never leaks | answers during review still show the older accepted 12%, not 19% | answered AMD minimum ['12'] |
| PASS | decision is recorded with its reviewer | approval stores who decided and why | status=approved, reviewer=reviewer@example.test |
| PASS | review queue is cleared | no pending review remains for this scope | 0 pending review(s) remain |
