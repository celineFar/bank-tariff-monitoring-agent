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
