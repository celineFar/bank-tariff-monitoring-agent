#!/usr/bin/env python3
"""Normal tariff extraction: one real monitoring run, published with evidence.

Runs against the persistent demonstration stack (../demo-stack). A monitoring
run is submitted through the API and followed stage by stage. The script then
reads back what was published, renders it the way a business user would read
it, and checks that every value carries evidence that can be found again.

    python3 extraction_demo.py --cold                   # a live run of Overdraft,
                                                        # every model call made
    python3 extraction_demo.py                          # the same, reusing cached
                                                        # model output when the
                                                        # sources are unchanged
    python3 extraction_demo.py --offering credit_line   # another offering
    python3 extraction_demo.py --no-run                 # report the latest accepted
                                                        # snapshot; no new run

Nothing is simulated: the bank's site is fetched and the PDFs are downloaded on
every run. Gemini's output is cached by content, exactly as in production, so
a run over byte-identical sources reuses it and calls no model. `--cold` first
deletes this offering's cached model output from the demo database, so the run
reads the PDFs and extracts the tariff live: about two minutes and $0.13 for
Overdraft. `--no-run` spends only the question at the end (under a cent).

Writes output/<offering>/card.md (the business view), output/<offering>/report.md
(the run, its checks and the question), and output/<offering>/audit/ (the
pipeline audit files the worker wrote for this run).

Standard library only. Prerequisite, once: ../demo-stack/stack.py up.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import time
from collections import defaultdict
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "demo-stack"))

import stack  # noqa: E402

OUTPUT = HERE / "output"
AUDIT_ROOT = "/code/artifacts/pipeline-audit"
# Armenia keeps UTC+4 all year.
YEREVAN = timezone(timedelta(hours=4), "Yerevan")
ACTIVE_RUN_STATES = ("queued", "running", "awaiting_review")
# The rows of the business card, in the order the assignment's example shows
# them: field-path prefixes of the typed facts, and a label. Of several
# prefixes, the first with values is shown; a revolving product projects its
# limit as both `amount` and `revolving.credit_limit`.
CARD_ROWS = (
    (("rate.nominal",), "Nominal interest rate"),
    (("rate.effective",), "Effective rate (APR)"),
    (("amount", "revolving.credit_limit"), "Amount"),
    (("term",), "Term"),
    (("fee",), "Fees"),
    (("eligibility.age",), "Borrower age"),
)
# Rows whose values are facets of one statement, shown on one line.
JOINED_ROWS = {"Term"}
CITATIONS_PER_ROW = 2
NUMBER = re.compile(r"(\d[\d,]*(?:\.\d+)?)\s*(million|mln)?", re.IGNORECASE)
# How a source says a fee is zero without writing the digit.
ZERO_IN_WORDS = re.compile(
    r"\b(free of charge|free|n/a|not applicable|none|not charged"
    r"|no (extra |additional )?(fees?|charges?|commission))\b",
    re.IGNORECASE,
)
QUOTE_WIDTH = 160
CONDITION_WIDTH = 90


class Report:
    """Prints as it goes and keeps the same lines for report.md."""

    def __init__(self) -> None:
        self.lines: list[str] = []

    def heading(self, text: str) -> None:
        print(f"\n==> {text}", flush=True)
        self.lines += ["", f"## {text}", ""]

    def say(self, text: str = "") -> None:
        print(f"    {text}" if text else "", flush=True)
        self.lines.append(text)

    def table(self, header: list[str], rows: list[list[str]]) -> None:
        widths = [
            max(len(str(cell)) for cell in column)
            for column in zip(header, *rows, strict=True)
        ]
        for row in (header, *rows):
            print(
                "    "
                + "  ".join(str(c).ljust(w) for c, w in zip(row, widths, strict=True))
            )
        self.lines += [
            "| " + " | ".join(header) + " |",
            "|" + "---|" * len(header),
            *("| " + " | ".join(str(c) for c in row) + " |" for row in rows),
            "",
        ]


# --------------------------------------------------------------------------
# the stack must be free before a live run


def worker_overlays() -> list[str]:
    """Compose files the demo worker runs with, beyond the normal two."""
    container = stack.compose("ps", "-q", "worker", capture=True).stdout.strip()
    if not container:
        raise stack.StackError("the demo worker is not running: stack.py up")
    label = subprocess.run(
        [
            "docker",
            "inspect",
            container,
            "--format",
            '{{index .Config.Labels "com.docker.compose.project.config_files"}}',
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    normal = {str(stack.REPO / "docker-compose.yml"), str(stack.OVERLAY)}
    return [path for path in label.split(",") if path and path not in normal]


def ensure_stack_is_free(restore_worker: bool) -> None:
    """Refuse to start while another demonstration is using the stack."""
    active = stack.sql(
        "SELECT id, status FROM monitoring_runs WHERE status IN "
        f"({', '.join(repr(state) for state in ACTIVE_RUN_STATES)})"
    )
    if active:
        runs = ", ".join(f"{row['id'][:8]} ({row['status']})" for row in active)
        raise stack.StackError(
            f"another run is active on the demo stack: {runs}. Wait for it to end."
        )
    overlays = worker_overlays()
    if not overlays:
        return
    names = ", ".join(Path(path).name for path in overlays)
    if not restore_worker:
        raise stack.StackError(
            f"the demo worker runs with an extra overlay ({names}); another "
            "demonstration is probably using the stack. Wait for it, or pass "
            "--restore-worker to restart the normal worker first."
        )
    print(f"    Restarting the normal worker (it had {names}) ...", flush=True)
    stack.restart_worker()


# --------------------------------------------------------------------------
# the run


def execute(statement: str) -> str:
    """Run a write statement against the demo database."""
    return stack.compose(
        "exec",
        "-T",
        "db",
        "psql",
        "-U",
        "tariff",
        "-d",
        "tariff_monitor",
        "-v",
        "ON_ERROR_STOP=1",
        "-qAtc",
        statement,
        capture=True,
    ).stdout


def clear_model_caches(product: str, offering: str, report: Report) -> None:
    """Delete the cached model output a run of this offering would reuse.

    These tables are caches keyed by content fingerprints; nothing references
    them. Extraction batches are keyed by product, not offering, so the other
    offerings of the product lose theirs too (they are only re-bought).
    """
    counts = stack.sql(
        f"""SELECT
              (SELECT count(*) FROM pdf_link_selections
                 WHERE offering_id = '{offering}') AS pdf_link_selections,
              (SELECT count(*) FROM pdf_extraction_cache
                 WHERE document_sha256 IN (SELECT content_sha256 FROM knowledge_documents
                                           WHERE offering_id = '{offering}'))
                 AS pdf_extraction_cache,
              (SELECT count(*) FROM source_discovery_assessments
                 WHERE offering_id = '{offering}') AS source_discovery_assessments,
              (SELECT count(*) FROM semantic_extraction_batches
                 WHERE product = '{product}') AS semantic_extraction_batches"""
    )[0]
    execute(
        f"""BEGIN;
            DELETE FROM pdf_link_selections WHERE offering_id = '{offering}';
            DELETE FROM pdf_extraction_cache
              WHERE document_sha256 IN (SELECT content_sha256 FROM knowledge_documents
                                        WHERE offering_id = '{offering}');
            DELETE FROM source_discovery_assessments WHERE offering_id = '{offering}';
            DELETE FROM semantic_extraction_batches WHERE product = '{product}';
            COMMIT;"""
    )
    report.say(
        "Cleared the cached model output (`--cold`): "
        + ", ".join(f"{count} `{table}`" for table, count in counts.items())
        + " rows."
    )


def product_for(offering: str) -> str:
    return "mortgage" if offering.startswith("mortgage") else "consumer_loan"


def live_run(product: str, offering: str, report: Report) -> tuple[str, float]:
    """Submit one run and follow it stage by stage until it ends."""
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
    run = stack.submit_run(product, offering, f"extraction-demo-{offering}-{stamp}")
    report.say(f"Submitted run `{run['id'][:8]}` through `POST /api/v1/runs`.")
    started = time.monotonic()
    deadline = started + 1200
    progress: list[list[str]] = []
    last = None
    while time.monotonic() < deadline:
        run = stack.api("GET", f"/runs/{run['id']}")
        execution = stack.sql(
            f"""SELECT current_stage FROM offering_executions
                WHERE run_id = '{run["id"]}' AND offering_id = '{offering}'"""
        )
        stage = execution[0]["current_stage"] if execution else None
        if (run["status"], stage) != last:
            elapsed = f"{time.monotonic() - started:.0f}s"
            print(f"    {elapsed:>6}  run {run['status']:<16} stage {stage or '-'}")
            progress.append([elapsed, f"`{run['status']}`", f"`{stage or '-'}`"])
            last = (run["status"], stage)
        if run["status"] in {
            "succeeded",
            "partial_success",
            "failed",
            "awaiting_review",
        }:
            break
        time.sleep(2)
    else:
        raise stack.StackError(f"run {run['id']} did not finish within 1200s")
    report.lines += ["", "Progress, as polled:", ""]
    report.lines += [
        "| Elapsed | Run | Stage |",
        "|---|---|---|",
        *(f"| {' | '.join(row)} |" for row in progress),
        "",
    ]
    return run["id"], time.monotonic() - started


def latest_accepted_run(offering: str) -> str:
    rows = stack.sql(
        f"""SELECT run_id FROM tariff_snapshots
            WHERE offering_id = '{offering}' AND status = 'accepted'
            ORDER BY accepted_at DESC LIMIT 1"""
    )
    if not rows:
        raise stack.StackError(
            f"no accepted {offering} snapshot in the demo database; run without --no-run"
        )
    return rows[0]["run_id"]


# --------------------------------------------------------------------------
# what the run published


def load_published(run_id: str, offering: str) -> dict:
    run = stack.api("GET", f"/runs/{run_id}")
    execution = stack.sql(
        f"""SELECT status, current_stage, source_count, document_count,
                   review_count, warning_count, failure_code, failure_detail,
                   started_at, completed_at, source_retrieved_at, acquisition_reused
            FROM offering_executions
            WHERE run_id = '{run_id}' AND offering_id = '{offering}'"""
    )
    snapshot = stack.sql(
        f"""SELECT id, status, accepted_at, validation, previous_accepted_snapshot_id
            FROM tariff_snapshots
            WHERE run_id = '{run_id}' AND offering_id = '{offering}'
            ORDER BY created_at DESC LIMIT 1"""
    )
    published = {
        "run": run,
        "execution": execution[0] if execution else {},
        "snapshot": snapshot[0] if snapshot else None,
        "facts": [],
        "sources": {},
        "changes": [],
    }
    usage = stack.sql(
        f"""SELECT stage, string_agg(DISTINCT model_id, ', ') AS models,
                   count(*) FILTER (WHERE outcome = 'succeeded') AS calls,
                   count(*) FILTER (WHERE outcome = 'cache_hit') AS cached,
                   count(*) FILTER (WHERE outcome NOT IN ('succeeded', 'cache_hit'))
                     AS failed,
                   coalesce(sum(input_tokens), 0) AS input_tokens,
                   coalesce(sum(output_tokens), 0) AS output_tokens,
                   coalesce(sum(estimated_cost_usd), 0) AS usd
            FROM model_call_usage WHERE run_id = '{run_id}'
            GROUP BY stage ORDER BY min(called_at)"""
    )
    published["usage"] = usage
    if published["snapshot"] is None:
        return published
    snapshot_id = published["snapshot"]["id"]
    published["facts"] = stack.sql(
        f"""SELECT f.field_path, f.variant_key, f.status, f.value_json,
                   f.number_value, f.unit, f.currency, f.conditions,
                   coalesce((
                     SELECT json_agg(json_build_object(
                              'evidence_id', e.evidence_id,
                              'quote', e.quote,
                              'source_url', e.source_url,
                              'source_item_id', e.source_item_id,
                              'locator', e.locator,
                              'authority', e.authority,
                              'document_name', d.document_name,
                              'document_kind', d.document_kind)
                            ORDER BY e.evidence_id)
                     FROM fact_evidence e
                     LEFT JOIN knowledge_documents d ON d.id = e.source_document_id
                     WHERE e.fact_id = f.id), '[]'::json) AS evidence
            FROM tariff_facts f
            WHERE f.snapshot_id = '{snapshot_id}'
            ORDER BY f.field_path, f.variant_key"""
    )
    # The source text each cited evidence item held when it was extracted.
    published["sources"] = {
        row["evidence_id"]: row["content"]
        for row in stack.sql(
            f"""SELECT e->>'evidence_id' AS evidence_id, e->>'content' AS content
                FROM tariff_snapshots s, jsonb_array_elements(s.evidence) e
                WHERE s.id = '{snapshot_id}'"""
        )
    }
    published["changes"] = stack.sql(
        f"""SELECT change_count, changes FROM tariff_changes
            WHERE current_snapshot_id = '{snapshot_id}'"""
    )
    return published


def same_sources(snapshot_id: str, previous_id: str) -> bool:
    """Whether two snapshots were extracted from byte-identical documents."""
    rows = stack.sql(
        f"""SELECT sd.snapshot_id::text AS snapshot,
                   string_agg(d.content_sha256, ',' ORDER BY d.content_sha256) AS hashes
            FROM snapshot_documents sd
            JOIN knowledge_documents d ON d.id = sd.document_id
            WHERE sd.snapshot_id IN ('{snapshot_id}', '{previous_id}')
            GROUP BY sd.snapshot_id"""
    )
    hashes = {row["snapshot"]: row["hashes"] for row in rows}
    return len(hashes) == 2 and hashes[snapshot_id] == hashes[previous_id]


def copy_audit(run_id: str, offering: str, destination: Path) -> list[str]:
    """Copy the worker's stage-numbered audit files for this run and offering."""
    if destination.exists():
        shutil.rmtree(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    result = stack.compose(
        "cp",
        f"worker:{AUDIT_ROOT}/run_{run_id}/{offering}",
        str(destination),
        capture=True,
        check=False,
    )
    if result.returncode != 0:
        return []
    return sorted(path.name for path in destination.iterdir())


# --------------------------------------------------------------------------
# rendering values


def normalize(text: str) -> str:
    return " ".join(text.split()).casefold()


def clip(text: str, width: int) -> str:
    collapsed = " ".join(str(text).split())
    return collapsed if len(collapsed) <= width else collapsed[: width - 1] + "…"


def number(value: object, unit: str | None) -> str:
    amount = float(value)
    if unit == "money":
        return f"{amount:,.0f}"
    return f"{amount:g}"


def unit_suffix(unit: str | None, currency: str | None) -> str:
    return {
        "percent": "%",
        "money": f" {currency}" if currency else "",
        "years": " years",
        "months": " months",
        "days": " days",
        "salary_multiple": "× salary",  # noqa: RUF001
    }.get(unit or "", f" {unit}" if unit else "")


def conditions_text(conditions: list[dict], currency: str | None) -> str:
    parts = [
        f"{str(item.get('dimension', '')).replace('_', ' ')}: {item.get('value')}"
        for item in conditions or []
        if item.get("value") is not None
        and not (item.get("dimension") == "currency" and item.get("value") == currency)
    ]
    return clip("; ".join(parts), CONDITION_WIDTH) if parts else ""


def plain(value: object) -> str:
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, dict):
        return clip(
            ", ".join(
                f"{k}: {plain(v)}" for k, v in value.items() if v not in (None, [])
            ),
            120,
        )
    if isinstance(value, list):
        return ", ".join(plain(item) for item in value)
    return str(value).replace("_", " ") if value is not None else "-"


