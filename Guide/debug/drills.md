# Practice drills: "change X live"

[← Debug](README.md) · recipes for more: [codebase-map/recipes.md](../codebase-map/recipes.md)

Each drill was **done once on this branch (dcab33a)**, with a focused test, the full unit suite green, and the new test shown to fail without the change. Then it was reverted.
The working solution for each is in [drills/](drills/). Practise without it first, then compare:

```bash
git apply Guide/debug/drills/A2-required-collateral.diff     # see a working solution
uv run pytest tests/unit/test_snapshot_lifecycle.py -q -p no:cacheprovider
git apply -R Guide/debug/drills/A2-required-collateral.diff  # undo; app/ and tests/ are clean again
```

**The same loop every time:** find → run the covering test green → edit → rerun it → `uv run pytest tests/unit -q` (~45 s) → show it ([README §5](README.md#5--say-it-out-loud-checklist-for-a-live-change)).

| # | Drill | Size | Touches |
|---|---|---|---|
| [A1](#a1--review-at-2-pp-instead-of-3) | Large-rate threshold 3 → 2 pp | 1 line / env | config |
| [A2](#a2--make-collateral-required) | Make `collateral` required | 1 line + test | review rules |
| [A3](#a3--ignore-rate-moves-below-01-pp) | Ignore rate moves < 0.1 pp | ~25 lines | change detection |
| [A4](#a4--new-hitl-trigger-any-fee-increase) | New HITL trigger: fee increase | ~60 lines, 4 files | review pipeline |
| [B1](#b1--new-agent-tool-list_supported_products) | New agent tool | new file + 4 edits | agent, plugin, routing |
| [B2](#b2--new-route-get-apiv1offerings) | New HTTP route | ~25 lines, 3 files | API, container |
| [B3](#b3--prompt-change-end-answers-with-the-accepted-date) | Prompt change | 1 line | agent prompt |
| [B4](#b4--log-how-many-sources-were-selected) | New log line | ~10 lines | observability |
| [C1](#c1--add-an-armenian-alias) | Armenian alias for an offering | 1 line (YAML) | catalog, interpreter |
| [C2](#c2--allow-another-domain-reject-http-and-subdomains) | Allow another domain | env only | security |
| [C3](#c3--1-mb-download-limit-controlled-failure) | 1 MB download limit | env only | security, failures |
| [C4](#c4--add-a-new-offering-product-page) | Add a new offering | 3 app files + migration + 4 test fixtures | catalog, DB |
| [C5](#c5--what-if-x-is-off-or-missing) | "What if X is off/missing?" | none | explain |

---

## A1 · Review at 2 pp instead of 3

> "A 2-point rate change should already need human confirmation."

- **No code:** `HITL_LARGE_RATE_CHANGE_PERCENTAGE_POINTS=2` in `.env`, then `docker compose up -d --force-recreate api worker`. Or prefix a single local command with it. **`.env` already pins it to 3**, so changing only the code default does nothing live.
- **Chain:** `.env` → [EnvironmentSettings](../../app/config/environment.py#L127) → [load_settings](../../app/config/loader.py#L174) → [HitlSettings](../../app/config/models.py#L412) → [runtime.py](../../app/runtime.py#L298) → [TariffPipeline](../../app/services/monitoring_pipeline.py#L202) → [build_snapshot_attempt](../../app/services/snapshot_lifecycle.py#L107) → [detect_large_rate_changes](../../app/services/snapshot_lifecycle.py#L497)
- **Rule:** [`largest[0] >= threshold`](../../app/services/snapshot_lifecycle.py#grep=largest%5B0%5D%20%3E%3D%20threshold). Exactly 2.00 triggers; 1.99 doesn't. It takes the largest absolute move over `min`/`max`/`rate_pct` of `interest_rate` and `effective_rate`.
- **Test:** `uv run pytest tests/unit/test_snapshot_lifecycle.py -q -p no:cacheprovider -k threshold` (existing: `…_is_three_absolute_percentage_points`)
- **Gotcha:** the function defaults `Decimal("3")` are only used by direct calls and tests, because runtime always passes the setting. If you change them, the existing "three" test breaks.
- Solution: [A1-threshold.diff](drills/A1-threshold.diff)

## A2 · Make `collateral` required

> "If a page doesn't state collateral, a human must confirm it."

- **Edit:** add `ExtractionField.COLLATERAL,` to [_REQUIRED_TARIFF_FIELDS](../../app/services/snapshot_lifecycle.py#L46). That's the whole change.
- **Why overdraft isn't affected:** only offerings that *request* the field are checked. See [_PRODUCT_FIELDS](../../app/services/extraction_planner.py#L52) and [CATEGORY_FIELDS](../../app/services/extraction_planner.py#L115). `overdraft` and `credit_line` never ask for collateral.
- **Read at:** [extraction_is_acceptable](../../app/services/snapshot_lifecycle.py#L189), [detect_review_signals](../../app/services/snapshot_lifecycle.py#L237), [_review_item_signal](../../app/services/snapshot_lifecycle.py#L366).
- **Test:** new `test_missing_collateral_routes_to_review_until_confirmed_not_stated`. **An existing test breaks:** [test_review_fixes.py](../../tests/unit/test_review_fixes.py#L430) used COLLATERAL as its "optional field" example. Switch it to `INCOME_VERIFICATION_REQUIRED`. The full suite catches this; the single file doesn't.
- **Behaviour:** reason `missing_required_field`; the reviewer can `confirm_not_stated`. A page that explicitly says "no collateral" is FOUND (`applicable: false`), so it passes.
- Solution: [A2-required-collateral.diff](drills/A2-required-collateral.diff)

## A3 · Ignore rate moves below 0.1 pp

> "Don't alert on 14.5% → 14.55%."

- **Where:** the per-field `!=` in [compare_accepted_snapshots](../../app/services/snapshot_lifecycle.py#L701)%20!=%20after.get(field)).
- **Edit:** replace it with `_field_changed(field, before, after)`. For fields in [_RATE_FIELDS](../../app/services/snapshot_lifecycle.py#L59), walk both JSON trees in parallel and treat `min`/`max` as equal when `abs(Δ) < Decimal("0.1")`.
- **Not in** [_canonicalize](../../app/services/snapshot_lifecycle.py#L724): that would change the stored payload and its sha.
- **Shape:** rates live at `interest_rate.value[i].value.{min,max}` (strings), not at top level. `loan_amount` also has `min`/`max`, so limit the tolerance to rate fields.
- **Test:** `-k tenth`: 14.5→14.59 gives no change; 14.5→14.6 gives `["interest_rate"]`.
- **Say this before they do:** *drift*. The new snapshot still becomes the baseline, so 0.05 pp per run adds up unreported. The fix is to compare against the last *reported* value.
- Solution: [A3-rate-tolerance.diff](drills/A3-rate-tolerance.diff)

## A4 · New HITL trigger: any fee increase

> "Any fee going up since the last accepted snapshot must be confirmed by a human."

Four places, copying the `large_rate_change` pattern:
1. Add `FEE_INCREASE = "fee_increase"` to [ReviewReason](../../app/domain/review.py#L17).
2. Add `detect_fee_increases(prev, payload)` next to [detect_large_rate_changes](../../app/services/snapshot_lifecycle.py#L497) and call it in [build_snapshot_attempt](../../app/services/snapshot_lifecycle.py#L145). Pair fees with [_paired_rate_entries](../../app/services/snapshot_lifecycle.py#L604) and compare amount per currency and `rate_pct`.
3. Allowed decisions + guidance: add a branch in [review_policy](../../app/services/review_resolution.py#L608) (approve / reject_all / override).
4. Add it to the **approve tuple** in [ReviewDecisionService.apply](../../app/services/review_decisions.py#L90). Without it, approving raises `approve is valid only for a complete large-change or OCR candidate`.

- **No CLI, parser or DB change:** [_review_tasks](../../app/services/monitoring_pipeline.py#L922) already copies any signal's `previous`/`current` into the evidence, and `reason_code` is free text (no CHECK constraint).
- **Test:** `-k fee`. 5000→6000 AMD gives `REVIEW_REQUIRED` with `["fee_increase"]`, approving it accepts the snapshot, and a decrease gives nothing.
- **Limits to mention:** one signal per snapshot; added or removed fees aren't flagged; the first run has no baseline.
- Solution: [A4-fee-increase-review.diff](drills/A4-fee-increase-review.diff) (+ doc row in `docs/native-hitl-review.md`)

---

## B1 · New agent tool `list_supported_products`

> "Let the agent tell users which products it covers."

- **Say this first:** it half-exists. The intent [LIST_SUPPORTED_PRODUCTS](../../app/domain/intent.py#L18) exists, and [resolve_request](../../app/tools/resolution.py#L204) already returns `supported_catalog` for it. It just routes to no tool ([_ROUTES](../../app/domain/interpretation.py#L146)).
- **Edits:**
  1. New `app/tools/catalog.py`: `async def list_supported_products(tool_context)` → `services.request_resolver.catalog_payload(language, complete=True)`. No arguments, so least privilege holds.
  2. Export it in [app/tools/\_\_init\_\_.py](../../app/tools/__init__.py).
  3. Append it to [TOOLS](../../app/agent.py#L55), and mention it inside an **existing** line of [INSTRUCTION](../../app/agent.py#L28).
  4. Add it to [BUSINESS_TOOLS](../../app/plugins.py#L22) (gated, like `get_monitoring_status`; a judgment call you can defend either way).
  5. Point `_ROUTES[LIST_SUPPORTED_PRODUCTS]` at `"list_supported_products"`.
- **Tests that pin things:** [test_the_agent_exposes_exactly_the_seven_tools](../../tests/unit/test_agent_wiring.py#L22) (exact set; rename it to eight). [test_the_prompt_is_short…](../../tests/unit/test_agent_wiring.py#L41) requires **≤ 25 lines, and the prompt is already at 25**, and bans phrases like "do not call". `test_plugins.py` picks up BUSINESS_TOOLS automatically.
- **Run:** `uv run pytest tests/unit/test_agent_wiring.py tests/unit/test_plugins.py -q -p no:cacheprovider`. Full suite: 1212 passed.
- **Show:** `--verbose` chat, "What products do you cover?", then `→ call list_supported_products`.
- **Also:** the eval case in `tests/eval/datasets/expanded-intent-safety.json` expects "call only resolve_request" for this intent, so it's now stale. `docs/architecture.md` says "seven tools".
- Solution: [B1-new-tool.diff](drills/B1-new-tool.diff)

## B2 · New route `GET /api/v1/offerings`

> "Expose the list of monitored offerings over the API."

- **Edits:**
  1. [ApplicationContainer](../../app/runtime.py#L90) gets `catalog: SeedCatalog | None = None`. Pass the already-loaded catalog in the return of [build_application_container](../../app/runtime.py#L123).
  2. In [lifespan](../../app/fast_api_app.py#L49), set `app.state.seed_catalog = container.catalog`.
  3. In [routes.py](../../app/api/routes.py), add an `OfferingSummary` model, a `get_seed_catalog(request)` dependency (copy [get_run_service](../../app/api/routes.py#L70)) and `@router.get("/offerings")` listing enabled entries.
- **Why a container field:** the catalog was private inside the resolver. The alternatives are loading it twice or reaching into `_catalog`.
- **Test:** a bare `FastAPI()` + `app.state.seed_catalog = load_seed_catalog()` + `include_router(router)` + `httpx.ASGITransport` ([test_trigger_adapters.py](../../tests/unit/test_trigger_adapters.py)).
- **Show:** `Guide/debug/local.sh uvicorn app.fast_api_app:app --port 8090 --reload`, then `curl -s localhost:8090/api/v1/offerings | jq '.[].offering_id'`. That gives 13 offerings, and `/openapi.json` lists the route.
- Solution: [B2-new-route.diff](drills/B2-new-route.diff)

## B3 · Prompt change: end answers with the accepted date

> "Every tariff answer should end with when the data was accepted."

- **Grounding first:** the model does receive the date. `as_of` on [TariffQueryResult](../../app/domain/structured_tariffs.py#L667) is the profile's `accepted_at`, and [model_facing_query_result](../../app/services/tariff_queries.py#L374) keeps it.
- **Edit:** one existing line of [INSTRUCTION](../../app/agent.py#L28): `…and end each tariff answer with "Accepted: <date>" from its as_of.` **Don't add a line**, because the 25-line cap test fails at 26.
- **Test:** add an assertion in [test_agent_wiring.py](../../tests/unit/test_agent_wiring.py). Evals are LLM-judged rubrics, so there's no exact-text breakage.
- **Show:** `printf 'What is the overdraft interest rate?\n' | Guide/debug/local.sh python app/cli_entry.py --session drill --verbose` (~$0.015) shows the last line `Accepted: 2026-…`. *Not checked in a live chat: Gemini credits ran out during the drill.*
- **Principle to say:** the prompt only controls presentation. Scope, order and grants are enforced in code ([ToolPolicyPlugin](../../app/plugins.py#L34)).
- Solution: [B3-prompt.diff](drills/B3-prompt.diff)

## B4 · Log how many sources were selected

> "I want to see in the logs how many sources discovery kept per offering."

- **Where:** in [IndexingPipeline.refresh](../../app/services/monitoring_pipeline.py#L226), right after [`audit.record_source_discovery(...)`](../../app/services/monitoring_pipeline.py#L340).
- **Edit:**
  ```python
  discovered = select_sources(discovery)
  logger.info(
      "source discovery selected run_id=%s offering_id=%s documents=%d items=%d assessments=%d",
      run_id, offering.offering_id.value, len(discovered.document_ids), len(discovered.items), len(discovery.assessments),
  )
  ```
  Use [select_sources](../../app/services/source_selection.py#L58), the same definition of "selected" that extraction uses. Don't count raw assessments. Follow the file's key=value log style.
- **Test:** `caplog` in [test_monitoring_pipeline.py](../../tests/unit/test_monitoring_pipeline.py). Run `-k logs_how_many`.
- **Find it:** `grep "source discovery selected" logs/worker.log logs/cli.log local-run/logs/local.log`. The worker logs API runs, `cli.log` gets `./tariff-chat` runs, and `local.log` gets `local.sh` runs. Docker needs a rebuild first.
- Solution: [B4-log-line.diff](drills/B4-log-line.diff)

---

## C1 · Add an Armenian alias

> "Users say «օվերդրաֆտային վարկ». Make the agent recognise it."

- **Edit:** append to the `hy` `aliases` of `overdraft` in [seed_catalog.yaml](../../app/config/seed_catalog.yaml#L56). No code.
- **Who matches it: both.**
  - **Gemini** gets every alias, synonym and transliteration as `also_called` ([_catalog_entry](../../app/services/intent_resolution.py#L508)).
  - **Code** cross-checks exact normalized terms ([_exact_offerings](../../app/services/intent_resolution.py#L447), Armenian suffixes in [_ARMENIAN_SUFFIXES](../../app/services/intent_resolution.py#L73)).
  - If the two disagree, [_cross_check](../../app/services/interpretation_validation.py#L401) turns it into a clarifying question.
- **Validation:** [normalize_catalog_term](../../app/domain/catalog.py#L29) applies NFKC, casefold and punctuation→space. After that, no duplicates within an offering and no collisions across offerings ([_validate_term_collisions](../../app/domain/catalog.py#L190)). A bad catalog **stops api/worker startup**.
- **Test:** `uv run pytest tests/unit/test_seed_catalog.py tests/unit/test_intent_resolution.py -q -p no:cacheprovider`
- **Show (no model call):**
  ```bash
  uv run python -c "from app.config import load_seed_catalog; from app.config.models import IntentResolutionSettings; from app.domain.catalog import normalize_catalog_term as n; from app.services.intent_resolution import RequestResolver; print(RequestResolver(load_seed_catalog(), IntentResolutionSettings(), interpreter=None)._exact_offerings(n('օվերդրաֆտային վարկի տոկոսադրույքը')))"
  ```
  Before the edit it prints `()`; after, `(<OfferingId.OVERDRAFT…>,)`.
- **Gotchas:**
  - Reusing another offering's name (e.g. `Վարկային գիծ`) raises `SeedCatalogError`.
  - An **alias** also goes into the extraction prompt (a synonym doesn't), so the next run of that offering misses the extraction cache and costs Gemini calls.
  - The YAML is in the image: rebuild for Docker.
- Solution: [C1-armenian-alias.diff](drills/C1-armenian-alias.diff)

## C2 · Allow another domain; reject http and subdomains

> "Also allow acba.am." / "Can it be tricked into another host?"

- **No code:** `ALLOWED_SOURCE_HOSTS=ameriabank.am,www.ameriabank.am,www.acba.am` in `.env`, then `docker compose up -d --force-recreate api worker`. The effective default is [EnvironmentSettings](../../app/config/environment.py#L34); [HttpSettings](../../app/config/models.py#L113) only matters when it's built directly (tests).
- **At startup:** [validate_source_hosts](../../app/config/models.py#L135) rejects `://`, wildcards, ports, paths and IPs. Every catalog `seed_url` must be on the list, or startup fails.
- **Per request:** [validate_source_url](../../app/security/urls.py#L9) requires https, a host that is not an IP literal, an **exact** host match, no credentials, and port 443 only. It runs on the first fetch **and on every redirect hop** (HTML, PDF, and each browser request).
- **"Reject http / subdomains" is already the behaviour:**

  | URL | Result |
  |---|---|
  | `https://www.ameriabank.am/x` | ok (listed explicitly) |
  | `https://WWW.AmeriaBank.am./x`, `…:443/x` | ok (normalized) |
  | `https://evil.ameriabank.am/x` | rejected, no wildcard subdomains |
  | `https://ameriabank.am.attacker.com/x`, `https://ameriabank.am@evil.com/x` | rejected |
  | `http://ameriabank.am/x` | rejected, "must use HTTPS" |
  | `https://[::1]/x` | rejected, IP literal |

- **Off-list PDF links are silently skipped** (marked not `same_allowlisted_source` by the parser), so they're neither fetched nor failed.
- **Tests:** [C2-allowlist-tests.diff](drills/C2-allowlist-tests.diff) adds two tests to [test_source_urls.py](../../tests/unit/test_source_urls.py): rejected before the host is added, and after adding it only the exact host passes. `-q` gives 11 passed.
- **Gotcha:** [offering_context_for](../../app/services/source_discovery.py#L66) loads the catalog with the hard-coded default hosts. That's fine at runtime, but a demo helper breaks for a non-Ameria seed URL.

## C3 · 1 MB download limit: controlled failure

> "Lower the download limit and show what happens."

- **No code:** `MAX_DOWNLOAD_BYTES=1048576`. As with A1, changing only [HttpSettings](../../app/config/models.py#L122) does nothing, because the env default wins.
- **Enforced on the header and on the streamed body:**
  - [HtmlRetriever](../../app/services/html_retriever.py#L194)
  - [PdfDownloader](../../app/services/pdf_downloader.py#L268)
  - the browser renderer
  - All three map to `source.size_rejected` ([source_failure_code](../../app/services/failure_mapping.py#L49)).
- **The outcome depends on what's too big:**
  - **Seed page** fails the `acquisition` stage, so the offering fails and the run is `failed`. A too-large *rendered* page is retried once first.
  - **Linked PDF** is only a warning (`acquisition.linked_document_failed`) and is skipped. Later, if fields that the previous snapshot had are now missing, the offering fails `source.linked_document_unavailable`, so values are never published as "removed". See [_fields_lost](../../app/services/monitoring_pipeline.py#L905).
- **Gotcha:** within `ACQUISITION_FRESHNESS_HOURS` (1 h) the last fetch is reused and nothing is downloaded, so set `ACQUISITION_FRESHNESS_HOURS=0`. At 1 MB the HTML page may still pass, which is why the demo uses 50 KB.
- **Existing demo:** the [size-limit.yml](../../Presentation-demonstrations/Controlled-failures/failures/size-limit.yml) overlay (`MAX_DOWNLOAD_BYTES: "50000"`). `python3 failure_demo.py --failure size-limit` fails in 6 s at `acquisition` with `source.size_rejected`, cause `HtmlRetrievalError:PAGE_TOO_LARGE`, 0 model calls, and published data unchanged.
- **Tests (no DB, mock transport):** `uv run pytest tests/integration/test_pdf_downloader.py tests/integration/test_html_retriever.py tests/unit/test_failure_mapping.py -q -p no:cacheprovider`. [C3-size-limit.diff](drills/C3-size-limit.diff) adds a header-path PDF test.

## C4 · Add a new offering (product page)

> "Start monitoring a car loan page."

1. Add the id to [OfferingId](../../app/domain/models.py#L12), **and** to the consumer set in [OfferingId.product](../../app/domain/models.py#L28). Otherwise it's treated as a mortgage and catalog load fails.
2. Add a catalog entry in [seed_catalog.yaml](../../app/config/seed_catalog.yaml#L25): `product`, `offering_id`, `display_name` (= en name), https `seed_url` on an allowed host, and `en` + `hy` names.
3. Add a baseline in [normalization_baseline.json](../../app/config/normalization_baseline.json). It's optional at runtime, but **required by a test** (`test_the_shipped_baseline_covers_every_enabled_seed`).
4. **DB:** the four CHECK constraints in [006](../../migrations/006_monitoring_pipeline_foundation.sql#L35) list the ids. No later migration touches them. Ready file: [C4-028_car_loan_offering.sql](drills/C4-028_car_loan_offering.sql) (tested on this DB inside a rolled-back transaction). Apply it with `docker compose exec -T db psql -U tariff -d tariff_monitor < migrations/028_….sql`.
5. **Tests that hard-code the set** (8 fail after steps 1–2, and that list is your checklist):
   - [test_seed_catalog.py](../../tests/unit/test_seed_catalog.py) (13 offerings / 4 consumer)
   - [test_intent_resolution.py](../../tests/unit/test_intent_resolution.py) (13)
   - [test_tariff_queries.py](../../tests/unit/test_tariff_queries.py) (4 consumer)
   - `CONSUMER_FAMILY` in [target_questions.py](../../tests/fixtures/target_questions.py)

   Once they're updated: 1208 passed.
6. No app code changes: everything iterates `OfferingId` / the catalog, and family runs pick it up.

- **Without the migration** the code runs, but the first run's INSERT fails with a CHECK violation.
- Solution: [C4-new-offering.diff](drills/C4-new-offering.diff) + [C4-028_car_loan_offering.sql](drills/C4-028_car_loan_offering.sql)

## C5 · "What if X is off or missing?"

Each answer names the line that decides it and the one test that proves it.

| If… | Then | Decided at | Prove it |
|---|---|---|---|
| `OCR_ENABLED=false` and a page has no text layer | Gemini usually transcribes scanned pages anyway. OCR only fills pages Gemini left empty. Off: the page **stays empty, no warning**. Its values end up missing, so a required one becomes a `missing_required_field` review | [_pages_needing_ocr](../../app/services/pdf_extraction.py#L230), [_apply_ocr](../../app/services/pdf_extraction.py#L355) | `uv run pytest tests/unit/test_ocr_fallback.py -k disabled_ocr -q` |
| …and every Gemini model fails too | no OCR rescue: `PDF_MODEL_FAILED`. If previous values would vanish, the offering fails `source.linked_document_unavailable` | [_ocr_only](../../app/services/pdf_extraction.py#L383) | `-k all_models_failed_with_no_ocr` |
| `ACQUISITION_BROWSER_ENABLED=false` | static HTML only. The tariff tables and PDF links exist only after rendering, so it fails the content floor or the baseline, is retried once, then fails `source.incomplete_content` @ acquisition. Cached fetches hide it for 1 h | [build_acquisition_service](../../app/services/acquisition.py#L413), [completeness_floor_failures](../../app/services/acquisition.py#L58) | `uv run pytest tests/unit/test_acquisition.py tests/unit/test_acquisition_completeness.py -q` |
| Gemini down for source discovery | per model, retries on 429/5xx (3×), then the next model in `SOURCE_DISCOVERY_FALLBACK_MODEL_NAMES`. All fail: `source.model_failed` @ `pdf_selection` or `source_discovery`, no snapshot; other offerings continue (`partial_success`). Rule-decided and cached sections need no model | [FallbackSourceDiscoveryService](../../app/services/source_discovery.py#L422), [is_model_fallback_error](../../app/services/discovery_classifier.py#L315) | `uv run pytest tests/unit/test_source_discovery.py tests/unit/test_pdf_link_selection.py -q`; recorded in [model-failure.yml](../../Presentation-demonstrations/Controlled-failures/failures/model-failure.yml) demo |
| No previous snapshot (first run) | no large-rate check, no lost-fields guard; change set with `changes=()` stored as `change_count 0` ("no changes", not "all added"). Other review triggers still apply | [compare_accepted_snapshots](../../app/services/snapshot_lifecycle.py#L680) | `uv run pytest tests/unit/test_change_detection.py tests/unit/test_snapshot_lifecycle.py -q` |
| `PIPELINE_AUDIT_ENABLED=false` | only the `artifacts/pipeline-audit/*.md` files disappear. Run, DB `audit_events`, snapshots and reviews are unchanged. Write errors never fail a run | [runtime.py](../../app/runtime.py#L269), [FileSystemPipelineAuditArchive](../../app/services/pipeline_audit_archive.py#L89) | `-k audit_failure_does_not_fail_the_run` in `test_monitoring_pipeline.py` |
