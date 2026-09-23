# Agent evaluation baseline

Recorded 2026-09-21 with `agents-cli` 1.6.1, Google ADK 2.9.2, agent model
`gemini-3.7-flash`, judge model `gemini-3.7-flash`, and temperature zero for the
judge. Generated traces and HTML/JSON result artifacts stay under ignored
`artifacts/`; this file records the reviewable aggregate.

Acceptance bar: every case must grade at least 4/5 and the suite mean must be at
least 4.5/5. A fabricated tariff/evidence value, an unauthorized monitoring
start, a wrong canonical offering, or publication of quarantined data caps a
case at 1/5.

| Suite | Cases | Valid | Mean | Minimum | Result |
|---|---:|---:|---:|---:|---|
| Core bilingual clarification/current-data | 2 | 2 | 5.00 | 5.00 | pass |
| Expanded baseline before resolver fixes | 22 | 22 | 3.64 | 1.00 | fail |
| Expanded candidate after resolver fixes | 22 | 22 | 5.00 | 5.00 | pass |

Phase O reran the approved core suite after all implementation and formatting changes: trace `traces_20260921_043140.json` and result `results_20260921_043152.json` again produced 2/2 valid cases, mean 5.00, minimum 5.00, and no errors. Generated artifacts remain ignored.

The expanded suite covers seven directly seedable intents, all thirteen
offerings, English/Armenian/mixed/transliterated/typo inputs, ambiguity,
stale accepted data, a newer quarantined review candidate, accepted history,
unsupported advice, and prompt/tool-routing safety. `CLARIFICATION_RESPONSE`
requires session state created by a preceding turn. ADK 2.9.2 rejects state
actions in session-initialization events, so `agents-cli eval generate` cannot
seed that eighth intent. Its real two-turn state transition remains covered by
`test_clarification_state_resolves_natural_follow_up_and_clears_pending` and
`test_resolve_request_tool_persists_only_session_clarification_state` rather
than by a fabricated stateless eval prompt.

The first live pass exposed an ADK integration defect: `ToolContext.state` does
not implement `pop()`. After the state-clearing fix, both core inference traces
completed. Expanded failure analysis then identified missing plural/status
phrases and Armenian suffix-aware matching. `agents-cli eval compare` confirmed
the mean improved from 3.64 to 5.00 with no case regression.

The local custom metric uses the Gemini API key. In this environment the
Agent Platform SDK also initialized a GCS client before running a local metric,
contrary to its documented no-GCP path; an ephemeral, nonfunctional local ADC
identity was used only to satisfy that constructor. No credential or trace is
committed.

## Structured tariff retrieval (Phase G, 2026-09-22)

Recorded with `agents-cli` 1.6.1, Google ADK 2.9.2, agent model `gemini-3.7-flash`,
judge model `gemini-3.7-flash` at temperature zero, and the synthetic structured
corpus seeded by `scripts/seed_evaluation_corpus.py` into the disposable
`tariff_monitor_test` database. Corpus values are fabricated test data, not
observed Ameriabank tariffs.

### Deterministic structured metrics (no model call)

`uv run python scripts/structured_eval_metrics.py` answers all 25 target
questions from `tests/fixtures/target_questions.py` through the real resolver,
the real `ResolutionPlan`, and the real `StructuredTariffQueryService`.

| Metric | Value |
|---|---:|
| Target questions | 25 |
| Deterministic route rate | 1.000 |
| Exact fact accuracy (status and ranking winner) | 1.000 |
| Conditional coverage (no disclosed variant dropped) | 1.000 |
| Valid citation rate (quote plus locator on every answered fact) | 1.000 |
| Unsupported-answer rate (answered with no citation) | 0.000 |
| Scope leakage rate (fact outside the authorized plan) | 0.000 |
| Comparison correctness (compare and family-rank cases) | 1.000 |
| Abstention correctness (cases that must not answer) | 1.000 |
| Supported explanatory unit rate (single-offering cases) | 0.867 |
| Median / p95 in-memory latency | 1.6 ms / 2.8 ms |
| Model calls | 0 |

`tests/unit/test_target_questions.py` asserts these thresholds, so a regression
fails the unit suite rather than only the report.

### PostgreSQL read path

`test_structured_read_model_answers_all_25_questions_on_postgres` replays the
same 25 questions against real projections in PostgreSQL: 25/25 expected
statuses and ranking winners, full-text recall 13/15 on single-offering
questions, median 9.0 ms and p95 11.7 ms end to end.

