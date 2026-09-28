# Debug and run cheat sheet (start here)

Open in Markdown preview (`Ctrl+Shift+V`). Every link opens the file at the line.
Code map for "where is X": [../codebase-map/README.md](../codebase-map/README.md).

| Page | Use it when |
|---|---|
| **This page** | You changed code and need to run it; you need a command |
| [diagnose.md](diagnose.md) | Something looks wrong: logs, SQL, audit files, trace scripts, debug knobs |
| [symptoms.md](symptoms.md) | You see a specific symptom and want the cause, the file to open, and the check that confirms it |
| [trace.md](trace.md) | "Walk me through what happens when…": one chat question, one monitoring run, one review, hop by hop |
| [drills.md](drills.md) | Practice: likely "change X live" tasks, each done and tested once |

---

## 0 · Before the interview (once)

```bash
docker compose ps                         # api, worker, db all Up
docker compose port api 8080              # → which host port the API is on
docker compose port db 5432               # → which host port Postgres is on
export API=http://localhost:8080          # use the port printed above (8081 on this machine)
curl -s $API/api/v1/healthz               # {"status":"ok"}
uv run pytest tests/unit -q -p no:cacheprovider   # baseline: 1208 passed, 5 skipped, ~45 s
```

Ports: the defaults are API `8080`, DB `5434` ([docker-compose.yml](../../docker-compose.yml#L11)).
On this machine they are `8081` / `5435` because [docker-compose.local.yml](../../docker-compose.local.yml) was used.
`docker compose up` without `COMPOSE_FILE=docker-compose.yml:docker-compose.local.yml` switches back to the defaults.

---

## 1 · Which process runs my code?

The images **copy** `app/` at build time ([Dockerfile](../../Dockerfile#L29)). The code is not mounted, so the containers keep the old code until you rebuild.

| You start… | Code that runs | Where the pipeline runs | Your edit applies after… |
|---|---|---|---|
| `./tariff-chat` | api **container** ([launcher](../../tariff-chat)) | in the chat process (the [monitoring node](../../app/services/monitoring_node.py#L160)) | `docker compose up --build -d api worker` |
| `Guide/debug/local.sh python app/cli_entry.py` | **host** (your working tree) | in that same host process | restart the command |
| `curl -X POST $API/api/v1/runs` | the api that received it only enqueues ([create_run](../../app/api/routes.py#L104)) | **worker** ([process_next](../../app/worker.py#L133)) | rebuild the worker, **or** run the worker locally (below) |
| Daily schedule | worker ([schedule_daily_monitoring](../../app/worker.py#L51)) | worker | same as above |
| `uv run pytest …` | host | in the test (fakes, no DB) | immediately |

Both paths call the same [TariffPipeline.execute](../../app/services/monitoring_pipeline.py#L584).

---

## 2 · The fast loop: edit → test → run locally (no rebuild)

[local.sh](local.sh) runs any command on the host against the **Docker Postgres**. It finds the DB port, keeps `.env` (API key, models), and writes logs to `local-run/logs/local.log` and audit files to `local-run/audit/`. The containers' `logs/` and `artifacts/` are owned by root.

```bash
# 1. closest unit test (which file: ../codebase-map/6-tests-evals-demos.md)
uv run pytest tests/unit/test_snapshot_lifecycle.py -q -p no:cacheprovider -k large_rate

# 2a. chat with YOUR code (a chat question costs ~$0.015; a cached monitoring run is ~free)
Guide/debug/local.sh python app/cli_entry.py --session demo --verbose

# 2b. one-shot, non-interactive (good for a quick proof)
printf 'What is the overdraft interest rate?\n' | Guide/debug/local.sh python app/cli_entry.py --session demo --verbose

# 2c. API with YOUR code, auto-reload on save
Guide/debug/local.sh uvicorn app.fast_api_app:app --port 8090 --reload
curl -s localhost:8090/api/v1/healthz

# 2d. worker with YOUR code (so POST /runs executes your pipeline)
docker compose stop worker
Guide/debug/local.sh python -m app.worker          # Ctrl-C to stop
docker compose start worker                        # afterwards

# override any setting for one command (shell env beats .env)
HITL_LARGE_RATE_CHANGE_PERCENTAGE_POINTS=1 LOG_LEVEL=DEBUG Guide/debug/local.sh python app/cli_entry.py --session demo
```

What's different on the host:
- **OCR is off locally.** The `ocr` extra and `tesseract` are only in the image ([Dockerfile](../../Dockerfile#L20)). The startup log says `OCR unavailable: pytesseract is not installed`. For OCR paths, rebuild and use Docker, or `uv sync --extra ocr` plus `sudo apt install tesseract-ocr tesseract-ocr-hye`.
- Host Python is 3.13 and the image uses 3.12. It hasn't mattered so far.
- `WARNING root: Failed to build response JSON schema for monitoring` plus a pydantic traceback at startup is normal (same in Docker).

## 3 · Final check in Docker

```bash
docker compose up --build -d api worker     # after editing app/  (≈1–2 min, cached layers)
docker compose up -d --force-recreate api worker   # after editing .env only
./tariff-chat --session demo --verbose      # --new for a fresh conversation
docker compose logs -f --tail=100 worker api
```

Keep the port override on this machine: prefix with `COMPOSE_FILE=docker-compose.yml:docker-compose.local.yml`.

## 4 · Commands you'll type most

| Task | Command |
|---|---|
| Start a run (one offering) | `curl -s -X POST $API/api/v1/runs -H 'content-type: application/json' -d '{"product":"consumer_loan","offering_id":"overdraft"}'` ([RunRequest](../../app/api/routes.py#L53)) |
| Start a run (whole family) | same with `-d '{"product":"mortgage"}'` |
| Run status | `curl -s $API/api/v1/runs/<run_id> \| jq` ([get_run](../../app/api/routes.py#L156)) |
| Current tariffs | `curl -s "$API/api/v1/tariffs/current?product=consumer_loan&offering_id=overdraft" \| jq` ([get_current_tariffs](../../app/api/routes.py#L230)) |
| Pending reviews | `curl -s $API/api/v1/reviews \| jq` ([list_reviews](../../app/api/routes.py#L283)) |
| Resume a paused review | `./tariff-chat --session <same name>` (it offers to continue) |
| SQL shell | `docker compose exec db psql -U tariff -d tariff_monitor` (no `psql` on the host) |
| One test | `uv run pytest tests/unit/<file>.py -q -p no:cacheprovider -k <name>` |
| All unit tests | `uv run pytest tests/unit -q` (~45 s) |
| Lint | `uv run ruff check app tests` |
| Why did it answer X? | `Guide/debug/local.sh python -m scripts.trace_structured_answer "<question>" --no-vector` ([script](../../scripts/trace_structured_answer.py)) |
| Cost today | `Guide/debug/local.sh python -m scripts.model_cost_report --days 1` |

More: [diagnose.md](diagnose.md) (SQL, logs, audit files).

## 5 · Say-it-out-loud checklist for a live change

1. **Locate**: find it in [codebase-map](../codebase-map/README.md#quick-lookup-change--go-here) or `grep -rn "<term>" app/`.
2. **Test first**: find the test that covers it and run it green ([6-tests](../codebase-map/6-tests-evals-demos.md)).
3. **Edit** the smallest place. Settings go in `.env` or as a command prefix. Rules go in code.
4. **Test** the same file again, then `uv run pytest tests/unit -q`.
5. **Show it**: `local.sh` chat, API or worker, then the evidence in [diagnose.md](diagnose.md) (log line, SQL row, audit file).
6. **Did I bypass a cache?** Prompt edits need a version bump ([why](../codebase-map/2-monitoring-pipeline.md#caches-why-a-rerun-costs-0)), and so does a new schema.
