"""Deliverable 11 — digital PDF path and the scanned-page fallback."""

from __future__ import annotations

from pathlib import Path

from app.domain.pdf_extraction import PdfInputMode
from app.services.pdf_input_probe import probe_pdf_input
from scripts.demonstrations import ScenarioResult

SAMPLES = Path("data/extraction-review-cases")


def image_only_pdf(width: int = 64, height: int = 64) -> bytes:
    """Build a one-page PDF whose only content is a raster image.

    The assignment allows a rendered or scanned sample page when the live bank
    documents happen to be machine readable, which the samples in
    `data/extraction-review-cases` are.
    """
    rows = [
        "".join(f"{(x * 4 + y * 3) % 256:02x}" for x in range(width))
        for y in range(height)
    ]
    data = "".join(rows) + ">"
    objects = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        "/Resources << /XObject << /Im0 4 0 R >> >> /Contents 5 0 R >>",
        f"<< /Type /XObject /Subtype /Image /Width {width} /Height {height} "
        f"/ColorSpace /DeviceGray /BitsPerComponent 8 /Filter /ASCIIHexDecode "
        f"/Length {len(data)} >>\nstream\n{data}\nendstream",
    ]
    stream = "q 612 0 0 792 0 0 cm /Im0 Do Q"
    objects.append(f"<< /Length {len(stream)} >>\nstream\n{stream}\nendstream")

    out = bytearray(b"%PDF-1.4\n")
    offsets: list[int] = []
    for index, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{index} 0 obj\n{body}\nendobj\n".encode("latin-1")
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    for offset in offsets:
        out += f"{offset:010d} 00000 n \n".encode()
    out += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref}\n%%EOF\n"
    ).encode()
    return bytes(out)


async def run() -> ScenarioResult:
    result = ScenarioResult(
        deliverable="Deliverable 11",
        title="Document processing: digital PDF path and scanned-page fallback",
    )

    digital_samples = sorted(SAMPLES.glob("*/source.pdf"))
    probes = {}
    for path in digital_samples:
        probes[path.parent.name] = probe_pdf_input(path.read_bytes())
        probe = probes[path.parent.name]
        result.step(
            f"Probed real sample {path.parent.name}: {probe.page_count} page(s), "
            f"mode={probe.document_mode.value}, "
            f"native text on page 1 = {probe.pages[0].native_text_characters} chars, "
            f"images on page 1 = {probe.pages[0].images_detected}."
        )

    scanned = image_only_pdf()
    scanned_probe = probe_pdf_input(scanned)
    result.step(
        f"Built a rendered scanned page ({len(scanned)} bytes) with no text layer "
        "and probed it with the same deterministic prober."
    )
    result.step(
        f"    scanned page: mode={scanned_probe.document_mode.value}, "
        f"native text = {scanned_probe.pages[0].native_text_characters} chars, "
        f"images detected = {scanned_probe.pages[0].images_detected}."
    )
    result.step(
        "The probe result is what routes the document: a page with no text layer "
        "cannot be parsed directly and is transcribed from the page image instead."
    )

    machine_readable = [
        name
        for name, probe in probes.items()
        if probe.document_mode is PdfInputMode.MACHINE_READABLE
    ]
    mixed = [
        name
        for name, probe in probes.items()
        if probe.document_mode is PdfInputMode.MIXED
    ]

    result.check(
        "real samples are available",
        "at least one real bank PDF is probed, not only a synthetic one",
        bool(probes),
        f"{len(probes)} sample PDF(s) under {SAMPLES}",
    )
    result.check(
        "digital PDFs take the direct path",
        "a PDF with a text layer is classified machine_readable or mixed",
        bool(machine_readable or mixed),
        f"machine_readable={machine_readable}, mixed={mixed}",
    )
    result.check(
        "scanned page is detected",
        "a page with no text layer is classified image_only, not machine_readable",
        scanned_probe.document_mode is PdfInputMode.IMAGE_ONLY,
        f"mode={scanned_probe.document_mode.value}",
    )
    result.check(
        "no text is invented for a scanned page",
        "the prober reports zero native characters rather than guessing",
        scanned_probe.pages[0].native_text_characters == 0
        and scanned_probe.pages[0].images_detected,
        f"chars={scanned_probe.pages[0].native_text_characters}, "
        f"images={scanned_probe.pages[0].images_detected}",
    )
    result.note(
        "This project has no tesseract OCR stage. Scanned pages are transcribed "
        "by Gemini's multimodal PDF reading, which is the fallback the probe "
        "routes to. The OCR_* variables in .env are dead configuration that no "
        "code reads."
    )
    result.note(
        "Run `uv run python scripts/demonstrate_pdf_extraction.py <case> "
        "--execute-llm` to see the actual transcription; that spends credits."
    )
    return result
