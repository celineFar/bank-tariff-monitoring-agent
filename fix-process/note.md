# Fix-process notes: decisions, assumptions, open points

Decisions taken without asking, as instructed on 2026-09-26 ("don't pause to ask; use
your best judgment; record decisions here"). Newest last. Each entry says what was
decided, why, and where it matters.

## Branches

- **Integration branch.** The instruction names `integration/fix-process`; no such
  branch exists. Every earlier fix (`fix/normalization`, `fix/source-discovery`) was
  merged into `integration/process-fixes`, so the semantic-extraction work is merged
  there too.
- **`fix/reviews`** did not exist; it is created from `integration/process-fixes` after
  the semantic-extraction merge, so the review work builds on it.

## Semantic extraction (fix-process/semantic_extraction/)

- **Field labels are unconfirmed.** `data/seed-extraction-labels.json` was drafted by
  Claude from the captured pages and is used as-is for S06. The user was not asked to
  confirm them, per the instruction not to pause. Read S06 results with that in mind.
- **S06 pass bar.** Adopted as proposed in the scenario: at least 85% `match` over
  labelled fields, and no rate or amount `wrong_value` caused by a wrong column or
  currency.
- **SE2 changes every page's identity once.** The plan expected the acquisition page
  identity to stay unchanged. It is a hash of the parsed blocks, and pairing headline
  cards changes blocks, so all 13 pages get a new id on the first run after deploy.
  Block ids after a card do not shift, because the consumed label keeps its id
  reserved. Added to the one-time effects.
- **SE3 prompt kept as in production.** A trial (13 PDF transcriptions,
  `gemini-3.1-flash-lite`) showed:
  - the model never filled `row_groups` or real header rows, even when asked;
  - asking cost rows (35 against 40 on the Primary terms PDF);
  - page coverage varied with incidental prompt wording, even at temperature 0.

  So the production instruction stays; `header_rows` and `row_groups` are optional
  schema fields used when present. PDF table structure comes from deterministic
  analysis of the rows, the same rules as HTML tables. Temperature 0 and the version
  bump (`PDF_EXTRACTION_*_VERSION=3`) stay.
- **Hand-off (normalization): PDF page coverage is fragile.** The same PDF came back
  with pages 4, 7, 8, 9 or 7, 8, 9 empty in some runs and complete in others, even at
  temperature 0. `PDF_PAGE_EMPTY` reports it, but nothing re-asks for those pages.
  A per-page re-transcription of empty text pages belongs in the normalization plan.
- **Extraction fallback model (plan Q8): `gemini-3.8-flash`.** The plan meant to ask the
  user. Following the instruction not to ask, one small call each on 2026-09-26 chose:
  - `gemini-3.8-flash`, `gemini-3.6-flash` and `gemini-3.5-flash-lite` answer this key;
  - `gemini-2.5-flash` returns 404 (retired for new users).

  `gemini-3.8-flash` is non-lite (a lite model is a weak fallback for extraction), in
  the primary's price tier, and newer than it. It is the default in `environment.py`
  and `.env.example`. `SemanticExtractionSettings` in `models.py` keeps an empty
  default, so code that builds settings directly (tests) has no chain unless it asks
  for one. On your earlier question "should the fallback list be empty by default?":
  no. Each call now falls back on its own, so one configured successor costs nothing
  until the primary fails.
- **S06 pass bar.** Adopted as proposed in the scenario, not agreed with the user: ≥ 85%
  `match` over labelled fields, and no rate or amount `wrong_value` from a wrong column or
  currency. Result: 104/120 (87%), no wrong values, after re-scoring.
- **Live run settings.** Repairs capped at 1 per offering (production default 3) and a
  $1.55 guard, to fit the $2 budget. The budgeted-mode live pass was dropped when the
  budget ran out; budgeted mode is measured offline only.

## Reviews (fix-process/reviews/)

Decisions the review-process report left open, taken without asking (plan table Q1–Q11):
- **`extraction_invalid`** is the new reason for a value that failed a check. Allowed:
  `select_candidate` (accept Gemini's value after checking), `override`, `reject_all`.
- **A validation failure on a non-required field is still a review** (as
  `extraction_invalid`). Dropping it silently would lose data.
- **Bounds are code constants** (1 unit, a second within `HITL_DOCUMENT_RANK_GAP`; tables
  whole up to 30 rows; section windows ±2 blocks, ≤ 3,000 characters).
- **No embeddings** in review ranking; ranking misses are logged instead.
- **The generic "Information Guide" tagged `current_product` on Overdraft** is a
  source-discovery issue: hand-off, not fixed here.
- **No separate table display rendering**: the semantic-extraction row records already are
  the readable form.
- **`get_current_tariffs` returns freshness and field statuses only** (D5 option i).
- **`?` shows the selected sources' Markdown saved with the snapshot**, never sent to the
  model.
- **The model gets at most 5 seed passages (600 characters each)** per review; the CLI
  renders the units itself.

### Reviews Phase 1 decisions (2026-09-26)

- **Sibling reviews (found, fixed).** Two reviews of one field in one snapshot (OCR +
  large rate change) superseded each other through `human_reviews_active_scope_uq` and
  the repository's supersede-on-create. Fixed in migration `022` (pending reviews unique
  per field *and* reason) and the supersede query; not in the report.
- **Unknown IDs with no valid citation.** An `extraction_invalid` answer citing only
  IDs that do not exist has no candidate (a candidate needs a real reference); its set
  falls back to the field's call passages, and the unknown IDs are listed.
- **Empty sets are allowed.** A not-stated field with no labelled passage gets no unit;
  the CLI says so and offers `?`. No keyword or embedding fallback (Q4).
- **Test database.** Postgres tests need
  `TEST_DATABASE_URL=postgresql+asyncpg://tariff:tariff@localhost:5434/tariff_acquisition_test`
  (local test container); without it they skip.

### Reviews Phase 2 decisions (2026-09-26)

- **Override scope = the whole snapshot.** A reviewer may cite any passage of the
  snapshot (as before, when the review copied all of it); a citation outside the shown
  units is allowed and logged (RV13). Restricting to the units would block the
  reviewer exactly when ranking missed.
- **Citation quote limit 4,000.** The plan assumed the stored citation already allowed
  4,000 characters; it allowed 1,500. `EvidenceCitation.quote` now allows 4,000 so
  the displayed passage, the override check and the saved quote are the same text.
- **Old rows with non-catalog items** show each cited item as its own passage; no
  keyword fallback for uncited ones.

