#!/usr/bin/env python3
"""Build the `oversized` mirror variant for the source.size_rejected leg.

The page is the same captured Overdraft page with readable filler appended until
it passes MAX_DOWNLOAD_BYTES (26,214,400). The filler is ordinary prose rather
than a highly compressible pattern, so the response is genuinely large on the
wire and the retriever's cut is not an artefact of decompression.

app/services/html_retriever.py stops reading and raises PAGE_TOO_LARGE, which
app/services/failure_mapping.py maps to source.size_rejected. A linked document
that is too large would only be skipped with a warning
(app/services/acquisition.py:264), so the page itself has to be the oversized
one for the failure to reach the chat.

The output is generated, large, and git-ignored.
"""

from __future__ import annotations

import os
import random
import string
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
MIRROR = REPO / "demo" / "mirror"
LIMIT = int(os.environ.get("MAX_DOWNLOAD_BYTES", 26_214_400))
TARGET = int(LIMIT * 1.2)


def main() -> None:
    source = MIRROR / "unchanged" / "overdraft" / "index.html"
    if not source.exists():
        raise SystemExit("run demo/bin/build-variants.py first")

    out = MIRROR / "oversized" / "overdraft"
    out.mkdir(parents=True, exist_ok=True)
    page = out / "index.html"

    html = source.read_text(encoding="utf-8")
    words = [
        "".join(random.choices(string.ascii_lowercase, k=random.randint(3, 11)))
        for _ in range(4000)
    ]

    with page.open("w", encoding="utf-8") as handle:
        handle.write(html)
        handle.write('\n<div id="oversize-filler" hidden>\n')
        written = len(html.encode("utf-8"))
        while written < TARGET:
            chunk = "<p>" + " ".join(random.choices(words, k=400)) + "</p>\n"
            handle.write(chunk)
            written += len(chunk.encode("utf-8"))
        handle.write("</div>\n")

    size = page.stat().st_size
    print(f"oversized page: {size:,} bytes (limit {LIMIT:,}, ratio {size / LIMIT:.2f}x)")
    if size <= LIMIT:
        raise SystemExit("the generated page does not exceed the limit")


if __name__ == "__main__":
    main()
