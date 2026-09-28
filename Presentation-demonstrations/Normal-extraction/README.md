# Normal tariff extraction

One real monitoring run of Overdraft, from the bank's website to a published
tariff. The run fetches the product page, downloads and reads the PDFs, has
Gemini extract the tariff, and passes it through deterministic validation into
the database. The script follows the run stage by stage, then renders what was
published the way a business user would read it, asks the API a question about
it, and checks that every value carries evidence that can be found again.

"Normal" means the path with no human in it: the run ends `succeeded` and the
snapshot is accepted with no review signal.

```
Normal-extraction/
├── extraction_demo.py        the demonstration (standard library only)
├── output/<offering>/
│   ├── card.md               the business view: values, conditions, quoted evidence
│   └── report.md             the run, its cost, admission, the question, the checks
└── pipeline-audit/           the worker's audit files, laid out like artifacts/pipeline-audit
    └── run_<run_id>/<offering>/
        ├── 0_run_context.md
        ├── 2_*.md            normalization: the normalized page, its diff, the PDF link choice
        ├── 3_*.md            source discovery: decisions, diff, selected sources
        └── 4_*.md            extraction: evidence overlay, pre-validation, review queue
```

## Run

The demo runs against the persistent demonstration stack (`../demo-stack`).
Start it once:

```bash
cd Presentation-demonstrations/demo-stack
python3 stack.py up
```

Then:

```bash
cd Presentation-demonstrations/Normal-extraction
python3 extraction_demo.py --cold      # live run, every model call made: ~90 s, ~$0.13
python3 extraction_demo.py             # live run; reuses cached model output if the
                                       # sources are unchanged: ~30 s, $0
python3 extraction_demo.py --no-run    # report the latest accepted snapshot again
python3 extraction_demo.py --offering credit_line --cold
```

Exit code 0 means every check passed. Each invocation rewrites
`output/<offering>/`; `--no-run` reports the latest accepted run, whoever
started it. `pipeline-audit/` only grows: each reported run adds its own
`run_<run_id>/` directory.

The script refuses to start a run while another run is active on the demo stack,
or while the demo worker runs with another demonstration's overlay (for example
one from `Controlled-failures`). `--restore-worker` restarts the normal worker
first. A run of this demo writes a new accepted snapshot, so don't run it while
`failure_demo.py` is between its before and after fingerprints.

This demo also leaves the accepted snapshot that `Controlled-failures` needs, so
it can replace `stack.py baseline` as the setup step.

## What is real, and the one intervention

Nothing is simulated. The API, the worker, the pipeline, the bank's site, the
PDFs and Gemini are all real, and so is the database the answer comes from.

**The model caches.** Gemini's output is cached by content, as it is in
production. That covers the PDF link choice, the PDF transcriptions, source
classification and the extraction batches. A run over byte-identical sources
therefore reuses the cached output and calls no model at all. The report says so
("Reused from cache"). `--cold` first deletes this offering's rows from those
four cache tables in the demo database, so the run does the whole job live. The
tables are pure caches that nothing references. Extraction batches are keyed by
product rather than offering, so the product's other offerings lose theirs too.

## What the script does

1. **Run.** It checks that the stack is free (`--cold` also clears the caches),
   submits `POST /api/v1/runs`, and polls the run and its offering stage until
   the run ends.
2. **What the run read and what it cost.** Sources discovered, PDFs read, the
   retrieval time, and every Gemini call by stage: model, live calls, cache
   hits, tokens and cost, from `model_call_usage`.
3. **Admission.** The snapshot's status, validated fields and review signals.
   It is also compared with the previous accepted snapshot; see *Extraction
   variance* below.
4. **The business view.** It builds `card.md` from the typed facts in the
   database, in the layout of the assignment's example: the official source, the
   documents read, the retrieval time and currency, then each rate, amount,
   term, fee and age limit with its conditions. Each value is followed by
   evidence in the form *document → page → section → quote*. A citation that
   quotes the value's own figure is listed first.
5. **A question.** It asks `POST /api/v1/tariffs/query` "What is the nominal
   interest rate of the Overdraft?". The answer comes from the stored facts,
   each with its citations.
6. **Audit files.** It copies the worker's stage-numbered audit files for this
   run into `pipeline-audit/run_<run_id>/<offering>/`, the same layout the worker
   writes to `artifacts/pipeline-audit`. Each run gets its own directory, so earlier
   runs stay available for comparison. In `4_extraction_evidence.md`, every cited quote is
   highlighted inside its source document.
7. **Checks.**

