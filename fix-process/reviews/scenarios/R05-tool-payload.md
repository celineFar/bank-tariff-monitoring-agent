# R05: `get_current_tariffs` payload size

**Checks.** The model-facing tool payload no longer carries evidence or values (RV8).

**Run.** Build the tool's payload for the dev database's accepted Overdraft snapshot
(read-only), before (the old `model_dump()`) and after (`current_tariffs_payload`).

**Pass when.** The new payload has no `evidence` and no `normalized_tariff`, and is under
2 kB per offering (the report measured ≈272 kB for Overdraft before).

**Result.** **PASS** (2026-09-26), read-only on `tariff_monitor`, accepted Overdraft snapshot:

| Tool | Before | After |
|---|---|---|
| `get_current_tariffs` | 265,845 bytes | **755 bytes** (freshness + 16 field statuses) |
| `get_tariff_history` (one snapshot) | 796,542 bytes | **10,919 bytes** (values, no evidence or extraction record) |

No `evidence` and no `normalized_tariff` in the current-tariffs payload.
