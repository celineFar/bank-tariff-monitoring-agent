# Diagnose: logs, SQL, audit files, trace scripts

[← Debug](README.md) · symptom lookup: [symptoms.md](symptoms.md)

Look in this order: **what failed** (SQL row), then **which stage** (SQL, progress log), then **what that stage saw** (audit files), then **why** (code + logs).

---

## 1 · Five-command triage

```bash
alias q='docker compose exec -T db psql -U tariff -d tariff_monitor -c'

# 1. last runs
q "SELECT id, trigger_type, product, offering_id, status, error_code, created_at_yerevan FROM monitoring_runs ORDER BY created_at DESC LIMIT 5;"
# 2. per offering: stage reached, failure, reviews   (swap in a run id for the subquery)
q "SELECT offering_id, status, current_stage, failure_code, failure_detail, review_count, acquisition_reused FROM offering_executions WHERE run_id=(SELECT id FROM monitoring_runs ORDER BY created_at DESC LIMIT 1) ORDER BY created_at;"
# 3. what the code means            → _FAILURE_EXPLANATIONS (link below)
# 4. log lines for that run
grep <run_id> logs/worker.log | cut -c1-220 | tail -40
# 5. what each stage saw
ls artifacts/pipeline-audit/run_<run_id>/<offering_id>/
```