| Check | Passes when |
|---|---|
| the run succeeded | run and offering both `succeeded`, offering at stage `published` |
| published without human review | snapshot `accepted`, 0 review signals, 0 reviews |
| the API serves this snapshot as current | `GET /tariffs/current` returns this snapshot id, freshness `fresh` |
| every value has evidence | no `found` fact without a citation |
| every citation has a quote and a locator | quote not empty; a PDF page, or a CSS selector or XPath on the web page |
| every quote is in the source text it cites | the quote appears, whitespace- and case-normalized, in the text of the evidence item it cites, as stored with the snapshot |
| every figure appears in the source text it cites | each numeric value appears as a number in at least one cited evidence item ("15 million" counts as 15,000,000); a zero may be stated in words ("N/A", "no extra fees") and is listed separately |
| the question is answered from this snapshot | status `answered`, every returned fact from this snapshot and cited |

## Results

The last `--cold` run of Overdraft made by this script (run `c0b8cacd`,
2026-09-28 07:25 UTC; its audit files are in `pipeline-audit/run_c0b8cacd-…/`):

| | |
|---|---|
| Run | `succeeded` in 85 s: acquisition 21 s, PDF selection 2 s, normalization with 3 PDF transcriptions 40 s, source discovery 5 s, extraction 13 s, publication 2 s |
| Read | the product page and 3 PDFs (Informational summary, Lending terms, Loan service fees), 11 sources |
| Gemini | 12 live calls: `gemini-3.1-flash-lite` for PDF link choice, transcription and classification, `gemini-3.7-flash` for extraction; **$0.126** |
| Published | `accepted`, 21 fields validated, 0 review signals; 64 found facts |
| Evidence | 181 citations, all with quote and locator, all 181 quotes found verbatim; 33 of 33 figures in their cited text |
| Question | answered from the new snapshot: 15–21% (scoring-based), 21% (Classic cards), 20% (Gold and higher cards), all cited |
| Checks | 8 of 8 PASS |

An earlier `--cold` run gave the same result (95 s, $0.127, 172 of 172 quotes,
8 of 8 PASS, with 2 zeros stated in words).

### Assessment

**The normal path works end to end, with evidence throughout.** A live run takes
about a minute and a half and costs about 13 cents. Every value in the
published tariff cites text that the script finds verbatim in what the pipeline
stored, with a locator back to the web page element or PDF page. The answer to
the question comes from those stored facts, not from a new model call over the
page.

**Citations point at the right item, not always at the right line.** The figure
check is done per evidence item, which may be a whole table row or passage. The
quote itself can be a neighbouring line. In the first cached run, the Gold-card
rates (20%, 21.92%) cited the Classic-card line of the same table row, and the
report lists such cases under a note. The value is right and it is in the
cited item, but the words quoted don't state it.

**Zeros are often written as words.** "There are no extra fees when applying
online" and "Early repayment fee: N/A" are stored as 0 AMD. The figure check
accepts a zero stated in a small, explicit vocabulary and names each one in the
report, so a reviewer can judge the reading. Whether "N/A" means *free* or *not
offered* is a real ambiguity in the source.

**Extraction variance.** Four Overdraft snapshots were taken from byte-identical
documents: the first run, a cached rerun and two `--cold` reruns. The cached
rerun reproduced the first exactly, with 0 field changes. Each `--cold` rerun
extracted the same text again and recorded 11 and then 10 field changes. The
headline rates did not move. The changes were a rate type (`fixed` became `unknown`),
capitalization and ordering ("Cash withdrawal" / "cash withdrawal"), reworded
conditions and descriptions, and `variants` going from `[]` to `not_stated`.
The report detects that the documents were identical and says so.

Two consequences follow. In production, the content-keyed cache is what keeps
unchanged pages from producing spurious changes: the model is asked again only
when the sources change, or when the prompt, schema or model version does. And
when a source does change, a change report can mix real changes with this kind
of noise. That is a known limit for the change-detection deliverable.

**Choice of offering.** Overdraft, `credit_line` and `online_consumer_finance`
each went through two earlier runs without a review. `consumer_standard` raised
one review item in each of its runs, so it belongs in the HITL demonstration,
not here.

## Presenting it

1. Open the Overdraft page on ameriabank.am and point to the rate table: 21%
   for Classic cards and 20% for Gold, with a note giving 15–21% for scoring-based
   loans.
2. Run `python3 extraction_demo.py --cold`. Narrate the stages as they appear.
   The long one is normalization, where Gemini reads the three PDFs.
3. The cost table: 12 calls, about 13 cents, split between a cheap model for
   reading and classifying and a stronger one for extraction.
4. Open `output/overdraft/card.md`: the business view. Follow one evidence line
   to the page, and one to a PDF page.
5. Open `pipeline-audit/run_<run_id>/overdraft/4_extraction_evidence.md` (the
   run id is in the report): the same quotes,
   highlighted inside the source.
6. End on the checks: 8 PASS, no human review, every quote found verbatim.
7. Optional: run it again without `--cold`. It takes 30 seconds and costs $0,
   because nothing changed and the cached output is reused.
