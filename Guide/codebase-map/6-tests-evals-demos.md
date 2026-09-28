# 6 · Tests, evals, demos, scripts

[← Guide](README.md) · Deep dives: [demonstrations.md](../../docs/demonstrations.md), [eval datasets README](../../tests/eval/datasets/README.md), [eval RESULTS.md](../../tests/eval/RESULTS.md)

## Which unit test covers what ([tests/unit/](../../tests/unit/))

Run one file: `uv run pytest tests/unit/<file> -q`. Run one test: add `-k <name>`.

| Area | Test files |
|---|---|
| Agent wiring, tool policy, tool flows | [test_agent_wiring](../../tests/unit/test_agent_wiring.py), [test_plugins](../../tests/unit/test_plugins.py), [test_tool_flows](../../tests/unit/test_tool_flows.py), [test_read_tool_scope](../../tests/unit/test_read_tool_scope.py), [test_tariff_query_authorization](../../tests/unit/test_tariff_query_authorization.py) |
| Intent / interpretation | [test_intent_resolution](../../tests/unit/test_intent_resolution.py), [test_interpretation_validation](../../tests/unit/test_interpretation_validation.py), [test_interpretation_cases](../../tests/unit/test_interpretation_cases.py), [test_intent_contracts](../../tests/unit/test_intent_contracts.py) |
| CLI, monitoring node, progress | [test_cli](../../tests/unit/test_cli.py), [test_monitoring_node](../../tests/unit/test_monitoring_node.py), [test_monitoring_progress](../../tests/unit/test_monitoring_progress.py), [test_run_stop](../../tests/unit/test_run_stop.py) |
| URL / domain validation | [test_source_urls](../../tests/unit/test_source_urls.py) |
| Acquisition, HTML, browser | [test_acquisition](../../tests/unit/test_acquisition.py), [test_acquisition_completeness](../../tests/unit/test_acquisition_completeness.py), [test_acquisition_freshness](../../tests/unit/test_acquisition_freshness.py), [test_html_parser](../../tests/unit/test_html_parser.py), [test_browser_renderer_rules](../../tests/unit/test_browser_renderer_rules.py) |
| PDF, OCR | [test_gemini_pdf_extraction](../../tests/unit/test_gemini_pdf_extraction.py), [test_ocr_fallback](../../tests/unit/test_ocr_fallback.py), [test_pdf_admission_gate](../../tests/unit/test_pdf_admission_gate.py), [test_pdf_link_selection](../../tests/unit/test_pdf_link_selection.py); downloader in [integration/test_pdf_downloader](../../tests/integration/test_pdf_downloader.py) |
| Normalization / parsing | [test_normalization](../../tests/unit/test_normalization.py), [test_normalization_service](../../tests/unit/test_normalization_service.py), [test_normalization_fixes](../../tests/unit/test_normalization_fixes.py), [test_normalization_baseline](../../tests/unit/test_normalization_baseline.py) |
| Source discovery | [test_source_discovery](../../tests/unit/test_source_discovery.py), [test_source_discovery_fixes](../../tests/unit/test_source_discovery_fixes.py), [test_source_selection](../../tests/unit/test_source_selection.py) |
| Extraction + field validation | [test_semantic_extraction](../../tests/unit/test_semantic_extraction.py), [test_semantic_extraction_fixes](../../tests/unit/test_semantic_extraction_fixes.py) |
| Snapshots, change detection, review signals | [test_snapshot_lifecycle](../../tests/unit/test_snapshot_lifecycle.py), [test_change_detection](../../tests/unit/test_change_detection.py) |
| Review / HITL | [test_review_resolution](../../tests/unit/test_review_resolution.py), [test_review_input](../../tests/unit/test_review_input.py), [test_review_fixes](../../tests/unit/test_review_fixes.py), [test_multi_review_approval](../../tests/unit/test_multi_review_approval.py), [test_review_publication_fixes](../../tests/unit/test_review_publication_fixes.py) |
| Pipeline orchestration | [test_monitoring_pipeline](../../tests/unit/test_monitoring_pipeline.py), [test_pipeline_spans](../../tests/unit/test_pipeline_spans.py), [test_pipeline_audit](../../tests/unit/test_pipeline_audit.py) |
| Error handling / failure codes | [test_failure_mapping](../../tests/unit/test_failure_mapping.py), [test_embedding_retry_policy](../../tests/unit/test_embedding_retry_policy.py) |
| Answering, projection, retrieval | [test_structured_tariff_query](../../tests/unit/test_structured_tariff_query.py), [test_structured_projection](../../tests/unit/test_structured_projection.py), [test_answer_read_model](../../tests/unit/test_answer_read_model.py), [test_tariff_queries](../../tests/unit/test_tariff_queries.py), [test_target_questions](../../tests/unit/test_target_questions.py) |
| Config, catalog | [test_config](../../tests/unit/test_config.py), [test_seed_catalog](../../tests/unit/test_seed_catalog.py) |
| Observability, cost | [test_telemetry](../../tests/unit/test_telemetry.py), [test_logging_setup](../../tests/unit/test_logging_setup.py), [test_model_call_usage](../../tests/unit/test_model_call_usage.py), [test_model_pricing](../../tests/unit/test_model_pricing.py) |
| Triggers (API, scheduler, worker) | [test_trigger_adapters](../../tests/unit/test_trigger_adapters.py) |

