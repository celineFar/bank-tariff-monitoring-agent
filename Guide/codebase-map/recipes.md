# Recipes: likely "change X" tasks

[← Guide](README.md)

**Every change ends the same way:**
1. Run the closest unit test: `uv run pytest tests/unit/<file> -q` ([which file](6-tests-evals-demos.md))
2. Apply it:
   - **code** change → `docker compose up --build -d api worker`
   - **`.env`** change only → `docker compose up -d --force-recreate api worker`
3. Try it: `./tariff-chat`, or `curl -X POST localhost:8080/api/v1/runs -H 'content-type: application/json' -d '{"product":"consumer_loan","offering_id":"overdraft"}'` (request body: [RunRequest](../../app/api/routes.py#L53))

---

## Settings only (no code)

| Change | Env var in `.env` | Default in code |
|---|---|---|
| Large rate change threshold | `HITL_LARGE_RATE_CHANGE_PERCENTAGE_POINTS=3` | [HitlSettings](../../app/config/models.py#L412) |
| Allowed domains | `ALLOWED_SOURCE_HOSTS=ameriabank.am,www.ameriabank.am` | [HttpSettings](../../app/config/models.py#L113) |
| Max download size | `MAX_DOWNLOAD_BYTES=26214400` | [HttpSettings](../../app/config/models.py#L122) |
| HTTP timeout / retries | `DOWNLOAD_TIMEOUT_SECONDS`, `HTTP_MAX_ATTEMPTS`, `HTTP_BACKOFF_BASE_SECONDS` | [HttpSettings](../../app/config/models.py#L116) |
| Chat / extraction model | `MODEL_NAME` | [ModelSettings](../../app/config/models.py#L63) |
| Discovery / PDF model | `SOURCE_DISCOVERY_MODEL_NAME`, `PDF_EXTRACTION_MODEL_NAME` | [SourceDiscoverySettings](../../app/config/models.py#L336), [PdfExtractionSettings](../../app/config/models.py#L223) |
| Schedule time / off | `SCHEDULE_HOUR`, `SCHEDULE_MINUTE`, `SCHEDULE_ENABLED` | [SchedulerSettings](../../app/config/models.py#L416) |
| Freshness (days before "stale") | `TARIFF_FRESHNESS_DAYS` | [TariffQuerySettings](../../app/config/models.py#L309) |
| Re-fetch instead of reusing the last page | `ACQUISITION_FRESHNESS_HOURS=0` | [AcquisitionSettings](../../app/config/models.py#L211) |
| OCR on/off, confidence floor | `OCR_ENABLED`, `OCR_MIN_CONFIDENCE` | [OcrSettings](../../app/config/models.py#L248) |

A new model must be listed in [MODEL_PRICE_CATALOG](../../app/services/model_pricing.py#L18), or the startup price cap check ([enforce_model_price_cap](../../app/services/model_pricing.py#L150)) refuses it.

---

## Add a new setting
1. Add the flat env field to [EnvironmentSettings](../../app/config/environment.py#L10).
2. Add the typed field to the right group in [models.py](../../app/config/models.py#L45).
3. Map it in [load_settings](../../app/config/loader.py#L28).
4. Add it to [.env.example](../../.env.example). Read it via `settings.<group>.<field>` where the service is built in [runtime.py](../../app/runtime.py#L123).
5. Test: [test_config.py](../../tests/unit/test_config.py).

## Change the agent's wording / behaviour
- Prompt: [INSTRUCTION](../../app/agent.py#L28). Keep it to language and presentation. Tool order and scope are enforced by code ([ToolPolicyPlugin](../../app/plugins.py#L34), [resolve_request](../../app/tools/resolution.py#L48)).
- If the model is missing a piece of information, add it to the tool's return payload instead ([reads.py](../../app/tools/reads.py), [monitoring.py](../../app/tools/monitoring.py)).

## Add a new agent tool
1. Write `async def my_tool(tool_context: ToolContext) -> dict` in [app/tools/](../../app/tools/), next to [reads.py](../../app/tools/reads.py#L56). Reach services through the shared [services](../../app/tools/_services.py#L27) object, e.g. `services.answer_router`. Never accept a URL, SQL or path argument.
2. Export it in [app/tools/\_\_init\_\_.py](../../app/tools/__init__.py).
3. Add it to [TOOLS](../../app/agent.py#L55) and mention it in [INSTRUCTION](../../app/agent.py#L28).
4. If it reads business data, add its name to [BUSINESS_TOOLS](../../app/plugins.py#L22). The plugin then requires `resolve_request` first.
5. If an intent should route to it, update [route_for / _ROUTES](../../app/domain/interpretation.py#L139).
6. Test: [test_agent_wiring.py](../../tests/unit/test_agent_wiring.py), [test_tool_flows.py](../../tests/unit/test_tool_flows.py).

## Add an HTTP route
1. Add a handler to [routes.py](../../app/api/routes.py) with `@router.get/post(...)`. Copy [get_run](../../app/api/routes.py#L156).
2. Get services with a `Depends(get_…)` helper ([get_run_service](../../app/api/routes.py#L70)). They read `request.app.state`, which is filled in [lifespan](../../app/fast_api_app.py#L49).
3. Test: [test_trigger_adapters.py](../../tests/unit/test_trigger_adapters.py).

## Add a synonym / Armenian name for a product
Edit `aliases` / `synonyms` / `transliterations` for that entry in [seed_catalog.yaml](../../app/config/seed_catalog.yaml). Test: [test_seed_catalog.py](../../tests/unit/test_seed_catalog.py).

## Add a new offering (product page)
1. Add an entry to [seed_catalog.yaml](../../app/config/seed_catalog.yaml#L25): `product`, `offering_id`, `category` (optional: `overdraft`/`credit_line`/…), `seed_url`, names.
2. Add the id to [OfferingId](../../app/domain/models.py#L12). If it is a consumer loan, also add it to the set in [OfferingId.product](../../app/domain/models.py#L27).
3. **DB**: four CHECK constraints list the offering ids in [006](../../migrations/006_monitoring_pipeline_foundation.sql#L35) (`monitoring_runs`, `offering_executions`, `source_manifests`, `tariff_snapshots`). Write `migrations/028_….sql` that drops each one and adds it back with the new id. Apply it (see [README](README.md#run-rebuild-test)).
4. Add a structure baseline to [normalization_baseline.json](../../app/config/normalization_baseline.json). It is optional at runtime, but `test_the_shipped_baseline_covers_every_enabled_seed` in [test_normalization_baseline.py](../../tests/unit/test_normalization_baseline.py) requires one per enabled seed.
5. Update the tests that hard-code the offering set: counts in [test_seed_catalog.py](../../tests/unit/test_seed_catalog.py), [test_intent_resolution.py](../../tests/unit/test_intent_resolution.py) and [test_tariff_queries.py](../../tests/unit/test_tariff_queries.py), plus `CONSUMER_FAMILY` in [target_questions.py](../../tests/fixtures/target_questions.py). Run `uv run pytest tests/unit -q`: the failures are the checklist.
6. Worked, tested example: [debug/drills.md → C4](../debug/drills.md#c4--add-a-new-offering-product-page).

## Add / change an extracted field
Trace an existing field with a similar type (e.g. `grace_period_days`, an int) and copy it:
1. [ExtractionField](../../app/domain/semantic_extraction.py#L444) enum value, plus the attribute on [LoanProduct](../../app/domain/semantic_extraction.py#L419) or a category details model ([OverdraftDetails](../../app/domain/semantic_extraction.py#L398) …).
2. Which offerings ask for it: [_GROUPS](../../app/services/extraction_planner.py#L18) (common fields) or [_PRODUCT_FIELDS](../../app/services/extraction_planner.py#L52) + [CATEGORY_FIELDS](../../app/services/extraction_planner.py#L115) (per category).
3. Keyword terms: [FIELD_TERMS](../../app/domain/extraction_terms.py#L22).
4. Type adapter: [_field_adapter](../../app/services/semantic_extraction.py#L2440). Assembly: [assemble_loan_product](../../app/services/semantic_extraction.py#L2760). If numbers must appear in the quote, add it to [_GROUNDED_FIELDS](../../app/services/semantic_extraction.py#L1815).
5. Reviewer entry format: [_FORMATS](../../app/services/review_input.py#L488).
6. Answering: [FieldPath](../../app/domain/structured_tariffs.py#L19), [FIELD_LABELS](../../app/domain/structured_tariffs.py#L92), [SOURCE_FIELD_PATHS](../../app/domain/structured_tariffs.py#L341). For a non-scalar type, also add a branch in [StructuredTariffProjector.project](../../app/services/structured_projection.py#L168). If it should be rankable, add it to [RANKABLE_PATHS](../../app/domain/tariff_comparison.py#L26).
7. Required? Add it to [_REQUIRED_TARIFF_FIELDS](../../app/services/snapshot_lifecycle.py#L46).
8. Bump `SEMANTIC_EXTRACTION_SCHEMA_VERSION` ([default](../../app/config/models.py#L372)).
9. Test: [test_semantic_extraction.py](../../tests/unit/test_semantic_extraction.py), [test_review_input.py](../../tests/unit/test_review_input.py), [test_structured_projection.py](../../tests/unit/test_structured_projection.py).
No migration is needed, because values are stored as JSON.

## Change a validation rule for extracted values
- Per-field checks (evidence ids, quote in source, numbers in quote): [_validate_field_result](../../app/services/semantic_extraction.py#L2379), [_validate_individual_fields](../../app/services/semantic_extraction.py#L2252).
- Value types and bounds (e.g. a rate is ≥ 0 and min ≤ max): Pydantic models such as [Rate](../../app/domain/semantic_extraction.py#L228), [TermRange](../../app/domain/semantic_extraction.py#L270), [MoneyRange](../../app/domain/semantic_extraction.py#L162).
- A failing field becomes an `extraction_invalid` review ([_review_item](../../app/services/semantic_extraction.py#L2500)). It does not fail the run.
- Test: [test_semantic_extraction_fixes.py](../../tests/unit/test_semantic_extraction_fixes.py).

## Add a new HITL review trigger
1. Add a value to [ReviewReason](../../app/domain/review.py#L17).
2. Raise it in [detect_review_signals](../../app/services/snapshot_lifecycle.py#L237) with `_signal("<reason>", field, evidence_set)`. Copy the `large_rate_change` pattern in [detect_large_rate_changes](../../app/services/snapshot_lifecycle.py#L497) if it compares against the previous snapshot.
3. Allowed decisions + guidance text: [review_policy](../../app/services/review_resolution.py#L608).
4. If `approve` is one of its decisions, also add the reason to the tuple at [review_decisions.py:90](../../app/services/review_decisions.py#L90). Otherwise the approval is rejected there.
5. Test: [test_snapshot_lifecycle.py](../../tests/unit/test_snapshot_lifecycle.py), [test_review_resolution.py](../../tests/unit/test_review_resolution.py).
The `reason_code` column is free text, so no migration is needed.

## Change what counts as a "change"
[compare_accepted_snapshots](../../app/services/snapshot_lifecycle.py#L674) compares canonical values with `!=`, field by field. To ignore a field or add a tolerance, filter inside that comprehension. To normalize formatting, change [_canonicalize](../../app/services/snapshot_lifecycle.py#L724). Test: [test_snapshot_lifecycle.py](../../tests/unit/test_snapshot_lifecycle.py).

## Change a Gemini prompt

| Prompt | Where | Also do |
|---|---|---|
| Chat agent | [INSTRUCTION](../../app/agent.py#L28) | — |
| Request interpreter | [INTERPRETER_INSTRUCTION](../../app/services/intent_resolution.py#L98) | re-record: [record_interpretations.py](../../scripts/record_interpretations.py) |
| PDF link selection | [PDF_LINK_INSTRUCTION](../../app/services/pdf_link_selection.py#L46) | bump [PDF_LINK_PROMPT_VERSION](../../app/services/pdf_link_selection.py#L43) |
| PDF transcription | [PDF_EXTRACTION_INSTRUCTION](../../app/services/gemini_pdf_extractor.py#L38) | bump `PDF_EXTRACTION_PROMPT_VERSION` |
| Source discovery | [SOURCE_DISCOVERY_INSTRUCTION](../../app/services/discovery_classifier.py#L27) | bump `SOURCE_DISCOVERY_PROMPT_VERSION` |
| Semantic extraction | [SEMANTIC_EXTRACTION_INSTRUCTION](../../app/services/semantic_extraction.py#L92) | cache invalidates itself ([prompt_fingerprint](../../app/services/semantic_extraction.py#L603)); bump `SEMANTIC_EXTRACTION_PROMPT_VERSION` for the record |

Without the version bump, runs silently reuse the cached answers from the old prompt.

## Change a rule-based (no-model) decision
- Which PDFs are skipped by link text: [pdf_admission.py](../../app/services/pdf_admission.py#L17) term lists.
- Which page sections are decided without the model: [_rule_assessment](../../app/services/source_discovery.py#L500).
- Minimum page content: [completeness_floor_failures](../../app/services/acquisition.py#L58).
- When a page is sent to OCR: [_pages_needing_ocr](../../app/services/pdf_extraction.py#L230), and the text threshold `PDF_EXTRACTION_PROBE_TEXT_THRESHOLD`.

---

## Diagnose a failed or odd run
1. **What failed**: the chat prints `failure_summary`. Or run `curl localhost:8080/api/v1/runs/<run_id>`.
2. **Which stage**:
   ```bash
   docker compose exec -T db psql -U tariff -d tariff_monitor -c \
     "SELECT offering_id, status, current_stage, failure_code, failure_detail FROM offering_executions ORDER BY created_at DESC LIMIT 5;"
   ```
3. **What the code means**: look it up in [_FAILURE_EXPLANATIONS](../../app/services/failure_mapping.py#L152). Find where the exception mapped to it in [source_failure_code](../../app/services/failure_mapping.py#L49).
4. **Logs**: `docker compose logs --tail=200 worker api`, or [logs/](../../logs/) (`worker.log`, `api.log`, `cli.log`).
5. **What each stage saw**: `artifacts/pipeline-audit/run_<run_id>/<offering_id>/`. The `2_*` files cover normalization, `3_*` source selection and `4_*` extraction evidence, validation and review queue.
6. **Events**: `SELECT event_type, payload FROM audit_events WHERE run_id='<id>' ORDER BY id;`. Reviews are in `human_reviews` (`reason_code`, `issue_scope`, `status`).
7. **Stuck paused run**: `./tariff-chat` offers to continue the review. Or reject all pending with `POST /api/v1/reviews/abort-pending` (needs `REVIEW_ADMIN_TOKEN`).
8. **Cost**: `uv run python scripts/model_cost_report.py --days 1`.
