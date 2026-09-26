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