def fee_text(fee: dict) -> str:
    amounts = []
    if fee.get("amount") is not None:
        amounts.append(
            f"{float(fee['amount']):,.0f} {fee.get('currency') or ''}".strip()
        )
    if fee.get("rate_pct") is not None:
        amounts.append(f"{float(fee['rate_pct']):g}%")
    label = clip(fee.get("description") or fee.get("scope") or "fee", 70)
    return f"{' / '.join(amounts)}: {label}" if amounts else label


def quoted_numbers(quote: str) -> set[float]:
    numbers = set()
    for digits, scale in NUMBER.findall(quote or ""):
        value = float(digits.replace(",", ""))
        numbers.add(value * 1_000_000 if scale else value)
    return numbers


def rank_citations(evidence: list[dict], values: set[float]) -> list[dict]:
    """Distinct citations, those quoting one of the values first."""
    distinct = list({(ev["evidence_id"], ev["quote"]): ev for ev in evidence}.values())
    return sorted(distinct, key=lambda ev: not quoted_numbers(ev["quote"]) & values)


def card_entries(facts: list[dict]) -> list[dict]:
    """The card's rows: one per value, a minimum and maximum joined into a range."""
    entries = []
    for prefixes, label in CARD_ROWS:
        for prefix in prefixes:
            members = [
                fact
                for fact in facts
                if fact["status"] == "found"
                and (
                    fact["field_path"] == prefix
                    or fact["field_path"].startswith(prefix + ".")
                )
            ]
            if members:
                break
        clusters: dict[tuple[str, str], list[dict]] = defaultdict(list)
        for fact in members:
            base = re.sub(r"\.(minimum|maximum)$", "", fact["field_path"])
            clusters[(base, fact["variant_key"])].append(fact)
        rows = []
        for (base, _), cluster in clusters.items():
            values = {
                float(fact["number_value"])
                for fact in cluster
                if fact["number_value"] is not None
            }
            rows.append(
                {
                    "label": label,
                    "value": cluster_value(prefix, base, cluster),
                    "when": conditions_text(
                        cluster[0]["conditions"], cluster[0]["currency"]
                    ),
                    "evidence": rank_citations(
                        [ev for fact in cluster for ev in fact["evidence"]], values
                    ),
                }
            )
        if label in JOINED_ROWS and rows and not any(row["when"] for row in rows):
            rows = [
                {
                    "label": label,
                    "value": "; ".join(row["value"] for row in rows),
                    "when": "",
                    "evidence": rank_citations(
                        [ev for row in rows for ev in row["evidence"]], set()
                    ),
                }
            ]
        entries += rows
    return entries


