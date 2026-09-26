# S08: One failing call does not sink the offering

**What it checks.** Per-call fallback and saving (SE25), and raw responses that never cross offerings (SE13).

**Plan items.** SE13, SE25.

**Steps.** A fake primary model fails one call; a fake fallback model answers it. Then both fail that call.

**Pass criteria.** First case: the offering completes, only the failed call goes to the fallback, all calls are cached. Second case: the offering fails with `semantic_extraction.execution_failed`, the other calls are cached, and no review shows another offering's output.

**Gemini.** None (fake extractors).

## Result: **not run**
