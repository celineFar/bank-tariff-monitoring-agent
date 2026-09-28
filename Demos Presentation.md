

## OCR Fallback

This demo needs no database and no demo stack. It can run at any point; `present.py` runs it last. The live part takes about 4 minutes and costs nothing.

#### Before the audience arrives

1. **Check that the worker image has the OCR engine.** Run it once from `Presentation-demonstrations/OCR-fallback/`:

    ```
    ./run.sh
    ```

    The log should start by confirming the tesseract engine, then print `wrote output/...` for both samples. It runs offline in the main stack's `worker` image; if you changed `app/`, run `docker compose build worker` first.

2. **Open these tabs in order.** Use the Markdown preview (Ctrl+Shift+V) for the `.md` files.
    - `samples/mortgage-tariffs.pdf` in a PDF viewer
    - a terminal in `OCR-fallback/`, with a large font
    - `output/mortgage-tariffs.ocr.md`, next to the PDF
    - `output/comparison.md`

3. **Know what is simulated.** Only the Gemini call is replaced, by a stand-in that fails with the same `503 UNAVAILABLE` error a real outage produces. Everything after that is production code: the probe, the fallback decision, the rasterizer, tesseract and the confidence floor.

#### Live

**1. The scan (30 s).** Open `mortgage-tariffs.pdf`.

> "This is a scanned tariff sheet: the pages are images, so there's no text to select. There's a stamp over the right-hand column, and page 2 is sideways. The values are synthetic, but the layout is typical of what banks publish."

Try to select text to show there is none.

**2. Run it (about 30 s).**

```
./run.sh
```

> "I've made Gemini fail on purpose. Watch what the pipeline does."

Point at three things in the log, in this order:

| Log line | What to say |
|---|---|
| each page probed as `image_only`, 0 text characters | "The system checks the PDF first: no text layer, so it needs a transcriber." |
| `[simulated] gemini-3.1-flash-lite -> 503 UNAVAILABLE` | "Gemini is down. The pipeline doesn't stop." |
| `All gemini pdf models failed ... recovered N page(s) with ocr:tesseract:5.5.0` | "It falls back to local OCR, with the same code path it uses in production." |

**3. What OCR recovered (1–2 min).** Open `output/mortgage-tariffs.ocr.md` next to the PDF.

- **The Pages table:** page 1 was `transcribed` at a mean confidence of 76.7; page 2 is `low_confidence` at 38.1.
  > "The sideways page scored below the floor of 60, so the system emitted nothing for it instead of emitting nonsense."
- **The rate table on page 1:** find `11.596` and `2096`.
  > "The page says 11.5% and 20%. Tesseract read the percent sign as 96. That's the dangerous kind of error: a plausible-looking wrong number."
- **The stamp:** the right-hand column is partly missing where the stamp covers it.

**4. The comparison (1 min).** Open `output/comparison.md`.

> "The same scans through the real Gemini path: 28 of 28 tariff values correct, against 13 of 28 for OCR and 9 wrong numbers. Gemini costs about a third of a cent per document; OCR is free but much weaker."

**5. Why it's still safe. End here (30 s).**

> "That's why OCR is only the fallback, and why any value that cites an OCR-read block raises an `ocr_evidence` review. A misread 11.596 stops at a person; it never becomes a published rate. The fallback keeps the pipeline running during an outage, and it can't publish on its own."

#### Optional

- `OCR_MIN_CONFIDENCE=80 ./run.sh`: page 1 is now also held back, showing that the floor decides what OCR may emit. Run `./run.sh` again afterwards to restore the outputs.
- `output/loan-summary.ocr.md`: on a clean, simple layout OCR is almost word for word (11 of 13 values correct).

#### If something goes wrong

- **Docker or the image isn't available:** the outputs from the last run are saved in `output/`. Present from them, starting at step 3.
- **The tesseract check fails:** the image was built without the `ocr` extra. Rebuild it with `docker compose build worker`, or present from the saved outputs.

#### Likely questions

- **"Why not use OCR all the time? It's free."** On the mortgage sheet it got 46% of the values right, against 100% for Gemini, and it produces confident wrong numbers. It's a fallback that keeps the run going, not a replacement.
- **"Isn't the confidence score enough to catch bad pages?"** No. Mortgage page 1 scored 76.7, above the floor, and still had 9 wrong numbers. That's why the review rule exists as well as the floor.
- **"Is the outage real?"** The failure is simulated. It's the same error type a real Gemini outage raises, so the fallback is chosen by production code, not by the demo.


---
## Snapshot Change Detection and HITL


