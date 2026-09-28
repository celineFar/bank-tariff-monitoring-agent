#!/usr/bin/env python3
"""Tariff change detection with human review: the bank raises a rate by 4 points.

Runs against the persistent demonstration stack (../demo-stack). A local HTTPS
mirror serves a copy of the bank's Overdraft page. The demo "republishes" that
page with the nominal rates raised by 4 percentage points, runs real monitoring,
and shows that the system catches the change, does not publish it on its own
because the jump is over the review threshold (3 points), and publishes it only
after a person approves it in the chat.

    python3 change_demo.py setup   # once: certificates, mirror, baseline, checkpoint
    python3 change_demo.py         # the demonstration (repeatable)
    python3 change_demo.py show    # what the demo database holds now

The republished page is the only artificial part: the pipeline, Gemini, the
review queue and the chat are real. Every demonstration starts by restoring the
checkpoint taken at setup, so it always starts from the original rates. Writes
output/report.md.

Standard library only (plus openssl on the host, for the one-time certificates).
"""

from __future__ import annotations

import argparse
import difflib
import json
import os
import re
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "demo-stack"))

import stack  # noqa: E402

OVERLAY = HERE / "mirror.yml"
RUNTIME = HERE / "runtime"
OUTPUT = HERE / "output" / "report.md"
ORIGINAL = HERE / "mirror" / "original" / "overdraft" / "index.html"
REPUBLISHED = HERE / "mirror" / "republished" / "overdraft" / "index.html"
MIRROR_HOST = "tariff-mirror.demo"
BANK_SEED_URL = "https://ameriabank.am/en/personal/loans/consumer-loans/overdraft"
MIRROR_SEED_URL = f"https://{MIRROR_HOST}/overdraft"
PRODUCT, OFFERING = "consumer_loan", "overdraft"
CHECKPOINT = "change-demo"

# The republication: the nominal AMD rates, 4 percentage points up. The annual
# percentage rates are left as published, so the only change is the nominal rate.
EDITS: tuple[tuple[str, str, str], ...] = (
    ("standard cards, nominal rate", "AMD: 21%", "AMD: 25%"),
    ("premium cards, nominal rate", "AMD: 20%", "AMD: 24%"),
    ("scoring-based band, nominal rate", "15% -21%", "19% -25%"),
)
UNTOUCHED = ("AMD: 23.13 %", "AMD: 21.92 %", "16.06-23.13%")


def rel(path: Path) -> str:
    return "./" + str(path.relative_to(stack.REPO))


# --------------------------------------------------------------------------
# one-time material


def make_certificates() -> None:
    """A demo root and the mirror's certificate, trusted only in the demo worker."""
    ca, certs = RUNTIME / "ca", RUNTIME / "certs"
    ca.mkdir(parents=True, exist_ok=True)
    certs.mkdir(parents=True, exist_ok=True)
    root, root_key = ca / "rootCA.pem", ca / "rootCA-key.pem"
    leaf, leaf_key = certs / f"{MIRROR_HOST}.pem", certs / f"{MIRROR_HOST}-key.pem"
    if leaf.exists() and root.exists():
        return

    def openssl(*args: str) -> None:
        subprocess.run(["openssl", *args], check=True, capture_output=True)

    openssl(
        "req", "-x509", "-newkey", "rsa:4096", "-sha256", "-days", "3650", "-nodes",
        "-keyout", str(root_key), "-out", str(root),
        "-subj", "/CN=Tariff Monitor Demonstration Root/O=demo-only",
        "-addext", "basicConstraints=critical,CA:TRUE,pathlen:0",
        "-addext", "keyUsage=critical,keyCertSign,cRLSign",
    )  # fmt: skip
    csr = certs / f"{MIRROR_HOST}.csr"
    openssl(
        "req", "-newkey", "rsa:2048", "-sha256", "-nodes",
        "-keyout", str(leaf_key), "-out", str(csr),
        "-subj", f"/CN={MIRROR_HOST}/O=demo-only",
    )  # fmt: skip
    extensions = RUNTIME / "leaf.ext"
    extensions.write_text(
        f"subjectAltName=DNS:{MIRROR_HOST}\n"
        "basicConstraints=critical,CA:FALSE\n"
        "keyUsage=critical,digitalSignature,keyEncipherment\n"
        "extendedKeyUsage=serverAuth\n"
    )
    openssl(
        "x509", "-req", "-in", str(csr), "-CA", str(root), "-CAkey", str(root_key),
        "-CAcreateserial", "-out", str(leaf), "-days", "825", "-sha256",
        "-extfile", str(extensions),
    )  # fmt: skip
    csr.unlink()
    extensions.unlink()
    # Caddy runs as its own user and must read the leaf key.
    leaf_key.chmod(0o644)
    print(f"    issued a demo root and a certificate for {MIRROR_HOST}")