def cluster_value(prefix: str, base: str, cluster: list[dict]) -> str:
    by_bound = {fact["field_path"].rsplit(".", 1)[-1]: fact for fact in cluster}
    low, high = by_bound.get("minimum"), by_bound.get("maximum")
    sample = cluster[0]
    if (low or high) and sample["number_value"] is not None:
        suffix = unit_suffix(sample["unit"], sample["currency"])
        qualifier = base[len(prefix) + 1 :].replace("_", " ").replace(".", " ")
        # The unit already names the salary for a salary multiple.
        qualifier = (
            f"{qualifier}: "
            if qualifier and sample["unit"] != "salary_multiple"
            else ""
        )

        def fmt(fact: dict) -> str:
            return number(fact["number_value"], fact["unit"])

        if low and high and fmt(low) != fmt(high):
            return f"{qualifier}{fmt(low)}–{fmt(high)}{suffix}"  # noqa: RUF001
        if (low and high) or base.startswith("rate."):
            # A rate stated as one figure is stored as its minimum alone.
            return f"{qualifier}{fmt(low or high)}{suffix}"
        return f"{qualifier}{'from ' if low else 'up to '}{fmt(low or high)}{suffix}"
    if prefix == "fee" and isinstance(sample["value_json"], dict):
        return fee_text(sample["value_json"])
    name = sample["field_path"][len(prefix) + 1 :].replace("_", " ").replace(".", " ")
    value = plain(sample["value_json"])
    return f"{name}: {value}" if name else value


