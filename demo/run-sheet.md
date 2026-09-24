# Demonstration run sheet

Every clip is filmed from this sheet. Read the disclosure lines aloud or type
them; do not improvise them.

Plan: `fix-plans/demonstration-recording-plan.md`. Deliverables:
`Project Documents/System Description.md` section 7.

---

## Before any recording

1. **Build from current source.** The image bakes `app/` in; a stale image was
   already caught once during preparation.

   ```bash
   docker compose -f docker-compose.yml build api worker
   ```

2. **Issue the demonstration certificate** (idempotent; reuses an existing root):

   ```bash
   ./demo/bin/make-certs.sh
   ```

3. **Select the demo stack** for the whole session, so `./tariff-chat` works
   unchanged and the recording shows the ordinary command:

   ```bash
   export COMPOSE_FILE=docker-compose.yml:docker-compose.demo.yml
   docker compose build api
   docker compose up -d
   ```

4. **Restart the mirror after any branch switch or variant rebuild.** The mirror
   bind-mounts `demo/mirror/<variant>`. Checking out another branch, or
   rebuilding the variants, deletes and recreates that directory, and the
   container keeps the old inode and serves 404 for everything. A run then fails
   instantly with `source.not_found`, which looks like a real failure and is not
   one:

   ```bash
   ./demo/bin/mirror-variant.sh unchanged
   docker compose exec -T api uv run python -c \
     "import httpx; print(httpx.get('https://tariff-mirror.demo/overdraft').status_code)"
   ```

   The check runs inside `api` on purpose: the mirror is only on the Compose
   network, so a `curl` from the host cannot reach it and proves nothing. Going
   through the container also proves the demo root is trusted.

   Expect `200`. This bit during preparation, so check it before every take.

5. **Confirm the trust wiring** before rolling:

   ```bash
   docker compose logs api | grep 'demo: trusted'
   ```

6. **Capture the baseline** if there is not one already:

   ```bash
   ./demo/bin/baseline.sh capture
   ./demo/bin/baseline.sh show
   ```

### Secrets checklist — every take

- Never run `cat .env`, `docker compose config`, or `env` on camera.
- Do not open `.env` in an editor while recording.
- Show configuration from `docs/configuration.md` instead.
- Review the finished clip before it leaves the machine.

---

## Clip 9 — extraction and evidence

**Deliverable 9. Nothing is staged.**

Preconditions: baseline restored, so the accepted snapshot is the one acquired
from the bank.

```bash
./demo/bin/baseline.sh restore
./tariff-chat
```

| # | Type this | Expect |
|---|---|---|
| 1 | `What are the interest rates on the card overdraft?` | 21% standard, 20% premium, 15–21% scoring-based, each with its APR, plus the +0.5% / +0.25% adjustments |
| 2 | `Which official document does the 21% come from, and when was it retrieved?` | the bank's page URL and leaflet URL, the section path, quoted evidence, and both `Snapshot Accepted At` and `Current As Of` |

Do not shorten this to one question: a bare tariff question returns the values
without citations, locators or as-of, and the deliverable needs all three.

---

## Clip 10 — change detection

**Deliverable 10 and 12. The republished page is staged.**

> **Disclosure, before the first run.** "The seed URL for this offering points at
> a local mirror. It serves a copy of Ameriabank's own Overdraft page. In the
> second half I will republish that copy with the nominal rate band raised by
> four points — 21% to 25%, 20% to 24%, and the 15–21% band to 19–25%. The APR
> figures are left at their published values, so exactly one field changes.
> Everything after the fetch is the real pipeline."

```bash
./demo/bin/baseline.sh restore
./demo/bin/mirror-variant.sh unchanged
./tariff-chat
```

| # | Step | Expect |
|---|---|---|
| 1 | `Run monitoring for the card overdraft now.` | stage lines, then a published snapshot. If it raised reviews, answer them — this run is not yet a usable baseline |
| 1b | `Run monitoring for the card overdraft now.` | run again until one completes **without** review. Only then is the extraction fully cached, and only then does an identical re-run report nothing |
| 2 | `Run monitoring for the card overdraft now.` | a second run over identical content; **no change reported** |
| 3 | `./demo/bin/mirror-variant.sh republished` in a second terminal | mirror now serves the raised band |
| 4 | `Run monitoring for the card overdraft now.` | `large_rate_change`, the run pauses for review |
| 5 | answer every review in the queue (see below) | decisions recorded, snapshot published |
| 6 | `What changed in the card overdraft tariffs?` | previous and current value with evidence for both |

**Why step 1b exists.** A batch that raises a review is not cached, so the next
run re-calls the model for it, and the model varies on free-text shape —
`["Payments", "cash withdrawal"]` one run, `["Payments, cash withdrawal"]` the
next. Change detection reports that variance. Only a run whose extraction was
fully cached re-runs byte-identically, so the baseline has to be a review-free
run. Confirmed in the log as `Reusing 6 cached semantic-extraction batch(es)`.

**Quota.** Each publishing run spends Gemini embedding quota, and clip 10 needs
three of them. Exhausting it fails the run at the embedding stage with
`indexing.embedding_failed`. Check quota before a session, and film clip 10
early rather than after a dozen retakes.

Step 2 is the point of the clip as much as step 4: equal content must raise no
alert.

Use the exact wording in step 1. "Check for changes" resolves to the history
intent and no run starts.

---

## How a review is answered

Read this before clips 10, 11, 12 or 15. It is the part that is easy to get
wrong on camera.

