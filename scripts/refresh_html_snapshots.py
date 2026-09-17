"""Refresh compact HTML snapshots from the approved Ameriabank product pages.

The snapshots retain the real DNN wrapper, topbar, and product-section markup but
omit scripts, media, the large global header, and empty layout sections. They are
test artifacts, not a mirror of the source website.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import httpx
from bs4 import BeautifulSoup
from bs4.element import Tag

from app.config import HttpSettings
from app.services.restricted_http import RestrictedHttpTransport

OUTPUT_DIR = Path("tests/fixtures/html/recorded")
MANIFEST_PATH = OUTPUT_DIR / "manifest.json"


@dataclass(frozen=True, slots=True)
class SnapshotTarget:
    filename: str
    url: str
    language: str
    expected_phrases: tuple[str, ...]


TARGETS = (
    SnapshotTarget(
        filename="consumer_en.html",
        url=("https://ameriabank.am/en/personal/loans/consumer-loans/consumer-loans"),
        language="en",
        expected_phrases=("Consumer loan", "Want to make a surprise gift"),
    ),
    SnapshotTarget(
        filename="consumer_hy.html",
        url=("https://ameriabank.am/personal/loans/consumer-loans/consumer-loans"),
        language="hy",
        expected_phrases=("Սպառողական վարկ", "Պայմաններ և սակագներ"),
    ),
    SnapshotTarget(
        filename="mortgage_en.html",
        url=("https://ameriabank.am/en/personal/loans/mortgage/secondary-market"),
        language="en",
        expected_phrases=(
            "Real estate loan for secondary market",
            "No loan service fees",
            "Property insurance by the Bank",
        ),
    ),
    SnapshotTarget(
        filename="mortgage_hy.html",
        url="https://ameriabank.am/personal/loans/mortgage/secondary-market",
        language="hy",
        expected_phrases=(
            "Հիփոթեքային վարկ",
            "Առանց վարկի սպասարկման վճարների",
            "Գույքի ապահովագրությունը բանկի կողմից",
        ),
    ),
)

_DROP_TAGS = (
    "script",
    "style",
    "noscript",
    "iframe",
    "svg",
    "canvas",
    "template",
    "input",
    "button",
    "img",
    "picture",
    "source",
    "video",
    "audio",
)
_SAFE_ATTRIBUTES = frozenset(
    {
        "aria-label",
        "charset",
        "class",
        "colspan",
        "href",
        "id",
        "lang",
        "name",
        "rel",
        "rowspan",
        "scope",
    }
)


def _clean_text(element: Tag) -> str:
    return " ".join(element.get_text(" ", strip=True).split())


def _copy_tag(element: Tag) -> Tag:
    copied = BeautifulSoup(str(element), "html.parser").find()
    if not isinstance(copied, Tag):
        raise RuntimeError("could not copy fixture element")
    return copied


def _sanitize_snapshot(content: bytes, target: SnapshotTarget) -> bytes:
    source = BeautifulSoup(content, "html.parser")
    source_root = source.select_one("#wsc_main_content")
    if not isinstance(source_root, Tag):
        raise RuntimeError(f"{target.url} no longer contains #wsc_main_content")

    snapshot = BeautifulSoup(
        "<!doctype html><html><head></head><body></body></html>", "html.parser"
    )
    html = snapshot.html
    head = snapshot.head
    body = snapshot.body
    if html is None or head is None or body is None:
        raise RuntimeError("could not construct snapshot document")
    html["lang"] = target.language

    title = snapshot.new_tag("title")
    title.string = (
        source.title.get_text(" ", strip=True) if source.title else target.url
    )
    head.append(title)
    canonical = snapshot.new_tag("link", rel="canonical", href=target.url)
    head.append(canonical)

    form = snapshot.new_tag("form", id="Form")
    body.append(form)

    topbar = source.select_one("#topbar")
    if isinstance(topbar, Tag):
        form.append(_copy_tag(topbar))

    root = snapshot.new_tag("div", id="wsc_main_content")
    form.append(root)
    for selector in ("#slider", "section"):
        for element in source_root.select(selector):
            if _clean_text(element):
                root.append(_copy_tag(element))

    for element in snapshot.find_all(_DROP_TAGS):
        element.decompose()
    for element in snapshot.find_all(True):
        if element.attrs is None:
            continue
        element.attrs = {
            key: value
            for key, value in element.attrs.items()
            if key in _SAFE_ATTRIBUTES
        }

    visible_text = " ".join(snapshot.get_text(" ", strip=True).split())
    for phrase in target.expected_phrases:
        if phrase not in visible_text:
            raise RuntimeError(f"expected phrase {phrase!r} missing from {target.url}")

    return snapshot.prettify(encoding="utf-8")


async def _refresh() -> None:
    settings = HttpSettings()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest: list[dict[str, object]] = []

    async with httpx.AsyncClient(follow_redirects=False) as client:
        transport = RestrictedHttpTransport(client, settings)
        for target in TARGETS:
            response = await transport.fetch(
                target.url,
                accepted_mime_types={"text/html"},
                accept_header="text/html,application/xhtml+xml;q=0.9",
                max_bytes=settings.max_html_bytes,
            )
            snapshot = _sanitize_snapshot(response.content, target)
            (OUTPUT_DIR / target.filename).write_bytes(snapshot)
            manifest.append(
                {
                    "filename": target.filename,
                    "source_url": response.source_url,
                    "final_url": response.final_url,
                    "language": target.language,
                    "expected_phrases": list(target.expected_phrases),
                    "captured_at": datetime.now(UTC).isoformat(),
                    "source_size_bytes": response.size_bytes,
                    "source_sha256": response.sha256,
                    "snapshot_size_bytes": len(snapshot),
                    "snapshot_sha256": hashlib.sha256(snapshot).hexdigest(),
                }
            )

    MANIFEST_PATH.write_text(
        json.dumps({"pages": manifest}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    asyncio.run(_refresh())