def cell(text: str) -> str:
    """Text safe inside a Markdown table cell."""
    return " ".join(str(text).split()).replace("|", "\\|")


def evidence_path(evidence: dict) -> str:
    """Document → page → section, the way the assignment's example cites."""
    locator = evidence.get("locator") or {}
    name = evidence.get("document_name") or evidence.get("source_url")
    is_pdf = locator.get("source_type") == "pdf"
    parts = [f"[{cell(name)}]({evidence['source_url']})" + (" (PDF)" if is_pdf else "")]
    if locator.get("pdf_page"):
        parts.append(f"page {locator['pdf_page']}")
    if locator.get("section"):
        parts.append(f"“{clip(locator['section'], 90)}”")
    if not is_pdf and evidence.get("source_item_id"):
        parts.append(f"item `{evidence['source_item_id']}`")
    return " → ".join(parts)


# --------------------------------------------------------------------------
# the business card


def render_card(offering: str, published: dict) -> tuple[str, list[str]]:
    """card.md, and the few lines printed on the console for the same card."""
    facts = published["facts"]
    execution = published["execution"]
    snapshot = published["snapshot"]
    names = [
        fact["value_json"]
        for fact in facts
        if fact["field_path"] == "identity.product_name" and fact["status"] == "found"
    ]
    title = names[0] if names else offering
    documents: dict[str, tuple[str, bool]] = {}
    for fact in facts:
        for ev in fact["evidence"]:
            is_pdf = (ev.get("locator") or {}).get("source_type") == "pdf"
            documents.setdefault(
                ev["source_url"], (ev.get("document_name") or ev["source_url"], is_pdf)
            )
    pages = [url for url, (_, is_pdf) in documents.items() if not is_pdf]
    pdfs = [url for url, (_, is_pdf) in documents.items() if is_pdf]
    currencies = sorted({fact["currency"] for fact in facts if fact["currency"]})
    retrieved = datetime.fromisoformat(
        execution.get("source_retrieved_at") or snapshot["accepted_at"]
    )
    signals = (snapshot.get("validation") or {}).get("review_signals") or []

    lines = [
        f"# {title}",
        "",
        f"Published by monitoring run `{published['run']['id'][:8]}` on the "
        "demonstration stack. Every value below was extracted from the bank's own "
        "pages and documents and is shown with the text it came from.",
        "",
        "| | |",
        "|---|---|",
        "| Official source | "
        + "<br>".join(f"[{cell(documents[url][0])}]({url})" for url in pages)
        + " |",
        "| Documents read | "
        + (
            "<br>".join(f"[{cell(documents[url][0])}]({url}) (PDF)" for url in pdfs)
            or "-"
        )
        + " |",
        f"| Retrieved | {retrieved.astimezone(UTC):%Y-%m-%d %H:%M} UTC "
        f"({retrieved.astimezone(YEREVAN):%H:%M} Yerevan) |",
        f"| Currency | {', '.join(currencies) or '-'} |",
        f"| Status | `{snapshot['status']}`, "
        + (
            "no human review needed"
            if not signals
            else f"{len(signals)} review signal(s)"
        )
        + " |",
        "",
        "## Tariff",
        "",
        "| | Value | Applies when | Evidence |",
        "|---|---|---|---|",
    ]
    console = [
        f"{title}",
        f"  Source:    {', '.join(pages)}",
        f"  Retrieved: {retrieved.astimezone(UTC):%Y-%m-%d %H:%M} UTC",
        f"  Currency:  {', '.join(currencies) or '-'}",
    ]
    cited: dict[tuple[str, str], int] = {}
    footnotes: list[str] = []
    for entry in card_entries(facts):
        refs = []
        for ev in entry["evidence"][:CITATIONS_PER_ROW]:
            key = (ev["evidence_id"], ev["quote"])
            if key not in cited:
                cited[key] = len(cited) + 1
                footnotes += [
                    f"**E{cited[key]}.** {evidence_path(ev)}",
                    "",
                    f"> {clip(ev['quote'], QUOTE_WIDTH)}",
                    "",
                ]
            refs.append(f"E{cited[key]}")
        more = len(entry["evidence"]) - len(refs)
        lines.append(
            f"| {entry['label']} | {cell(entry['value'])} | {cell(entry['when'])} | "
            f"{', '.join(refs)}{f' (+{more})' if more > 0 else ''} |"
        )
        console.append(
            f"  {entry['label'] + ':':<23}{entry['value']}"
            + (f"   [{clip(entry['when'], 60)}]" if entry["when"] else "")
        )
    lines += ["", "## Evidence", "", *footnotes]
    lines.append(
        f"Each row shows at most {CITATIONS_PER_ROW} citations, those quoting "
        "the row's figure first; (+N) counts the others. The card shows the "
        f"headline fields; the snapshot holds {len(facts)} typed facts in all, "
        "and `report.md` checks the evidence of every one."
    )
    return "\n".join(lines).strip() + "\n", console


