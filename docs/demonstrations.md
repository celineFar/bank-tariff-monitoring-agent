# Deliverable demonstrations

`scripts/run_demonstration.py` runs the demonstrations required by
`Project Documents/System Description.md` section 7 and checks explicit success
criteria. Each scenario prints the steps it performed, then a `PASS`/`FAIL`
line per criterion. The process exits `0` only when every criterion of every
selected scenario passed, so a reviewer does not have to interpret the output.

Scenarios are deterministic and offline. They drive the real application
services — the run lifecycle, snapshot admission and comparison, review
repository, URL allowlist, HTTP retriever, retry policy, failure mapping,
projection, and the structured query service — against a disposable `_test`
database. None of these offline scenarios touches the bank website or spends model
credits; the live presentation demonstrations below do both.

Deliverable 9 runs on a **recorded live capture** rather than fixture data: it
replays the newest readable `end-to-end/run_NNN` written by
`scripts/demonstrate_end_to_end.py`, so the page text and the Gemini output on
screen are the real ones. The other scenarios use the synthetic corpus in
`tests/fixtures/`. Each scenario also writes a markdown transcript for screenshots. Every
invocation claims its own numbered directory —
`artifacts/demonstrations/run_NNN/<scenario>.md` — so a later run never
overwrites an earlier run's transcripts; pass `--no-audit` to skip writing them.

## Setup

```bash
docker compose --profile test up -d db-test
for migration in migrations/*.sql; do
  docker compose exec -T db-test psql -v ON_ERROR_STOP=1 \
    -U tariff -d tariff_monitor_test < "$migration"
done
export TEST_DATABASE_URL=postgresql+asyncpg://tariff:tariff@127.0.0.1:5433/tariff_monitor_test
```

The runner refuses any database whose name does not end in `_test`, and each
scenario truncates monitoring data before it starts.

## Running

```bash
uv run python scripts/run_demonstration.py --list
uv run python scripts/run_demonstration.py --scenario all
uv run python scripts/run_demonstration.py --scenario hitl --scenario failures
echo $?   # 0 only when every criterion passed
```

To record a fresh capture for the `extraction` scenario, or to replay a
specific one:

```bash
uv run python scripts/demonstrate_end_to_end.py \
  https://ameriabank.am/en/personal/loans/consumer-loans/overdraft
DEMONSTRATION_CAPTURE=run_006 uv run python scripts/run_demonstration.py \
  --scenario extraction
```

The capture must be of a seed URL in `app/config/seed_catalog.yaml`, so that
the replayed extraction belongs to a catalog offering.

### A capture is not a monitored tariff

`scripts/demonstrate_end_to_end.py` writes files and nothing else. It runs on
the filesystem repositories, covers `acquisition`, `normalization`,
`source-discovery`, and `semantic-extraction`, and stops there: it never
validates, publishes, compares, or persists a snapshot, and it never touches
PostgreSQL. So `end-to-end/run_006` being an Overdraft capture does not give
the chat an Overdraft tariff to answer from — `get_current_tariffs` reads
accepted rows in `tariff_snapshots`, which only a monitoring run writes (a worker run,
or a chat-initiated run executed in the chat's process; see
[run-lifecycle.md](run-lifecycle.md)). When the chat says a snapshot is missing for an offering you have a capture of, both
statements are true; ask it to monitor that offering to publish one.

## What a successful run shows

| Scenario | Deliverable | Criteria that must pass |
|---|---|---|
| `extraction` | 9 — normal tariff extraction | every quote the model cited is found verbatim in the captured source text; the extraction clears deterministic admission with no review signal; the question is answered from stored data; both requested rate fields returned; every value cited; each citation has an exact quote and locator; the stored as-of time is reported |
| `change-detection` | 10 — tariff change detection | the rate change between two accepted runs is detected; only that field is reported changed; two snapshots with equal disclosed values raise no alert; a history question answers; each change carries both previous and current evidence |
| `document-processing` | 11 — digital PDF and scanned OCR fallback | a real bank PDF ships as a committed fixture; a PDF with a text layer classifies as `machine_readable` or `mixed`; a page with no text layer classifies as `image_only`; the prober reports zero characters rather than guessing; **with an engine present**: OCR transcribes the image-only page, the recovered text contains values rendered into the page image, and a mean confidence is reported |
| `hitl` | 12 — human-in-the-loop | a jump past the threshold raises a signal without the model; the candidate is stored `review_required`, never auto-accepted; the reviewer gets candidate value, previous value and an evidence link; answers during review still show the older accepted value; the decision records its reviewer; the queue clears |
| `failures` | 13 — controlled failures | an off-domain URL is refused before any request; a 404 maps to `source.not_found`; a client error is not retried; a timeout maps to `source.timeout`; retries stop at `max_attempts`; an unexpected content type is refused; a question with no accepted data abstains; **every failure path returns zero tariff values** |

