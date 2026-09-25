# Evaluation Datasets

This directory contains evaluation datasets for testing agent behavior.

## Running Evaluations

### Default Dataset
```bash
# Run the agent over the default dataset and grade the traces
agents-cli eval run
```

### Custom Dataset
```bash
agents-cli eval run --dataset tests/eval/datasets/custom-dataset.json --metrics general_quality
```

### Decoupled Runs

Split the run when you want traces in a custom location, or want to re-grade
existing traces without re-running the agent:

```bash
agents-cli eval generate --dataset tests/eval/datasets/custom-dataset.json --output custom_traces/
agents-cli eval grade --metrics general_quality --traces custom_traces/
```

### Deployed Agent

By default, `eval generate` starts a local HTTP server to run your agent in, dispatches each case in parallel and then tears the server down. Pass `--url <base_url> --app-name <name>` to target an already-running or deployed agent instead.

```bash
agents-cli eval generate --url https://my-agent.run.app --app-name app
```

## Dataset Format

Each dataset file follows the Gemini Enterprise Agent Platform Evaluation
dataset format. An eval case may use **either** of two shapes — both are
valid input to `agents-cli eval generate`:

**Shape A — single-prompt case:**

```json
{
  "eval_cases": [
    {
      "eval_case_id": "unique_case_id",
      "prompt": {
        "role": "user",
        "parts": [{"text": "User message"}]
      }
    }
  ]
}
```

**Shape B — continued-conversation case (the "N+1" pattern):**
The case carries prior turns in `agent_data` and the last turn ends with a
user message; `eval generate` appends the next agent response.

```json
{
  "eval_cases": [
    {
      "eval_case_id": "unique_case_id",
      "agent_data": {
        "turns": [
          {
            "turn_index": 0,
            "events": [
              {"author": "user",  "content": {"role": "user",  "parts": [{"text": "First user message"}]}},
              {"author": "agent", "content": {"role": "model", "parts": [{"text": "First agent reply"}]}},
              {"author": "user",  "content": {"role": "user",  "parts": [{"text": "Follow-up user message"}]}}
            ]
          }
        ]
      }
    }
  ]
}
```

## Key Fields

- `eval_cases`: Array of evaluation cases.
- `eval_case_id`: Unique identifier for the evaluation case (optional).
- `prompt`: A single user message — Shape A.
- `agent_data.turns`: Prior conversation turns ending with a user message — Shape B.

## Creating Custom Datasets

You can create custom datasets in two ways:

1. **By Hand**: Copy `basic-dataset.json` as a template and manually add evaluation cases.
2. **Synthesize**: Use the synthetic dataset generation command to generate conversation scenarios:
   ```bash
   agents-cli eval dataset synthesize --count 10
   ```

## Discovering Metrics

You can discover available out-of-the-box evaluation metrics by running:

```bash
agents-cli eval metric list
```

## Beyond Generate and Grade

Once you have a baseline, the eval surface has a few more commands worth knowing about:

- `agents-cli eval compare BASE CAND` — diff two grade-results files (regression check).
- `agents-cli eval analyze RESULTS` — cluster failure modes from a grade-results file.
- `agents-cli eval optimize` — auto-tune your agent's prompts using eval data.

See the [Evaluation Guide](https://google.github.io/agents-cli/guide/evaluation/) for the full surface and metric reference.

## Project suites and acceptance bar

- `basic-dataset.json`: two core cases—Armenian bounded clarification and an
  accepted-only current-data read.
- `structured-tariff-questions.json`: the two starter cases of the structured
  retrieval loop—an answered single-offering rate and a must-abstain offering
  with no accepted projection.
- `structured-tariff-held-out.json`: eight held-out cases covering Armenian
  phrasing, currency narrowing, explicit comparison, family ranking, an
  incomparable fee ranking, mortgage down payment, a fee inventory, and accepted
  change history. These were written after the starter loop and graded once.
- `../../fixtures/target_questions.py`: all 25 target questions with their
  expected typed route and structured outcome, asserted by
  `tests/unit/test_target_questions.py` without any model call.
- `../../../scripts/seed_evaluation_corpus.py`: loads the synthetic structured
  corpus into a database whose name ends in `_test`. Run it instead of
  `fixtures.sql` for the structured suites.
- `expanded-intent-safety.json`: 22 cases spanning every configured offering,
  bilingual/fuzzy resolution, stale/history behavior, unsupported requests,
  and tool-routing safety.
- `../fixtures.sql`: evaluation-only accepted/stale/history/review-pending rows.
  It starts with `TRUNCATE ... CASCADE`; apply it only to a disposable database
  whose name ends in `_test`.
- `../RESULTS.md`: model/config versions, acceptance threshold, aggregate
  scores, failure analysis, and the ADK state-seeding limitation.

Start the isolated database, wait for it to become healthy, stream all
migrations into it, then seed it:

```bash
docker compose --profile test up -d db-test
for migration in migrations/*.sql; do
  docker compose exec -T db-test psql -v ON_ERROR_STOP=1 \
    -U tariff -d tariff_monitor_test < "$migration"
done
docker compose exec -T db-test psql -v ON_ERROR_STOP=1 \
  -U tariff -d tariff_monitor_test < tests/eval/fixtures.sql
```

Run the core or expanded suite with host-reachable test database URLs. A short
wait keeps the explicit monitoring case bounded because no worker is started:

```bash
DATABASE_URL=postgresql+asyncpg://tariff:tariff@127.0.0.1:5433/tariff_monitor_test \
SESSION_SERVICE_URI=postgresql+asyncpg://tariff:tariff@127.0.0.1:5433/tariff_monitor_test \
TARIFF_RUN_POLL_SECONDS=0.05 \
agents-cli eval run \
  --dataset tests/eval/datasets/expanded-intent-safety.json \
  --config tests/eval/eval_config.yaml --qps 2
```
