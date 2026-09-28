# Controlled failures

Generated 2026-09-28 07:21 UTC by `failure_demo.py` against the demonstration stack (Compose project `tariff-demo`). Offering: `overdraft`.

## Before: what the demo database holds

Tariff tables (before):
| Table | Rows | Content digest |
|---|---|---|
| tariff_snapshots | 3 | `0aaf712d7faf` |
| tariff_facts | 199 | `b9d2d0cc3087` |
| fact_evidence | 506 | `e02348fce0e8` |
| tariff_changes | 1 | `c4a6c07086ec` |
| snapshot_documents | 12 | `94445ec51a15` |
| human_reviews | 0 | `d41d8cd98f00` |

`GET /tariffs/current` for overdraft: snapshot `479e2bba`, accepted 2026-09-28T07:19:21.789171Z, freshness `fresh`, interest rates 21%, 20%, 15-21%.

## Failure: The bank's site does not answer (timeout)

Artificial part: inside the worker, `ameriabank.am` resolves to 192.0.2.1, an address routed nowhere (`failures/timeout.yml`).
Submitted run `2cf508bb` through `POST /api/v1/runs`.
| Outcome | Value |
|---|---|
| Run status | `failed` after 69s |
| Failed at stage | `acquisition` |
| Failure code | `source.timeout` (expected `source.timeout`) |
| Recorded cause | `HtmlRetrievalError:TIMEOUT` |
| Operator is told | Monitoring stopped because the bank's site did not respond in time. No tariff values were saved; the run can be retried. |
| Model calls | 0 (none), $0.0000 |
| Snapshots written | 0 |
| Changes written | 0 |

Worker log:
```text
2026-09-28T11:22:26.262+04:00 WARNING app.services.monitoring_pipeline: offering failed run_id=2cf508bb-fb2b-4cc5-8eee-adee7b11805d offering_id=overdraft stage=acquisition code=source.timeout reason=TIMEOUT
2026-09-28T11:22:26.270+04:00 INFO __main__: progress run_id=2cf508bb-fb2b-4cc5-8eee-adee7b11805d kind=offering_failed offering_id=overdraft stage=acquisition elapsed_ms=0 failure_code=source.timeout detail=None
2026-09-28T11:22:26.275+04:00 INFO __main__: progress run_id=2cf508bb-fb2b-4cc5-8eee-adee7b11805d kind=run_finished offering_id=None stage=None elapsed_ms=61730 failure_code=source.timeout detail=failed
2026-09-28T11:22:26.275+04:00 INFO __main__: monitoring run completed run_id=2cf508bb-fb2b-4cc5-8eee-adee7b11805d status=failed review_count=0
```


## Failure: The model provider fails (model-failure)

Artificial part: source discovery uses the retired `gemini-2.5-flash-lite`, with no fallback model (`failures/model-failure.yml`).
Submitted run `1ec9d546` through `POST /api/v1/runs`.
| Outcome | Value |
|---|---|
| Run status | `failed` after 24s |
| Failed at stage | `pdf_selection` |
| Failure code | `source.model_failed` (expected `source.model_failed`) |
| Recorded cause | `ClientError:http_404_NOT_FOUND` |
| Operator is told | Monitoring stopped because no configured model was available to read the sources. No tariff values were saved; the run can be retried. |
| Model calls | 1 (gemini-2.5-flash-lite failed), $0.0000 |
| Snapshots written | 0 |
| Changes written | 0 |

Worker log:
```text
2026-09-28T11:23:05.125+04:00 WARNING app.services.monitoring_pipeline: offering failed run_id=1ec9d546-d3b4-4811-84a0-a2115bdc3df0 offering_id=overdraft stage=pdf_selection code=source.model_failed reason=HTTP 404 / NOT_FOUND: This model models/gemini-2.5-flash-lite is no longer available to new us
2026-09-28T11:23:05.146+04:00 INFO __main__: progress run_id=1ec9d546-d3b4-4811-84a0-a2115bdc3df0 kind=offering_failed offering_id=overdraft stage=pdf_selection elapsed_ms=0 failure_code=source.model_failed detail=None
2026-09-28T11:23:05.158+04:00 INFO __main__: progress run_id=1ec9d546-d3b4-4811-84a0-a2115bdc3df0 kind=run_finished offering_id=None stage=None elapsed_ms=18415 failure_code=source.model_failed detail=failed
2026-09-28T11:23:05.158+04:00 INFO __main__: monitoring run completed run_id=1ec9d546-d3b4-4811-84a0-a2115bdc3df0 status=failed review_count=0
```


