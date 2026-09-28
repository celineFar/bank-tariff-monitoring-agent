# Demonstration run sheet

Every clip is filmed from this sheet. Read the disclosure lines aloud or type
them; do not improvise them.

Plan: `fix-plans/demonstration-recording-plan.md`. Deliverables:
`Project Documents/System Description.md` section 7.

---

## Status on the new system (2026-09-27)

The demonstration was moved onto the integrated runtime (`integration/process-fixes`:
one ADK agent, Gemini request interpreter, reviews applied one at a time, offering-aware
source discovery, acquisition completeness gate, legacy RAG removed) on branch
`demo/all-on-new-system`, against a fresh database built from migrations 001–027.

Verified end to end on 2026-09-27, with no model spend:

| Leg | Result |
|---|---|
| Mirror trust, `unchanged` / `republished` acquisition | 200 over HTTPS; both pass the completeness gate: 3 tables, 10 PDF links, 13,306 chars |
| 11 part two — OCR scenario | `RESULT: PASS (7/7 criteria)`, `outcome=transcribed`, confidence 92.6 |
| 13b — `source.timeout` | run and offering `failed · source.timeout` after 62 s, $0 |
| 13c — `source.size_rejected` | `failed · source.size_rejected` (`PAGE_TOO_LARGE`) at acquisition, $0 |
| 13d — `source.model_failed` | `gemini-2.5-flash-lite` answers `404 NOT_FOUND`; `failed · source.model_failed` at `pdf_selection`, $0 |
| `baseline.sh capture / reset / restore / show` | round trip restores every state table; caches and ledger kept |

**Not yet verified: everything that calls Gemini.** The project's prepaid Gemini
credits ran out during verification (`HTTP 402 RESOURCE_EXHAUSTED`), so the bank
baseline, clips 9, 10, 12, 15, clip 11 part one and clip 13a (the chat) have not been
run on the new system. Their scripts below are adapted to the new system from code
and from the interpreter's recorded cases; the **Expect** columns marked
*(confirm)* carry the old system's observations and must be checked on the first
take. Top up the credits before starting.

---

## Before any recording

0. **Free the machine.** It has 2 CPUs and 7 GB. With a second stack running
   (`second-monitor`) and several editor sessions, Chromium renders of the bank page
   took anywhere from 17 s to 329 s, and one render of the bank page came back with
   only its first tab (0 tables, 0 PDFs). Stop every other Compose stack before
   filming:

   ```bash
   docker ps --format '{{.Names}}'          # nothing but bank-tariff-monitoring-agent-*
   uptime                                   # load average well under 2
   ```

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

   The line appears once per container start. A container that restarts and never
   prints it again is stuck; the entrypoint used to hang on restart and was fixed
   on this branch.

