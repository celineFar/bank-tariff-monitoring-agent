# Demonstration stack

A second copy of the project's `db`, `api` and `worker` services, run as a
separate Compose project (`tariff-demo`) with its own database volume, network
and logs. Demonstrations that need real monitoring runs use it, so they never
touch the main stack or its data.

- **Same code as the main stack.** It runs the images the main stack built
  (`second-monitor-api`, `second-monitor-worker`) and never builds its own.
  After changing `app/`, rebuild those first: `docker compose build api worker`.
- **Same configuration**, from `.env`, with two overrides in `compose.demo.yml`:
  - `SCHEDULE_ENABLED=false`: runs happen only when a demonstration asks.
  - `ACQUISITION_FRESHNESS_HOURS=0`: every run fetches the source again.
- **API** at `http://127.0.0.1:8091/api/v1` (local only). The demo database is
  not exposed on the host.

## One-time setup

```bash
cd Presentation-demonstrations/demo-stack
python3 stack.py up          # creates the demo database from migrations/
python3 stack.py baseline    # one real run of Overdraft: Gemini is called
python3 stack.py status
```

The baseline is only needed once: the database persists across `down` and
`up`. If the baseline run pauses for a review, answer it with
`python3 stack.py chat` and type `Review the pending candidates`.

## Commands

| Command | What it does |
|---|---|
| `python3 stack.py up` | start the stack |
| `python3 stack.py baseline` | one real run, only if the offering has no accepted snapshot yet |
| `python3 stack.py status` | accepted snapshots and run counts in the demo database |
| `python3 stack.py chat` | the chat CLI, connected to the demo stack |
| `python3 stack.py logs` | follow the demo worker's log |
| `python3 stack.py down` | stop the stack and keep the database |
| `python3 stack.py destroy` | stop the stack and delete the demo database |

Accepted tariffs count as fresh for 7 days (`TARIFF_FRESHNESS_DAYS`). After
that the API still serves them, but marks them stale.