## Failure: A safety limit refuses the source (size-limit)

Artificial part: the download size cap is lowered from 25 MB to 50 KB (`failures/size-limit.yml`).
Submitted run `7a292ffe` through `POST /api/v1/runs`.
| Outcome | Value |
|---|---|
| Run status | `failed` after 6s |
| Failed at stage | `acquisition` |
| Failure code | `source.size_rejected` (expected `source.size_rejected`) |
| Recorded cause | `HtmlRetrievalError:PAGE_TOO_LARGE` |
| Operator is told | Monitoring stopped because a source was larger than the configured limit. No tariff values were saved; the run can be retried. |
| Model calls | 0 (none), $0.0000 |
| Snapshots written | 0 |
| Changes written | 0 |

Worker log:
```text
2026-09-28T11:23:24.608+04:00 WARNING app.services.monitoring_pipeline: offering failed run_id=7a292ffe-c914-4430-812b-229e179b2766 offering_id=overdraft stage=acquisition code=source.size_rejected reason=PAGE_TOO_LARGE
2026-09-28T11:23:24.614+04:00 INFO __main__: progress run_id=7a292ffe-c914-4430-812b-229e179b2766 kind=offering_failed offering_id=overdraft stage=acquisition elapsed_ms=0 failure_code=source.size_rejected detail=None
2026-09-28T11:23:24.619+04:00 INFO __main__: progress run_id=7a292ffe-c914-4430-812b-229e179b2766 kind=run_finished offering_id=None stage=None elapsed_ms=1189 failure_code=source.size_rejected detail=failed
2026-09-28T11:23:24.620+04:00 INFO __main__: monitoring run completed run_id=7a292ffe-c914-4430-812b-229e179b2766 status=failed review_count=0
```


## After: what the demo database holds

Tariff tables (after):
| Table | Rows | Content digest |
|---|---|---|
| tariff_snapshots | 3 | `0aaf712d7faf` |
| tariff_facts | 199 | `b9d2d0cc3087` |
| fact_evidence | 506 | `e02348fce0e8` |
| tariff_changes | 1 | `c4a6c07086ec` |
| snapshot_documents | 12 | `94445ec51a15` |
| human_reviews | 0 | `d41d8cd98f00` |

`GET /tariffs/current` for overdraft: snapshot `479e2bba`, accepted 2026-09-28T07:19:21.789171Z, freshness `fresh`, interest rates 21%, 20%, 15-21%.

## Was each failure safe?

|  | Check | Observed |
|---|---|---|
| PASS | timeout: the run failed | status `failed` |
| PASS | timeout: failed with the expected code | `source.timeout` |
| PASS | timeout: wrote no snapshot and no change | 0 snapshots, 0 changes |
| PASS | model-failure: the run failed | status `failed` |
| PASS | model-failure: failed with the expected code | `source.model_failed` |
| PASS | model-failure: wrote no snapshot and no change | 0 snapshots, 0 changes |
| PASS | size-limit: the run failed | status `failed` |
| PASS | size-limit: failed with the expected code | `source.size_rejected` |
| PASS | size-limit: wrote no snapshot and no change | 0 snapshots, 0 changes |
| PASS | every tariff table is byte-for-byte unchanged | 6 of 6 digests equal |
| PASS | the API still serves the same accepted tariff | snapshot `479e2bba`, rates 21%, 20%, 15-21% |
| PASS | the normal worker is back | running without a failure overlay |

Model spend for these failures: $0.0000.
RESULT: PASS