6. **Build and capture the baseline** if `demo/baseline/` holds no dump. A dump
   from the old system does not restore into the new schema; the one captured on
   2026-09-24 is archived outside the repository.

   The baseline is the Overdraft acquired from **the bank**, not the mirror, so the
   catalog is switched back to the bank for this one run:

   ```bash
   export COMPOSE_FILE=docker-compose.yml:docker-compose.demo.yml:demo/compose.bank-seed.yml
   docker compose up -d api worker
   ./demo/bin/baseline.sh reset              # empty run state; caches and ledger kept
   ./demo/bin/run-offering.sh consumer_loan overdraft
   ```

   Then check that the acquisition saw the whole page before going further:

   ```bash
   docker compose exec -T db psql -U tariff -d tariff_monitor -tAc \
     "select inventory from acquisition_baselines"
   ```

   Expect `"tables": 3, "pdf_links": 10`. Anything less (the 2026-09-27 attempt got
   0 and 0 on a loaded machine) means the render missed the tabs: run
   `./demo/bin/baseline.sh reset` and the run again. Do not capture it.

   If the run paused for review, answer it in the chat, reading each value off the
   bank's own passage (see *How a review is answered*):

   ```bash
   ./tariff-chat --session baseline-reviews
   # You > Review the pending candidates
   ```

   A review-free baseline matters for clip 10 step 2. Then capture it and go back to
   the demo stack:

   ```bash
   ./demo/bin/baseline.sh show              # runs succeeded, one accepted snapshot
   ./demo/bin/baseline.sh capture
   export COMPOSE_FILE=docker-compose.yml:docker-compose.demo.yml
   docker compose up -d api worker
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
| 1 | `What are the interest rates on the card overdraft?` | *(confirm)* 21% standard, 20% premium, 15–21% scoring-based, each with its APR, plus the +0.5% / +0.25% adjustments |
| 2 | `Which official document does the 21% come from, and when was it retrieved?` | the bank's page URL and leaflet URL, the section path, the source's own wording quoted verbatim, and both `Snapshot Accepted At` and `Current As Of` |

Keep it to two questions: on the old system a bare tariff question returned the
values without citations, locators or as-of, and the deliverable needs all three.
The new answer path cites every value from accepted facts; if question 1 already
shows citations and as-of on the first take, question 2 still earns its place by
naming the document.

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
| 1 | `Run tariff monitoring for the overdraft.` | stage lines, then published. This is the mirror baseline, compared against the bank capture, so it reports incidental wording changes and **no rate signal** *(confirm)* |
| 2 | `Run tariff monitoring for the overdraft.` | identical content, every batch reused: **no change reported** |
| 3 | `./demo/bin/mirror-variant.sh republished` in a second terminal | mirror now serves the raised band |
| 4 | `Run tariff monitoring for the overdraft.` | the run pauses with an `interest_rate (large_rate_change)` review *(confirm; the old system also raised `repayment (missing_required_field)`)* |
| 5 | answer every review (see below) | each answer applied as given; snapshot published once none is pending |
| 6 | `What changed in the overdraft tariff?` | the interest-rate change with its evidence |

**Wording.** Steps 1, 2, 4 and 6 use phrasings the request interpreter has recorded
cases for (`run tariff monitoring for the overdraft` → start a run; `What changed in
the … tariff?` → change history). On the new system "check overdraft for updates"
and "monitor overdraft" also start a run; the old warning that "check for changes"
lands on history no longer applies, but keep to the wording above on camera.

**What the rate review looks like.** Its first line states the jump:
*"Previous accepted value 21.0, candidate 25.0: a change of 4.0 percentage
points."* Confirm it by typing `approve`.

**First thing to check on the new system.** The republished edit changes the page's
nominal rates only; the leaflet PDFs are the bank's own and still say 21%. The new
source discovery picks the offering's leaflets itself, so if extraction reads the
rate from a leaflet as well as the page, step 4 may raise
`official_source_conflict` (pick the page's candidate) instead of, or beside,
`large_rate_change`. Film whichever the pipeline raises and name it; do not edit
the fixture to force the old one.

Step 2 is the point of the clip as much as step 4: equal content must raise no
alert. If step 1 raised a field review, answer it and run once more before step
2 — only a run that needed no review leaves every batch cached.

Measured on the old system, 2026-09-24, over HTTP: step 1 $0, step 2 $0, step 4
$0.026. Re-measure on the first take: the new system re-extracts against new
prompts, so nothing from before is cached. The chat adds its own cost on top,
mostly for the review turns.

---

## How a review is answered

Read this before clips 10, 11, 12 or 15. It is the part that is easy to get
wrong on camera.

**Each review shows what it needs.** The panel names the field and the reason,
states the jump for a rate change or Gemini's failed value for an
`extraction_invalid` review, and lists the answers it accepts. Type:

- `approve` to accept the extracted value (rate change, OCR evidence);
- a candidate number to pick one (source conflict, invalid extraction);
- the value itself to override it, in the format the panel states;
- `?` to read the selected sources, `all` to list every captured passage;
- `reject_all` to discard **this offering's** candidate snapshot. It no longer
  discards the whole run.

**An override needs its passage.** After a typed value the CLI looks for the
passage that states it: when exactly one does, it says *"Using passage N, which
states it, as support"* and moves on; otherwise it asks `Supporting passage >`.
Type `?` or `all` there to page through the passages with their source URL and
locator, then the number. A reviewer cannot record a value without pointing at the
evidence for it.

**Answers are applied one at a time.** This changed with the new runtime. Each
answer is applied as soon as it is given, and the snapshot publishes when none of
its reviews is pending. Leaving half-way keeps what was answered; reopen the chat
and type `Review the pending candidates` to finish. A review whose run has ended is
closed, not asked again.

**Which fields the overdraft run asks about** is to be confirmed on the new system.
The old system raised two `missing_required_field` reviews on the bank run:

| # | Field | Answer used in the old dry run | Supporting passage |
|---|---|---|---|
| 1 | Collateral | `none` | the passage reading "Overdraft: without collateral" |
| 2 | Product name | `Overdrafts via Cards not secured with property` | the leaflet's own title line on page 1 |

Whatever it asks, read the answer off the bank's own documents. Do not invent a
value to clear a prompt: `reject_all` is there for when the evidence does not
support one. The passage numbers shift between runs, so **read the list on
camera** rather than typing a number from this sheet.

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
`classified as mixed` for the bank's digital leaflets *(confirm)*. On the new system
source discovery chooses the offering's PDFs from their link metadata before any is
transcribed; the scanned leaflet keeps the original link text, so it should be
chosen. If the grep finds nothing, check that the run's
`pdf_link_selections` include `Overdraft_unsecured_scanned_eng.pdf`. If a value is
taken from OCR text, the run pauses with an `ocr_evidence` review: approve it
against the cited page.

**Part two — the OCR fallback, deterministic and free.** Verified 2026-09-27.

```bash
docker compose exec api uv run python scripts/run_demonstration.py \
  --scenario document-processing --no-audit
