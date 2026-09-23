# Deliverable 10 — Tariff change detection across two monitoring runs

**PASS — 5/5 criteria**

## Steps

1. Monitoring run 1 accepted a snapshot with a 10% minimum nominal rate (snapshot 7dd430a2).
2. Monitoring run 2 accepted a snapshot with an 11% minimum nominal rate (snapshot b98c11fc).
3. Deterministic comparison of the two canonical payloads found 1 changed field(s).
4.     interest_rate: {"status":"found","value":[{"conditions":[{"dimension":"currency","operator":null,"value":"AMD"}],"value":{"basis":"annual","formula":null,"max":"12","min":"10","rate_type":"fixed"}},{"conditions":[{"dimension":"currency","operator":null,"value":"USD"}],"value":{"basis":"annual","formula":null,"max":"13","min":"10","rate_type":"fixed"}}]} -> {"status":"found","value":[{"conditions":[{"dimension":"currency","operator":null,"value":"AMD"}],"value":{"basis":"annual","formula":null,"max":"12","min":"11","rate_type":"fixed"}},{"conditions":[{"dimension":"currency","operator":null,"value":"USD"}],"value":{"basis":"annual","formula":null,"max":"13","min":"10","rate_type":"fixed"}}]}
5. Persisted the accepted change set for audit and history reads.
6. Reprojected the offering so history can cite old and new values.
7. History query returned status=answered with 1 accepted change set(s).

## Success criteria

| | Criterion | Expected | Observed |
| --- | --- | --- | --- |
| PASS | a real change is detected | the rate change between the two accepted runs is reported | changed fields = ['interest_rate'] |
| PASS | only meaningful fields change | unchanged fields are not reported as changes | 1 field(s) reported changed |
| PASS | no false alert on formatting | two snapshots with the same disclosed values report no change | 0 changes between two equal-value snapshots |
| PASS | history is answerable | a history question returns the accepted change set | status=answered, operation=history |
| PASS | old and new values are both cited | each reported change carries previous and current source evidence | 1 change item(s) with both-sided evidence |
