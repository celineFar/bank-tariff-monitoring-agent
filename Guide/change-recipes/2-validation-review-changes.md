# 2 · Validation, human review, change detection

[← Change recipes](README.md)

Where a value goes after Gemini returns it:

```text
Gemini answer ─► _validate_individual_fields ─┬─ passes ─► validated_fields ─┐
 (per field)      (quote in source, schema,    └─ fails ──► review_items ─────┤
                   semantic checks)              ("extraction_invalid")        ▼
                                                   build_snapshot_attempt ─► detect_review_signals
                                                   (+ detect_large_rate_changes vs previous accepted)
                                                        │ no signals              │ signals
                                                        ▼                         ▼
                                                   ACCEPTED ─► compare_accepted_snapshots   REVIEW_REQUIRED ─► _review_tasks
                                                               (change set, published)       (one ReviewTask per signal, CLI panel)
```

---

## A · Add a deterministic validation rule
✅ dry-run: rate cap, 61 extraction tests pass. **Ask:** "reject an annual rate above 60%".

**Where rules live:**
- **Per-field semantic checks** with access to the batch's evidence:
  [_validate_semantic_completeness](../../app/services/semantic_extraction.py#L2049). Copy the shape of any
  `if result.status is ExtractionStatus.FOUND and result.field ...: raise ValueError(...)` block. The last
  one is at [line 2197](../../app/services/semantic_extraction.py#L2197).
- **Pure value shape and bounds** (apply to reviewers' input too): Pydantic models such as
  [Rate](../../app/domain/semantic_extraction.py#L228), [TermRange](../../app/domain/semantic_extraction.py#L270)
  and [MoneyRange](../../app/domain/semantic_extraction.py#L162). A `@model_validator` there rejects the value everywhere,
  including a human override.
- **Citation checks** (quote must be verbatim in the evidence; numbers must appear in the quote):
  [_validate_field_result](../../app/services/semantic_extraction.py#L2379) and
  [_GROUNDED_FIELDS](../../app/services/semantic_extraction.py#L1815).

**Steps**
1. Constants, above [_NUMBER_KEYS](../../app/services/semantic_extraction.py#L1822):
   ```python
   _RATE_CAP_FIELDS = frozenset(
       {ExtractionField.INTEREST_RATE, ExtractionField.EFFECTIVE_RATE}
   )
   _MAX_ANNUAL_RATE_PCT = Decimal(60)
   ```
2. The check, inside [_validate_semantic_completeness](../../app/services/semantic_extraction.py#L2049), before the
   `INCOME_VERIFICATION_REQUIRED` block at [line 2197](../../app/services/semantic_extraction.py#L2197):
   ```python
   if (
       result.status is ExtractionStatus.FOUND
       and result.field in _RATE_CAP_FIELDS
       and isinstance(validated.value, tuple)
   ):
       # A plausibility cap: an annual rate above it is a misread (a fee, a
       # year, a monthly rate read as annual), so a person checks it.
       for item in validated.value:
           rate = getattr(item, "value", None)
           if (
               isinstance(rate, Rate)
               and rate.basis is RateBasis.ANNUAL
               and rate.max is not None
               and rate.max > _MAX_ANNUAL_RATE_PCT
           ):
               raise ValueError(
                   f"annual rate {rate.max}% exceeds the {_MAX_ANNUAL_RATE_PCT}% "
                   "plausibility cap"
               )
   ```
3. **Gotcha:** `RateBasis` is not imported in that module. Add `RateBasis,` after `Rate,` in the import
   block at [line 54](../../app/services/semantic_extraction.py#L54).

**What happens at runtime:** the `ValueError` is caught in [_validate_individual_fields](../../app/services/semantic_extraction.py#L2252)
and becomes an `extraction_invalid` review item ([_review_item](../../app/services/semantic_extraction.py#L2500)).
The reviewer sees Gemini's value as a candidate, with your message appended to the guidance.
The run does not fail and nothing is published unchecked.

**Test** (new file `tests/unit/test_rate_cap.py`, calls the same entry point the pipeline uses):
```python
from app.domain.acquisition import SourceLocator, SourceType
from app.domain.models import ProductType
from app.domain.semantic_extraction import (EvidenceItem, ExtractionBatch, ExtractionField,
    ExtractionStatus, ModelCitation, ModelFieldResult)
from app.domain.source_discovery import Authority, InformationRole, TemporalStatus
from app.services.semantic_extraction import _field_semantic_issues

URL = "https://ameriabank.am/en/personal/loans/consumer-loans/overdraft"

def _issues(rate: int):
    text = f"Annual interest rate {rate}%"
    item = EvidenceItem(evidence_id="ev_" + "a" * 24, document_id="page", source_item_id="terms",
        content=text, role=InformationRole.PRODUCT_TERMS, authority=Authority.OFFICIAL_TERMS,
        temporal_status=TemporalStatus.CURRENT, precedence=1,
        locator=SourceLocator(source_url=URL, source_type=SourceType.PAGE))
    batch = ExtractionBatch(id="b", product=ProductType.CONSUMER_LOAN, group="core",
        fields=(ExtractionField.INTEREST_RATE,), evidence=(item,), content_fingerprint="f" * 64)
    result = ModelFieldResult(field=ExtractionField.INTEREST_RATE, status=ExtractionStatus.FOUND,
        value_json=f'[{{"value":{{"min":{rate},"max":{rate}}},"conditions":[]}}]',
        evidence=(ModelCitation(evidence_id=item.evidence_id, quote=text),))
    return _field_semantic_issues(batch, result, {item.evidence_id: item}, product=ProductType.CONSUMER_LOAN)

def test_rate_above_cap_is_rejected():
    assert "plausibility cap" in _issues(75)[0].message

def test_rate_within_cap_passes():
    assert _issues(21) == () and _issues(60) == ()
```
`uv run pytest tests/unit/test_rate_cap.py tests/unit/test_semantic_extraction.py tests/unit/test_semantic_extraction_fixes.py -q -p no:cacheprovider`

**See it live, at no model cost:** set the cap below the real Overdraft rate (21%), for example `Decimal(15)`, rebuild, then run
Overdraft. The cached extraction is re-validated, so the rate fields go to review:
`./tariff-chat` → "monitor overdraft".

---

## B · Add a new HITL review trigger
✅ dry-run: 78 review/snapshot tests pass, and the signal becomes a pending `ReviewTask`.
**Ask:** "send it to a human when the effective rate is below the nominal rate" (impossible, because
the EIR includes fees).

**Five places, in this order:**

1. **Reason:** add to [ReviewReason](../../app/domain/review.py#L17), after `EXTRACTION_INVALID` at [line 24](../../app/domain/review.py#L24):
   ```python
   # The effective rate is below the nominal rate, which fees cannot produce.
   RATE_INCONSISTENCY = "rate_inconsistency"
   ```
2. **Raise it:** in [detect_review_signals](../../app/services/snapshot_lifecycle.py#L237), just before
   `existing_scopes = {` at [line 347](../../app/services/snapshot_lifecycle.py#L347):
   ```python
   fields = {field.field: field for field in result.validated_fields}
   nominal = fields.get(ExtractionField.INTEREST_RATE)
   effective = fields.get(ExtractionField.EFFECTIVE_RATE)
   lowest_nominal = _lowest_rate(nominal)
   lowest_effective = _lowest_rate(effective)
   if (
       lowest_nominal is not None
       and lowest_effective is not None
       and lowest_effective < lowest_nominal
   ):
       signals.append(
           _signal(
               "rate_inconsistency",
               ExtractionField.EFFECTIVE_RATE.value,
               cited(
                   [c.evidence_id for c in (*nominal.evidence, *effective.evidence)],
                   "cited",
               ),
               failed_checks=[
                   f"effective rate {lowest_effective}% is below nominal "
                   f"rate {lowest_nominal}%"
               ],
           )
       )
   ```
   and a helper above [_review_item_signal](../../app/services/snapshot_lifecycle.py#L366):
   ```python
   def _lowest_rate(field) -> Decimal | None:
       """The lowest stated minimum of a found rate field, or None."""
       if field is None or field.status is not ExtractionStatus.FOUND:
           return None
       lows = [
           rate.min
           for item in field.value or ()
           if isinstance(rate := getattr(item, "value", None), Rate)
           and rate.min is not None
       ]
       return min(lows, default=None)
   ```
   Add `Rate,` to the import block at [line 26](../../app/services/snapshot_lifecycle.py#L26).
3. **Allowed decisions + guidance:** in [review_policy](../../app/services/review_resolution.py#L608), before the
   `OFFICIAL_SOURCE_CONFLICT` branch at [line 621](../../app/services/review_resolution.py#L621):
   ```python
   if reason is ReviewReason.RATE_INCONSISTENCY:
       return (
           (
               ReviewDecisionType.APPROVE,
               ReviewDecisionType.OVERRIDE,
               ReviewDecisionType.REJECT_ALL,
           ),
           "The effective rate is below the nominal rate, which fees cannot "
           "produce. Check both against the passages: approve if the source "
           "really says so, enter the correct effective rate with its passage, "
           "or reject the candidate snapshot.",
       )
   ```
4. **Allow `approve`:** if `APPROVE` is one of its decisions, add the reason to the tuple in
   [review_decisions.py:90](../../app/services/review_decisions.py#L90). Otherwise approving raises
   "approve is valid only for …".
5. **Test** (new file, reuses the fixture from [test_snapshot_lifecycle.py:44](../../tests/unit/test_snapshot_lifecycle.py#L44)):
   ```python
   from app.domain.review import ReviewReason
   from app.domain.semantic_extraction import (ConditionalValue, ExtractionField, ExtractionStatus,
       Rate, ValidatedFieldResult)
   from app.services.snapshot_lifecycle import detect_review_signals
   from tests.unit.test_snapshot_lifecycle import _result

   def _with_rates(nominal, effective):
       base = _result()
       cite = base.validated_fields[0].evidence[0]

       def rate(field, value):
           return ValidatedFieldResult(field=field, status=ExtractionStatus.FOUND,
               value=(ConditionalValue(value=Rate(min=value, max=value)),),
               evidence=(cite,), batch_id="core")

       return base.model_copy(update={"validated_fields": (*base.validated_fields,
           rate(ExtractionField.INTEREST_RATE, nominal), rate(ExtractionField.EFFECTIVE_RATE, effective))})

   def test_effective_below_nominal_raises_a_review():
       (signal,) = detect_review_signals(_with_rates(18, 15))
       assert signal["reason"] == "rate_inconsistency" and signal["issue_scope"] == "effective_rate"

   def test_consistent_rates_are_fine():
       assert detect_review_signals(_with_rates(18, 19.6)) == ()

   def test_signal_becomes_a_review_task():
       from uuid import uuid4
       from app.domain.models import OfferingId, ProductType
       from app.services.monitoring_pipeline import _review_tasks
       from app.services.snapshot_lifecycle import build_snapshot_attempt
       snap = build_snapshot_attempt(run_id=uuid4(), offering_execution_id=uuid4(),
           product=ProductType.CONSUMER_LOAN, offering_id=OfferingId.CONSUMER_STANDARD,
           result=_with_rates(18, 15), previous_accepted_snapshot_id=None)
       (task,) = _review_tasks(snap)
       assert task.reason is ReviewReason.RATE_INCONSISTENCY
   ```
   Then run: `uv run pytest tests/unit/test_snapshot_lifecycle.py tests/unit/test_review_resolution.py tests/unit/test_multi_review_approval.py tests/unit/test_review_fixes.py -q -p no:cacheprovider`

**Gotchas**
- **The reason string in `_signal(...)` must equal the enum value.** [_review_tasks](../../app/services/monitoring_pipeline.py#L922)
  parses it with `ReviewReason(...)` at [line 929](../../app/services/monitoring_pipeline.py#L929) and *silently skips* an unknown
  one. The offering then fails with "candidate needs review but raised no review signal"
  ([line 445](../../app/services/monitoring_pipeline.py#L445)). The third test above catches this.
- **Show numbers through `failed_checks`**, which are appended to the guidance by
  [_with_failed_checks](../../app/services/review_resolution.py#L559). Don't use `previous`/`current` keys:
  [_review_tasks](../../app/services/monitoring_pipeline.py#L966) treats those as a *rate change* and labels them so.
- **Approval is not remembered.** The same inconsistency is raised again next run. To remember it like an OCR reading, extend
  [_remembered_approval](../../app/services/review_decisions.py#L342).
- **One review per `(snapshot, reason, issue_scope)`.** The task id is derived from that triple. Two signals with the same triple collapse into one.
- **No migration:** `human_reviews.reason_code` is plain `text` with no CHECK constraint ([001_initial.sql:35](../../migrations/001_initial.sql#L35)).
- **A signal that compares against the previous run** (like `large_rate_change`) goes in
  [build_snapshot_attempt](../../app/services/snapshot_lifecycle.py#L107), which has `previous_accepted_snapshot`.
  Copy lines 144–154 and [detect_large_rate_changes](../../app/services/snapshot_lifecycle.py#L497).

**See it live:** the reviewer panel is [_show_review](../../app/cli.py#L666). There's no cheap way to make the live
Ameria page produce EIR < nominal, so show it with the test and the panel code.

---

## Make a field required or optional
📖 [_REQUIRED_TARIFF_FIELDS](../../app/services/snapshot_lifecycle.py#L46). A required field that Gemini marks
`not_stated` raises `missing_required_field`. The reviewer can enter it, confirm it's not stated, or reject.
Removing a field from the set lets `not_stated` pass silently. Test: [test_snapshot_lifecycle.py](../../tests/unit/test_snapshot_lifecycle.py)
(`test_ambiguous_applicability_and_missing_required_field_route_to_review`).

---

## C · Change what counts as a "change"
✅ dry-run: ignore a field, 20 tests pass. **Ask:** "don't report changes to `special_conditions`".

[compare_accepted_snapshots](../../app/services/snapshot_lifecycle.py#L674) compares each field's canonical JSON with `!=`
([line 701](../../app/services/snapshot_lifecycle.py#L701)). Formatting is already normalized before that:
[_canonicalize](../../app/services/snapshot_lifecycle.py#L724) sorts keys and lists and drops
[_PROVENANCE_KEYS](../../app/services/snapshot_lifecycle.py#L64) (quotes, URLs, timestamps). So "10 000 000" and "10,000,000"
are both the number `10000000` by then, and a moved quote is not a change.

1. Above `compare_accepted_snapshots`:
   ```python
   # Stored and answered, but a difference in them alone is not reported as a change.
   _IGNORED_CHANGE_FIELDS = frozenset({"special_conditions"})
   ```
2. In the comprehension at [line 700–701](../../app/services/snapshot_lifecycle.py#L700):
   ```python
   for field in sorted(set(before) | set(after))
   if field not in _IGNORED_CHANGE_FIELDS and before.get(field) != after.get(field)
   ```
3. Test:
   ```python
   from datetime import timedelta
   from app.services.snapshot_lifecycle import compare_accepted_snapshots
   from tests.unit.test_snapshot_lifecycle import NOW, _snapshot

   def test_special_conditions_alone_is_not_a_change():
       prev = _snapshot({"special_conditions": {"status": "found", "value": ["a"]}})
       cur = _snapshot({"special_conditions": {"status": "found", "value": ["b"]}},
                       created_at=NOW + timedelta(days=1))
       assert compare_accepted_snapshots(prev, cur).changes == ()
   ```
   `uv run pytest tests/unit/test_snapshot_lifecycle.py tests/unit/test_change_detection.py -q -p no:cacheprovider`

Field names are the keys of [tariff_fields](../../app/services/snapshot_lifecycle.py#L657): the top-level
[ExtractionField](../../app/domain/semantic_extraction.py#L444) values, with `details.*` flattened in.
The field is still stored and still answerable. It just never appears in a change set.

### Variant: a numeric tolerance
📖 Replace `before.get(field) != after.get(field)` with a helper that compares numbers leniently:
```python
def _differs(a, b, tol=Decimal("0.01")) -> bool:
    if isinstance(a, (int, float, str)) and isinstance(b, (int, float, str)):
        try:
            return abs(Decimal(str(a)) - Decimal(str(b))) > tol
        except InvalidOperation:
            return a != b
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() != b.keys() or any(_differs(a[k], b[k], tol) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) != len(b) or any(_differs(x, y, tol) for x, y in zip(a, b))
    return a != b
```
`Decimal` and `InvalidOperation` are already imported there. Lists are canonically sorted, so zip pairs are stable
unless an entry is added or removed, which counts as a change anyway.

**Related knobs:**
- The rate-change *review* threshold is separate from change *reporting*. See [Settings](1-settings.md#settings-only-changes).
- How rate entries are paired across runs: [_RATE_ENTRY_MATCH_FLOOR](../../app/services/snapshot_lifecycle.py#L574).