One caveat first: I haven't rehearsed the second half (answering the review in the chat) yet, and the script's check still expects a `large_rate_change` review. So as it stands the report ends with one FAIL. Until you choose option 1 or 2, plan to walk through it live and not rely on the final RESULT line.

##### Before the session

```
cd Presentation-demonstrations/demo-stack
python3 stack.py up
python3 stack.py status          # nothing else should be running
cd ../Change-detection-and-review
```

- Open two terminals: **A** runs the demo and **B** runs the chat.
- In the editor, open the republished page next to the original, or plan to show the edit table the script prints.
- Make sure the other session isn't running `Normal-extraction` against the same stack at that moment.

##### During the session (about 6–8 minutes)

###### 1. Give the setup honestly (30 s).

"Overdraft's seed URL points at a local copy of the bank's real page. I'll republish that copy with the nominal rates raised 4 points. Everything after the fetch is the real system: pipeline, Gemini, review queue, chat."

###### 2. Start the demo in terminal A: `python3 change_demo.py`

- **"Before":** the accepted tariff is 21%, 20% and 15–21%, and the review threshold is 3 points.
    
- **"The bank republishes":** exactly three lines changed (21→25, 20→24, 15–21 → 19–25). Everything else, including the PDFs, is byte-identical.
- **The run** (about 25 s): it goes `running`, then `awaiting_review`. It did not publish.

###### 3. "Caught" (the key moment).

- **The review:** `official_source_conflict` on `interest_rate`. Say: "The page now says 25%, but the bank's own leaflet still says 21%. The system won't choose between two official sources on its own, so it asks a person."
- **Point at the API line:** it still serves 21%, `pending newer review: True`, and 0 changes recorded. "Users are never shown an unverified number."

###### 4. The human decides, in terminal B.

```
python3 ../demo-stack/stack.py chat
You > Review the pending candidates
```

- The panel shows the candidates with their sources and quotes. Read them aloud: candidate 1 is the page at 25%; candidates 2 and 3 are the leaflets at 21%.
- Type the page candidate's number to accept 25%, or `reject_all` to keep 21%.
- Say: "The decision is recorded with the reviewer's name. The model never makes this decision; only a person in the CLI can."

###### 5. After the decision, back in terminal A.

The script has been waiting for your decision and continues on its own:

- **If you approved:** the candidate becomes `accepted`, a `tariff_changes` row shows `interest_rate` going from 21 to 25, and the API serves 25%.
- **If you rejected:** nothing is published and the API still serves 21%.

###### 6. End in the chat.

Ask `What changed in the overdraft tariff?` It answers with the change and its evidence from both versions.

##### Questions you'll probably get

- **"Why wasn't this flagged as a large rate change?"** Because the rate never resolved: the sources disagreed. Be ready to mention the gap I found. Once a reviewer picks 25% in the conflict review, the 4-point threshold isn't checked again (`monitoring_pipeline.py:419`). Only the person who picked the value saw it.
- **"Is the mirror cheating?"** Only the fetched page is staged. The HTTPS check, the host allowlist and every safety limit are unchanged.
- **"Can you run it again?"** Yes. Each run restores the `change-demo` checkpoint, so it always starts from 21%.

To show the rate rising past the 3-point threshold, choose option 1 (republish the leaflets too). The steps stay the same, except that step 3 becomes a `large_rate_change` review ("previous 21, candidate 25, change 4 points") and step 4's answer becomes `approve`. Should I build option 1, or adjust the script's checks so the conflict version reports PASS?


---

## Extraction Demonstration
This version adds a walk through the audit trail. The live part takes about 8 minutes.

#### Before the audience arrives

1. **Get the order right.** This demo goes first, because it publishes the snapshot the change-detection demo compares against. Your other session's change-demo setup (`d93c4414`) is currently the latest snapshot. Once the change-detection demo is ready, refresh this demo's output from `Normal-extraction/`:
    
    ```
    python3 extraction_demo.py --cold
    ```
    
    Check that it ends with `RESULT: PASS`. This is also your rehearsal: it confirms the bank's site and Gemini are answering today.
    
2. **Note the run id.** The report prints `pipeline-audit/run_<id>/overdraft/`, which is the folder you'll open during the audit walk-through.
    
