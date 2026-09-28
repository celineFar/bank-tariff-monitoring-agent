# Presentation demonstrations

| Folder | Deliverable | Needs the demo stack | Live bank site | Cost |
|---|---|---|---|---|
| [Normal-extraction](Normal-extraction/) | 9: normal tariff extraction | yes | yes | ~$0.13 |
| [Controlled-failures](Controlled-failures/) | 13: controlled failures | yes | yes | $0 |
| [Change-detection-and-review](Change-detection-and-review/) | 10 and 12: change detection, human review | yes | no (local mirror) | ~$0.08 |
| [OCR-fallback](OCR-fallback/) | 11: OCR fallback | no (own container, no database) | no | $0 |

## Run them all

```bash
cd Presentation-demonstrations
python3 present.py            # setup, then each demonstration, asking before each
python3 present.py --check    # what setup would do; changes nothing
python3 present.py --from change
```

`present.py` sets everything up on its own. It builds the images if they are
missing, starts the demo stack, and clears anything an interrupted demonstration
left behind: a leftover worker overlay, the mirror, or a pending review. It runs
the change demonstration's one-time setup if that is missing, and it restores
the `bank-baseline` checkpoint. Before each demonstration it asks: Enter to
start, `s` to skip, `q` to stop. The change demonstration also needs your review
decision: the chat opens in the same terminal and tells you what to type. Run it
from an interactive terminal.

## Why the order matters

The three stack demonstrations share one database and one worker:

1. **Normal extraction** publishes the bank's real Overdraft tariff (21%, 20%,
   15–21%).
2. **Controlled failures** needs an accepted tariff to protect, and checks that
   three failed runs leave it byte-for-byte unchanged. After 1, that is the real
   one.
3. **Change detection and review** starts by restoring its own checkpoint, which
   erases what 1 and 2 wrote to the database; their files on disk stay. If you
   approve the change, the demo database then serves a **synthetic** rate 4
   points higher (25%, 24%, 19–25%). So it goes last among the three:
   - A normal extraction after it would compare the live 21% with the synthetic
     25%, see a 4-point drop, and stop for review, which fails that demo.
   - The failure demo after it would be protecting made-up rates.
4. **OCR fallback** uses no database and can run at any point.

`present.py` restores `bank-baseline` (the real-bank state) before step 1 every
time, so a second rehearsal starts clean.

## Caveats

- **One demonstration at a time, from one place.** The stack is shared. A second
  terminal or another session running a demo, or `present.py`, at the same time
  will collide: runs get refused, the worker is restarted mid-run, or
  checkpoints are restored underneath it. `present.py`'s setup restores a
  checkpoint, so don't start it while someone else is working on the stack.
- **The images come from the main stack.** After changing `app/`, run
  `docker compose build api worker`, or the demonstrations run the old code.
- **Live dependencies.** Normal extraction and the failures reach
  ameriabank.am, and normal extraction and the change demo call Gemini. If
  either is down on the day, `python3 Normal-extraction/extraction_demo.py
  --no-run` re-reports the last run, and the other reports in `output/` are
  there to show.
- **The real site can change.** If the bank changes the Overdraft rates, normal
  extraction will rightly detect the change against `bank-baseline`, and it may
  stop for review. Refresh the checkpoint once the new rate is accepted:
  `python3 demo-stack/stack.py checkpoint save bank-baseline`.
- **`--cold` clears model caches** for Overdraft, including the PDF
  transcriptions the change demo would otherwise reuse. The change demo may then
  take about 40 s longer and cost about 2 cents more.
- **The same pages give slightly different extractions.** Run over the same text
  twice, Gemini returns a few wording and ordering differences, which are
  recorded as field changes. Normal extraction's report says so when the source
  documents are byte-identical.
- **Setup from scratch.** `python3 demo-stack/stack.py destroy` removes the
  database and the mirror's trust volumes. The next `present.py` recreates
  everything; the change setup then costs one extra run of about $0.13.
