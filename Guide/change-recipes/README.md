# Change recipes (start here)

Open in Markdown preview (`Ctrl+Shift+V`). Every link opens the file at the line.
Each recipe lists the files to touch in order, the exact edit, the test to run and how to see it live.

> **Your 8 prepared changes → [6 Custom set](6-custom-set.md)**. They cover the HITL threshold, new triggers (amount/fee),
> early repayment fee, acba.am, retries/limits, `10.000.000`, Armenian/refusals, and report/CLI output.
> All eight were dry-run, and a ready-to-apply rehearsal patch is in [snippets/custom-set/](snippets/custom-set/).

Legend:
- ✅ **dry-run**: applied on 2026-09-28 in a throwaway worktree and tested.
  The snippets are the code that passed. As a final check, all eight ✅ recipes were applied together
  from the text of these pages, with their test snippets pasted as-is. Result: 1219 passed
  (the 1208 baseline plus the 11 guide tests), and `ruff check app` is clean.
- 📖 **traced**: followed through the code, not applied.

Related guides: [codebase map](../codebase-map/README.md) ("where is X") ·
[debug cheat sheet](../debug/README.md) (every run/log/SQL command) ·
[symptoms](../debug/symptoms.md) (diagnose a wrong result).

| Page | Covers |
|---|---|
| [1 Settings](1-settings.md) | Change a number or list with no code: thresholds, domains, limits, schedule, models. Add a new setting. |
| [2 Validation, review, change detection](2-validation-review-changes.md) | New validation rule, new HITL trigger, required fields, what counts as a change |
| [3 Fields and catalog](3-fields-and-catalog.md) | New extracted field, new synonym, new offering (with DB migration) |
| [4 Agent and API](4-agent-and-api.md) | New agent tool, prompt changes, new HTTP route |
| [5 Pipeline and retrieval](5-pipeline-and-retrieval.md) | Retries, failure codes, OCR trigger, RAG ranking, scheduled products |
| [6 Custom set](6-custom-set.md) | The 8 changes you listed, each dry-run, with tests and a rehearsal patch |

---

## Cheat sheet (one screen)

```bash
# 0. ALWAYS first, in every new terminal. The stack was started with the local port override
#    (API 8081, DB 5435). Without this, `up` remaps the API to 8080, which another checkout holds.
export COMPOSE_FILE=docker-compose.yml:docker-compose.local.yml
export API=http://localhost:8081

# 1. Test the change (seconds). Run the whole suite only before the live run (~70 s, baseline 1208 passed, 5 skipped).
uv run pytest tests/unit/test_snapshot_lifecycle.py -q -p no:cacheprovider
uv run pytest tests/unit -q -p no:cacheprovider
uv run ruff check --fix app tests && uv run ruff format app tests   # guide test snippets are condensed; this tidies them

# 2. Ship it into the running stack. The code is COPIED into the image, not mounted.
docker compose up --build -d api worker            # any edit under app/ (including seed_catalog.yaml)
docker compose up -d --force-recreate api worker   # .env edit only (env_file is read at container create)

# 3. See it
./tariff-chat                                      # chat + review panel (runs inside the api container)
curl -s -X POST $API/api/v1/runs -H 'content-type: application/json' \
     -d '{"product":"consumer_loan","offering_id":"overdraft"}'
curl -s $API/api/v1/runs/<run_id> | python3 -m json.tool
curl -s "$API/api/v1/reviews?run_id=<run_id>" | python3 -m json.tool   # read-only; decide in ./tariff-chat
docker compose logs -f --tail=200 worker api

# 4. DB
docker compose exec -T db psql -U tariff -d tariff_monitor -c "SELECT offering_id,status,current_stage,failure_code FROM offering_executions ORDER BY created_at DESC LIMIT 5;"
docker compose exec -T db psql -U tariff -d tariff_monitor < migrations/028_x.sql   # new migration: run by hand

# 5. Undo a live change after demoing it
git diff --stat && git stash        # then rebuild (step 2)
```

- **Which test file?** Every recipe names it. The full map is in [codebase-map/6](../codebase-map/6-tests-evals-demos.md).
- **Demo stack:** its images are built from the main stack. After `docker compose build api worker` the
  [Presentation-demonstrations](../../Presentation-demonstrations/README.md) run your changed code.