def install_trust() -> None:
    """Make the demo root known to httpx and to Chromium inside the worker.

    Runs once, in a throwaway container of the worker image, and leaves the
    result in two Docker volumes the overlay mounts. No image is built.
    """
    script = r"""
set -e
if [ -f /demo-trust/rootCA.pem ] && cmp -s /demo-ca/rootCA.pem /demo-trust/rootCA.pem \
   && [ -f /root/.pki/nssdb/cert9.db ]; then echo "already trusted"; exit 0; fi
apt-get update -qq >/dev/null
apt-get install -y -qq --no-install-recommends libnss3-tools >/dev/null
bundle="$(/code/.venv/bin/python -c 'import certifi; print(certifi.where())')"
cat "$bundle" /demo-ca/rootCA.pem > /demo-trust/ca-bundle.pem
cp /demo-ca/rootCA.pem /demo-trust/rootCA.pem
[ -f /root/.pki/nssdb/cert9.db ] || \
  certutil -d sql:/root/.pki/nssdb -N --empty-password </dev/null
certutil -d sql:/root/.pki/nssdb -D -n tariff-demo-root </dev/null >/dev/null 2>&1 || true
certutil -d sql:/root/.pki/nssdb -A -t C,, -n tariff-demo-root -i /demo-ca/rootCA.pem
echo "trusted the demo root for httpx and Chromium"
"""
    result = stack.compose(
        "run", "--rm", "--no-deps", "-T", "--entrypoint", "sh", "worker", "-c", script,
        overlays=(OVERLAY,), capture=True, check=False,
    )  # fmt: skip
    if result.returncode != 0:
        raise stack.StackError(
            f"installing the demo root failed: {result.stderr.strip()}"
        )
    print(f"    {result.stdout.strip().splitlines()[-1]}")


def make_catalog() -> None:
    """The shipped catalog with exactly one line changed: Overdraft's seed URL."""
    shipped = (stack.REPO / "app" / "config" / "seed_catalog.yaml").read_text()
    line = f"seed_url: {BANK_SEED_URL}"
    if shipped.count(line) != 1:
        raise stack.StackError(f"expected exactly one '{line}' in the shipped catalog")
    RUNTIME.mkdir(exist_ok=True)
    (RUNTIME / "seed_catalog.yaml").write_text(
        "# Generated by change_demo.py from app/config/seed_catalog.yaml. One line\n"
        "# differs: Overdraft's seed URL points at the demonstration mirror.\n"
        + shipped.replace(line, f"seed_url: {MIRROR_SEED_URL}")
    )


def make_republished() -> list[str]:
    """The original page with the rate edits applied; returns what changed."""
    html = ORIGINAL.read_text(encoding="utf-8")
    for _, old, new in EDITS:
        if html.count(old) != 1:
            raise stack.StackError(f"expected '{old}' exactly once in the original")
        html = html.replace(old, new)
    for value in UNTOUCHED:
        if value not in html:
            raise stack.StackError(f"an annual percentage rate went missing: {value}")
    REPUBLISHED.parent.mkdir(parents=True, exist_ok=True)
    REPUBLISHED.write_text(html, encoding="utf-8")
    return changed_lines()


