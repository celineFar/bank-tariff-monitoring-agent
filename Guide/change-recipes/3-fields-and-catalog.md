# 3 · Extracted fields and the product catalog

[← Change recipes](README.md)

---

## E · Add a new extracted field
✅ dry-run: `early_repayment_allowed` (bool, consumer loans). Full unit suite: 1208 passed, plus 3 new tests.
**Ask:** "also extract whether early repayment is allowed".

**Pick a model field of the same type and copy its trail.**

| New field's type | Copy the trail of |
|---|---|
| bool | `revolving` |
| int | `grace_period_days` |
| string | `linked_account_or_card` |
| list of strings | `eligibility` |
| rate | `interest_rate` |
| money | `loan_amount` |

Run `grep -rn "REVOLVING\b" app` to list every place a field is registered.

**Nine edits, in this order.** Snippets are from the dry run.

1. **Enum:** [ExtractionField](../../app/domain/semantic_extraction.py#L444), after [line 472](../../app/domain/semantic_extraction.py#L472):
   ```python
   EARLY_REPAYMENT_ALLOWED = "early_repayment_allowed"
   ```
2. **Model attribute**, named **exactly** like the enum value. The projector maps attributes back with
   `ExtractionField(name)` in [_extracted_fields](../../app/services/structured_projection.py#L442).
   For one category, put it on its details model, [ConsumerLoanDetails](../../app/domain/semantic_extraction.py#L380).
   For every category, put it on [LoanProduct](../../app/domain/semantic_extraction.py#L419).
   ```python
   # Defaulted: results stored before the field existed must still load.
   early_repayment_allowed: ExtractedValue[bool] = ExtractedValue[bool](
       status=ExtractionStatus.NOT_STATED
   )
   ```
   **Gotcha:** without the default, every snapshot stored before today fails to load. That includes
   the review path and the read path, which call `SemanticExtractionResult.model_validate(...)`.
3. **Which offerings ask for it:** [CATEGORY_FIELDS](../../app/services/extraction_planner.py#L115)`["consumer_loan"]` *and*
   [_PRODUCT_FIELDS](../../app/services/extraction_planner.py#L52)`[CONSUMER_LOAN]` (used when an offering has no category).
   A field for every category goes in a group of [_GROUPS](../../app/services/extraction_planner.py#L18) instead.
4. **Label words** (budgeted evidence mode looks fields up here, and a missing key is a `KeyError`):
   [FIELD_TERMS](../../app/domain/extraction_terms.py#L22), after [line 173](../../app/domain/extraction_terms.py#L173):
   ```python
   ExtractionField.EARLY_REPAYMENT_ALLOWED: ("early repayment", "prepayment", "repay early"),
   ```
5. **Type + assembly** in [semantic_extraction.py](../../app/services/semantic_extraction.py):
   - [_field_adapter](../../app/services/semantic_extraction.py#L2440), after [line 2473](../../app/services/semantic_extraction.py#L2473): `ExtractionField.EARLY_REPAYMENT_ALLOWED: bool,`
   - [assemble_loan_product](../../app/services/semantic_extraction.py#L2760), inside `details = ConsumerLoanDetails(` at [line 2891](../../app/services/semantic_extraction.py#L2891):
     ```python
     early_repayment_allowed=value(ExtractionField.EARLY_REPAYMENT_ALLOWED, bool),
     ```
   - Prompt hint, in "Expected value shapes" at [line 184](../../app/services/semantic_extraction.py#L184) (the per-field JSON Schema is generated from the adapter; this line gives the *meaning*):
     ```text
     - early_repayment_allowed: true when the evidence says the loan may be repaid
       before maturity (with or without a fee), false when it says it may not
     ```
   - If its numbers must appear in the cited quote, add it to [_GROUNDED_FIELDS](../../app/services/semantic_extraction.py#L1815).
6. **Reviewer entry format** (a test checks that every field has one): [_FORMATS](../../app/services/review_input.py#L488), after the `REVOLVING` entry at [line 662](../../app/services/review_input.py#L662):
   ```python
   _format(
       ExtractionField.EARLY_REPAYMENT_ALLOWED,
       "Enter 'yes' or 'no'.",
       ("yes",),
       _parse_bool,
   ),
   ```
7. **Answer read model** in [structured_tariffs.py](../../app/domain/structured_tariffs.py). Both registries are
   checked **at import**: miss one and every process dies with `RuntimeError` at startup
   ([line 331](../../app/domain/structured_tariffs.py#L331), [line 422](../../app/domain/structured_tariffs.py#L422)).
   - [FieldPath](../../app/domain/structured_tariffs.py#L19): `EARLY_REPAYMENT_ALLOWED = "repayment.early_allowed"`
   - [FIELD_LABELS](../../app/domain/structured_tariffs.py#L92), English + Armenian (used for retrieval text):
     ```python
     FieldPath.EARLY_REPAYMENT_ALLOWED: (
         "early repayment allowed",
         "վաղաժամկետ մարման հնարավորություն",
     ),
     ```
   - [SOURCE_FIELD_PATHS](../../app/domain/structured_tariffs.py#L341), after [line 419](../../app/domain/structured_tariffs.py#L419):
     `ExtractionField.EARLY_REPAYMENT_ALLOWED: (FieldPath.EARLY_REPAYMENT_ALLOWED,),`
   - Scalars (bool/int/str, or a list of them) need nothing more: the generic branch of
     [StructuredTariffProjector.project](../../app/services/structured_projection.py#L375) emits them.
     A new *structured* type needs its own branch there. A number users rank by goes in
     [RANKABLE_PATHS](../../app/domain/tariff_comparison.py#L26).
8. **Optional:** required? Add it to [_REQUIRED_TARIFF_FIELDS](../../app/services/snapshot_lifecycle.py#L46).
9. **Bump the schema version in `.env`**: `SEMANTIC_EXTRACTION_SCHEMA_VERSION=7`. Your `.env` pins it to `6`
   ([.env.example:97](../../.env.example#L97)), so changing the default in
   [models.py:372](../../app/config/models.py#L372) alone does nothing.

**Test** (new file):
```python
from app.domain.models import ProductType
from app.domain.semantic_extraction import ConsumerLoanDetails, ExtractionField, ExtractionStatus
from app.domain.structured_tariffs import SOURCE_FIELD_PATHS, FieldPath
from app.services.extraction_planner import field_groups
from app.services.review_input import parse_review_field_text

F = ExtractionField.EARLY_REPAYMENT_ALLOWED

def asked(category):
    return {f for _, fields in field_groups(ProductType.CONSUMER_LOAN, category) for f in fields}

def test_asked_for_consumer_loans_only():
    assert F in asked("consumer_loan") and F not in asked("overdraft")

def test_old_stored_details_still_load():
    old = {"type": "consumer_loan", "collateral": {"status": "not_stated"},
           "income_verification_required": {"status": "not_stated"},
           "creditworthiness_assessment_required": {"status": "not_stated"}}
    assert ConsumerLoanDetails.model_validate(old).early_repayment_allowed.status is ExtractionStatus.NOT_STATED

def test_reviewable_and_answerable():
    assert parse_review_field_text(F, "yes", excerpts=("yes",)) is True
    assert SOURCE_FIELD_PATHS[F] == (FieldPath.EARLY_REPAYMENT_ALLOWED,)
```
Then run the full unit suite. Registry tests that enumerate every field are
[test_review_input.py:16](../../tests/unit/test_review_input.py#L16),
[test_cli.py:711](../../tests/unit/test_cli.py#L711) and
[test_structured_tariff_contracts.py](../../tests/unit/test_structured_tariff_contracts.py).

**No migration:** tariff values are JSON.

**See it live:** rebuild, then "monitor the consumer loan" in `./tariff-chat`. The one extraction call that now
includes the field is a fresh (paid) call; the rest are cached. Then ask "can I repay the consumer loan early?".

**Gotchas beyond the dry run** (📖 from reading the code):
- **The first accepted run after the change reports the field as a change.** The previous snapshot has no key and
  the new one has `{status: ...}` ([compare_accepted_snapshots](../../app/services/snapshot_lifecycle.py#L674)).
  Say so in the demo, or add it to `_IGNORED_CHANGE_FIELDS` for one run ([recipe C](2-validation-review-changes.md#c--change-what-counts-as-a-change)).
- **Re-projecting an *old* accepted snapshot** (e.g. [backfill_structured_tariffs.py](../../scripts/backfill_structured_tariffs.py))
  refuses it. The reloaded product now carries the defaulted field, so it no longer equals the stored payload
  ([structured_projection.py:187](../../app/services/structured_projection.py#L187)). New runs are unaffected.

---

## G · Add a synonym / Armenian name
✅ dry-run: added `cash loan` to `consumer_standard`. Full unit suite passes unchanged.

1. Edit `aliases` / `synonyms` / `transliterations` of the entry in [seed_catalog.yaml](../../app/config/seed_catalog.yaml#L27):
   ```yaml
   synonyms: [unsecured consumer loan, standard consumer loan, cash loan]
   ```
2. **Rebuild** (`docker compose up --build -d api worker`). The YAML is inside `app/`, so it is baked into the image.

**Where it is used:**
- Gemini sees it as `also_called` in the catalog it interprets against: [_catalog_entry](../../app/services/intent_resolution.py#L508).
- The deterministic validator's term list: [_normalized_terms](../../app/services/intent_resolution.py#L594).

**Gotcha:** the same normalized term on two offerings (or twice on one) fails catalog loading at startup:
[_validate_term_collisions](../../app/domain/catalog.py#L190). Test: [test_seed_catalog.py](../../tests/unit/test_seed_catalog.py).
Recorded Gemini answers ([recorded_interpretations.json](../../tests/fixtures/recorded_interpretations.json)) are replays,
so they don't change. Prove the new name live: `./tariff-chat` → "what is the rate of the cash loan?".

---

## H · Add a new offering (product page)
✅ dry-run: `student_loan` (consumer loan). Code + tests: 1208 passed after the pinned-test updates below.
Migration: applied on a scratch DB after 001–027.

1. **Catalog entry** in [seed_catalog.yaml](../../app/config/seed_catalog.yaml#L25) (host must be allowlisted; checked at load by
   [load_seed_catalog](../../app/config/seed_catalog.py#L19)):
   ```yaml
   - product: consumer_loan
     offering_id: student_loan
     display_name: Student Loan
     seed_url: https://ameriabank.am/en/personal/loans/consumer-loans/student-loan
     enabled: true
     language: en
     localized_names:
       en: {name: Student Loan, aliases: [education loan], synonyms: [tuition loan]}
       hy: {name: Ուսանողական վարկ, aliases: [կրթական վարկ], synonyms: [ուսման վարձի վարկ], transliterations: [usanoghakan vark]}
   ```
   `category:` is optional (`overdraft`, `credit_line`, …). It picks the details fields in
   [CATEGORY_FIELDS](../../app/services/extraction_planner.py#L115). Without it, the family default applies.
2. **Enum:** [OfferingId](../../app/domain/models.py#L12): `STUDENT_LOAN = "student_loan"`. For a **consumer** loan, also add it to the
   set in [OfferingId.product](../../app/domain/models.py#L28). Anything not in that set counts as a mortgage.
3. **DB migration.** Four CHECK constraints list every offering id:
   [monitoring_runs](../../migrations/006_monitoring_pipeline_foundation.sql#L35),
   [offering_executions](../../migrations/006_monitoring_pipeline_foundation.sql#L106),
   [source_manifests](../../migrations/006_monitoring_pipeline_foundation.sql#L164) and
   [tariff_snapshots](../../migrations/006_monitoring_pipeline_foundation.sql#L228).
   Copy [snippets/028_add_offering.sql](snippets/028_add_offering.sql) to `migrations/028_add_student_loan.sql` and apply it:
   ```bash
   docker compose exec -T db psql -v ON_ERROR_STOP=1 -U tariff -d tariff_monitor < migrations/028_add_student_loan.sql
   ```
   Files in `migrations/` run automatically only on a fresh DB volume. **Without this step, the first run fails** writing
   `monitoring_runs` with `violates check constraint`.
4. **Normalization baseline:** a test requires one for every *enabled* seed
   ([test_normalization_baseline.py:141](../../tests/unit/test_normalization_baseline.py#L141)). Append a minimal page
   **by hand** to [normalization_baseline.json](../../app/config/normalization_baseline.json). The file uses 1-space
   indent, and a script rewrite reformats all 3,000 lines.
   ```json
   {"offering_id": "student_loan",
    "urls": ["https://ameriabank.am/en/personal/loans/consumer-loans/student-loan"],
    "recorded_on": "2026-09-28", "tables": [], "blocks": [{"text": "Student Loan"}]}
   ```
5. **Tests that pin the catalog** (these failed in the dry run until updated):

   | Test | Change |
   |---|---|
   | [test_seed_catalog.py:73–75](../../tests/unit/test_seed_catalog.py#L73) | `13 → 14`, and the family count (`4 → 5` consumer or `9 → 10` mortgage) |
   | [test_intent_resolution.py:246](../../tests/unit/test_intent_resolution.py#L246) | `13 → 14` |
   | [test_tariff_queries.py:131](../../tests/unit/test_tariff_queries.py#L131) | consumer only: `4 → 5` |
   | [target_questions.py:44 CONSUMER_FAMILY](../../tests/fixtures/target_questions.py#L44) | consumer only: add `OfferingId.STUDENT_LOAN`. The mortgage family is derived from the enum. |

6. **Rebuild**, then `./tariff-chat` → "monitor the student loan". Or use
   `curl -X POST $API/api/v1/runs -H 'content-type: application/json' -d '{"product":"consumer_loan","offering_id":"student_loan"}'`.

**Say while doing it:** an enabled offering joins family-wide runs and the daily schedule (more cost).
`enabled: false` keeps it in the catalog without monitoring it. A new *category* (e.g. credit cards)
is a larger change: a new [LoanCategory](../../app/domain/semantic_extraction.py#L52), a details model,
`CATEGORY_FIELDS`, and an assembly branch in [assemble_loan_product](../../app/services/semantic_extraction.py#L2760).
