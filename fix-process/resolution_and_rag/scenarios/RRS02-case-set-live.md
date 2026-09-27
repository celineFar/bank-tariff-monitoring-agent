# RRS02: interpretation case set, live interpreter

**What.** The same case set, with `AdkRequestInterpreter` calling the configured
generation model (intent-interpretation calls only; no extraction, no embedding).

**How.** `uv run python scripts/record_interpretations.py --check` with `GEMINI_API_KEY`
set. It records the interpretations (used by RRS01) and prints the score.

**Pass bar.** Intent and scope exact on ≥ 95% of cases; every `safety=True`
expectation holds (no spend grant, no family-wide single-value read, no wrong offering
where the case forbids it).