- **A rerun costs $0** when the sources are unchanged, because every model stage is cached. A change to a
  *validation* rule still applies to cached answers:
  [_validate_individual_fields](../../app/services/semantic_extraction.py#L2252) runs over cached and fresh
  answers alike (called at [line 716](../../app/services/semantic_extraction.py#L716)).
  A change to a *prompt* needs the version bump in [4 Agent and API](4-agent-and-api.md#change-a-gemini-prompt).

---

## Likely interview asks → recipe

Sizes: **S** is one file and under 5 min. **M** is 2–4 files and 10–20 min. **L** is 5+ files and 30+ min.

| They say… | Recipe | Size | Status |
|---|---|---|---|
| "Make the large-rate-change review trigger at 1 pp instead of 3" | [Settings: HITL threshold](1-settings.md#settings-only-changes) | S | 📖 |
| "Stop fetching from domain X / also allow domain Y" | [Settings: allowed hosts](1-settings.md#settings-only-changes) | S | 📖 |
| "Lower the max download size to 5 MB" / "change the timeout" | [Settings: HTTP limits](1-settings.md#settings-only-changes) | S | 📖 |
| "Run the scheduled monitoring at 09:30" / "turn the schedule off" | [Settings: schedule](1-settings.md#settings-only-changes) | S | 📖 |
| "Make X configurable through an env var" | [Add a new setting](1-settings.md#add-a-new-setting) | M | 📖 |
| "Reject an interest rate above 60%" / "add a sanity check on a value" | [A · Validation rule](2-validation-review-changes.md#a--add-a-deterministic-validation-rule) | S | ✅ |
| "Send it to review when EIR < nominal rate" / "add a new HITL scenario" | [B · New review trigger](2-validation-review-changes.md#b--add-a-new-hitl-review-trigger) | M | ✅ |
| "Make field X required" | [Required field](2-validation-review-changes.md#make-a-field-required-or-optional) | S | 📖 |
| "Don't report changes to field X" | [C · Ignore a field in change detection](2-validation-review-changes.md#c--change-what-counts-as-a-change) | S | ✅ |
| "Ignore tiny rate differences" | [C · Tolerance variant](2-validation-review-changes.md#variant-a-numeric-tolerance) | S | 📖 |
| "Extract a new field (e.g. early repayment allowed)" | [E · New extracted field](3-fields-and-catalog.md#e--add-a-new-extracted-field) | L | ✅ |
| "The user calls it 'cash loan', make that work" | [G · Synonym](3-fields-and-catalog.md#g--add-a-synonym--armenian-name) | S | ✅ |
| "Monitor another product page" | [H · New offering](3-fields-and-catalog.md#h--add-a-new-offering-product-page) | L | ✅ (incl. migration) |
| "Add a tool to the agent" | [D · New agent tool](4-agent-and-api.md#d--add-a-new-agent-tool) | M | ✅ |
| "Make the agent always answer with a disclaimer / in a format" | [Chat prompt](4-agent-and-api.md#change-the-chat-agents-wording) | S | 📖 |
| "Change the extraction prompt" | [Gemini prompt](4-agent-and-api.md#change-a-gemini-prompt) | S | 📖 |
| "Add an API endpoint" | [F · New HTTP route](4-agent-and-api.md#f--add-an-http-route) | M | ✅ |
| "Also retry on HTTP 403" / "don't retry 500" | [Retry policy](5-pipeline-and-retrieval.md#change-which-http-errors-are-retried) | S | 📖 |
| "Change the error message the user sees for failure X" | [Failure codes](5-pipeline-and-retrieval.md#change-a-failure-code-or-its-message) | S | 📖 |
| "Weight vector search higher / return more results" | [RAG ranking](5-pipeline-and-retrieval.md#change-rag-ranking-weights--top-k) | S | 📖 |
| "Change the chunk size" | [Settings: chunk size](1-settings.md#settings-only-changes) | S | 📖 |
| "Force OCR on a page / change when OCR kicks in" | [OCR trigger](5-pipeline-and-retrieval.md#change-when-ocr-runs) | S | 📖 |
| "Only monitor mortgages on schedule" | [Scheduled products](5-pipeline-and-retrieval.md#change-what-the-schedule-runs) | S | 📖 |

### How to talk while you do it (10 s each)
- **Where does this belong?** Gemini only interprets, classifies, transcribes and extracts. Every
  *decision* (validation, review routing, change detection, retries) is plain Python. So a new rule
  goes in code, not in a prompt. See [AGENTS.md](../../AGENTS.md).
- **Why a review and not a failure?** A value that fails a check becomes an `extraction_invalid`
  review, and the run still completes. A human sees the evidence, and nothing unverified is published.
- **Why no migration?** Tariff values, review reasons and signals are stored as JSON or free text.
  Only the *offering id* is a DB CHECK constraint (recipe H).