# --------------------------------------------------------------------------
# the question


def ask(question: str) -> dict:
    return stack.api("POST", "/tariffs/query", {"query": question})


def show_answer(report: Report, question: str, answer: dict) -> None:
    report.say(f"Question: “{question}” (`POST /api/v1/tariffs/query`)")
    report.say(
        f"Status `{answer['status']}`, operation `{answer.get('operation')}`, "
        f"as of {answer.get('as_of')}, {len(answer.get('facts') or [])} facts."
    )
    rows = []
    for fact in answer.get("facts") or []:
        value = fact.get("number")
        ranked = rank_citations(
            fact.get("evidence") or [], {float(value)} if value is not None else set()
        )
        first = ranked[0] if ranked else {}
        rows.append(
            [
                f"`{fact['field_path']}`",
                f"{fact.get('value')}{unit_suffix(fact.get('unit'), fact.get('currency'))}",
                conditions_text(fact.get("conditions") or [], fact.get("currency"))
                or "-",
                f"“{clip(first.get('quote', '-'), 70)}”",
            ]
        )
    if rows:
        report.table(["Field", "Value", "Applies when", "Citation"], rows)


# --------------------------------------------------------------------------
# checks


def states(text: str, value: float) -> bool:
    """Whether a source text states this figure, a zero possibly in words."""
    return value in quoted_numbers(text) or (
        value == 0 and bool(ZERO_IN_WORDS.search(text))
    )


