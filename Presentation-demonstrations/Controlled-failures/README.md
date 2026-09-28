# Controlled failures

Three real monitoring runs of Overdraft fail on purpose, each at a different
point in the pipeline. The script shows what the database holds before and
after, and checks that the failures were safe: no tariff value was written, and
the API still serves the last accepted tariff.

| Failure | The one artificial change (`failures/*.yml`) | Fails at | Code |
|---|---|---|---|
| The bank's site does not answer | inside the worker, `ameriabank.am` resolves to 192.0.2.1, an address routed nowhere | `acquisition`, after about 60 s of bounded retries | `source.timeout` |
| The model provider fails | source discovery uses the retired `gemini-2.5-flash-lite`, with no fallback | `pdf_selection`: Google answers `404 NOT_FOUND` | `source.model_failed` |
| A safety limit refuses the source | download size cap lowered from 25 MB to 50 KB | `acquisition` | `source.size_rejected` |

Everything else is real: the monitoring API, the worker, the pipeline, the
bank's site, and Gemini. The failures cost nothing, because none of them
reaches a paid model call.

## Run

The demo runs against the persistent demonstration stack (`../demo-stack`). Set
it up once:

```bash
cd Presentation-demonstrations/demo-stack
python3 stack.py up
python3 stack.py baseline        # one real Overdraft run, about $0.13
```

Then, as often as you like:

```bash
cd Presentation-demonstrations/Controlled-failures
python3 failure_demo.py                      # all three, about 2 minutes
python3 failure_demo.py --failure timeout    # just one (repeatable)
```

Exit code 0 means every check passed. The report is written to
`output/report.md`.

## What the script does

1. **Before.** It fingerprints every table a run writes tariff data into:
   `tariff_snapshots`, `tariff_facts`, `fact_evidence`, `tariff_changes`,
   `snapshot_documents` and `human_reviews`. The fingerprint is the row count plus
   an MD5 of every row. It also asks `GET /api/v1/tariffs/current` what Overdraft
   costs.
2. **Each failure.** It restarts the demo worker with that failure's overlay and
   submits a run through `POST /api/v1/runs`. From the database it then reads the
   run's status, the stage it failed at, the failure code, the recorded cause,
   the model calls made, and whether any snapshot or change was written. It also
   shows the sentence an operator is given, taken from the application's own
   `explain_failure_code`, and the worker's log lines for the run.
3. **After.** It takes the same fingerprints and asks the same API question
   again.
4. **Checks.** Each run failed with its expected code and wrote no snapshot or
   change. All six table fingerprints are identical. The API serves the same
   snapshot, with the same content hash and rates. The normal worker is running
   again.

The normal worker is restored at the end, even if the script is interrupted by
an error. Each run of the demo adds three failed runs to the demo database's run
history; tariff data is never touched.

## Presenting it

- Before running, open `failures/`: each file is a few lines and states the one
  thing it changes.
- The timeout failure takes about a minute. The wait is the point: the retries
  are bounded, and the run doesn't hang.
- For the model failure, point at the recorded cause
  `ClientError:http_404_NOT_FOUND`. That is Google's real answer for the retired
  model, the same failure this system hit on 2026-09-22.
- End on the before and after tables: the same digests, the same snapshot and
  the same rates.