**Every review takes two answers: a value, then the passage that supports it.**
The prompt sequence is `Collateral >` then `Supporting passage (1-15) >`. Type
`?` at the passage prompt to page through every captured passage with its source
URL and page or table locator, then enter the number. A reviewer cannot record a
value without pointing at the evidence for it.

**Answer the whole queue in one sitting.** Decisions are held in session state
and committed as a batch when the last review is answered. Leaving half-way
leaves every review `pending`, and reopening the session starts again at the
first one. This was confirmed during the dry run: four separate part-answers
recorded nothing, and one session answering both reviews committed both.

**The overdraft run raises two reviews, reliably**, both
`missing_required_field`:

| # | Field | Answer used in the dry run | Supporting passage |
|---|---|---|---|
| 1 | Collateral | `none` | the passage reading "Overdraft: without collateral" |
| 2 | Product name | `Overdrafts via Cards not secured with property` | the leaflet's own title line on page 1 |

Both answers are read off the bank's own documents. Do not invent a value to
clear a prompt: `reject_all` is there for when the evidence does not support one.

The passage numbers shift between runs, so **read the list on camera** rather
than typing a number from this sheet. That is also the better demonstration: it
shows the reviewer being given what they need to decide.

---

## Clip 11 — OCR fallback

**Deliverable 11. The scanned document is staged.**

Two halves, both real. The live pipeline shows the scan being *detected*; the
scenario shows OCR *taking over*. OCR does not run in the live pipeline here,
and the clip should say why rather than hide it: a page goes to OCR only when
the probe calls it image-only **and Gemini returned nothing for it**. Gemini is
multimodal and reads the scan, so the fallback correctly has nothing to catch.

> **Disclosure.** "The mirror now links a scanned version of the bank's own
> Overdraft information guide: the real document rendered to page images, with
> the text layer removed. Nothing in it was retyped."

**Part one — detection in the live pipeline.**

```bash
./demo/bin/mirror-variant.sh scanned
./demo/bin/run-offering.sh consumer_loan overdraft
docker compose logs worker | grep "classified as image_only"
```

Expect `classified as image_only (image_only=2)` for the scanned document, beside
`classified as mixed` for the bank's digital leaflets.

**Part two — the OCR fallback, deterministic and free.**

```bash
docker compose exec api uv run python scripts/run_demonstration.py \
  --scenario document-processing --no-audit
```

Expect `RESULT: PASS (7/7 criteria)`, OCR `outcome=transcribed`, recovered
tokens `13.5`, `14.2`, `AMD`, `300,000`, and a mean confidence near 92.6. It runs
inside `api` because that is where Tesseract is installed.

Cost: part one ≈ $0.12 the first time (every extraction batch re-runs when a
document changes) and near $0 on a retake, from cache. Part two is free.

---

## Clip 12 — human review

**Deliverable 12. Same staging as clip 10.**

Film the review pause from clip 10 in full, unhurried: the field, the candidate
value, the previous value, the evidence, and the input format the tool states.
Show both paths — a rejection and then, on a retake, an approval — and finish by
showing the queue empty.

---

## Clip 13 — controlled failures

**Deliverable 13. Four legs, four boundaries.**

Confirm after every leg that no tariff values were saved.

### 13a — no accepted data (nothing staged)

```bash
./demo/bin/baseline.sh restore
./tariff-chat
```

Ask about an offering with no snapshot, for example the credit line, and decline
monitoring when offered. Expect an abstention, not a number.

### 13b — source.timeout

```bash
export COMPOSE_FILE=docker-compose.yml:docker-compose.demo.yml:demo/compose.timeout.yml
docker compose up -d api worker
./tariff-chat
```

`Run monitoring for the card overdraft now.` Expect about a minute of heartbeats
while the bounded retries run, then `source.timeout` with its operator sentence.
Leave the pacing alone: the wait is the evidence that retries are bounded.

### 13c — source.size_rejected

```bash
export COMPOSE_FILE=docker-compose.yml:docker-compose.demo.yml
docker compose up -d api worker
uv run python demo/bin/build-oversized.py
./demo/bin/mirror-variant.sh oversized
```

Expect `source.size_rejected`. The mirror compresses, so there is no
`Content-Length` and the retriever stops mid-stream on decoded bytes.

### 13d — source.model_failed

```bash
export COMPOSE_FILE=docker-compose.yml:docker-compose.demo.yml:demo/compose.model-failure.yml
docker compose up -d api worker
```

> **Disclosure.** "Source discovery is pointed at a model the provider retired.
> This is not hypothetical: it is the failure this system actually hit on
> 22 September, and it is why the fallback chain exists."

Expect `source.model_failed`. Afterwards, restore the default stack:

```bash
export COMPOSE_FILE=docker-compose.yml:docker-compose.demo.yml
docker compose up -d api worker
```

---

## Clip 15 — full session, uncut

**Deliverables 8, 9 and 15.**

One take. Accept stumbles; do not edit.

```bash
./demo/bin/baseline.sh restore
./demo/bin/mirror-variant.sh unchanged
./tariff-chat
```

1. Ask the overdraft question and then for its source — the bank's own evidence.
2. Ask for a mortgage the system has never monitored (primary market), authorize
   the run, and let it publish. This one acquires from `ameriabank.am` for real.
3. Republish the overdraft copy, run again, take the review, and read the
   detected change.

Budget for a retake: step 2 spends model credits and depends on the bank's site.

---

## After filming

```bash
./demo/bin/baseline.sh restore
export COMPOSE_FILE=docker-compose.yml
docker compose up -d
```

Confirm the shipped stack runs with no demo overlay before the technical review.
