# R05: `get_current_tariffs` payload size

**Checks.** The model-facing tool payload no longer carries evidence or values (RV8).

**Run.** Build the tool's payload for the dev database's accepted Overdraft snapshot
(read-only), before (the old `model_dump()`) and after (`current_tariffs_payload`).

**Pass when.** The new payload has no `evidence` and no `normalized_tariff`, and is under
2 kB per offering (the report measured ≈272 kB for Overdraft before).

**Result.** _pending (Phase 5)_
