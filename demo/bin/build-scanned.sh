#!/usr/bin/env bash
# Build the `scanned` mirror variant: the same page, linking one tariff document
# that has no text layer.
#
# The document is a real Ameriabank leaflet, rendered to page images and rewrapped
# as an image-only PDF. Nothing is retyped, so what OCR recovers on camera is the
# bank's own wording; only the text layer is gone, which is what a scanned
# publication looks like to the pipeline.
set -euo pipefail
cd "$(dirname "$0")/../.."

SOURCE_PDF="${1:-demo/mirror/unchanged/docs/Overdraft_unsecured_eng.pdf}"
PAGES="${PAGES:-2}"
DPI="${DPI:-200}"
export COMPOSE_FILE=docker-compose.yml:docker-compose.demo.yml

[[ -f "${SOURCE_PDF}" ]] || { printf '%s\n' "missing ${SOURCE_PDF}; run build-variants.py first" >&2; exit 1; }

rm -rf demo/mirror/scanned
cp -a demo/mirror/unchanged demo/mirror/scanned

docker compose cp "${SOURCE_PDF}" api:/tmp/source.pdf
docker compose exec -T -e PAGES="${PAGES}" -e DPI="${DPI}" api uv run python - <<'PY'
import os
import pypdfium2 as pdfium
from PIL import Image

pages = int(os.environ["PAGES"])
dpi = int(os.environ["DPI"])
document = pdfium.PdfDocument("/tmp/source.pdf")
scale = dpi / 72

images = []
for index in range(min(pages, len(document))):
    bitmap = document[index].render(scale=scale)
    images.append(bitmap.to_pil().convert("RGB"))

# Saved as images only: no text layer, so the input probe must classify this
# image_only and the OCR fallback is the only way to read it.
images[0].save(
    "/tmp/scanned.pdf", "PDF", resolution=float(dpi), save_all=True,
    append_images=images[1:],
)
print(f"rendered {len(images)} page(s) at {dpi} dpi")
PY

docker compose cp api:/tmp/scanned.pdf demo/mirror/scanned/docs/Overdraft_unsecured_scanned_eng.pdf

python3 - <<'PY'
import pathlib, re
page = pathlib.Path("demo/mirror/scanned/overdraft/index.html")
html = page.read_text(encoding="utf-8")
old = "/docs/Overdraft_unsecured_eng.pdf"
new = "/docs/Overdraft_unsecured_scanned_eng.pdf"
count = html.count(f'"{old}"')
if not count:
    raise SystemExit(f"link {old} not found in the scanned variant")
html = html.replace(f'"{old}"', f'"{new}"')
page.write_text(html, encoding="utf-8")
print(f"scanned: repointed {count} link(s) to the image-only document")
PY

rm -f demo/mirror/scanned/docs/Overdraft_unsecured_eng.pdf
ls -la demo/mirror/scanned/docs/Overdraft_unsecured_scanned_eng.pdf