Shared test data: [tests/fixtures/](../../tests/fixtures/), for example [structured_tariffs.py](../../tests/fixtures/structured_tariffs.py), [monitoring_node.py](../../tests/fixtures/monitoring_node.py) and [interpretation_cases.py](../../tests/fixtures/interpretation_cases.py).
Integration tests (real PostgreSQL, need `TEST_DATABASE_URL`): [tests/integration/](../../tests/integration/). The end-to-end vertical slice is [test_monitoring_vertical_slice](../../tests/integration/test_monitoring_vertical_slice.py).

## Evaluation (assignment §5.14)

| What | Where |
|---|---|
| Agent evals (`agents-cli eval run`) config and judge | [eval_config.yaml](../../tests/eval/eval_config.yaml), [response_quality.py](../../tests/eval/response_quality.py) |
| Datasets | [datasets/](../../tests/eval/datasets/): [basic-dataset](../../tests/eval/datasets/basic-dataset.json), [expanded-intent-safety](../../tests/eval/datasets/expanded-intent-safety.json), [seed-url-ground-truth-v2](../../tests/eval/datasets/seed-url-ground-truth-v2.json) (expected values + evidence per seed URL), [structured-tariff-questions](../../tests/eval/datasets/structured-tariff-questions.json) |
| Model-free retrieval/answer metrics | [structured_metrics.py](../../tests/eval/structured_metrics.py), `uv run python scripts/structured_eval_metrics.py` |
| Recorded scores | [RESULTS.md](../../tests/eval/RESULTS.md) |
| Record / score the interpreter live | [record_interpretations.py](../../scripts/record_interpretations.py) → [recorded_interpretations.json](../../tests/fixtures/recorded_interpretations.json) |

## Live demos ([Presentation-demonstrations/](../../Presentation-demonstrations/README.md))

Run all of them: `cd Presentation-demonstrations && python3 present.py` (`--check` does a dry run, `--from change` starts partway). The code runs from the images, so after changing `app/`, run `docker compose build api worker` first.

| Deliverable | Script | Notes |
|---|---|---|
| 9 Normal extraction (Overdraft) | [extraction_demo.py](../../Presentation-demonstrations/Normal-extraction/extraction_demo.py) | `--no-run` re-reports the last run. [README](../../Presentation-demonstrations/Normal-extraction/README.md) |
| 13 Controlled failures (timeout, model 404, size limit) | [failure_demo.py](../../Presentation-demonstrations/Controlled-failures/failure_demo.py) | each failure is one compose override in [failures/](../../Presentation-demonstrations/Controlled-failures/failures/) |
| 10 + 12 Change detection + review | [change_demo.py](../../Presentation-demonstrations/Change-detection-and-review/change_demo.py) | local mirror with a synthetic +4 pp rate |
| 11 OCR fallback | [ocr_fallback_demo.py](../../Presentation-demonstrations/OCR-fallback/ocr_fallback_demo.py), [run.sh](../../Presentation-demonstrations/OCR-fallback/run.sh) | no DB. Gemini is forced to fail with a 503 |
| Demo stack (isolated DB, checkpoints) | [stack.py](../../Presentation-demonstrations/demo-stack/stack.py) | `python3 demo-stack/stack.py checkpoint save bank-baseline` |

Script-based, offline, pass/fail demos: `uv run python scripts/run_demonstration.py` ([runner](../../scripts/run_demonstration.py), scenarios in [scripts/demonstrations/](../../scripts/demonstrations/__init__.py)).

## Useful scripts ([scripts/](../../scripts/))

| Script | Purpose |
|---|---|
| [demonstrate_end_to_end.py](../../scripts/demonstrate_end_to_end.py) | Run every stage on one URL and write readable per-stage reports to `end-to-end/run_NNN/` |
| [demonstrate_source_discovery.py](../../scripts/demonstrate_source_discovery.py), [demonstrate_semantic_extraction.py](../../scripts/demonstrate_semantic_extraction.py), [demonstrate_pdf_extraction.py](../../scripts/demonstrate_pdf_extraction.py), [demonstrate_normalization.py](../../scripts/demonstrate_normalization.py), [demonstrate_acquisition.py](../../scripts/demonstrate_acquisition.py) | One stage at a time |
| [trace_structured_answer.py](../../scripts/trace_structured_answer.py) | Stage-by-stage trace of how a question is answered |
| [reset_acquisition_baseline.py](../../scripts/reset_acquisition_baseline.py) | Accept a page redesign that the completeness gate rejects |
| [check_adk_session_schema.py](../../scripts/check_adk_session_schema.py) | Prepare the ADK session tables (setup step) |
| [probe_adk_runtime.py](../../scripts/probe_adk_runtime.py) | Re-demonstrate the ADK resume behaviour the monitoring node relies on |