Failure code → sentence: [_FAILURE_EXPLANATIONS](../../app/services/failure_mapping.py#L152). Exception → code: [source_failure_code](../../app/services/failure_mapping.py#L49). The stored `failure_detail` is only `ExceptionType[:http_<code>_<STATUS>]` ([bounded_failure_detail](../../app/services/failure_mapping.py#L138)). The full provider message is in the **log**, from [describe_failure](../../app/services/failure_mapping.py#L125).

---

## 2 · Logs

Format: `<ISO time +04:00> LEVEL logger: message` ([ZonedFormatter](../../app/services/logging_setup.py#L15)). Set up in [configure_application_logging](../../app/services/logging_setup.py#L26).

| File | Written by |
|---|---|
| `logs/worker.log` | worker: API-started and scheduled runs |
| `logs/api.log` | API: requests, `/questions` |
| `logs/cli.log` | `./tariff-chat` and the runs it starts (**no per-stage progress lines**, the CLI renders those) |
| `logs/model_usage.log` | one line per Gemini call: stage, model, tokens, cost, outcome |
| `local-run/logs/local.log` (+ `model_usage.log`) | anything started with [local.sh](local.sh) |
| `docker compose logs -f worker api` | same as the files, live |

### grep patterns that matter

| Pattern | Tells you | Emitted at |
|---|---|---|
| `monitoring run started run_id=` / `completed run_id=… status=… review_count=` | worker picked up / finished a run | [process_next](../../app/worker.py#L133) |
| `progress run_id=… kind=stage_started … stage=` | stage by stage (worker only) | [LogProgressSink](../../app/services/monitoring_progress.py#L62) |
| `failure_code=source.` | the stage that failed and why | same |
| `HTTP Request: GET https://` | every fetch (httpx) | acquisition / PDF download |
| `classified as … admission=` | PDF probe: text / scanned / mixed, rule admission | [GeminiPdfExtractionService.extract](../../app/services/pdf_extraction.py#L456) |
| `Reusing cached Gemini PDF extraction` | cache hit: no model call for that PDF | same file |
| `Gemini PDF model attempt` | real transcription call | same file |
| `OCR available` / `OCR unavailable` | at startup: can OCR run in this process? | [ocr_transcriber.py](../../app/services/ocr_transcriber.py) |
| `was unusable (…); asking again` | Gemini returned invalid JSON / schema, retried | [semantic_extraction.py](../../app/services/semantic_extraction.py#L415) |
| `repair accepted for <field>` / `repair for <field> failed validation` | a field failed validation → one repair call | [_repair_batch](../../app/services/semantic_extraction.py#L1944) |
| `tariff.model_usage … outcome=failed error=` | model call failed (429, 404, 5xx) | [observe_model_call](../../app/services/model_call_usage.py#L288) |
| `tariff.retrieval: trace=… status=… facts=` | one question answered: status, fact count | [retrieval_trace](../../app/services/retrieval_trace.py#L105) |
| `embedding provider rejected batch code=402` | embedding quota; answers still work lexically | [embedding_providers.py](../../app/services/embedding_providers.py#L135) |

```bash
grep -E "stage_started|failure_code=source" logs/worker.log | tail -30 | cut -c1-200
grep -E "outcome=failed" logs/model_usage.log | tail -5
grep -c "Reusing cached" logs/worker.log            # cache hits
```

### Turn up detail (one command, no code change)

| Knob | Effect |
|---|---|
| `LOG_LEVEL=DEBUG` | everything, including ADK/httpx debug ([validate_log_level](../../app/config/models.py#L504)) |
| `RETRIEVAL_TRACE_LEVEL=steps` or `verbose` | per-step retrieval trace for answers ([RetrievalTraceLevel](../../app/services/retrieval_trace.py#L47)) |
| `OTEL_ENABLED=true` (no endpoint) | spans printed to the console, one per stage with timings ([configure_telemetry](../../app/services/telemetry.py#L171)) |
| `--verbose` on the chat | shows tool calls and run ids |
| `PIPELINE_AUDIT_ENABLED=true` | the stage audit files (on by default) |

Example: `LOG_LEVEL=DEBUG RETRIEVAL_TRACE_LEVEL=verbose Guide/debug/local.sh python app/cli_entry.py --session dbg --verbose`

---

## 3 · SQL cookbook

All tested against the live DB. Tables: [006 runs/snapshots/changes](../../migrations/006_monitoring_pipeline_foundation.sql), [007 reviews](../../migrations/007_review_quarantine.sql), [011 typed facts](../../migrations/011_structured_tariff_read_model.sql). Each `*_at` column has a `*_at_yerevan` twin.

```sql
-- runs and what each offering did
SELECT id, trigger_type, product, offering_id, status, error_code, created_at_yerevan
  FROM monitoring_runs ORDER BY created_at DESC LIMIT 5;
SELECT offering_id, status, current_stage, failure_code, failure_detail, review_count, acquisition_reused
  FROM offering_executions WHERE run_id = '<run_id>' ORDER BY created_at;

-- failed runs with their stage
SELECT r.id, r.error_code, e.offering_id, e.current_stage, e.failure_code, e.failure_detail
  FROM monitoring_runs r JOIN offering_executions e ON e.run_id = r.id
 WHERE r.status = 'failed' ORDER BY r.created_at DESC LIMIT 5;

-- audit events for a run (publish timings, review decisions)
SELECT event_type, reason_code, left(payload::text, 150) FROM audit_events WHERE run_id = '<run_id>' ORDER BY id;

-- reviews
SELECT offering_id, reason_code, issue_scope, status, created_at_yerevan FROM human_reviews ORDER BY created_at DESC LIMIT 10;
SELECT jsonb_pretty(evidence) FROM human_reviews WHERE id = '<review_id>';

-- snapshots and a field's value (JSON keys = ExtractionField names: interest_rate, effective_rate, fees, term, loan_amount…)
SELECT id, status, accepted_at_yerevan FROM tariff_snapshots WHERE offering_id = 'overdraft' ORDER BY created_at DESC LIMIT 3;
SELECT jsonb_path_query_array(normalized_tariff, '$.interest_rate.value[*].value')
  FROM tariff_snapshots WHERE offering_id = 'overdraft' AND status = 'accepted' ORDER BY created_at DESC LIMIT 1;

-- detected changes
SELECT offering_id, change_count, jsonb_path_query_array(changes, '$[*].field') AS fields, created_at_yerevan
  FROM tariff_changes ORDER BY created_at DESC LIMIT 5;
SELECT jsonb_pretty(changes -> 0) FROM tariff_changes WHERE change_count > 0 ORDER BY created_at DESC LIMIT 1;

-- the typed facts answers are built from
SELECT field_path, number_value, unit, currency FROM tariff_facts
 WHERE is_active AND offering_id = 'overdraft' AND field_path LIKE 'rate.%' ORDER BY field_path;

-- which sources were used
SELECT source_url, status, selected, reason_code FROM source_manifests WHERE run_id = '<run_id>' AND offering_id = 'overdraft';

-- model calls and cost, last 24 h
SELECT stage, model_id, outcome, count(*), round(sum(estimated_cost_usd)::numeric, 4) AS usd
  FROM model_call_usage WHERE called_at > now() - interval '1 day' GROUP BY 1,2,3 ORDER BY 5 DESC NULLS LAST;

-- anything stuck?
SELECT id, status, claimed_by, heartbeat_at FROM monitoring_runs WHERE status IN ('queued','running','awaiting_review');
```

Other tables: `source_discovery_assessments`, `pdf_link_selections`, `pdf_extraction_cache`, `semantic_extraction_batches` (the caches); `knowledge_chunks` and `retrieval_units` (RAG); `sessions` and `events` (ADK chat sessions).

---

## 4 · Audit files: what each stage saw

`artifacts/pipeline-audit/run_<run_id>/<offering_id>/` (local runs: `local-run/audit/…`). Written by [FileSystemPipelineAuditArchive](../../app/services/pipeline_audit_archive.py#L89). Open them in Markdown preview, because they use coloured blocks.

| File | Stage | Open it when… |
|---|---|---|
| `0_run_context.md` | — | you need the run/execution id and seed URL |
| `2_normalized_webpage.md` | normalization | you're checking the page as the pipeline read it (tables, blocks) |
| `2_normalization_diff.md` | normalization | you suspect a table or number was mangled |
| `2_pdf_link_selection.md` | PDF selection | a PDF was or wasn't used: decision, role, rule or model, reason |
| `3_source_selection_decisions.md` | source discovery | a value came from the wrong section: every block is labelled SELECTED / HISTORICAL / NOT SELECTED |
| `3_source_selection_diff.md`, `3_selected_sources.md` | source discovery | you want exactly what went to extraction |
| `4_extraction_evidence.md` | extraction | you're checking which evidence ids and quotes back each value |
| `4_pre_validation.md` | extraction | you want Gemini's raw value per field: **green** valid, **red** failed → review, **orange** ambiguous/conflicting |
| `4_review_queue.md` | extraction | you want to know why a review was opened |

Stage 1 (acquisition) has no audit file. Look at `HTTP Request` log lines and `source_manifests`.

---

## 5 · Scripts that debug without the chat

Run them through [local.sh](local.sh) so they hit the Docker DB.

| Script | Answers |
|---|---|
| `python -m scripts.trace_structured_answer "<question>" --no-vector` | Why did the answer say X? Prints resolution → plan → facts + citations → units. Makes one interpreter call; `--no-vector` skips embeddings. ([script](../../scripts/trace_structured_answer.py)) |
| `python -m scripts.model_cost_report --days 1` | What did it cost, and which model failed? ([script](../../scripts/model_cost_report.py)) |
| `python -m scripts.run_metrics_report --days 30` | Durations, failure rates, completeness, HITL rate ([script](../../scripts/run_metrics_report.py)) |
| `python scripts/demonstrate_end_to_end.py <seed_url>` | Every stage on one URL, no DB publication, readable per-stage reports ([script](../../scripts/demonstrate_end_to_end.py)) |
| `python -m scripts.reset_acquisition_baseline <offering_id>` | Accept a page redesign the completeness gate rejects ([script](../../scripts/reset_acquisition_baseline.py)) |

---

## 6 · Force a cache miss (when a rerun "does nothing")

A rerun reuses the page fetch (`ACQUISITION_FRESHNESS_HOURS`, default 1 h) and four model caches ([why](../codebase-map/2-monitoring-pipeline.md#caches-why-a-rerun-costs-0)).

| To redo | Do |
|---|---|
| page fetch | `ACQUISITION_FRESHNESS_HOURS=0` |
| PDF transcription | bump `PDF_EXTRACTION_PROMPT_VERSION` |
| source discovery | bump `SOURCE_DISCOVERY_PROMPT_VERSION` |
| extraction | any prompt/model change invalidates it on its own ([prompt_fingerprint](../../app/services/semantic_extraction.py#L603)) |

Proof that a cache was used: `Reusing cached …` in the log, and `outcome=cache_hit` rows in `model_call_usage`.