3. **Open these tabs in order.** Use the VS Code Markdown preview (Ctrl+Shift+V) for the `.md` files, because the audit files use coloured HTML blocks.
    - the [Overdraft page](https://ameriabank.am/en/personal/loans/consumer-loans/overdraft), scrolled to "Terms and conditions"
    - a terminal in `Normal-extraction/`, with a large font
    - `output/overdraft/card.md`
    - from `pipeline-audit/run_<id>/overdraft/`: `2_pdf_link_selection.md`, `3_source_selection_decisions.md`, `4_extraction_evidence.md`, `4_review_queue.md`
        
4. **Have the fallback ready:** `python3 extraction_demo.py --no-run` re-reports the latest accepted run with nothing fetched live.
    

#### Live

**1. The source (30 s).** Show the bank page.

> "This is the official Overdraft page: 21% for Classic cards, 20% for Gold, and a footnote saying 15–21% for scoring-based loans. The full terms are in linked PDFs. The goal: get these values into a database, each with proof of where it came from."

**2. Start the run (about 90 s).**

```
python3 extraction_demo.py --cold
```

> "`--cold` clears the cached model output, so you see the whole job."

Narrate each stage as it appears:

|Stage|What to say|
|---|---|
|`acquisition`|"It fetches the page live, only from the bank's allowlisted domain."|
|`pdf_selection`|"It decides which linked PDFs belong to this product."|
|`normalization` (~40 s)|"Gemini transcribes the 3 PDFs, and everything becomes structured text."|
|`source_discovery`|"Each section is classified: pricing, eligibility, navigation, outdated."|
|`semantic_extraction`|"A stronger model extracts the tariff. Every value must cite a quote."|
|`publication`|"Deterministic code validates, compares with the last snapshot and publishes. No model is involved."|

**3. Cost and admission (30 s).**

> "12 calls, about 13 cents. A cheap model reads and classifies, and the stronger one is used only for extraction. `accepted`, 0 review signals: nothing needed a human."

If the report says the documents were **byte-identical** but lists field changes, say this before anyone asks:

> "Same pages, re-extracted: small wording differences. The system detects that the documents are identical and says so. In production the cache stops this."

**4. The business view (1–2 min).** Open `card.md`.

- The header: official source, the 3 PDFs, retrieval time, "no human review needed".
- The **Nominal interest rate** rows: 15–21%, 21%, 20%, with their conditions. Compare them with the page from step 1.
- Scroll to **Evidence** and read one entry aloud: _page → section → table row → "…AMD: 21%"_. Then show a fee citation that points to the _Loan service fees_ PDF, page 1.

**5. The audit trail, stage by stage (2 min).** Open the files in the run's folder in this order:

|File|What to show|
|---|---|
|`2_pdf_link_selection.md`|The decision table. Two PDFs are `current_product` and "Loan service fees" is `shared_terms`, each with the model's reason. Older versions were skipped by deterministic admission (`not asked`) and never sent to the model.|
|`3_source_selection_decisions.md`|Scroll a little. Green blocks are **SELECTED**, and navigation is **NOT SELECTED** by a `rule`, not by the model. "Only the green material reaches extraction."|
|`4_extraction_evidence.md`|Scroll to the rate table. The quotes Gemini cited are highlighted inside the original text, tagged `EX-…`. "An auditor can check every value right here."|
|`4_review_queue.md`|"Open review items: **0**. No human review is required." That's the definition of a normal run.|

> "Every run leaves this trail in its own folder, and earlier runs are kept beside it."

**6. The question (20 s).** Go back to the terminal and the "A question" table.

> "The question is answered from the stored database, not by re-reading the page. Every figure comes with its citation."

**7. The checks. End here (30 s).**

> "8 checks. The most important one: every quote, about 180 of them, is found word for word in the stored source text. An invented quote would fail it."

Point at `RESULT: PASS`.

#### If something goes wrong

- **"Another run is active" or "extra overlay":** another demo is using the stack. Wait, or add `--restore-worker`.
- **The site or Gemini fails:**
    > "Let me show this morning's run."  
    > Then run `--no-run`. Steps 3–7 work unchanged, because the audit folder is already there.
- **The run ends** `**awaiting_review**`**:**
    > "That's the safety net: it goes to a person instead of being published."  
    > Then move on to the HITL demo.

#### Likely questions

- **"What if the model invents a number?"** The quote must exist in the stored source text, validation blocks values without evidence, and the figure check confirms each number appears in the text it cites.
- **"Why does the 20% Gold rate cite the Classic line?"** When that happens, the citation points at the right table row but quotes a neighbouring line of it. The report flags these cases.
- **"Why Overdraft and not the standard consumer loan?"** `consumer_standard` goes to human review on every run, so it's used in the HITL demo.

Should I replace the README's shorter "Presenting it" section with this version?



---
## Safe Failure

Three real monitoring runs fail on purpose, each at a different point in the pipeline. The demo shows that a failure never touches the published tariff. The live part takes about 4 minutes and costs nothing: none of the failures reaches a paid model call.

#### Before the audience arrives

1. **Run it after the normal extraction demo.** It needs an accepted Overdraft tariff to protect, and after the normal extraction demo that's the real one (21%, 20%, 15–21%). Don't run it after the change demo: it would then be protecting the synthetic +4 point rates. `present.py` runs the demos in the right order.
2. **Make sure nothing else is using the stack.** The demo restarts the demo worker three times.
3. **Open these tabs in order.**
    - the three files in `Presentation-demonstrations/Controlled-failures/failures/`: `timeout.yml`, `model-failure.yml`, `size-limit.yml`
    - a terminal in `Controlled-failures/`, with a large font
    - `output/report.md` (Markdown preview), once the run has finished

#### Live

**1. What's artificial (30 s).** Open the three files in `failures/`. Each one is a few lines and changes one thing:

| File | The one change | What it simulates |
|---|---|---|
| `timeout.yml` | inside the worker, `ameriabank.am` resolves to 192.0.2.1, an address routed nowhere | the bank's site doesn't answer |
| `model-failure.yml` | source discovery uses the retired `gemini-2.5-flash-lite`, with no fallback | the model provider fails |
| `size-limit.yml` | download size cap lowered from 25 MB to 50 KB | a safety limit refuses the source |

> "Everything else is real: the API, the worker, the pipeline, the bank's site, and Gemini."

**2. Start it (about 2 minutes).**

```
python3 failure_demo.py
```

**3. "Before" (20 s).** The script fingerprints the six tables a run writes tariff data into, and asks the API for the current rates.

> "This is what's published now: 21%, 20%, 15–21%. Each table has a row count and a digest of every row. We'll compare them at the end."

**4. The three failures, as they come.**

| Failure | What to point at | What to say |
|---|---|---|
| Timeout (about 70 s) | `failed` at `acquisition`, code `source.timeout` | "The wait is the point. Each request has a timeout and there are at most 3 attempts, so the run gives up in about a minute. It doesn't hang." |
| Model failure (about 25 s) | `failed` at `pdf_selection`, recorded cause `ClientError:http_404_NOT_FOUND` | "That's Google's real answer for a retired model: the same failure this system hit on 22 September. It stops cleanly instead of guessing without a model." |
| Size limit (about 6 s) | `failed` at `acquisition`, code `source.size_rejected` | "A safety limit refused an oversized source before anything read it." |

For each one, read the **"Operator is told"** line aloud, for example:

> "Monitoring stopped because the bank's site did not respond in time. No tariff values were saved; the run can be retried."

Also point at **Snapshots written: 0** and **Changes written: 0**.

**5. "After", and the checks. End here (1 min).** The script restores the normal worker, then repeats the fingerprints.

> "Same row counts, same digests, all six tables byte-for-byte unchanged. The API serves the same snapshot with the same rates. Three failures, zero tariff values written, and not a cent spent on models."

Point at the checks table and `RESULT: PASS`. Then open `output/report.md` if you want to show the worker log lines behind each failure.

#### Optional

- `python3 failure_demo.py --failure size-limit` runs one failure in about 30 seconds, if time is short.

#### If something goes wrong

- **"No accepted overdraft snapshot":** run the normal extraction demo first, or `python3 ../demo-stack/stack.py baseline`.
- **"A run is in progress":** another demo is using the stack. Wait for it to end.
- **A failure ends with a different code than expected**, for example the bank's site is down for real: the script marks that check FAIL. The table-and-API safety checks still show the point. Say so, and show the saved `output/report.md` from the last full run.
- **It was interrupted:** the script restores the normal worker even after an error. If in doubt, `python3 ../present.py --check` reports any leftover overlay, and `present.py` clears it.

#### Likely questions

- **"What happens to users during a failure?"** They keep getting the last accepted tariff, with its date and freshness. A failed run never replaces or blanks it.
- **"Does it retry forever?"** No. Retries are bounded (3 attempts, a timeout per request, a capped delay), and the run ends `failed` with a code an operator can act on.
- **"Why would a model be retired mid-run?"** It happened to this system on 22 September. Since then, the configured models have fallbacks. This demo removes the fallback on purpose, to show what happens when every model fails.
- **"Are these the only failures handled?"** They're three of about 20 mapped failure codes. The same mapping covers others, such as a page not found (`source.not_found`), an unexpected content type (`source.mime_rejected`), and a redirect or URL outside the allowed hosts (`source.redirect_rejected`, `source.url_rejected`). Each stops the run with its own code and writes nothing.