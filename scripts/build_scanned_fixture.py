"""Render Armenian tariff text to a raster-only PDF page.

The deliverable 11 demonstration needs a page that genuinely has no text layer
but does carry readable glyphs, so an OCR engine has something to recover. The
previous synthetic fixture was a grayscale gradient: it proved the probe detects
a missing text layer, but no engine could ever read it.

The generated PDF is committed to `tests/fixtures/pdfs/`, so a clean clone can
run the demonstration without re-rendering. Re-run this script only when the
fixture text changes:

    uv run python scripts/build_scanned_fixture.py

Requires the optional `ocr` extra (Pillow) and a font with Armenian coverage.
"""

from __future__ import annotations

import argparse
import sys
import zlib
from io import BytesIO
from pathlib import Path

DEFAULT_OUTPUT = Path("tests/fixtures/pdfs/scanned_armenian_sample.pdf")

# Deliberately shaped like an «տեղեկատվական ամփոփագիր» extract. The values are
# synthetic test data, not observed Ameriabank tariffs.
LINES: tuple[str, ...] = (
    "ՍՊԱՌՈՂԱԿԱՆ ՎԱՐԿ",
    "Տեղեկատվական ամփոփագիր",
    "",
    "Արժույթ: AMD",
    "Ժամկետ: 12-60 ամիս",
    "Գումար: 300,000 - 10,000,000 AMD",
    "Անվանական տոկոսադրույք: 13.5%",
    "Փաստացի տոկոսադրույք: 14.2%",
    "Հայտի ուսումնասիրության վճար: 0 AMD",
    "Տրամադրման վճար: 1%",
)

FONT_CANDIDATES: tuple[str, ...] = (
    "C:/Windows/Fonts/sylfaen.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansArmenian-Regular.ttf",
    "/Library/Fonts/Arial Unicode.ttf",
)


def _load_font(size: int):
    from PIL import ImageFont

    for candidate in FONT_CANDIDATES:
        if Path(candidate).exists():
            try:
                return ImageFont.truetype(candidate, size), candidate
            except OSError:
                continue
    raise SystemExit(
        "No font with Armenian coverage was found. Install one of:\n  "
        + "\n  ".join(FONT_CANDIDATES)
    )


def render_page_image(width: int = 1240, height: int = 1754, dpi: int = 150):
    """Render the tariff extract at roughly A4 @ 150 dpi, as a scan would be."""
    from PIL import Image, ImageDraw

    font, font_path = _load_font(34)
    title_font, _ = _load_font(46)
    image = Image.new("L", (width, height), color=255)
    draw = ImageDraw.Draw(image)

    y = 140
    for index, line in enumerate(LINES):
        if not line:
            y += 40
            continue
        use = title_font if index == 0 else font
        draw.text((120, y), line, fill=25, font=use)
        y += 78 if index == 0 else 62

    # A faint scan artifact keeps the fixture honest about what OCR receives.
    draw.line((110, 120, width - 110, 120), fill=160, width=2)
    draw.line((110, y + 30, width - 110, y + 30), fill=160, width=2)
    return image, font_path, dpi


def image_to_pdf(image, dpi: int) -> bytes:
    """Wrap the raster in a minimal PDF with no text layer at all."""
    buffer = BytesIO()
    image.save(buffer, format="PNG")

    raw = image.tobytes()
    stream = zlib.compress(raw, 9)
    width, height = image.size
    # 72 PDF points per inch.
    page_width = width * 72.0 / dpi
    page_height = height * 72.0 / dpi

    objects: list[bytes] = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            f"<< /Type /Page /Parent 2 0 R /MediaBox "
            f"[0 0 {page_width:.2f} {page_height:.2f}] "
            f"/Resources << /XObject << /Im0 4 0 R >> >> /Contents 5 0 R >>"
        ).encode("latin-1"),
        (
            f"<< /Type /XObject /Subtype /Image /Width {width} /Height {height} "
            f"/ColorSpace /DeviceGray /BitsPerComponent 8 /Filter /FlateDecode "
            f"/Length {len(stream)} >>\nstream\n"
        ).encode("latin-1")
        + stream
        + b"\nendstream",
    ]
    content = (f"q {page_width:.2f} 0 0 {page_height:.2f} 0 0 cm /Im0 Do Q").encode(
        "latin-1"
    )
    objects.append(
        f"<< /Length {len(content)} >>\nstream\n".encode("latin-1")
        + content
        + b"\nendstream"
    )

    out = bytearray(b"%PDF-1.4\n")
    offsets: list[int] = []
    for index, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{index} 0 obj\n".encode("latin-1") + body + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode("latin-1")
    for offset in offsets:
        out += f"{offset:010d} 00000 n \n".encode("latin-1")
    out += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref}\n%%EOF\n"
    ).encode("latin-1")
    return bytes(out)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    image, font_path, dpi = render_page_image()
    pdf = image_to_pdf(image, dpi)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(pdf)

    from app.services.pdf_input_probe import probe_pdf_input

    probe = probe_pdf_input(pdf)
    print(f"Rendered with {font_path}")
    print(f"Wrote {args.output} ({len(pdf):,} bytes)")
    print(
        f"Probe: {probe.page_count} page(s), mode={probe.document_mode.value}, "
        f"native text characters={probe.pages[0].native_text_characters}"
    )
    if probe.document_mode.value != "image_only":
        print("ERROR: fixture is not image_only", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