```

Expect `RESULT: PASS (7/7 criteria)`, OCR `outcome=transcribed`, recovered
tokens `13.5`, `14.2`, `AMD`, `300,000`, and a mean confidence near 92.6. It runs
inside `api` because that is where Tesseract is installed.

Cost: part one ≈ $0.12 on the old system the first time (every extraction batch
re-runs when a document changes) and near $0 on a retake, from cache. Part two is
free.

---

## Clip 12 — human review

**Deliverable 12. Same staging as clip 10.**

Film the review pause from clip 10 in full, unhurried: the field, the candidate
value, the previous value, the evidence, and the input format the panel states.
Show both paths — a rejection and then, on a retake, an approval — and finish by
showing the queue empty (`Are any candidates waiting for my review?`).

---

## Clip 13 — controlled failures

**Deliverable 13. Four legs, four boundaries.**

Confirm after every leg that no tariff values were saved. Legs b, c and d were
verified on the new system on 2026-09-27, with no model spend.

### 13a — no accepted data (nothing staged)

```bash
./demo/bin/baseline.sh restore
./tariff-chat
```

Ask about an offering with no snapshot, for example `What fees apply to the
Credit Line?`, and decline monitoring when offered. Expect an abstention, not a
number *(confirm)*.

### 13b — source.timeout

```bash
export COMPOSE_FILE=docker-compose.yml:docker-compose.demo.yml:demo/compose.timeout.yml
docker compose up -d api worker
./tariff-chat
```

`Run tariff monitoring for the overdraft.` Expect about a minute of heartbeats
while the bounded retries run (62 s measured), then `source.timeout` with its
operator sentence. Leave the pacing alone: the wait is the evidence that retries
are bounded.

On an overloaded machine the first attempt once closed as `run.internal_error`,
with the offering left `running`: recording the failure could not get a database
connection in time. It did not recur with the load down. If it happens on camera,
it is step 0 that was skipped.

### 13c — source.size_rejected

```bash
export COMPOSE_FILE=docker-compose.yml:docker-compose.demo.yml
docker compose up -d api worker
uv run python demo/bin/build-oversized.py
./demo/bin/mirror-variant.sh oversized
```

`Run tariff monitoring for the overdraft.` Expect `source.size_rejected`. The mirror
compresses, so there is no `Content-Length` and the retriever stops mid-stream on
decoded bytes.

### 13d — source.model_failed

```bash
./demo/bin/mirror-variant.sh unchanged
export COMPOSE_FILE=docker-compose.yml:docker-compose.demo.yml:demo/compose.model-failure.yml
docker compose up -d api worker
```

> **Disclosure.** "Source discovery is pointed at a model the provider retired.
> This is not hypothetical: it is the failure this system actually hit on
> 22 September, and it is why the fallback chain exists."

`Run tariff monitoring for the overdraft.` Expect `source.model_failed` at the
`pdf_selection` stage: choosing the offering's PDFs from their links is the first
thing source discovery asks Gemini on the new system. `logs/worker.log` shows the
provider's `404 NOT_FOUND` for `gemini-2.5-flash-lite`. Afterwards, restore the
default stack:

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
2. Ask for a mortgage the system has never monitored (`What is the interest rate
   of the Primary Market Mortgage?`). The assistant offers to check the bank's
   website; accept, and let the run publish. This one acquires from
   `ameriabank.am` for real.
3. Republish the overdraft copy, run again, take the review, and read the
   detected change.

Budget for a retake: step 2 depends on the bank's site and has never run on the
new system. A restore keeps the caches, so a retake re-reads the same bank content
for close to nothing unless the bank has changed it.

---

## Cost of a take

Measured during the old system's dry runs, pipeline only. The new system starts
with empty caches and new prompts, so the first take of each clip pays in full;
re-measure it. The chat agent is extra: every turn now also makes one request
interpreter call, and review turns are the largest.

| Clip | First run (old system) | Retake from cache |
|---|---|---|
| 9 | $0 — reads the stored snapshot | $0 |
| 10 | ≈ $0.03 | ≈ $0.03 — the batch that raised the field review is never cached |
| 11 part one | ≈ $0.12 — a changed document re-runs every batch | ≈ $0 |
| 11 part two | $0 — deterministic scenario | $0 |
| 13 b, c, d | $0 — each fails before or at its first model call (verified on the new system) | $0 |
| 15 mortgage leg | not yet run on the new system | ≈ $0 if the bank is unchanged |

`demo/bin/baseline.sh restore` keeps every cache and the spend ledger, so a
retake never re-pays for content that has not changed. Check what a session
actually spent with `logs/model_usage.log` or
`uv run python scripts/model_cost_report.py --days 1`. Pipeline calls are logged
without a run id on the new system; `demo/bin/run-offering.sh` therefore totals
the calls made while its run was executing.

---

## After filming

```bash
./demo/bin/baseline.sh restore
export COMPOSE_FILE=docker-compose.yml
docker compose up -d
```

Confirm the shipped stack runs with no demo overlay before the technical review.
