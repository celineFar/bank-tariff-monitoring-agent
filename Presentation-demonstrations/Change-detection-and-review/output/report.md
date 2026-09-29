# Tariff change detection and human review

Generated 2026-09-29 02:06 UTC by `change_demo.py` against the demonstration stack (Compose project `tariff-demo`). Offering: `overdraft`, fetched from the demonstration mirror `https://tariff-mirror.demo/overdraft`.

## Before: the accepted tariff

Restored checkpoint `change-demo`. `GET /tariffs/current` for overdraft: snapshot `5fdc76b4`, interest rates **21%, 20%, 15-21%**.
Review threshold: a rate change of 3 percentage points or more (`HITL_LARGE_RATE_CHANGE_PERCENTAGE_POINTS`).

## The bank republishes the page

The mirror now serves `mirror/republished/overdraft/index.html`. Compared with the original, exactly these lines differ:
| What | Before | After |
|---|---|---|
| standard cards, nominal rate | `AMD: 21%` | `AMD: 25%` |
| premium cards, nominal rate | `AMD: 20%` | `AMD: 24%` |
| scoring-based band, nominal rate | `15% -21%` | `19% -25%` |

The annual percentage rates, the PDFs and every other byte of the page are unchanged.
Worker fetches the mirror: `200 AMD: 25% AMD: 24%`.

## Monitoring run

Submitted run `c86d701e` through `POST /api/v1/runs`.

## Caught: what the system did with the change

Candidate snapshot `62e6a6ca`: status `review_required`, interest rates **none**.
| Review | Field | Status | What the reviewer sees |
|---|---|---|---|
| `official_source_conflict` | `interest_rate` | pending | - |

Meanwhile `GET /tariffs/current` still serves snapshot `5fdc76b4` with **21%, 20%, 15-21%** (pending newer review: True). Changes recorded so far: 0.

## Human review

| Review | Field | Decision | Reviewer | Decided at |
|---|---|---|---|---|
| `official_source_conflict` | `interest_rate` | `{'reason': 'Reviewer confirmed the value against the selected official passage.', 'candidate_id': None, 'decision_type': 'override', 'override_value': [{'value': {'max': 21, 'min': 1, 'basis': 'annual', 'rate_type': 'unknown'}, 'conditions': []}], 'evidence_reference': 'ev_94f53cd170b87922c908c1cc'}` | cli-user | 2026-09-29T02:12:29 |


## After the decision

Run `c86d701e`: `succeeded`. Candidate snapshot: `accepted`.
Change recorded in `tariff_changes`:
| Field | Previous | Current |
|---|---|---|
| `age_requirements` | {"value": [{"value": {"max_age": 65, "min_age": 18, "measured_at": "at the time … | {"value": [{"value": {"max_age": 65, "min_age": 18, "measured_at": "at the time … |
| `application_channel` | {"value": [{"value": {"channel": "branch", "available": true}, "conditions": []}… | {"value": [{"value": {"channel": "Online (https://customer.ameriabank.am/signin)… |
| `effective_rate` | 23.13, 21.92, 16.06 | 23.13, 21.92, 16.06 |
| `eligibility` | {"value": ["Aged 18-65 years old, provided that the borrower’s age at the time o… | {"value": ["Aged 18-65 years old, provided that the borrower's age at the time o… |
| `fees` | {"value": [{"scope": "product", "amount": "0", "currency": null, "rate_pct": nul… | {"value": [{"scope": "general_loan_service", "amount": "10000", "currency": "AMD… |
| `formal_terms_names` | {"value": ["Information Guide", "Retail Lending Terms and Conditions (Overdrafts… | {"value": ["Information Guide: Overdrafts via Cards not secured with property (u… |
| `interest_rate` | 21, 20, 15 | 21, 1 |
| `linked_account_or_card` | {"value": "card", "status": "found"} | {"value": "debit card", "status": "found"} |
| `loan_amount` | 1e+08, 100000, 1e+07, 300000, 1.5e+07 | 1e+07, 300000, 1e+08, 100000, 1.5e+07 |
| `repayment` | {"value": [{"value": {"method": "Monthly minimum payment (interest + 3% of used … | {"value": [{"value": {"method": "Minimum monthly payment", "description": "3% of… |
| `required_documents` | {"value": [{"value": {"name": "ID", "requirement": "required"}, "conditions": [{… | {"value": [{"value": {"name": "ID", "requirement": "required"}, "conditions": [{… |
| `special_conditions` | {"value": ["If repayment schedule is differentiated or mixed, the applicable int… | {"value": ["Consumers are allowed to cancel the credit agreement at their own di… |

`GET /tariffs/current` now serves snapshot `62e6a6ca` with **1-21%**.
`GET /tariffs/history?kind=what_changed`: `changes_found`.

## Checks

|  | Check | Observed |
|---|---|---|
| PASS | only the nominal rates were edited | 3 changed lines |
| PASS | the run stopped for review instead of publishing | status `awaiting_review` |
| FAIL | a large rate change was flagged for review | none |
| PASS | the candidate was not published while pending | snapshot `review_required`, API serves `5fdc76b4` |
| PASS | the approved change was recorded, with the rate in it | 12 field change(s) |
| PASS | the API serves the new rates | 1-21% |
| PASS | the normal worker is back | mirror stopped |

Model spend for the monitoring run: $0.0016.
RESULT: FAIL