def figure_coverage(published: dict) -> tuple[list[dict], list[dict], list[dict]]:
    """Numeric facts by how their cited text states the figure.

    A citation points at an evidence item (a paragraph, a table row, a PDF
    passage) and quotes part of it. The figure should be somewhere in the item;
    the quote itself may be a neighbouring line of the same row. Returns the
    facts whose figure no cited item states, those whose cited items state it
    but no quote does, and the zeros that are stated only in words.
    """
    sources = published["sources"]
    numeric = [
        fact
        for fact in published["facts"]
        if fact["status"] == "found" and fact["number_value"] is not None
    ]
    outside_items, outside_quotes, zeros_in_words = [], [], []
    for fact in numeric:
        value = float(fact["number_value"])
        items = [sources.get(ev["evidence_id"], "") for ev in fact["evidence"]]
        if not any(states(item, value) for item in items):
            outside_items.append(fact)
            continue
        if not any(states(ev["quote"], value) for ev in fact["evidence"]):
            outside_quotes.append(fact)
        if not any(value in quoted_numbers(item) for item in items):
            zeros_in_words.append(fact)
    return outside_items, outside_quotes, zeros_in_words


def checks_for(
    published: dict, served: dict, answer: dict
) -> list[tuple[str, bool, str]]:
    run = published["run"]
    execution = published["execution"]
    snapshot = published["snapshot"] or {}
    facts = published["facts"]
    found = [fact for fact in facts if fact["status"] == "found"]
    citations = [ev for fact in found for ev in fact["evidence"]]
    validation = snapshot.get("validation") or {}
    signals = validation.get("review_signals") or []

    uncited = [fact["field_path"] for fact in found if not fact["evidence"]]
    unlocated = [
        ev
        for ev in citations
        if not ev.get("quote")
        or not (
            (ev.get("locator") or {}).get("pdf_page")
            or (ev.get("locator") or {}).get("css_selector")
            or (ev.get("locator") or {}).get("xpath")
        )
    ]
    sources = published["sources"]
    unmatched = [
        ev
        for ev in citations
        if normalize(ev["quote"] or "")
        not in normalize(sources.get(ev["evidence_id"], ""))
    ]
    numeric = [fact for fact in found if fact["number_value"] is not None]
    outside_items, _, zeros_in_words = figure_coverage(published)
    answer_facts = answer.get("facts") or []
    answer_snapshots = {fact.get("snapshot_id") for fact in answer_facts}
    return [
        (
            "the run succeeded",
            run["status"] == "succeeded",
            f"run `{run['status']}`, offering `{execution.get('status')}` at "
            f"`{execution.get('current_stage')}`",
        ),
        (
            "published without human review",
            snapshot.get("status") == "accepted"
            and not signals
            and not execution.get("review_count"),
            f"snapshot `{snapshot.get('status')}`, "
            f"{validation.get('validated_field_count', 0)} validated fields, "
            f"{len(signals)} review signals, {execution.get('review_count', 0)} reviews",
        ),
        (
            "the API serves this snapshot as current",
            served.get("snapshot_id") == snapshot.get("id")
            and served.get("freshness") == "fresh",
            f"`GET /tariffs/current`: snapshot `{str(served.get('snapshot_id'))[:8]}`, "
            f"freshness `{served.get('freshness')}`",
        ),
        (
            "every value has evidence",
            bool(found) and not uncited,
            f"{len(found)} found facts, {len(uncited)} without evidence",
        ),
        (
            "every citation has a quote and a locator",
            bool(citations) and not unlocated,
            f"{len(citations)} citations, {len(unlocated)} missing quote or locator",
        ),
        (
            "every quote is in the source text it cites",
            bool(citations) and not unmatched,
            f"{len(citations) - len(unmatched)} of {len(citations)} found verbatim",
        ),
        (
            "every figure appears in the source text it cites",
            bool(numeric) and not outside_items,
            f"{len(numeric) - len(outside_items)} of {len(numeric)} numeric values"
            + (
                f" ({len(zeros_in_words)} zeros stated in words)"
                if zeros_in_words
                else ""
            )
            + (
                ": missing "
                + ", ".join(
                    f"`{fact['field_path']}` {fact['number_value']}"
                    for fact in outside_items[:4]
                )
                if outside_items
                else ""
            ),
        ),
        (
            "the question is answered from this snapshot",
            answer.get("status") == "answered"
            and bool(answer_facts)
            and answer_snapshots == {snapshot.get("id")}
            and all(fact.get("evidence") for fact in answer_facts),
            f"`{answer.get('status')}`, {len(answer_facts)} facts, all cited, "
            f"as of {answer.get('as_of')}",
        ),
    ]