A scenario with zero criteria is treated as a failure, so an empty or
half-written scenario cannot report a pass.

## Known limits of these demonstrations

- **The OCR leg needs a local engine.** The four probe criteria run anywhere.
  The OCR criteria run only when the optional `ocr` extra and a tesseract binary
  with the configured language data are both present; otherwise the scenario
  prints a `SKIPPED` note and evaluates only the four deterministic criteria. A
  skip is never reported as a pass. `OCR_*` in `.env.example` is live
  configuration now — see [configuration.md](configuration.md).
- **Transport failures are scripted** through `httpx.MockTransport` so the run
  is reproducible offline. The retriever, allowlist, retry policy, and failure
  mapping are the production code paths; only the socket is simulated.
- **Deliverable 9 replays, it does not re-acquire.** The fetch and the Gemini
  calls happened when the capture was recorded; the scenario replays their
  stored output and runs admission, persistence, projection and the query for
  real. Re-record with `scripts/demonstrate_end_to_end.py` to demonstrate
  acquisition itself.
- **Row citations inherit a rowspan cell's locator.** A table row is cited with
  the locator of its first cell (`app/services/extraction_evidence.py`), so
  rows sharing a vertical rowspan header resolve to the same DOM node. The
  quote and the row id stay exact; the CSS path is not row-unique.
- **Fixture values are synthetic.** Outside deliverable 9, the numbers come
  from `tests/fixtures/evaluation_corpus.py` and are not observed Ameriabank
  tariffs.

## Live presentation demonstrations

`Presentation-demonstrations/` holds the demonstrations shown in the presentation.
Unlike the scenarios above, the stack demonstrations run real monitoring runs against
the live bank site (or a local mirror of it) and Gemini. They use a separate Compose project, `demo-stack/` (`tariff-demo`: its own
`db`, `api` and `worker` on the main stack's images, with `SCHEDULE_ENABLED=false`
and `ACQUISITION_FRESHNESS_HOURS=0`, API at `127.0.0.1:8091`), so they never touch the
main stack's data. `python3 present.py` sets up the stack, restores the
`bank-baseline` checkpoint, and runs each demonstration in order, asking before each
(`--check` shows what setup would do). See `Presentation-demonstrations/README.md`.

| Folder | Deliverable | Source | Cost |
|---|---|---|---|
| `Normal-extraction/` | 9 — one real Overdraft run to a published tariff, with its card, report and pipeline audit | live bank site + Gemini | ~$0.13 |
| `Controlled-failures/` | 13 — three real runs failed on purpose (`source.timeout`, `source.model_failed`, `source.size_rejected`); the accepted tariff stays unchanged | live bank site, no paid model call | $0 |
| `Change-detection-and-review/` | 10 and 12 — a local HTTPS mirror republishes Overdraft 4 points higher; the run stops for review and publishes after approval in the chat | local mirror + Gemini | ~$0.08 |
| `OCR-fallback/` | 11 — synthetic scanned PDFs through the PDF service with Gemini made to fail, scored against the real Gemini path | worker image, no database | $0 (OCR); ~$0.003 per sample with `--engine gemini` |

Order matters: the change demonstration restores its own checkpoint and leaves a
synthetic rate behind, so it runs last among the three stack demonstrations.

## Related demonstrations

| Script | Purpose | Cost |
|---|---|---|
| `scripts/demonstrate_end_to_end.py` | the live acquisition pipeline, to files only — no snapshot is published | network + Gemini |
| `scripts/demonstrate_source_discovery.py` | official source discovery | network + Gemini |
| `scripts/demonstrate_pdf_extraction.py` | PDF transcription (`--execute-llm`) | Gemini |
| `scripts/demonstrate_native_hitl.py` | the ADK native review payload | free |
| `scripts/trace_structured_answer.py` | one answer, stage by stage | free with `--no-vector` |
| `scripts/structured_eval_metrics.py` | quality metrics over the 25 target questions | free |