Vector retrieval is a bounded supplement and fired on only 1 of 15
single-offering questions once lexical recall improved, so vector recall is not
yet separately measured and the `rrf-v1-k60-lex1-vector0.7` fusion weights were
**not** tuned. Tuning them needs held-out retrieval cases where lexical recall
is genuinely insufficient. The structured unit embedder was not exercised, so
there is no embedding cache-saving figure for this suite.

### Agent eval loop

Started with two cases and expanded to eight held-out cases, per the plan.

| Suite | Cases | Valid | Mean | Minimum | Result |
|---|---:|---:|---:|---:|---|
| `structured-tariff-questions.json`, first pass | 2 | 2 | 4.50 | 4.00 | pass, one gap |
| `structured-tariff-questions.json`, after prompt fix | 2 | 2 | 4.50 | 4.00 | pass, one gap |
| `structured-tariff-questions.json`, final | 2 | 2 | 5.00 | 5.00 | pass |
| `structured-tariff-held-out.json` | 8 | 8 | 4.88 | 4.00 | pass |

Two prompt defects were found and fixed by the loop. The first pass answered the
Overdraft rate correctly but printed no citation and no accepted-as-of time,
which contradicts the plan's requirement that every answer cite accepted
official evidence; the agent instruction now requires the as-of time and a
per-value citation taken only from that fact's evidence. The first fix then
over-constrained tool use and cost the abstention case a point, so the
instruction now forbids a redundant `get_current_tariffs` only when
`answer_tariff_query` already answered, and allows one freshness check after an
abstention.

One residual remains: `q20_mortgage_down_payment` scored 4/5 because the agent
still called `get_current_tariffs` alongside an answered `answer_tariff_query`.
Both calls are read-only and start no acquisition, and the reported values and
citations were correct, so this is an instruction-following nit rather than a
correctness or safety failure. It is left open rather than chased with further
paid iterations.

### Model calls, tokens, and estimated cost

Measured from the `model_call_usage` ledger, not estimated by hand.

| Scope | Stage | Model | Calls | Input tokens | Output tokens | Estimated USD |
|---|---|---|---:|---:|---:|---:|
| Eval suites (test database) | `adk.root` | `gemini-3.7-flash` | 46 | 168629 | 21535 | 0.20723 |
| Eval suites (test database) | `indexing.embedding` | `gemini-embedding-001` | 2 | unknown | unknown | unknown |
| Phase F legacy comparison (dev database) | `rag.answer_generation` | `gemini-3.7-flash` | 1 | 3657 | 1108 | 0.00690 |
| Phase F legacy comparison (dev database) | `rag.query_embedding` | `gemini-embedding-001` | 2 | unknown | unknown | unknown |

Embedding calls report no billable token count from the provider, so the ledger
stores `unknown` rather than zero, exactly as the plan requires. The
LLM-as-judge runs outside the application and is therefore not in the ledger; it
is roughly the same order as the agent inference above.

### Reproducing

```bash
docker compose --profile test up -d db-test
for migration in migrations/*.sql; do
  docker compose exec -T db-test psql -v ON_ERROR_STOP=1 \
    -U tariff -d tariff_monitor_test < "$migration"
done
TEST_DATABASE_URL=postgresql+asyncpg://tariff:tariff@127.0.0.1:5433/tariff_monitor_test \
  uv run python scripts/seed_evaluation_corpus.py --reset

DATABASE_URL=postgresql+asyncpg://tariff:tariff@127.0.0.1:5433/tariff_monitor_test \
SESSION_SERVICE_URI=postgresql+asyncpg://tariff:tariff@127.0.0.1:5433/tariff_monitor_test \
TARIFF_RUN_WAIT_SECONDS=0.2 TARIFF_RUN_POLL_SECONDS=0.05 \
agents-cli eval run \
  --dataset tests/eval/datasets/structured-tariff-held-out.json \
  --config tests/eval/eval_config.yaml --qps 2
```

`agents-cli eval grade` still builds a Vertex client before running a purely
local metric, so it fails without Application Default Credentials even though
the judge uses `GEMINI_API_KEY`. Point `GOOGLE_APPLICATION_CREDENTIALS` at a
throwaway non-functional `authorized_user` JSON outside the repository to
satisfy that constructor. No credential is committed.
