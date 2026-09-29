# Controlled failures

Generated 2026-09-29 01:46 UTC by `failure_demo.py` against the demonstration stack (Compose project `tariff-demo`). Offering: `overdraft`.

## Before: what the demo database holds

Tariff tables (before):
| Table | Rows | Content digest |
|---|---|---|
| tariff_snapshots | 5 | `41643daf3c64` |
| tariff_facts | 328 | `31a816c6ead2` |
| fact_evidence | 842 | `b899adff2398` |
| tariff_changes | 3 | `118900301d06` |
| snapshot_documents | 20 | `34e06c586e44` |
| human_reviews | 0 | `d41d8cd98f00` |

`GET /tariffs/current` for overdraft: snapshot `3bb3d6cc`, accepted 2026-09-29T01:44:03.852631Z, freshness `fresh`, interest rates 21%, 20%, 15-21%.

## Failure: The bank's site does not answer (timeout)

Artificial part: inside the worker, `ameriabank.am` resolves to 192.0.2.1, an address routed nowhere (`failures/timeout.yml`).
Submitted run `bcff8997` through `POST /api/v1/runs`.
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
2026-09-29T05:47:25.357+04:00 WARNING app.services.monitoring_pipeline: offering failed run_id=bcff8997-af94-48d0-9298-a801c0c0af67 offering_id=overdraft stage=acquisition code=source.timeout reason=TIMEOUT
2026-09-29T05:47:25.369+04:00 INFO __main__: progress run_id=bcff8997-af94-48d0-9298-a801c0c0af67 kind=offering_failed offering_id=overdraft stage=acquisition elapsed_ms=0 failure_code=source.timeout detail=None
2026-09-29T05:47:25.374+04:00 INFO __main__: progress run_id=bcff8997-af94-48d0-9298-a801c0c0af67 kind=run_finished offering_id=None stage=None elapsed_ms=61668 failure_code=source.timeout detail=failed
2026-09-29T05:47:25.374+04:00 INFO __main__: monitoring run completed run_id=bcff8997-af94-48d0-9298-a801c0c0af67 status=failed review_count=0
```


## Failure: The model provider fails (model-failure)

Artificial part: source discovery uses the retired `gemini-2.5-flash-lite`, with no fallback model (`failures/model-failure.yml`).
Submitted run `4172f524` through `POST /api/v1/runs`.
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
2026-09-29T05:48:05.696+04:00 WARNING app.services.monitoring_pipeline: offering failed run_id=4172f524-531c-409d-ac7f-f1f800eaaf16 offering_id=overdraft stage=pdf_selection code=source.model_failed reason=HTTP 404 / NOT_FOUND: This model models/gemini-2.5-flash-lite is no longer available to new us
2026-09-29T05:48:05.703+04:00 INFO __main__: progress run_id=4172f524-531c-409d-ac7f-f1f800eaaf16 kind=offering_failed offering_id=overdraft stage=pdf_selection elapsed_ms=0 failure_code=source.model_failed detail=None
2026-09-29T05:48:05.708+04:00 INFO __main__: progress run_id=4172f524-531c-409d-ac7f-f1f800eaaf16 kind=run_finished offering_id=None stage=None elapsed_ms=20695 failure_code=source.model_failed detail=failed
2026-09-29T05:48:05.708+04:00 INFO __main__: monitoring run completed run_id=4172f524-531c-409d-ac7f-f1f800eaaf16 status=failed review_count=0
```


## Failure: A safety limit refuses the source (size-limit)

Artificial part: the download size cap is lowered from 25 MB to 50 KB (`failures/size-limit.yml`).
Submitted run `7accb0ab` through `POST /api/v1/runs`.
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
2026-09-29T05:48:26.755+04:00 WARNING app.services.monitoring_pipeline: offering failed run_id=7accb0ab-5ec8-44fb-b1ae-42963724659b offering_id=overdraft stage=acquisition code=source.size_rejected reason=PAGE_TOO_LARGE
2026-09-29T05:48:26.762+04:00 INFO __main__: progress run_id=7accb0ab-5ec8-44fb-b1ae-42963724659b kind=offering_failed offering_id=overdraft stage=acquisition elapsed_ms=0 failure_code=source.size_rejected detail=None
2026-09-29T05:48:26.766+04:00 INFO __main__: progress run_id=7accb0ab-5ec8-44fb-b1ae-42963724659b kind=run_finished offering_id=None stage=None elapsed_ms=1146 failure_code=source.size_rejected detail=failed
2026-09-29T05:48:26.767+04:00 INFO __main__: monitoring run completed run_id=7accb0ab-5ec8-44fb-b1ae-42963724659b status=failed review_count=0
```


## After: what the demo database holds

Tariff tables (after):
| Table | Rows | Content digest |
|---|---|---|
| tariff_snapshots | 5 | `41643daf3c64` |
| tariff_facts | 328 | `31a816c6ead2` |
| fact_evidence | 842 | `b899adff2398` |
| tariff_changes | 3 | `118900301d06` |
| snapshot_documents | 20 | `34e06c586e44` |
| human_reviews | 0 | `d41d8cd98f00` |

`GET /tariffs/current` for overdraft: snapshot `3bb3d6cc`, accepted 2026-09-29T01:44:03.852631Z, freshness `fresh`, interest rates 21%, 20%, 15-21%.

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
| PASS | the API still serves the same accepted tariff | snapshot `3bb3d6cc`, rates 21%, 20%, 15-21% |
| PASS | the normal worker is back | running without a failure overlay |

Model spend for these failures: $0.0000.
RESULT: PASS
