# Symptom → cause → where → confirm

[← Debug](README.md) · tools used below: [diagnose.md](diagnose.md) (`q` = the psql alias there)

Find the row that matches what you see. **Open** is where to put your eyes; **Confirm** is the fastest check.

---

## "My change doesn't show up"

| Symptom | Likely cause | Open | Confirm |
|---|---|---|---|
| Edited `app/`, chat behaves the same | `./tariff-chat` runs the **api container**, which has the old code | [README §1](README.md#1--which-process-runs-my-code) | use `Guide/debug/local.sh python app/cli_entry.py …`, or `docker compose up --build -d api worker` |
| `POST /runs` still runs the old pipeline | the **worker** container executes API runs | [process_next](../../app/worker.py#L133) | `docker compose stop worker` + local worker ([README §2](README.md#2--the-fast-loop-edit--test--run-locally-no-rebuild)) |
| Changed a default in `models.py`, nothing changes | `.env` sets it explicitly, and `.env` wins over code defaults | [.env.example](../../.env.example) / `.env` | `grep <NAME> .env` |
| Edited `.env`, containers ignore it | `env_file` is read only when the container is created | [docker-compose.yml](../../docker-compose.yml#L5) | `docker compose up -d --force-recreate api worker` |
| Edited a prompt, run output identical | cache keyed on a **version string** | [2-pipeline caches](../codebase-map/2-monitoring-pipeline.md#caches-why-a-rerun-costs-0) | `Reusing cached` in log; bump `*_PROMPT_VERSION` |
| Rerun finished in seconds, nothing refetched | page fetch reused (< `ACQUISITION_FRESHNESS_HOURS`) | [FreshnessGatedAcquisitionService](../../app/services/acquisition_freshness.py#L28) | `acquisition_reused = t` in `offering_executions`; rerun with `ACQUISITION_FRESHNESS_HOURS=0` |
| New migration not applied | `migrations/` run only on a **fresh** DB volume | [docker-compose.yml](../../docker-compose.yml#L42) | `docker compose exec -T db psql -U tariff -d tariff_monitor < migrations/0NN_x.sql` |
| Local run: `No API key was provided` | the key reached settings but not the process env (the Gemini SDK reads `os.environ`) | [local.sh](local.sh) | run through `local.sh` (it does `uv run --env-file .env`) |
| Local run: `mkdir: Permission denied` / log file error | `logs/`, `artifacts/` are root-owned by the containers | [local.sh](local.sh) | `local.sh` writes to `local-run/` |

## Startup

| Symptom | Likely cause | Open | Confirm |
|---|---|---|---|
| Refuses to start: model price above cap | new model not priced, or above `*_MAX_PRICE_PER_MILLION_TOKENS_USD` | [enforce_model_price_cap](../../app/services/model_pricing.py#L150), [MODEL_PRICE_CATALOG](../../app/services/model_pricing.py#L18) | the startup traceback names the model |
| Refuses to start: settings validation error | bad env value (e.g. host not a bare hostname, value out of `Field(...)` bounds) | [models.py](../../app/config/models.py), [HttpSettings.validate_source_hosts](../../app/config/models.py#L135) | `uv run python -c "from app.config import get_settings; get_settings()"` |
| `Failed to build response JSON schema for monitoring` + traceback | harmless ADK/pydantic warning | — | appears on every start |
| `OCR unavailable: pytesseract is not installed` | host run: the `ocr` extra is not installed | [Dockerfile](../../Dockerfile#L32) | OCR works in Docker (`OCR available: tesseract … hye+eng`) |
| Model call fails `http_404_NOT_FOUND` | model retired or not served for this API key (the app uses the Gemini API backend, see `backend: GEMINI_API` in the log) | `.env` `*_MODEL_NAME`, `*_FALLBACK_MODEL_NAMES`, [runtime.py model wiring](../../app/runtime.py#L169) | `grep http_404 logs/model_usage.log`; deliberate version in [model-failure.yml](../../Presentation-demonstrations/Controlled-failures/failures/model-failure.yml) |
| Chat: "Gemini credits exhausted"; every call `http_402_RESOURCE_EXHAUSTED` | the API key's prepaid credits are used up (happened on 2026-09-28, 17:17). Nothing works until they are topped up, except cached runs and answers that need no model | [_print_api_error](../../app/cli.py#L962) | `grep http_402 logs/model_usage.log local-run/logs/model_usage.log \| tail -3` |

## Chat / agent

| Symptom | Likely cause | Open | Confirm |
|---|---|---|---|
| Tool returns `policy.resolve_first` | a business tool was called before `resolve_request` in this invocation | [ToolPolicyPlugin.before_tool_callback](../../app/plugins.py#L38), [BUSINESS_TOOLS](../../app/plugins.py#L22) | `--verbose` shows the call order |
| Tool returns `{"status":"error","reason_code":"tool.exception"}` | exception inside the tool | [on_tool_error_callback](../../app/plugins.py#L64) | `grep "tool .* failed" logs/cli.log` (the traceback follows) |
| "I couldn't understand" / `intent.interpretation_unavailable` | interpreter call failed or returned invalid JSON; nothing is guessed | [resolve_request](../../app/tools/resolution.py#L48), [AdkRequestInterpreter](../../app/services/intent_resolution.py#L206) | `stage=intent.resolution outcome=failed` in `model_usage.log` |
| Wrong product/offering picked | interpreter output, or missing alias/synonym | [INTERPRETER_INSTRUCTION](../../app/services/intent_resolution.py#L98), [seed_catalog.yaml](../../app/config/seed_catalog.yaml) | `trace_structured_answer "<q>"` step [1] prints intent/product/offering |
| Agent asks a clarifying question instead of answering | validator decided the scope is ambiguous | [InterpretationValidator.validate](../../app/services/interpretation_validation.py#L143) | step [1] shows `clarify=True` |
| Monitoring tool returns `run.intent_not_authorized` | no **spend grant** this turn (user didn't ask to monitor, or scope differs) | [run_tariff_monitoring](../../app/tools/monitoring.py#L37), grant issued in [resolve_request](../../app/tools/resolution.py#L119) | ask explicitly: "check the overdraft tariffs now" |
| `needs_scope_confirmation` | a whole-family run needs an explicit yes | [monitoring.py](../../app/tools/monitoring.py#L111) | reply "yes" next turn |
| Chat says a turn "failed" and points at `logs/cli.log` | exception in the turn | [_print_api_error](../../app/cli.py#L939) | `tail -80 logs/cli.log` (local: `local-run/logs/local.log`) |

## Answers

| Symptom | Likely cause | Open | Confirm |
|---|---|---|---|
| "No accepted data" / `status=missing` | offering never published (no accepted snapshot) | [CurrentTariffService.get_current](../../app/services/tariff_queries.py#L38) | `q "SELECT status, accepted_at_yerevan FROM tariff_snapshots WHERE offering_id='<id>' ORDER BY created_at DESC LIMIT 3;"` |
| `insufficient_evidence` | no typed fact for the asked field (NOT_FOUND, or field not mapped) | [StructuredTariffQueryService.answer](../../app/services/structured_tariff_query.py#L252), [SOURCE_FIELD_PATHS](../../app/domain/structured_tariffs.py#L341) | `tariff.retrieval … status=insufficient_evidence facts=0`; SQL on `tariff_facts` |
| Answer says data is **stale** | accepted > `TARIFF_FRESHNESS_DAYS` (7) ago | [TariffQuerySettings](../../app/config/models.py#L308) | `accepted_at` in `/tariffs/current` |
| Answer value differs from the PDF | extraction picked another row/condition, or the wrong section was selected | `4_pre_validation.md`, `3_source_selection_decisions.md` | the cited quote in `4_extraction_evidence.md` |
| Compare/rank refuses two offerings | not comparable (different basis/currency/condition) | [comparison_issue](../../app/domain/tariff_comparison.py#L65), [IncomparabilityReason](../../app/domain/tariff_comparison.py#L14) | `trace_structured_answer` step [6] |

## Monitoring run failed (`failure_code` in `offering_executions`)

| `failure_code` @ stage | Meaning | Open | Confirm / fix |
|---|---|---|---|
| `source.timeout` / `source.transport` @ acquisition | site slow/unreachable; retries were bounded | [HtmlRetriever.retrieve](../../app/services/html_retriever.py#L82), `DOWNLOAD_TIMEOUT_SECONDS`, `HTTP_MAX_ATTEMPTS` | `HTTP Request` lines; `curl -sI https://ameriabank.am` |
| `source.not_found` / `source.http_status` | 404 / other status on page or PDF | [source_failure_code](../../app/services/failure_mapping.py#L49) | log line with the URL |
| `source.url_rejected` | link outside `ALLOWED_SOURCE_HOSTS` | [validate_source_url](../../app/security/urls.py#L9) | `grep ALLOWED_SOURCE_HOSTS .env` |
| `source.size_rejected` | bigger than `MAX_DOWNLOAD_BYTES` (header or streamed) | [PdfDownloader.download](../../app/services/pdf_downloader.py#L121) | [Controlled-failures demo](../../Presentation-demonstrations/Controlled-failures/failure_demo.py) |
| `source.mime_rejected` / `source.signature_rejected` | not HTML/PDF, or bytes don't start with `%PDF-` | [PdfDownloader](../../app/services/pdf_downloader.py#L103) | the URL in the log |
| `source.browser_unavailable` / `source.browser_failed` @ acquisition | Playwright couldn't start or render (seen in this DB) | [PlaywrightBrowserRenderer](../../app/services/browser_renderer.py#L256), [acquire_with_retry](../../app/services/monitoring_pipeline.py#L142) | `failure_detail = AcquisitionError:BROWSER_FAILED`; rerun; `ACQUISITION_BROWSER_ENABLED` |
| `source.incomplete_content` @ acquisition | page came back much smaller than the last good fetch (redesign or broken render) | [compare_inventory](../../app/services/acquisition_completeness.py#L23), [completeness_floor_failures](../../app/services/acquisition.py#L58) | if the redesign is real: `local.sh python -m scripts.reset_acquisition_baseline <offering_id>` |
| `source.model_failed` @ pdf_selection / source_discovery / semantic_extraction | every model in the fallback chain failed (seen: @ pdf_selection) | [FallbackSourceDiscoveryService](../../app/services/source_discovery.py#L422), [FallbackSemanticExtractionService](../../app/services/semantic_extraction.py#L2994) | `failure_detail` has `…:http_429_RESOURCE_EXHAUSTED` / `http_404`; `outcome=failed` in `model_usage.log` |
| `source.pdf_extraction_failed` | no model could transcribe a PDF and OCR couldn't cover it | [GeminiPdfExtractionService.extract](../../app/services/pdf_extraction.py#L456) | `Gemini PDF model attempt` lines |
| `source.malformed_structured_output` | model JSON failed the Pydantic schema, even after the retry | [parse_batch_response](../../app/services/semantic_extraction.py#L2647) | `was unusable (…); asking again` then failure |
| `source.linked_document_unavailable` | a PDF that previous values came from failed this time; fails rather than recording "withdrawn" | [_fields_lost](../../app/services/monitoring_pipeline.py#L905), [check in refresh](../../app/services/monitoring_pipeline.py#L433) | previous tariffs stay current; rerun later |
| run `failed`, **no** code, stage `review_superseded` | a newer candidate superseded this run's pending review (not an error) | [close_unreviewable_snapshots](../../app/repositories/review_supersession.py#L95) | `review.superseded` in `audit_events` |
| run `failed` `run.abandoned` | process died, lease expired | [recover_abandoned](../../app/worker.py#L121), [execute_with_lease](../../app/services/run_lease.py#L49) | `claimed_by`, `heartbeat_at` in `monitoring_runs` |
| run `partial_success` | some offerings failed, others published (siblings are isolated) | [TariffPipeline.execute](../../app/services/monitoring_pipeline.py#L584) | query 2 in [diagnose §1](diagnose.md#1--five-command-triage) |
| Run stays `queued` | no worker running, or it crashed | [MonitoringWorker.run_forever](../../app/worker.py#L268) | `docker compose ps worker`; `docker compose logs --tail=50 worker` |

## Reviews (HITL)

| Symptom | Likely cause | Open | Confirm |
|---|---|---|---|
| Run is `awaiting_review` | a review signal fired; `reason_code` says which | [detect_review_signals](../../app/services/snapshot_lifecycle.py#L237), [ReviewReason](../../app/domain/review.py#L17) | `q "SELECT reason_code, issue_scope, status FROM human_reviews WHERE run_id='<id>';"` + `4_review_queue.md` |
| `extraction_invalid` on a field | Gemini's value failed validation (quote not in evidence, number not in quote, bad type) | [_validate_field_result](../../app/services/semantic_extraction.py#L2379) | red block in `4_pre_validation.md` shows the reason |
| `missing_required_field` | a required field was NOT_FOUND | [_REQUIRED_TARIFF_FIELDS](../../app/services/snapshot_lifecycle.py#L46) | `4_extraction_evidence.md`: was it on the page at all? |
| `large_rate_change` | rate moved ≥ `HITL_LARGE_RATE_CHANGE_PERCENTAGE_POINTS` vs last accepted | [detect_large_rate_changes](../../app/services/snapshot_lifecycle.py#L497) | `human_reviews.evidence` shows previous → current |
| `ocr_evidence` | a value cites OCR text | [is_ocr_source_item](../../app/domain/pdf_extraction.py#L165) | `classified as image_only` / `mixed` in the log ([PdfInputMode](../../app/domain/pdf_extraction.py#L13)) |
| Expected a review, got none | the decision was **remembered** from an earlier identical result | [PostgresReviewDecisionMemory](../../app/repositories/review_memory.py#L99) | `review_decision_memory` table |
| Chat doesn't show the review panel | the pause event wasn't detected | [pending_review](../../app/cli.py#L184), [_review_request](../../app/services/monitoring_node.py#L532) | `./tariff-chat --session <same>` offers to continue |
| Stuck paused run blocks new ones | open review from an old session | [reject_all_pending](../../app/services/review_resolution.py#L353) | `curl -X POST $API/api/v1/reviews/abort-pending -H "X-Review-Admin-Token: <REVIEW_ADMIN_TOKEN from .env>"` ([abort_pending_reviews](../../app/api/routes.py#L311)) |
| Reviewer's typed value rejected | the format parser didn't accept it | [parse_review_field_text](../../app/services/review_input.py#L91), [_FORMATS](../../app/services/review_input.py#L488) | `uv run pytest tests/unit/test_review_input.py -q` |

## Changes

| Symptom | Likely cause | Open | Confirm |
|---|---|---|---|
| Many "changes" but the bank changed nothing | the model **reworded** free-text values (seen: `"Ameria’s branches"` → `"branch"`, 14 changes on `mortgage_express`) after a prompt/model change | [compare_accepted_snapshots](../../app/services/snapshot_lifecycle.py#L674), [_canonicalize](../../app/services/snapshot_lifecycle.py#L724) | `jsonb_pretty(changes -> 0)` in [diagnose §3](diagnose.md#3--sql-cookbook): compare `previous` and `current` |
| "10 000 000" vs "10,000,000" flagged as a change | shouldn't happen: values are typed before comparing | [MoneyRange](../../app/domain/semantic_extraction.py#L162), [normalize_extraction_field_value](../../app/services/semantic_extraction.py#L1341) | [test_snapshot_lifecycle.py](../../tests/unit/test_snapshot_lifecycle.py) |
| No change reported on the first run | no previous accepted snapshot; nothing to compare | [get_latest_accepted](../../app/repositories/monitoring.py#L1167) | `previous_accepted_snapshot_id` is NULL |
| A real change not reported | the value's snapshot went to review and wasn't approved, or the field was NOT_FOUND | `human_reviews`, `4_pre_validation.md` | `tariff_changes` for that run |
