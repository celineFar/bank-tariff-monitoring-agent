# IXS10: live overdraft run (optional; needs budget approval)

**Checks.** On a real accepted run for `overdraft` against the dev database after
migration 023: IXS02 and IXS08's post-conditions hold, and embedding cost is reported
from the usage ledger (`model_call_usage`, stages `indexing.embedding` and
`indexing.embedding_sweep`).

**Run.** Only with the user's approval of the model spend (acquisition, discovery,
extraction and embedding calls; about $0.05 of it for the re-embed).

**Pass when.** One active version per source, no active `api:*` document, 0 unlinked
evidence rows, no active chunk without a vector after the sweep.

**Result.** **Not run**: needs the user's approval of the model spend.
