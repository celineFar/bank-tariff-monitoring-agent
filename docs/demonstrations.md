# Deliverable demonstrations

`scripts/run_demonstration.py` runs the demonstrations required by
`Project Documents/System Description.md` section 7 and checks explicit success
criteria. Each scenario prints the steps it performed, then a `PASS`/`FAIL`
line per criterion. The process exits `0` only when every criterion of every
selected scenario passed, so a reviewer does not have to interpret the output.

Scenarios are deterministic and offline. They drive the real application
services — the run lifecycle, snapshot comparison, review repository, URL
allowlist, HTTP retriever, retry policy, failure mapping, projection, and the
structured query service — against a disposable `_test` database and fixture
data. No demonstration touches the bank website or spends model credits.

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

## What a successful run shows

| Scenario | Deliverable | Criteria that must pass |
|---|---|---|
| `extraction` | 9 — normal tariff extraction | answered from accepted data; both requested rate fields returned; every value cited; each citation has an exact quote and locator; AMD and USD stay separate; the accepted as-of time is reported |
| `change-detection` | 10 — tariff change detection | the rate change between two accepted runs is detected; only that field is reported changed; two snapshots with equal disclosed values raise no alert; a history question answers; each change carries both previous and current evidence |
| `document-processing` | 11 — digital PDF and scanned fallback | at least one real bank PDF is probed; PDFs with a text layer classify as `machine_readable` or `mixed`; a page with no text layer classifies as `image_only`; the prober reports zero characters rather than guessing |
| `hitl` | 12 — human-in-the-loop | a jump past the threshold raises a signal without the model; the candidate is stored `review_required`, never auto-accepted; the reviewer gets candidate value, previous value and an evidence link; answers during review still show the older accepted value; the decision records its reviewer; the queue clears |
| `failures` | 13 — controlled failures | an off-domain URL is refused before any request; a 404 maps to `source.not_found`; a client error is not retried; a timeout maps to `source.timeout`; retries stop at `max_attempts`; an unexpected content type is refused; a question with no accepted data abstains; **every failure path returns zero tariff values** |

A scenario with zero criteria is treated as a failure, so an empty or
half-written scenario cannot report a pass.

## Known limits of these demonstrations

- **No OCR engine.** This project has no tesseract stage. Scanned pages are
  transcribed by Gemini's multimodal PDF reading; the deterministic prober is
  what detects a page with no text layer and routes it there. `.env.example` no
  longer carries `OCR_*` variables — no code ever read them — so delete them
  from an older local `.env` rather than tuning them. The `document-processing`
  scenario proves the detection and routing, not a local OCR engine.
- **Transport failures are scripted** through `httpx.MockTransport` so the run
  is reproducible offline. The retriever, allowlist, retry policy, and failure
  mapping are the production code paths; only the socket is simulated.
- **The read side, not live acquisition.** Deliverable 9 demonstrates an
  accepted snapshot being projected and answered with evidence. The live
  acquisition pipeline needs the bank website and Gemini; use
  `scripts/demonstrate_end_to_end.py` for that.
- **Fixture values are synthetic.** The numbers come from
  `tests/fixtures/evaluation_corpus.py` and are not observed Ameriabank
  tariffs.

## Related demonstrations

| Script | Purpose | Cost |
|---|---|---|
| `scripts/demonstrate_end_to_end.py` | the live acquisition pipeline | network + Gemini |
| `scripts/demonstrate_source_discovery.py` | official source discovery | network + Gemini |
| `scripts/demonstrate_pdf_extraction.py` | PDF transcription (`--execute-llm`) | Gemini |
| `scripts/demonstrate_native_hitl.py` | the ADK native review payload | free |
| `scripts/trace_structured_answer.py` | one answer, stage by stage | free with `--no-vector` |
| `scripts/structured_eval_metrics.py` | quality metrics over the 25 target questions | free |
