# 5 · Pipeline behaviour and retrieval

[← Change recipes](README.md)

Stage order and the per-offering stage runner: [IndexingPipeline.refresh](../../app/services/monitoring_pipeline.py#L226).
A full walkthrough is in [codebase-map/2](../codebase-map/2-monitoring-pipeline.md).

---

## Change which HTTP errors are retried
📖 There are two fetchers, each with a bounded retry loop driven by `HTTP_MAX_ATTEMPTS` and backoff
([HttpSettings](../../app/config/models.py#L112)):

| Fetcher | Retryable statuses | Edit |
|---|---|---|
| Static HTML | [_RETRYABLE_STATUSES](../../app/services/html_retriever.py#L18) = `{429, 500, 502, 503, 504}` | add or remove codes in the set |
| PDF download | inline at [pdf_downloader.py:227](../../app/services/pdf_downloader.py#L227): `429` or any `5xx` (honours `Retry-After`) | change the condition |

Timeouts and transport errors are retried too. A 404 never is: it maps to `source.not_found`
([source_failure_code](../../app/services/failure_mapping.py#L49)).
The whole acquisition stage also gets one delayed retry ([monitoring_pipeline.py:271–279](../../app/services/monitoring_pipeline.py#L271)).
**Say:** 4xx is not retried because retrying cannot fix it. Retrying a 403 means knocking on a bot wall, which the
assignment forbids (no bypassing access restrictions).
Test: [test_acquisition.py](../../tests/unit/test_acquisition.py) and [test_source_urls.py](../../tests/unit/test_source_urls.py). Grep for `503` to find the retry cases.

## Change a failure code or its message
📖
- Exception → stable code: [source_failure_code](../../app/services/failure_mapping.py#L49). It walks the `__cause__` chain.
  The codes are the enum [SourceFailureCode](../../app/domain/monitoring.py#L122).
- Code → the sentence the chat shows: [_FAILURE_EXPLANATIONS](../../app/services/failure_mapping.py#L152), used by
  [explain_failure_code](../../app/services/failure_mapping.py#L234).
- A new code needs an enum value, a branch in `source_failure_code` and an explanation. `failure_code` is a
  `varchar(100)` column, so no migration is needed.
- Test: [test_failure_mapping.py](../../tests/unit/test_failure_mapping.py). Live failures (timeout, size limit, model):
  [Controlled-failures demo](../../Presentation-demonstrations/Controlled-failures/).

## Change when OCR runs
📖 Gemini transcribes the PDF first. OCR (Tesseract, `hye+eng`) then runs only on pages that have **no text layer**
and that Gemini returned nothing for: [_pages_needing_ocr](../../app/services/pdf_extraction.py#L230).
- A page counts as having a text layer at `PDF_EXTRACTION_PROBE_TEXT_THRESHOLD=20` extractable characters or more
  ([probe_pdf_input](../../app/services/pdf_input_probe.py#L10), setting at [models.py:230](../../app/config/models.py#L230)).
  Raise it to send sparse pages to OCR.
- Turn it off or change the confidence floor: `OCR_ENABLED`, `OCR_MIN_CONFIDENCE` ([OcrSettings](../../app/config/models.py#L248)).
- Every value cited from an OCR page goes to review (`ocr_evidence`):
  [detect_review_signals](../../app/services/snapshot_lifecycle.py#L262).
- Demo without the bank site or the DB: [OCR-fallback](../../Presentation-demonstrations/OCR-fallback/).
- Test: [test_ocr_fallback.py](../../tests/unit/test_ocr_fallback.py).

## Change RAG ranking (weights / top-k)
📖 The field finder, [_find_fields](../../app/services/structured_tariff_query.py#L397), fuses lexical
(Postgres FTS) and vector (pgvector) hits with reciprocal rank fusion:

```python
for weight, hits in ((1.0, lexical), (0.7, vector)):          # line 454: source weights
    for rank, hit in enumerate(hits, start=1):
        scores[hit.unit.unit_id] = scores.get(hit.unit.unit_id, 0) + weight / (
            60 + rank                                            # RRF k = 60
        )
```

| Knob | Where |
|---|---|
| Weights (lexical 1.0, vector 0.7) | [line 454](../../app/services/structured_tariff_query.py#L454) |
| RRF `k` (60) | [line 457](../../app/services/structured_tariff_query.py#L457) |
| Hits per source (8) | `limit=8` at [line 426](../../app/services/structured_tariff_query.py#L426) and [line 444](../../app/services/structured_tariff_query.py#L444) |
| Field paths kept (3) | [FIELD_FINDER_MAX_PATHS](../../app/services/structured_tariff_query.py#L49) |
| Version label in traces | [RANK_FUSION_VERSION](../../app/services/structured_tariff_query.py#L47): update it with the numbers |
| Chunk size | `CHUNK_SIZE_CHARS`, see [Settings](1-settings.md#settings-only-changes) |

**Say:** retrieval only picks *which field paths* to answer. The values always come from accepted,
cited facts, never from generated text. Vector search is optional: if embedding fails, it falls back to lexical only
([line 447](../../app/services/structured_tariff_query.py#L447)).
Test: [test_structured_tariff_query.py](../../tests/unit/test_structured_tariff_query.py),
[test_target_questions.py](../../tests/unit/test_target_questions.py).
Debug a retrieval: `RETRIEVAL_TRACE_LEVEL=steps` ([TariffQuerySettings](../../app/config/models.py#L315)).

## Change what the schedule runs
📖 [run_scheduled_monitoring](../../app/worker.py#L70) submits one run per family in [PRODUCTS](../../app/worker.py#L36).
- Only mortgages: `PRODUCTS = (ProductType.MORTGAGE,)`.
- Time, timezone and on/off: [Settings](1-settings.md#settings-only-changes). The cron job is built in
  [schedule_daily_monitoring](../../app/worker.py#L51) (`max_instances=1`, `coalesce=True`).
- The worker and the chat both go through the same `RunService` → `TariffPipeline`. Only the trigger differs (`RunTrigger.SCHEDULE`).
- Test: [test_trigger_adapters.py](../../tests/unit/test_trigger_adapters.py) (imports `run_scheduled_monitoring`).
- Apply: `docker compose up --build -d worker`.