def changed_lines() -> list[str]:
    before = ORIGINAL.read_text(encoding="utf-8").splitlines()
    after = REPUBLISHED.read_text(encoding="utf-8").splitlines()
    return [
        line
        for line in difflib.unified_diff(before, after, lineterm="", n=0)
        if line[:1] in "+-" and not line.startswith(("+++", "---"))
    ]


# --------------------------------------------------------------------------
# the mirror


def serve(page: Path) -> None:
    """(Re)start the mirror serving `page` as the Overdraft page."""
    os.environ["MIRROR_PAGE"] = rel(page)
    stack.compose(
        "up", "-d", "--no-deps", "--force-recreate", "mirror",
        overlays=(OVERLAY,), capture=True,
    )  # fmt: skip
    time.sleep(2)


def stop_mirror() -> None:
    stack.compose("rm", "-sf", "mirror", overlays=(OVERLAY,), capture=True, check=False)


def mirror_serves() -> str:
    """Fetch the Overdraft page from inside the worker, through its own trust."""
    probe = (
        "import httpx, re; r = httpx.get('https://tariff-mirror.demo/overdraft'); "
        "rates = re.findall(r'AMD: \\d+%', r.text); print(r.status_code, *rates)"
    )
    result = stack.compose(
        "exec", "-T", "worker", "/code/.venv/bin/python", "-c", probe,
        overlays=(OVERLAY,), capture=True, check=False,
    )  # fmt: skip
    return (result.stdout or result.stderr).strip().splitlines()[-1]


def use_mirror() -> None:
    """Point the worker at the mirror, and check it can fetch the page."""
    make_catalog()
    stack.restart_worker((OVERLAY,))
    answer = mirror_serves()
    if not answer.startswith("200"):
        raise stack.StackError(f"the worker cannot fetch the mirror: {answer}")


def release_mirror() -> None:
    try:
        stack.restart_worker()
    finally:
        stop_mirror()


# --------------------------------------------------------------------------
# reading the database


def run_rows(run_id: str) -> dict:
    snapshot = stack.sql(
        f"""SELECT id, status, normalized_tariff FROM tariff_snapshots
            WHERE run_id = '{run_id}' ORDER BY created_at DESC LIMIT 1"""
    )
    reviews = stack.sql(
        f"""SELECT id, reason_code, issue_scope, status, decision, reviewer,
                   decided_at, evidence, candidates
            FROM human_reviews WHERE run_id = '{run_id}' ORDER BY created_at"""
    )
    changes = stack.sql(
        f"""SELECT id, change_count, changes FROM tariff_changes
            WHERE run_id = '{run_id}'
               OR current_snapshot_id = (SELECT id FROM tariff_snapshots
                                         WHERE run_id = '{run_id}' LIMIT 1)"""
    )
    return {
        "snapshot": snapshot[0] if snapshot else None,
        "reviews": reviews,
        "changes": changes,
    }


def find_key(node: object, key: str) -> object | None:
    """The first value stored under `key` anywhere in a JSON document."""
    if isinstance(node, dict):
        if key in node:
            return node[key]
        for value in node.values():
            if (found := find_key(value, key)) is not None:
                return found
    elif isinstance(node, list):
        for value in node:
            if (found := find_key(value, key)) is not None:
                return found
    return None


def review_threshold() -> str:
    result = stack.compose(
        "exec", "-T", "worker", "printenv", "HITL_LARGE_RATE_CHANGE_PERCENTAGE_POINTS",
        capture=True, check=False,
    )  # fmt: skip
    return result.stdout.strip() or "3"


def describe_review(review: dict) -> str:
    rate_change = find_key(review, "rate_change")
    if isinstance(rate_change, dict):
        return (
            f"previous {rate_change.get('previous')}, candidate "
            f"{rate_change.get('current')}, change {rate_change.get('delta')} points"
        )
    return "-"


def describe_changes(changes: list[dict]) -> list[list[str]]:
    rows = []
    for record in changes:
        entries = record.get("changes") or []
        if isinstance(entries, dict):
            entries = entries.get("changes") or [entries]
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            field = entry.get("field") or entry.get("path") or entry.get("field_path")
            rows.append(
                [
                    f"`{field}`",
                    compact(entry.get("previous")),
                    compact(entry.get("current")),
                ]
            )
    return rows


