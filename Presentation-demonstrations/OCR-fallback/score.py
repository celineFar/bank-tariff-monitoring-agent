"""Score the OCR and Gemini transcriptions against each sample's ground truth.

Reads `samples/<name>.truth.json` (written by make_samples.py) and whatever
`output/<name>.<engine>.md` exists, then writes `output/comparison.md`.

What is measured, per sample and engine:

- Tariff values: for each tariff row in the truth, find the output line on the
  same page whose text best matches the row's label (fuzzy, so a misread letter
  does not hide a correct number), then compare the numbers after the label,
  in column order. `12.0` and `12` are equal; `1,000` and `1.000` are not.
- Wrong numbers: numbers in the output that are not on the page. For tariffs
  this is the dangerous error: a missing value is visible, a misread one is not.
- Number recall: the page's numbers found anywhere in the output.
- Word F1: overlap of the word multisets, ignoring order and layout.

Pure standard library: runs through ./run.sh or with any python3.
"""

from __future__ import annotations

import json
import re
import unicodedata
from collections import Counter
from decimal import Decimal, InvalidOperation
from difflib import SequenceMatcher
from pathlib import Path

HERE = Path(__file__).resolve().parent
SAMPLES = HERE / "samples"
OUTPUT = HERE / "output"
ENGINES = ("ocr", "gemini")
# A misread letter or two scores above 0.8; a different label sharing a word
# ("Տրամադրման վճար" for "Գնահատման վճար") scores around 0.7.
LABEL_THRESHOLD = 0.8

_PAGE = re.compile(r"<!-- page:(\d+) -->\n(.*?)\n<!-- /page -->", re.DOTALL)
_NUMBER = re.compile(r"(?<![\w.,])\d+(?:[.,]\d+)*")
_WORD = re.compile(r"\w[\w.,%-]*")
_DATE = re.compile(r"\d{2}\.\d{2}\.\d{4}")
_THOUSANDS = re.compile(r"\d{1,3}(?:,\d{3})+(?:\.\d+)?")


def normalize(text: str) -> str:
    # NFKC: the ligature "և" and its spelled-out "եւ" are the same word.
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"<[^>]+>|\*\*|[|`#>*]", " ", text)
    # "Column 5" is the pipeline's placeholder for a header the model left out.
    text = re.sub(r"\bcolumn \d+\b", " ", text.casefold())
    return " ".join(text.split())


def page_lines(markdown: str) -> dict[int, list[str]]:
    """The transcribed lines of each page, markdown syntax removed."""
    pages: dict[int, list[str]] = {}
    for number, body in _PAGE.findall(markdown):
        lines = []
        for raw in body.splitlines():
            if raw.strip().startswith("```") or re.fullmatch(r"\|(-+\|)+", raw.strip()):
                continue
            if line := normalize(raw):
                lines.append(line)
        pages[int(number)] = lines
    return pages


def number_key(token: str) -> str:
    """A number's value, so 12.0 equals 12 but 1.000 does not equal 1,000."""
    if _DATE.fullmatch(token):
        return token
    if _THOUSANDS.fullmatch(token):
        token = token.replace(",", "")
    try:
        return format(Decimal(token).normalize(), "f")
    except InvalidOperation:
        return token


def numbers(text: str) -> list[str]:
    return [number_key(token) for token in _NUMBER.findall(text)]


def words(text: str) -> Counter[str]:
    return Counter(token.rstrip(".,:") for token in _WORD.findall(normalize(text)))


def locate(label: str, lines: list[str]) -> tuple[float, str]:
    """The best fuzzy match of `label` in `lines`, and the text after it."""
    target = normalize(label)
    size = len(target)
    best = (0.0, "")
    for line in lines:
        for start in range(max(1, len(line) - size + 1)):
            ratio = SequenceMatcher(
                None, target, line[start : start + size], autojunk=False
            ).ratio()
            if ratio > best[0]:
                best = (ratio, line[start + size :])
    return best


def score(truth: dict, markdown: str) -> dict[str, object]:
    output = page_lines(markdown)
    truth_text = "\n".join(line for page in truth["pages"] for line in page["lines"])
    output_text = "\n".join(line for lines in output.values() for line in lines)

    rows = []
    for row in truth["rows"]:
        expected = [number_key(value) for value in row["values"]]
        ratio, after = locate(row["label"], output.get(row["page"], []))
        found = numbers(after) if ratio >= LABEL_THRESHOLD else []
        correct = sum(a == b for a, b in zip(expected, found, strict=False))
        rows.append(
            {
                "page": row["page"],
                "label": row["label"],
                "expected": expected,
                "found": found[: len(expected)] if ratio >= LABEL_THRESHOLD else None,
                "correct": correct,
            }
        )

    truth_numbers = Counter(numbers(truth_text))
    output_numbers = Counter(numbers(output_text))
    truth_words, output_words = words(truth_text), words(output_text)
    overlap = sum((truth_words & output_words).values())
    precision = overlap / max(1, sum(output_words.values()))
    recall = overlap / max(1, sum(truth_words.values()))
    return {
        "pages_with_text": len(output),
        "pages": len(truth["pages"]),
        "rows": rows,
        "values_correct": sum(row["correct"] for row in rows),
        "values_total": sum(len(row["expected"]) for row in rows),
        "number_recall": sum((truth_numbers & output_numbers).values())
        / max(1, sum(truth_numbers.values())),
        "wrong_numbers": sorted((output_numbers - truth_numbers).elements()),
        "word_f1": 2 * precision * recall / (precision + recall)
        if precision + recall
        else 0.0,
    }


