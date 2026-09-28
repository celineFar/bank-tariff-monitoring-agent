# ruff: noqa: RUF001 -- the Armenian comma (U+055D) is page text, not a typo.
"""Build the scanned sample PDFs and their ground truth.

Each sample is rendered, then made to look like a flatbed scan (grey paper,
skew, grain, an edge shadow, JPEG compression), and saved with no text layer.
Next to each PDF goes `<name>.truth.json`: every printed line, and every tariff
row as a label with its values in column order. `score.py` measures the OCR and
Gemini transcriptions against it.

- `loan-summary`: two pages, a key-value list and one ruled table.
- `mortgage-tariffs`: harder. A table with a two-level header, merged cells and
  group rows, footnote markers, a two-column section with a stamp over it, and a
  landscape fee table scanned sideways.

The values are synthetic demonstration data, not observed Ameriabank tariffs.
The PDFs are committed; re-run only when the samples change:

    ./run.sh make_samples.py
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent
SAMPLES = HERE / "samples"

DPI = 200
PORTRAIT = (1654, 2339)  # A4 at 200 dpi
LANDSCAPE = (2339, 1654)
REGULAR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
INK = 20
RULE = 70


def font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(BOLD if bold else REGULAR, size)


@dataclass
class Page:
    """A page being drawn, and the truth it will carry."""

    number: int
    size: tuple[int, int] = PORTRAIT
    lines: list[str] = field(default_factory=list)
    rows: list[dict[str, object]] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.image = Image.new("L", self.size, color=255)
        self.draw = ImageDraw.Draw(self.image)

    def text(self, xy: tuple[int, int], value: str, size: int, *, bold: bool = False):
        self.draw.text(xy, value, fill=INK, font=font(size, bold=bold))

    def line(self, value: str) -> None:
        self.lines.append(value)

    def row(self, label: str, *values: str) -> None:
        """A tariff row: its label, and the numbers printed after it, in order."""
        self.rows.append({"page": self.number, "label": label, "values": list(values)})

    def rule(self, x0: int, y0: int, x1: int, y1: int, width: int = 2) -> None:
        self.draw.line((x0, y0, x1, y1), fill=RULE, width=width)


# --------------------------------------------------------------------------
# loan-summary


def loan_summary() -> list[Page]:
    first = Page(1)
    y = 200
    first.rule(150, 170, PORTRAIT[0] - 150, 170, 3)
    entries = (
        ("title", "ՍՊԱՌՈՂԱԿԱՆ ՎԱՐԿ", None, ()),
        ("subtitle", "Տեղեկատվական ամփոփագիր", None, ()),
        ("gap", "", None, ()),
        ("line", "Արժույթ: AMD", None, ()),
        ("line", "Ժամկետ: 12-60 ամիս", "Ժամկետ", ("12", "60")),
        (
            "line",
            "Գումար: 300,000 - 10,000,000 AMD",
            "Գումար",
            ("300,000", "10,000,000"),
        ),
        (
            "line",
            "Անվանական տոկոսադրույք: 13.5%",
            "Անվանական տոկոսադրույք",
            ("13.5",),
        ),
        ("line", "Փաստացի տոկոսադրույք: 14.2%", "Փաստացի տոկոսադրույք", ("14.2",)),
        (
            "line",
            "Հայտի ուսումնասիրության վճար: 0 AMD",
            "Հայտի ուսումնասիրության վճար",
            ("0",),
        ),
        ("line", "Տրամադրման վճար: 1%", "Տրամադրման վճար", ("1",)),
        ("gap", "", None, ()),
        ("line", "Մարման եղանակ: անուիտետային", None, ()),
        ("line", "Գրավ: չի պահանջվում", None, ()),
    )
    sizes = {
        "title": (60, True, 105),
        "subtitle": (44, False, 95),
        "line": (42, False, 78),
    }
    for kind, value, label, values in entries:
        if kind == "gap":
            y += 50
            continue
        size, bold, advance = sizes[kind]
        first.text((160, y), value, size, bold=bold)
        first.line(value)
        if label:
            first.row(label, *values)
        y += advance
    first.rule(150, y + 40, PORTRAIT[0] - 150, y + 40, 3)

    second = Page(2)
    second.text((160, 200), "Սակագներ և վճարներ", 52, bold=True)
    second.line("Սակագներ և վճարներ")
    table = (
        ("Ծառայություն", "Վճար", None),
        ("Հաշվի սպասարկում", "0 AMD", "0"),
        ("Վաղաժամկետ մարում", "0%", "0"),
        ("Ուշացման տույժ", "0.13% օրական", "0.13"),
        ("Քաղվածքի տրամադրում", "1,000 AMD", "1,000"),
    )
    left, right, split, top, height = 160, PORTRAIT[0] - 160, 1000, 340, 95
    for index, (service, fee, number) in enumerate(table):
        y = top + index * height
        second.text((left + 25, y + 22), service, 40, bold=index == 0)
        second.text((split + 25, y + 22), fee, 40, bold=index == 0)
        second.line(f"{service} {fee}")
        if number is not None:
            second.row(service, number)
    bottom = top + len(table) * height
    for index in range(len(table) + 1):
        second.rule(left, top + index * height, right, top + index * height)
    for x in (left, split, right):
        second.rule(x, top, x, bottom)
    y = bottom + 90
    for value in (
        "Սակագները գործում են 01.09.2026 թվականից:",
        "SAMPLE - synthetic values for demonstration only",
    ):
        second.text((160, y), value, 40)
        second.line(value)
        y += 75
    second.row("Սակագները գործում են", "01.09.2026")
    return [scan(first, skew=0.7), scan(second, skew=-0.5)]


# --------------------------------------------------------------------------
# mortgage-tariffs


def mortgage_tariffs() -> list[Page]:
    return [scan(_mortgage_rates(), skew=1.2), _mortgage_fees()]


def _mortgage_rates() -> Page:
    page = Page(1)
    page.text((120, 150), "ՀԻՓՈԹԵՔԱՅԻՆ ՎԱՐԿ", 54, bold=True)
    page.line("ՀԻՓՈԹԵՔԱՅԻՆ ՎԱՐԿ")
    subtitle = "Սակագներ և պայմաններ / Mortgage loan tariffs and conditions"
    page.text((120, 230), subtitle, 32)
    page.line(subtitle)

    # A two-level header: "Rate" spans the AMD and USD columns, "Term" and
    # "Down payment" span both header rows. Group rows span the whole table.
    columns = (120, 600, 900, 1200, 1534)
    top, height = 330, 80
    page.rule(columns[0], top, columns[-1], top)
    page.text((columns[0] + 20, top + 60), "Ժամկետ", 34, bold=True)
    page.text((columns[1] + 90, top + 20), "Տոկոսադրույք*", 34, bold=True)
    page.text((columns[3] + 25, top + 60), "Կանխավճար**", 34, bold=True)
    page.rule(columns[1], top + height, columns[3], top + height)
    page.text((columns[1] + 105, top + height + 20), "AMD", 34, bold=True)
    page.text((columns[2] + 105, top + height + 20), "USD", 34, bold=True)
    page.line("Ժամկետ Տոկոսադրույք* Կանխավճար**")
    page.line("AMD USD")
    for x in (columns[1], columns[3]):
        page.rule(x, top, x, top + 2 * height)
    page.rule(columns[2], top + height, columns[2], top + 2 * height)
    y = top + 2 * height
    page.rule(columns[0], y, columns[-1], y)
    body = (
        ("Առաջնային շուկա", None),
        ("մինչև 10 տարի", ("11.5%", "7.9%", "20%")),
        ("10-20 տարի", ("12.0%", "8.4%", "25%")),
        ("Երկրորդային շուկա", None),
        ("մինչև 7 տարի", ("12.5%", "8.9%", "30%")),
        ("7-15 տարի", ("13.0%", "9.4%", "30%")),
    )
    for label, cells in body:
        if cells is None:
            page.text((columns[0] + 20, y + 20), label, 32, bold=True)
            page.line(label)
        else:
            page.text((columns[0] + 20, y + 20), label, 32)
            for column, value in enumerate(cells, start=1):
                page.text((columns[column] + 90, y + 20), value, 32)
            page.line(" ".join((label, *cells)))
            page.row(label, *(value.rstrip("%") for value in cells))
            # Group rows span the table; only value rows are divided.
            for x in columns[1:-1]:
                page.rule(x, y, x, y + height)
        y += height
        page.rule(columns[0], y, columns[-1], y)
    page.rule(columns[0], top, columns[0], y)
    page.rule(columns[-1], top, columns[-1], y)

    y += 30
    for value, label, numbers in (
        (
            "* Փաստացի տոկոսադրույքը՝ 12.9%-ից 14.8%:",
            "Փաստացի տոկոսադրույքը",
            ("12.9", "14.8"),
        ),
        (
            "** Պետական ծրագրերի դեպքում՝ 10%:",
            "Պետական ծրագրերի դեպքում",
            ("10",),
        ),
    ):
        page.text((120, y), value, 27)
        page.line(value)
        page.row(label, *numbers)
        y += 45

    y += 60
    page.text((120, y), "Պայմաններ", 40, bold=True)
    page.line("Պայմաններ")
    y += 80
    left = (
        ("Գումար՝ 5,000,000-150,000,000 AMD", "Գումար", ("5,000,000", "150,000,000")),
        ("Առավելագույն ժամկետ՝ 20 տարի", "Առավելագույն ժամկետ", ("20",)),
        ("Տրամադրման վճար՝ 0.5%", "Տրամադրման վճար", ("0.5",)),
    )
    right = (
        ("Ապահովագրություն՝ 0.12% տարեկան", "Ապահովագրություն", ("0.12",)),
        ("Գնահատման վճար՝ 35,000 AMD", "Գնահատման վճար", ("35,000",)),
        ("Վաղաժամկետ մարում՝ 0%", "Վաղաժամկետ մարում", ("0",)),
    )
    for x, column in ((120, left), (880, right)):
        for index, (value, label, numbers) in enumerate(column):
            page.text((x, y + index * 62), value, 31)
            page.line(value)
            page.row(label, *numbers)
    stamp(page, center=(1330, y + 130), radius=125)
    return page


def _mortgage_fees() -> Page:
    """A landscape table, fed through the scanner sideways."""
    page = Page(2, size=LANDSCAPE)
    page.text((160, 150), "Լրացուցիչ վճարներ / Additional fees", 46, bold=True)
    page.line("Լրացուցիչ վճարներ / Additional fees")
    table = (
        ("Ծառայություն", "Վճար", "Պարբերականություն", None),
        ("Վարկային հաշվի սպասարկում", "2,000 AMD", "ամսական", "2,000"),
        ("Անշարժ գույքի գնահատում", "35,000 AMD", "միանվագ", "35,000"),
        ("Նոտարական վավերացում", "15,000 AMD", "միանվագ", "15,000"),
        ("Ապահովագրություն", "0.12%", "տարեկան", "0.12"),
        ("Պայմանների փոփոխություն", "10,000 AMD", "յուրաքանչյուր դիմում", "10,000"),
    )
    columns, top, height = (160, 1060, 1500, 2180), 280, 105
    for index, (service, fee, period, number) in enumerate(table):
        y = top + index * height + 28
        for column, value in enumerate((service, fee, period)):
            page.text((columns[column] + 25, y), value, 40, bold=index == 0)
        page.line(f"{service} {fee} {period}")
        if number is not None:
            page.row(service, number)
    bottom = top + len(table) * height
    for index in range(len(table) + 1):
        page.rule(columns[0], top + index * height, columns[-1], top + index * height)
    for x in columns:
        page.rule(x, top, x, bottom)
    footer = "Գործում է 01.09.2026 թվականից:"
    page.text((160, bottom + 70), footer, 38)
    page.line(footer)
    page.row("Գործում է", "01.09.2026")

    # Turned before scanning: the scanner sees a portrait sheet lying sideways.
    page.image = page.image.rotate(90, expand=True)
    return scan(page, skew=0.4)


def stamp(page: Page, *, center: tuple[int, int], radius: int) -> None:
    """A round ink stamp, pressed over whatever is printed there."""
    size = radius * 2 + 20
    mark = Image.new("L", (size, size), color=255)
    draw = ImageDraw.Draw(mark)
    c = size // 2
    draw.ellipse((c - radius, c - radius, c + radius, c + radius), outline=110, width=7)
    inner = radius - 22
    draw.ellipse((c - inner, c - inner, c + inner, c + inner), outline=110, width=3)
    draw.text((c, c - 18), "ՆՄՈՒՇ", fill=110, font=font(44, bold=True), anchor="mm")
    draw.text((c, c + 32), "SAMPLE", fill=110, font=font(30, bold=True), anchor="mm")
    mark = mark.rotate(-18, resample=Image.Resampling.BICUBIC, fillcolor=255)
    box = (center[0] - c, center[1] - c)
    region = page.image.crop((*box, box[0] + size, box[1] + size))
    page.image.paste(ImageChops.darker(region, mark), box)


# --------------------------------------------------------------------------
# scanning and output


def scan(page: Page, *, skew: float, seed: int = 0) -> Page:
    """Make a clean render look like a flatbed scan, deterministically."""
    image = page.image.rotate(skew, resample=Image.Resampling.BICUBIC, fillcolor=255)
    image = image.filter(ImageFilter.GaussianBlur(radius=0.8))
    # Paper is never white on a scan, and the sensor adds grain.
    image = image.point(lambda v: v * 236 // 255)
    rng = random.Random(f"{seed}:{page.number}:{page.size}")
    noise = Image.frombytes("L", image.size, rng.randbytes(image.width * image.height))
    grain = noise.point(lambda v: 128 + (v - 128) // 8)
    image = ImageChops.add(image, grain, offset=-128)
    # A shadow along the binding edge, as a flatbed lid leaves.
    shadow = ImageDraw.Draw(image)
    for offset in range(30):
        shadow.line((offset, 0, offset, image.height), fill=140 + offset * 3)
    page.image = image
    return page


def save(name: str, pages: list[Page]) -> None:
    SAMPLES.mkdir(exist_ok=True)
    pdf = SAMPLES / f"{name}.pdf"
    # Each page is embedded as a JPEG image with no text layer: what a scanner
    # produces, and what the input probe must classify image_only.
    first, *rest = (page.image for page in pages)
    first.save(
        pdf, "PDF", save_all=True, append_images=rest, resolution=DPI, quality=80
    )
    truth = {
        "sample": pdf.name,
        "pages": [{"page": page.number, "lines": page.lines} for page in pages],
        "rows": [row for page in pages for row in page.rows],
    }
    path = SAMPLES / f"{name}.truth.json"
    path.write_text(json.dumps(truth, ensure_ascii=False, indent=2) + "\n", "utf-8")
    print(
        f"Wrote samples/{pdf.name} ({pdf.stat().st_size:,} bytes, {len(pages)} pages) "
        f"and samples/{path.name} ({len(truth['rows'])} tariff rows)"
    )


def main() -> None:
    save("loan-summary", loan_summary())
    save("mortgage-tariffs", mortgage_tariffs())


if __name__ == "__main__":
    main()
