#!/usr/bin/env python3
"""Build the demonstration mirror's page variants from a real capture.

The mirror exists to republish an official page on cue. Everything it serves
therefore starts as a genuine capture of the bank's Overdraft page; the
`republished` variant differs from it by a stated set of single-value edits and
nothing else.

The page is made self-contained so a recording never depends on the bank being
reachable:

* linked tariff PDFs are copied beside the page and their links repointed at the
  mirror, so the documents are the bank's own, byte for byte;
* the site's stylesheets are fetched once and served from their original paths,
  because the renderer's visibility rules read computed styles and a page
  stripped of CSS does not hide what the real one hides;
* the Google Fonts stylesheet is dropped, which is what the renderer itself does
  to an off-allowlist subresource; and
* scripts are dropped. The capture is already the rendered DOM, and re-running
  the site's JavaScript against a mirror would call back to the bank.

Usage:
    uv run python demo/bin/build-variants.py [--capture end-to-end/run_007]
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path
from urllib.parse import urlsplit

import httpx
from bs4 import BeautifulSoup

REPO = Path(__file__).resolve().parents[2]
MIRROR = REPO / "demo" / "mirror"
BANK = "https://ameriabank.am"

# The `republished` edit. Nominal rates only: the effective rate is also cited
# from a PDF this fixture does not touch, and changing it on the page alone
# would stage a source conflict rather than a rate change.
NOMINAL_EDITS: tuple[tuple[str, str], ...] = (
    ("AMD: 21%", "AMD: 25%"),
    ("AMD: 20%", "AMD: 24%"),
    ("15% -21%", "19% -25%"),
)


def _document_map(capture: Path) -> dict[str, Path]:
    """Map each linked PDF URL to the file the capture downloaded for it."""
    manifest = json.loads(
        (capture / "acquisition" / "source files" / "document_manifest.json").read_text()
    )
    entries = manifest if isinstance(manifest, list) else manifest.get("documents", [])
    documents = capture / "acquisition" / "documents"
    mapping: dict[str, Path] = {}
    for entry in entries:
        url = entry.get("source_url") or entry.get("url")
        name = entry.get("original_file") or entry.get("stored_as") or entry.get("name")
        if not url:
            continue
        candidate = documents / name if name else None
        if candidate is None or not candidate.exists():
            stem = Path(urlsplit(url).path).name
            matches = sorted(documents.glob(f"*{stem}"))
            candidate = matches[0] if matches else None
        if candidate is not None and candidate.exists():
            mapping[url] = candidate
    return mapping


def _fetch_stylesheets(soup: BeautifulSoup, out: Path) -> int:
    """Serve the bank's stylesheets from the mirror at their original paths."""
    fetched = 0
    with httpx.Client(timeout=30, follow_redirects=True) as client:
        for link in soup.find_all("link", rel=lambda v: v and "stylesheet" in v):
            href = link.get("href") or ""
            if href.startswith("http") and "ameriabank.am" not in href:
                # Off-allowlist; the renderer blocks it during a real acquisition.
                link.decompose()
                continue
            path = urlsplit(href).path
            if not path:
                continue
            target = out / path.lstrip("/")
            target.parent.mkdir(parents=True, exist_ok=True)
            try:
                response = client.get(f"{BANK}{path}")
                response.raise_for_status()
            except httpx.HTTPError as exc:
                print(f"  ! stylesheet {path} not fetched: {type(exc).__name__}")
                continue
            target.write_bytes(response.content)
            fetched += 1
    return fetched


def build_unchanged(capture: Path) -> Path:
    out = MIRROR / "unchanged"
    if out.exists():
        shutil.rmtree(out)
    (out / "overdraft").mkdir(parents=True)
    (out / "docs").mkdir(parents=True)

    html = (capture / "acquisition" / "source files" / "rendered.html").read_text(
        encoding="utf-8", errors="replace"
    )
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup.find_all(["script", "noscript"]):
        tag.decompose()

    sheets = _fetch_stylesheets(soup, out)

    documents = _document_map(capture)
    copied = 0
    for anchor in soup.find_all("a", href=True):
        href = anchor["href"]
        if not href.lower().endswith(".pdf"):
            continue
        absolute = href if href.startswith("http") else f"{BANK}{href}"
        source = documents.get(absolute)
        if source is None:
            print(f"  ! no captured file for {absolute}")
            continue
        name = Path(urlsplit(absolute).path).name
        shutil.copy2(source, out / "docs" / name)
        anchor["href"] = f"/docs/{name}"
        copied += 1

    (out / "overdraft" / "index.html").write_text(str(soup), encoding="utf-8")
    print(f"unchanged: {sheets} stylesheets, {copied} PDF links repointed")
    return out


def build_republished(unchanged: Path) -> Path:
    out = MIRROR / "republished"
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(unchanged, out)

    page = out / "overdraft" / "index.html"
    html = page.read_text(encoding="utf-8")
    applied: list[str] = []
    for old, new in NOMINAL_EDITS:
        count = html.count(old)
        if not count:
            raise SystemExit(f"republished edit not found in the capture: {old!r}")
        html = html.replace(old, new)
        applied.append(f"{old!r} -> {new!r} ({count}x)")
    page.write_text(html, encoding="utf-8")

    # Nothing but the nominal rate may differ.
    untouched = ("AMD: 23.13 %", "AMD: 21.92 %", "16.06-23.13%")
    for value in untouched:
        if value not in html:
            raise SystemExit(f"effective-rate value went missing: {value!r}")

    print("republished: " + "; ".join(applied))
    print("republished: effective-rate values left untouched")
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", default="end-to-end/run_007")
    args = parser.parse_args()

    capture = (REPO / args.capture).resolve()
    if not capture.exists():
        raise SystemExit(f"capture not found: {capture}")

    print(f"Building mirror variants from {capture.relative_to(REPO)}")
    unchanged = build_unchanged(capture)
    build_republished(unchanged)


if __name__ == "__main__":
    main()
