# R04: stored old-format reviews still work

**Checks.** The 4 Overdraft reviews in the dev database were written before this fix
(`evidence.items`, a full evidence copy, no `set`). They must still build a review view
and a CLI rendering, and a decision on one must still resolve its evidence reference.

**Run.** Read-only: load the 4 rows and their snapshots from the dev database
(`tariff_monitor`, never written), then build the view and the CLI text with the new code.

**Pass when.** All 4 build without errors and show the same passages as before
(the old path), and `ReviewDecisionService` resolves an evidence reference from `items`.

**Result.** _pending (Phase 5)_
