# IXS04: approving content first seen by an earlier run (IX3)

**Checks.** Run A needs review; run B produces the same content, needs review, and its
review supersedes A's. B is approved.

**Run.** `test_ix3_approval_activates_a_version_first_seen_by_an_earlier_run`.

**Pass when.** B's whole document set is active (including the version first inserted
by A), and nothing from before is left active.

**Result.** **PASS** (2026-09-26). See [../scenario-results.md](../scenario-results.md#ixs02ixs06-behaviour-one-test-each).
