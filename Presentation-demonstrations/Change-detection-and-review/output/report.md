# Tariff change detection and human review

Generated 2026-09-28 08:34 UTC by `change_demo.py` against the demonstration stack (Compose project `tariff-demo`). Offering: `overdraft`, fetched from the demonstration mirror `https://tariff-mirror.demo/overdraft`.

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

Submitted run `7e428b42` through `POST /api/v1/runs`.

## Caught: what the system did with the change

Candidate snapshot `6bdc2400`: status `review_required`, interest rates **none**.
| Review | Field | Status | What the reviewer sees |
|---|---|---|---|
| `official_source_conflict` | `interest_rate` | pending | - |

Meanwhile `GET /tariffs/current` still serves snapshot `5fdc76b4` with **21%, 20%, 15-21%** (pending newer review: True). Changes recorded so far: 0.

## Checks

|  | Check | Observed |
|---|---|---|
| PASS | only the nominal rates were edited | 3 changed lines |
| PASS | the run stopped for review instead of publishing | status `awaiting_review` |
| FAIL | a large rate change was flagged for review | none |
| PASS | the candidate was not published while pending | snapshot `review_required`, API serves `5fdc76b4` |
| PASS | the normal worker is back | mirror stopped |

Model spend for the monitoring run: $0.0799.
RESULT: FAIL
