#!/usr/bin/env bash
# Point the demonstration mirror at one prepared variant and restart it.
#
# The seed URL never changes between shots; only what the mirror serves does.
# Usage: demo/bin/mirror-variant.sh unchanged|republished|scanned|oversized
set -euo pipefail
cd "$(dirname "$0")/../.."

VARIANT="${1:-}"
AVAILABLE="$(cd demo/mirror && ls -d */ 2>/dev/null | tr -d '/' | grep -v '^_' | tr '\n' ' ')"

if [[ -z "${VARIANT}" || ! -d "demo/mirror/${VARIANT}" ]]; then
  printf '%s\n' "Usage: demo/bin/mirror-variant.sh <variant>" >&2
  printf '%s\n' "Available: ${AVAILABLE}" >&2
  exit 2
fi

export COMPOSE_FILE=docker-compose.yml:docker-compose.demo.yml
export DEMO_MIRROR_ROOT="./demo/mirror/${VARIANT}"

docker compose up -d --force-recreate mirror >/dev/null
printf '%s\n' "Mirror now serving the '${VARIANT}' variant at https://tariff-mirror.demo/overdraft"
