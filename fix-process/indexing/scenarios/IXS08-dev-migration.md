# IXS08: migration 023 on a copy of the dev database (IX9, IX12)

**Checks.** Migration `023_indexing_publication_sets.sql` applies to a copy of the dev
database (dump: `fix-process/indexing/data/dev-db-before.dump`, not committed), and the
backfill and clean-up behave.

**Run.**
1. Restore the dump into a scratch database; record counts (documents by state, chunks,
   `api:*` documents active, unlinked `fact_evidence`).
2. Apply migration 023; record the same counts and the `snapshot_documents` rows.
3. Replay one accepted publication for `overdraft` from the stored rows (no model
   calls) and record the counts again.

**Pass when.**
- the migration applies without error on the existing schema;
- `rejected`/`superseded` documents are gone; every active document has a
  `snapshot_documents` row;
- after the replayed publication: no `api:*` document is active; 0 unlinked evidence
  rows for the new snapshot.

**Before (Phase 0, 2026-09-26).** 17 documents (10 active, 7 rejected), 999 chunks,
5 active `api:*` documents holding 135 HTML chunks, 22 of 246 active evidence rows
unlinked.

**Result.** **PASS** (2026-09-26): `api:*` active 5 → 0; unlinked evidence 22 → 0 of 246; one active version per URL. The dev DB is at migration 015: deployment must apply 016–023. Script: `run_ixs08_replay.py`. See [../scenario-results.md](../scenario-results.md#ixs08-migration-023-on-a-copy-of-the-dev-database).