# --------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--offering", default=stack.BASELINE_OFFERING[1])
    parser.add_argument(
        "--no-run",
        action="store_true",
        help="report the latest accepted snapshot instead of running (no extraction cost)",
    )
    parser.add_argument(
        "--cold",
        action="store_true",
        help="clear this offering's cached model output first, so every call is live",
    )
    parser.add_argument(
        "--question",
        help="the question asked at the end (default: its nominal interest rate)",
    )
    parser.add_argument(
        "--restore-worker",
        action="store_true",
        help="restart the normal worker if it runs with another demo's overlay",
    )
    args = parser.parse_args()
    if args.cold and args.no_run:
        parser.error("--cold clears caches for a new run; it has no use with --no-run")
    offering = args.offering
    product = product_for(offering)
    folder = OUTPUT / offering

    report = Report()
    report.lines = [
        "# Normal tariff extraction",
        "",
        f"Generated {datetime.now(UTC):%Y-%m-%d %H:%M UTC} by `extraction_demo.py"
        f"{' --no-run' if args.no_run else ''}{' --cold' if args.cold else ''}` against the demonstration stack "
        f"(Compose project `{stack.PROJECT}`). Offering: `{product}/{offering}`.",
    ]
    stack.wait_for_api(timeout=30)

    if args.no_run:
        report.heading("Run: the latest accepted one (no new run)")
        run_id = latest_accepted_run(offering)
        report.say(
            f"Reporting run `{run_id[:8]}`; nothing was fetched or extracted now."
        )
    else:
        report.heading("Run: fetch, read, extract, validate, publish")
        ensure_stack_is_free(args.restore_worker)
        if args.cold:
            clear_model_caches(product, offering, report)
        run_id, elapsed = live_run(product, offering, report)
        report.say(f"Run `{run_id[:8]}` ended after {elapsed:.0f}s.")

    published = load_published(run_id, offering)
    execution = published["execution"]
    snapshot = published["snapshot"]
    if snapshot is None:
        report.say(
            f"No snapshot was written: `{execution.get('failure_code')}`: "
            f"{execution.get('failure_detail')}"
        )
        return 1

    report.heading("What the run read and what it cost")
    report.table(
        ["", ""],
        [
            ["Sources discovered", str(execution.get("source_count"))],
            ["Documents read (PDFs)", str(execution.get("document_count"))],
            ["Retrieved", str(execution.get("source_retrieved_at"))],
            [
                "Reused an earlier fetch",
                "yes" if execution.get("acquisition_reused") else "no",
            ],
        ],
    )
    usage = published["usage"]
    total = sum(float(row["usd"]) for row in usage)
    report.say("Gemini, by stage:")
    report.table(
        ["Stage", "Model", "Calls", "Reused from cache", "Tokens in / out", "Cost"],
        [
            [
                f"`{row['stage']}`",
                row["models"],
                str(row["calls"])
                + (f" (+{row['failed']} failed)" if row["failed"] else ""),
                str(row["cached"]),
                f"{row['input_tokens']:,} / {row['output_tokens']:,}",
                f"${float(row['usd']):.4f}",
            ]
            for row in usage
        ]
        + [
            [
                "**Total**",
                "",
                str(sum(row["calls"] for row in usage)),
                str(sum(row["cached"] for row in usage)),
                "",
                f"**${total:.4f}**",
            ]
        ],
    )
    if usage and not any(row["calls"] for row in usage):
        report.say(
            "No model was called: the page and PDFs were byte-identical to an "
            "earlier run, so the pipeline reused the output it had cached for that "
            "content. Pass --cold to clear it and extract live."
        )

    report.heading("Admission")
    validation = snapshot.get("validation") or {}
    report.say(
        f"Snapshot `{snapshot['id'][:8]}` is `{snapshot['status']}`: "
        f"{validation.get('validated_field_count', 0)} fields validated, "
        f"{len(validation.get('review_signals') or [])} review signals, "
        f"{len(published['facts'])} typed facts projected."
    )
    if snapshot.get("previous_accepted_snapshot_id") is None:
        report.say("First accepted observation of this offering: nothing to compare.")
    else:
        count = sum(row["change_count"] for row in published["changes"])
        fields = sorted(
            {
                str(change.get("field"))
                for row in published["changes"]
                for change in row["changes"] or []
            }
        )
        report.say(
            f"Compared with the previous accepted snapshot "
            f"`{snapshot['previous_accepted_snapshot_id'][:8]}`: {count} field change(s)"
            + (f": {', '.join(fields)}." if fields else ".")
        )
        if fields and same_sources(
            snapshot["id"], snapshot["previous_accepted_snapshot_id"]
        ):
            report.say(
                "Both snapshots were extracted from byte-identical documents, so these "
                "are differences between two extractions of the same text (wording, "
                "ordering, a rate type), not a new tariff."
            )

    report.heading("The business view")
    card, console = render_card(offering, published)
    for line in console:
        print(f"    {line}")
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "card.md").write_text(card, encoding="utf-8")
    report.lines.append(
        "The card is in [card.md](card.md): values, the conditions they apply "
        "under, and the quoted source of each."
    )
    print(f"    Wrote {(folder / 'card.md').relative_to(HERE)}")

    report.heading("A question, answered from the stored data")
    names = [
        fact["value_json"]
        for fact in published["facts"]
        if fact["field_path"] == "identity.product_name"
    ]
    question = (
        args.question
        or f"What is the nominal interest rate of the {names[0] if names else offering}?"
    )
    answer = ask(question)
    show_answer(report, question, answer)

    audit = copy_audit(run_id, offering, folder / "audit")
    report.heading("Pipeline audit files")
    if audit:
        report.say(
            "Copied from the worker; `4_extraction_evidence.md` highlights every "
            "cited quote inside its source."
        )
        report.lines += [f"- [{name}](audit/{name})" for name in audit]
        print("    " + ", ".join(audit))
    else:
        report.say("No audit files found for this run in the worker.")

    served = stack.api(
        "GET", f"/tariffs/current?product={product}&offering_id={offering}"
    )["items"][0]
    report.heading("Checks")
    checks = checks_for(published, served, answer)
    report.table(
        ["", "Check", "Observed"],
        [["PASS" if ok else "FAIL", title, observed] for title, ok, observed in checks],
    )
    _, outside_quotes, zeros_in_words = figure_coverage(published)
    for fact in zeros_in_words:
        quote = next(
            (
                ev["quote"]
                for ev in fact["evidence"]
                if ZERO_IN_WORDS.search(ev["quote"])
            ),
            fact["evidence"][0]["quote"],
        )
        report.say(
            f"Zero in words: `{fact['field_path']}` = 0 "
            f"({conditions_text(fact['conditions'], fact['currency']) or 'no conditions'})"
            f" from “{clip(quote, 80)}”."
        )
    if outside_quotes:
        report.say(
            f"Note: {len(outside_quotes)} figure(s) are in the cited evidence item "
            "but not in the quoted words themselves (the model quoted a neighbouring "
            "line of the same table row or passage):"
        )
        for fact in outside_quotes:
            quote = rank_citations(fact["evidence"], set())[0]["quote"]
            report.say(
                f"- `{fact['field_path']}` = {fact['number_value']:g}"
                f"{unit_suffix(fact['unit'], fact['currency'])}"
                f" ({conditions_text(fact['conditions'], fact['currency']) or 'no conditions'})"
                f", quoted as “{clip(quote, 80)}”"
            )
    passed = all(ok for _, ok, _ in checks)
    report.say(f"RESULT: {'PASS' if passed else 'FAIL'}")

    (folder / "report.md").write_text(
        "\n".join(report.lines).strip() + "\n", encoding="utf-8"
    )
    print(f"\n    Wrote {(folder / 'report.md').relative_to(HERE)}")
    return 0 if passed else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except stack.StackError as exc:
        sys.exit(f"error: {exc}")
