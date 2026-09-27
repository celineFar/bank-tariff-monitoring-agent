# RRS01: interpretation case set, recorded interpretations

**What.** Every case in `tests/fixtures/interpretation_cases.py` is replayed through
`RequestResolver` with `RecordedInterpreter` (interpretations recorded from the live
interpreter by `scripts/record_interpretations.py`), and scored by
`tests/fixtures/interpretation_scoring.py`.

**How.** `uv run pytest tests/unit/test_interpretation_cases.py` (no network).

**Pass bar.** 100% of the cases that the live run (RRS02) passes; any case the live
interpreter gets wrong is listed in the results with its mismatch and marked `xfail`.
