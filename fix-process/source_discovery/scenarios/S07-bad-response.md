# S07: One item the model cannot answer: retry, split, keep the rest, next model

**What it checks.** On the real primary-mortgage page, a first model that always answers one
item with an invented id: its batch is asked again, split down to that item, the good batches
are saved as soon as they are checked, and the second model then answers the run (SD6).

**Plan items.** SD6, SD8.

**Steps.** A fake first model breaks on the fourth item of the second batch; a fake second
model accepts everything; both behind `FallbackSourceDiscoveryService`.

**Pass criteria.** The first model's good answers are saved; the run is answered by the
second model.

**Gemini.** None.

## Result: **PASS**

Raw result: [results/S07.json](results/S07.json). The first model got 11 calls (3 batches,
then retries and splits `batch_001` → `.b` → `.b.a` → `.b.a.a`), saved 13 good answers,
then raised `DiscoveryResponseError`; the second model answered all 20 items.

| Gemini calls | Gemini cost | Bank HTTP requests | Wall time |
|---|---|---|---|
| 0 | $0.00 | 0 | 0.9 s |