def compact(value: object) -> str:
    """A changed value in a table cell: its rates when it has any, else JSON."""
    text = json.dumps(value, ensure_ascii=False)
    rates = [f"{float(r):g}" for r in re.findall(r'"(?:min|max)": "([\d.]+)"', text)]
    if rates:
        return ", ".join(dict.fromkeys(rates))
    return (text[:80] + "…") if len(text) > 80 else text


# --------------------------------------------------------------------------
# commands


def cmd_setup(_: argparse.Namespace) -> None:
    stack.wait_for_api(timeout=30)
    print("==> One-time setup")
    make_certificates()
    # Before any container starts: a missing bind-mount source would be created
    # by Docker as an empty directory.
    make_catalog()
    edits = make_republished()
    print(f"    republished page: {len(edits) // 2} lines differ from the original")
    install_trust()
    serve(ORIGINAL)
    try:
        use_mirror()
        print(f"    worker fetches the mirror: {mirror_serves()}")
        print("==> Baseline: one real run of Overdraft against the original page")
        run = stack.submit_run(
            PRODUCT, OFFERING, f"change-demo-setup-{int(time.time())}"
        )
        run = stack.wait_for_run(run["id"])
        while run["status"] == "awaiting_review":
            print(
                "    The run is waiting for a review. In a second terminal:\n"
                "      python3 ../demo-stack/stack.py chat\n"
                "      You > Review the pending candidates"
            )
            run = wait_for_decisions(run["id"])
        if run["status"] != "succeeded":
            raise stack.StackError(
                f"baseline run ended {run['status']}: {run.get('failure_code')}"
            )
        answer = stack.current_tariff(PRODUCT, OFFERING)
        print(f"    accepted: interest rates {answer['rates']}")
    finally:
        release_mirror()
    stack.save_checkpoint(CHECKPOINT)
    print(f"==> Saved checkpoint '{CHECKPOINT}'. Setup is complete.")


