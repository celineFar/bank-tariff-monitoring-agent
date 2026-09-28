#!/usr/bin/env bash
# Run a script from this folder inside the project's existing `worker` image,
# which already carries tesseract (hye + eng) and the `ocr` extra.
#
#   ./run.sh                      # OCR fallback on every sample (Gemini made to fail)
#   ./run.sh --engine gemini      # the real Gemini baseline (spends credits)
#   ./run.sh score.py             # score both against the ground truth
#   ./run.sh make_samples.py      # re-render the scanned samples
#
# Only this folder is mounted, so the application code that runs is the code
# baked into the image. Rebuild it after changing app/: docker compose build worker
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo="$(cd "$here/../.." && pwd)"
script="ocr_fallback_demo.py"
if [[ "${1:-}" == *.py ]]; then
  script="$1"
  shift
fi
mount="/code/Presentation-demonstrations/OCR-fallback"

# OCR_* set in your shell override .env, e.g. OCR_MIN_CONFIDENCE=80 ./run.sh
ocr_env=()
for name in $(compgen -e | grep '^OCR_' || true); do
  ocr_env+=(-e "$name=${!name}")
done

cd "$repo"
# --no-deps: the demonstration needs no database or API.
# --user: generated files belong to you, not to root.
exec docker compose run --rm --no-deps -T \
  --user "$(id -u):$(id -g)" \
  "${ocr_env[@]}" \
  -e HOME=/tmp \
  -e PYTHONPATH=/code \
  -e PYTHONDONTWRITEBYTECODE=1 \
  -e PYTHONWARNINGS=ignore::UserWarning \
  -e LOG_FILE= \
  -v "$here:$mount" \
  -w /code \
  worker /code/.venv/bin/python "$mount/$script" "$@"
