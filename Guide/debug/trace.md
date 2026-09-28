# Trace one request, hop by hop

[← Debug](README.md) · bigger picture: [codebase-map flow](../codebase-map/README.md#the-flow-on-one-screen)

Each hop links the code and names the **evidence** that shows it happened: a log line, a DB row or a file. Log examples are real lines from this machine.

---

## A · A chat question: "What is the overdraft interest rate?"

Reproduce (≈ $0.015, no monitoring run):
```bash
printf 'What is the overdraft interest rate?\n' | Guide/debug/local.sh python app/cli_entry.py --session trace --verbose
```

| # | Hop | Code | Evidence |
|---|---|---|---|
| 1 | CLI sends the message as one ADK invocation | [ChatSession.converse](../../app/cli.py#L463) | — |
| 2 | Root agent (Gemini) decides to call `resolve_request` | [root_agent](../../app/agent.py#L65), [INSTRUCTION](../../app/agent.py#L28) | `tariff.model_usage … stage=adk.root … in_tokens=1213` · `--verbose`: `→ call resolve_request` |
| 3 | Interpreter call (tool-free Gemini, strict JSON) | [resolve_request](../../app/tools/resolution.py#L48) → [RequestResolver.resolve_turn](../../app/services/intent_resolution.py#L330) → [AdkRequestInterpreter](../../app/services/intent_resolution.py#L206) | `stage=intent.resolution … cost_usd=0.003753` |
| 4 | Code validates it against catalog and enums | [InterpretationValidator.validate](../../app/services/interpretation_validation.py#L143) | `trace_structured_answer` step [1]: `intent=answer_indexed_tariff_question product=consumer_loan offering=overdraft method=gemini clarify=False` |
| 5 | **Read grant** issued into session state (30 min, this invocation only) | [issue_read_grant](../../app/services/structured_query_planning.py#L51), key [TARIFF_PLAN_KEY](../../app/tools/_state.py#L20) | step [2]: `operation=single offerings=['overdraft'] fields=['rate.nominal.minimum', …]` |
| 6 | Agent calls `answer_tariff_query` → plugin checks resolve-first | [ToolPolicyPlugin.before_tool_callback](../../app/plugins.py#L38) | `--verbose`: `→ call answer_tariff_query` (a rejection would be `policy.resolve_first`) |
| 7 | Tool reads the grant (no scope args) → router | [answer_tariff_query](../../app/tools/reads.py#L56) → [TariffAnswerRouter](../../app/services/answer_read_model.py#L118) | — |
| 8 | Typed facts from accepted snapshot (+ lexical/vector units if needed) | [StructuredTariffQueryService.answer](../../app/services/structured_tariff_query.py#L252), SQL in [PostgresStructuredTariffQueryRepository](../../app/repositories/structured_tariff_query.py#L227) | `tariff.retrieval: trace=… operation=single product=consumer_loan status=answered facts=8 units=0` |
| 9 | Result → citations → trimmed payload for the model | [structured_to_answer_result](../../app/services/answer_read_model.py#L56), [model_facing_query_result](../../app/services/tariff_queries.py#L374) | SQL: `tariff_facts` rows for `overdraft` ([diagnose §3](diagnose.md#3--sql-cookbook)) |
| 10 | Root agent writes the answer from the payload (presentation only) | [INSTRUCTION](../../app/agent.py#L28) | `stage=adk.root … out_tokens=1132`; answer shows Source URL, section, "Accepted As Of" |

Total: 4 model calls (root ×3 + interpreter), ≈ 5 s. The numbers come from `tariff_facts`, never from the model.
Break it on purpose: ask about an offering with no accepted snapshot and you get `status=missing`.

---

## B · A monitoring run from the API (worker path)

```bash
curl -s -X POST $API/api/v1/runs -H 'content-type: application/json' -d '{"product":"consumer_loan","offering_id":"overdraft"}'
docker compose logs -f worker | grep -E "run_id|stage_started|failure_code=source"
```

| # | Hop | Code | Evidence |
|---|---|---|---|
| 1 | Route validates and enqueues (202, idempotent) | [create_run](../../app/api/routes.py#L104) → [RunService.submit](../../app/services/run_service.py#L51) → [PostgresRunRepository.submit](../../app/repositories/monitoring.py#L226) | `monitoring_runs` row `status=queued`, `trigger_type=api` |
| 2 | Worker claims it (poll loop) | [MonitoringWorker.process_next](../../app/worker.py#L133) → [claim_next](../../app/repositories/monitoring.py#L352) | `monitoring run started run_id=… product=consumer_loan offering_id=overdraft`; `claimed_by` set |
| 3 | Lease + heartbeat around the whole run | [execute_with_lease](../../app/services/run_lease.py#L49) | `heartbeat_at` advances |
| 4 | Family loop, one offering at a time | [TariffPipeline.execute](../../app/services/monitoring_pipeline.py#L584) | `progress … kind=offering_started offering_id=overdraft` |
| 5 | Stage runner | [IndexingPipeline.refresh](../../app/services/monitoring_pipeline.py#L226), wrapper [_stage](../../app/services/monitoring_pipeline.py#L541) | `progress … kind=stage_started stage=<name>` for each stage below; `offering_executions.current_stage` |
| 5.1 | **acquisition**: HTML + browser + linked PDFs, allowlisted | [acquire_with_retry](../../app/services/monitoring_pipeline.py#L142) → [AcquisitionService.acquire](../../app/services/acquisition.py#L109) | `HTTP Request: GET https://ameriabank.am/…`; `acquisition_reused` |
| 5.2 | **pdf_selection**: rule admission, then Gemini picks PDFs | [assess_pdf_metadata](../../app/services/pdf_admission.py#L100), [PdfLinkSelectionService.select](../../app/services/pdf_link_selection.py#L184) | `stage=discovery.pdf_link_selection` in model_usage · `2_pdf_link_selection.md` |
| 5.3 | **normalization**: tables/blocks; PDF transcription; OCR fallback | [StructuralNormalizationService.normalize](../../app/services/normalization.py#L126), [GeminiPdfExtractionService.extract](../../app/services/pdf_extraction.py#L456) | `PDF document:… classified as mixed`, `Reusing cached Gemini PDF extraction` · `2_normalized_webpage.md` |
| 5.4 | **source_discovery**: rules → cache → Gemini classifier | [SourceDiscoveryService.discover](../../app/services/source_discovery.py#L313) | `stage=discovery.classification` (`cache_hit` on reruns) · `3_source_selection_decisions.md` |
| 5.5 | **semantic_extraction**: evidence-bound Gemini, then Python validates | [SemanticExtractionService.extract](../../app/services/semantic_extraction.py#L621) | `stage=semantic.extraction`, `repair accepted for <field>` · `4_pre_validation.md`, `4_extraction_evidence.md` |
| 5.6 | previous snapshot, build snapshot, review signals | [get_latest_accepted](../../app/repositories/monitoring.py#L1167), [build_snapshot_attempt](../../app/services/snapshot_lifecycle.py#L107), [detect_review_signals](../../app/services/snapshot_lifecycle.py#L237) | `4_review_queue.md`; `human_reviews` rows if any |
| 5.7 | change set vs previous accepted | [compare_accepted_snapshots](../../app/services/snapshot_lifecycle.py#L674) | `tariff_changes.change_count` |
| 5.8 | **publication**, one transaction: docs, snapshot, changes, typed facts | [PostgresOfferingPublicationRepository.publish](../../app/repositories/monitoring.py#L1388), [publish_structured_projection](../../app/repositories/structured_projection.py#L19) | `audit_events` `offering.published` with `{"chunks":…, "changes":…, "timings":[…]}`; `current_stage=published` |
| 6 | Run closed | [process_next](../../app/worker.py#L133) | `monitoring run completed run_id=… status=succeeded review_count=0` |
| 7 | Later: embeddings for new retrieval units | [MonitoringWorker.sweep_embeddings](../../app/worker.py#L224) | `embedding sweep filled N vector(s)` |

Stage timings for a finished offering: `q "SELECT payload->'metadata'->'timings' FROM audit_events WHERE event_type='offering.published' ORDER BY id DESC LIMIT 1;"`

---

## C · The same run started from the chat (monitoring node)

"Check the overdraft tariffs now." There's no worker: the pipeline runs **inside the chat process**.

| # | Hop | Code | Evidence |
|---|---|---|---|
| 1 | `resolve_request` sees a monitoring intent → **spend grant** | [resolve_request](../../app/tools/resolution.py#L119), key [MONITOR_AUTHORIZATION_KEY](../../app/tools/_state.py#L23) | `--verbose`: `→ call run_tariff_monitoring` |
| 2 | Tool checks the grant (whole family → asks to confirm) | [run_tariff_monitoring](../../app/tools/monitoring.py#L37) | `needs_scope_confirmation` for a family |
| 3 | Tool runs the ADK node | [build_monitoring_node](../../app/services/monitoring_node.py#L160) | `monitoring_runs.trigger_type = adk` |
| 4 | Same `TariffPipeline` as in B, progress streamed to the CLI | [_progress_event](../../app/services/monitoring_node.py#L566), [STAGE_LABELS](../../app/services/monitoring_progress.py#L163) | CLI progress lines (**not** in `cli.log`); DB `current_stage` |
| 5 | Pending review → **RequestInput pause** (one per review) | [_run_to_review](../../app/services/monitoring_node.py#L446), [_review_request](../../app/services/monitoring_node.py#L532) | run `awaiting_review`; CLI shows the review panel |
| 6 | Run closed, original question answered from new facts | [_with_answer](../../app/services/monitoring_node.py#L721) | assistant answer lists changes if any |

ADK re-runs the node from the top on every resume, so each branch re-reads state from PostgreSQL. That's why a crash mid-review can be resumed with `./tariff-chat --session <same>`.

---

## D · A review, from signal to publication

| # | Hop | Code | Evidence |
|---|---|---|---|
| 1 | Signal raised with its evidence set | [detect_review_signals](../../app/services/snapshot_lifecycle.py#L237), [field_evidence_set](../../app/services/review_evidence.py#L123) | `human_reviews` `status=pending`, `reason_code`, `issue_scope`, `evidence` |
| 2 | Snapshot held as a candidate (not published) | [_review_tasks](../../app/services/monitoring_pipeline.py#L922) | `tariff_snapshots.status=review_required` |
| 3 | CLI detects the pause and shows evidence | [pending_review](../../app/cli.py#L184), [_show_review](../../app/cli.py#L666), view [build_review_view](../../app/services/review_resolution.py#L574) | the panel |
| 4 | Allowed decisions for that reason | [review_policy](../../app/services/review_resolution.py#L608) | prompt choices |
| 5 | Reviewer's reply parsed **deterministically** | [_ask_review_decision](../../app/cli.py#L793), [parse_review_field_text](../../app/services/review_input.py#L91) | — |
| 6 | Validate → apply | [ReviewResolutionService.validate](../../app/services/review_resolution.py#L143), [.apply](../../app/services/review_resolution.py#L182) → [ReviewDecisionService.apply](../../app/services/review_decisions.py#L57) | `audit_events`: `review.resume_attempt {"decision_type":"override"}` |
| 7 | Snapshot activated + published, decision remembered | [approve_with_snapshot](../../app/repositories/reviews.py#L301), [PostgresReviewDecisionMemory](../../app/repositories/review_memory.py#L99) | `review.snapshot_activated`, `review.approved {"approved":3}`; `current_stage=review_approved` |
| 8 | Run closed when nothing is pending | [ReviewResolutionService.complete_run](../../app/services/review_resolution.py#L256) | run `succeeded` |

Reject instead leads to snapshot `rejected` and `review.rejected`. A newer candidate for the same offering leads to `review.superseded`, and the older run is closed `failed` at `review_superseded`.