def wait_for_decisions(run_id: str, timeout: float = 1800) -> dict:
    """Wait until a person has answered every review of the run."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        pending = stack.sql(
            f"""SELECT count(*) AS n FROM human_reviews
                WHERE run_id = '{run_id}' AND decided_at IS NULL"""
        )[0]["n"]
        run = stack.api("GET", f"/runs/{run_id}")
        if not pending and run["status"] != "awaiting_review":
            return run
        if not pending:
            # Decided; give the run a moment to record its outcome.
            time.sleep(3)
            continue
        time.sleep(3)
    raise stack.StackError("no review decision within the time allowed")


def cmd_demo(args: argparse.Namespace) -> int:
    if not (stack.CHECKPOINTS / f"{CHECKPOINT}.dump").exists():
        sys.exit("Run the one-time setup first: python3 change_demo.py setup")
    stack.wait_for_api(timeout=30)
    report = stack.Report()
    report.lines = [
        "# Tariff change detection and human review",
        "",
        f"Generated {datetime.now(UTC):%Y-%m-%d %H:%M UTC} by `change_demo.py` "
        f"against the demonstration stack (Compose project `{stack.PROJECT}`). "
        f"Offering: `{OFFERING}`, fetched from the demonstration mirror "
        f"`{MIRROR_SEED_URL}`.",
    ]
    checks: list[tuple[str, bool, str]] = []

    report.heading("Before: the accepted tariff")
    stack.restore_checkpoint(CHECKPOINT)
    before = stack.current_tariff(PRODUCT, OFFERING)
    threshold = review_threshold()
    report.say(
        f"Restored checkpoint `{CHECKPOINT}`. `GET /tariffs/current` for "
        f"{OFFERING}: snapshot `{str(before['snapshot_id'])[:8]}`, interest rates "
        f"**{before['rates']}**."
    )
    report.say(
        f"Review threshold: a rate change of {threshold} percentage points or more "
        "(`HITL_LARGE_RATE_CHANGE_PERCENTAGE_POINTS`)."
    )

    report.heading("The bank republishes the page")
    edits = changed_lines()
    report.say(
        "The mirror now serves `mirror/republished/overdraft/index.html`. Compared "
        "with the original, exactly these lines differ:"
    )
    report.table(
        ["What", "Before", "After"],
        [[what, f"`{old}`", f"`{new}`"] for what, old, new in EDITS],
    )
    report.say(
        "The annual percentage rates, the PDFs and every other byte of the page "
        "are unchanged."
    )
    checks.append(
        (
            "only the nominal rates were edited",
            len(edits) == 2 * len(EDITS),
            f"{len(edits) // 2} changed lines",
        )
    )

    serve(REPUBLISHED)
    try:
        use_mirror()
        report.say(f"Worker fetches the mirror: `{mirror_serves()}`.")

        report.heading("Monitoring run")
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
        run = stack.submit_run(PRODUCT, OFFERING, f"change-demo-{stamp}")
        run_id = run["id"]
        report.say(f"Submitted run `{run_id[:8]}` through `POST /api/v1/runs`.")
        run = stack.wait_for_run(run_id)
        paused = run["status"] == "awaiting_review"
        checks.append(
            (
                "the run stopped for review instead of publishing",
                paused,
                f"status `{run['status']}`",
            )
        )

        report.heading("Caught: what the system did with the change")
        rows = run_rows(run_id)
        snapshot = rows["snapshot"] or {}
        report.say(
            f"Candidate snapshot `{str(snapshot.get('id'))[:8]}`: status "
            f"`{snapshot.get('status')}`, interest rates "
            f"**{stack.rate_summary(snapshot.get('normalized_tariff'))}**."
        )
        report.table(
            ["Review", "Field", "Status", "What the reviewer sees"],
            [
                [
                    f"`{review['reason_code']}`",
                    f"`{review['issue_scope']}`",
                    review["status"],
                    describe_review(review),
                ]
                for review in rows["reviews"]
            ],
        )
        during = stack.current_tariff(PRODUCT, OFFERING)
        report.say(
            f"Meanwhile `GET /tariffs/current` still serves snapshot "
            f"`{str(during['snapshot_id'])[:8]}` with **{during['rates']}** "
            f"(pending newer review: {during['pending_newer_review']}). "
            f"Changes recorded so far: {len(rows['changes'])}."
        )
        large = [
            review
            for review in rows["reviews"]
            if review["reason_code"] == "large_rate_change"
        ]
        checks += [
            (
                "a large rate change was flagged for review",
                bool(large),
                ", ".join(f"`{r['issue_scope']}`" for r in large) or "none",
            ),
            (
                "the candidate was not published while pending",
                snapshot.get("status") == "review_required"
                and during["snapshot_id"] == before["snapshot_id"]
                and not rows["changes"],
                f"snapshot `{snapshot.get('status')}`, API serves "
                f"`{str(during['snapshot_id'])[:8]}`",
            ),
        ]

        decision = None
        if paused and not args.no_wait:
            report.heading("Human review")
            print(
                "    Answer the review in a second terminal:\n"
                "      python3 ../demo-stack/stack.py chat\n"
                "      You > Review the pending candidates\n"
                "      then type `approve` (publish the new rate) or `reject_all`\n"
                "    Waiting for the decision ...",
                flush=True,
            )
            run = wait_for_decisions(run_id, timeout=args.review_timeout)
            rows = run_rows(run_id)
            decision = [review["decision"] for review in rows["reviews"]]
            report.table(
                ["Review", "Field", "Decision", "Reviewer", "Decided at"],
                [
                    [
                        f"`{review['reason_code']}`",
                        f"`{review['issue_scope']}`",
                        f"`{review['decision'] or review['status']}`",
                        review["reviewer"] or "-",
                        str(review["decided_at"])[:19],
                    ]
                    for review in rows["reviews"]
                ],
            )
    finally:
        print(
            "\n    Restoring the normal worker and stopping the mirror ...", flush=True
        )
        release_mirror()

    if decision is not None:
        report.heading("After the decision")
        after = stack.current_tariff(PRODUCT, OFFERING)
        snapshot = rows["snapshot"] or {}
        approved = snapshot.get("status") == "accepted"
        report.say(
            f"Run `{run_id[:8]}`: `{run['status']}`. Candidate snapshot: "
            f"`{snapshot.get('status')}`."
        )
        change_rows = describe_changes(rows["changes"])
        if change_rows:
            report.say("Change recorded in `tariff_changes`:")
            report.table(["Field", "Previous", "Current"], change_rows)
        report.say(
            f"`GET /tariffs/current` now serves snapshot "
            f"`{str(after['snapshot_id'])[:8]}` with **{after['rates']}**."
        )
        if approved:
            history = stack.api(
                "GET",
                f"/tariffs/history?kind=what_changed&product={PRODUCT}"
                f"&offering_id={OFFERING}",
            )
            report.say(
                f"`GET /tariffs/history?kind=what_changed`: `{history.get('status')}`."
            )
            checks += [
                (
                    "the approved change was recorded, with the rate in it",
                    any("interest_rate" in row[0] for row in change_rows),
                    f"{len(change_rows)} field change(s)",
                ),
                (
                    "the API serves the new rates",
                    after["snapshot_id"] == snapshot.get("id")
                    and after["rates"] != before["rates"],
                    after["rates"],
                ),
            ]
        else:
            checks.append(
                (
                    "the rejected candidate was never published",
                    after["snapshot_id"] == before["snapshot_id"] and not change_rows,
                    f"API still serves `{str(after['snapshot_id'])[:8]}`",
                )
            )
    checks.append(
        ("the normal worker is back", stack.worker_running(), "mirror stopped")
    )

    report.heading("Checks")
    report.table(
        ["", "Check", "Observed"],
        [["PASS" if ok else "FAIL", title, seen] for title, ok, seen in checks],
    )
    spend = stack.sql(
        f"""SELECT coalesce(sum(estimated_cost_usd), 0) AS usd FROM model_call_usage
            WHERE run_id = '{run_id}'"""
    )[0]["usd"]
    report.say(f"Model spend for the monitoring run: ${float(spend):.4f}.")
    passed = all(ok for _, ok, _ in checks)
    report.say(f"RESULT: {'PASS' if passed else 'FAIL'}")
    OUTPUT.parent.mkdir(exist_ok=True)
    OUTPUT.write_text("\n".join(report.lines).strip() + "\n", encoding="utf-8")
    print(f"\n    Wrote {OUTPUT.relative_to(HERE)}")
    return 0 if passed else 1


def cmd_show(_: argparse.Namespace) -> None:
    answer = stack.current_tariff(PRODUCT, OFFERING)
    print(
        f"Current {OFFERING}: snapshot {str(answer['snapshot_id'])[:8]}, "
        f"rates {answer['rates']}, pending newer review: "
        f"{answer['pending_newer_review']}"
    )
    for review in stack.sql(
        """SELECT reason_code, issue_scope, status, decision FROM human_reviews
           ORDER BY created_at DESC LIMIT 5"""
    ):
        print(f"  review {review['reason_code']} {review['issue_scope']}: "
              f"{review['decision'] or review['status']}")  # fmt: skip
    for change in stack.sql(
        """SELECT created_at, change_count FROM tariff_changes
           ORDER BY created_at DESC LIMIT 3"""
    ):
        print(
            f"  change recorded {change['created_at']}: {change['change_count']} field(s)"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "command", nargs="?", default="demo", choices=("demo", "setup", "show")
    )
    parser.add_argument(
        "--no-wait",
        action="store_true",
        help="stop once the review is raised, without waiting for the decision",
    )
    parser.add_argument("--review-timeout", type=float, default=1800)
    args = parser.parse_args()
    try:
        if args.command == "setup":
            cmd_setup(args)
        elif args.command == "show":
            cmd_show(args)
        else:
            return cmd_demo(args)
    except stack.StackError as exc:
        sys.exit(f"error: {exc}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