def percent(part: float, whole: float) -> str:
    return f"{100 * part / whole:.0f}%" if whole else "-"


def wrong_numbers(result: dict) -> str:
    wrong = result["wrong_numbers"]
    listed = ": " + ", ".join(f"`{n}`" for n in wrong[:8]) if wrong else ""
    return f"**{len(wrong)}**{listed}"


# One line of the summary table: its title, and how to render one engine's cell
# from that engine's score and run record.
METRICS = (
    ("Pages with text", lambda s, r: f"{s['pages_with_text']} of {s['pages']}"),
    (
        "Tariff values correct",
        lambda s, r: (
            f"**{s['values_correct']}/{s['values_total']}** "
            f"({percent(s['values_correct'], s['values_total'])})"
        ),
    ),
    ("Wrong numbers (not on the page)", lambda s, r: wrong_numbers(s)),
    ("Number recall", lambda s, r: f"{100 * s['number_recall']:.0f}%"),
    ("Word F1", lambda s, r: f"{s['word_f1']:.2f}"),
    ("Time", lambda s, r: f"{r['elapsed_seconds']:.1f}s"),
    (
        "Cost",
        lambda s, r: f"${r['cost_usd']:.5f}" if r["cost_usd"] is not None else "$0",
    ),
)


def render(results: dict[str, dict[str, dict]], runs: dict) -> str:
    lines = [
        "# OCR fallback vs Gemini: transcription quality",
        "",
        "Generated by `score.py` from the ground truth in `samples/*.truth.json`. "
        "See the docstring of `score.py` for how each metric is computed.",
    ]
    for sample, engines in results.items():
        lines += ["", f"## {sample}", ""]
        names = [engine for engine in ENGINES if engine in engines]
        header = ["Metric"] + [
            f"{engine.upper()} (`{runs[sample][engine]['produced_by']}`)"
            for engine in names
        ]
        lines += ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
        for title, render_one in METRICS:
            cells = [render_one(engines[e], runs[sample][e]) for e in names]
            lines.append(f"| {title} | " + " | ".join(cells) + " |")

        lines += ["", "<details><summary>Row by row</summary>", ""]
        row_header = ["Page", "Label", "Expected"] + [e.upper() for e in names]
        lines += ["| " + " | ".join(row_header) + " |", "|" + "---|" * len(row_header)]
        first = engines[names[0]]["rows"]
        for index, row in enumerate(first):
            cells = [str(row["page"]), row["label"], ", ".join(row["expected"])]
            for engine in names:
                found = engines[engine]["rows"][index]
                if found["found"] is None:
                    cells.append("label not found")
                    continue
                mark = "✅" if found["correct"] == len(found["expected"]) else "❌"
                cells.append(f"{mark} {', '.join(found['found']) or 'no number'}")
            lines.append("| " + " | ".join(cells) + " |")
        lines += ["", "</details>"]
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    results: dict[str, dict[str, dict]] = {}
    runs: dict[str, dict[str, dict]] = {}
    for truth_path in sorted(SAMPLES.glob("*.truth.json")):
        sample = truth_path.name.removesuffix(".truth.json")
        truth = json.loads(truth_path.read_text("utf-8"))
        for engine in ENGINES:
            markdown = OUTPUT / f"{sample}.{engine}.md"
            if not markdown.exists():
                continue
            results.setdefault(sample, {})[engine] = score(
                truth, markdown.read_text("utf-8")
            )
            runs.setdefault(sample, {})[engine] = json.loads(
                markdown.with_suffix(".json").read_text("utf-8")
            )

    for sample, engines in results.items():
        for engine, result in engines.items():
            print(
                f"{sample:<18} {engine:<7} values {result['values_correct']:>2}/"
                f"{result['values_total']:<2}  wrong numbers "
                f"{len(result['wrong_numbers']):>2}  number recall "
                f"{100 * result['number_recall']:>3.0f}%  word F1 "
                f"{result['word_f1']:.2f}"
            )
    target = OUTPUT / "comparison.md"
    target.write_text(render(results, runs), encoding="utf-8")
    print(f"\nWrote output/{target.name}")


if __name__ == "__main__":
    main()
