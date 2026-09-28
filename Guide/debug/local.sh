#!/usr/bin/env bash
# Run any command against the Docker Postgres from the host, with no image rebuild.
#   Guide/debug/local.sh python app/cli_entry.py --session x --verbose
#   Guide/debug/local.sh uvicorn app.fast_api_app:app --port 8090 --reload
#   Guide/debug/local.sh python -m app.worker        (stop the container worker first)
# Your edits under app/ apply on the next start. Only the db container has to be running.
set -euo pipefail
cd "$(dirname "$0")/../.."

# The host port Docker published for Postgres (5434 by default, 5435 with docker-compose.local.yml).
db_port="$(docker compose port db 5432 | cut -d: -f2)"
db_url="postgresql+asyncpg://tariff:tariff@localhost:${db_port}/tariff_monitor"

# logs/ and artifacts/ are root-owned (the containers created them), so local runs
# write to local-run/logs/ and local-run/audit/ instead. The folder ignores itself in git.
mkdir -p local-run/logs local-run/audit
[ -f local-run/.gitignore ] || echo '*' > local-run/.gitignore

export DATABASE_URL="$db_url"
export SESSION_SERVICE_URI="$db_url"
export LOG_FILE="${LOG_FILE:-$PWD/local-run/logs/local.log}"
export PIPELINE_AUDIT_DIR="${PIPELINE_AUDIT_DIR:-$PWD/local-run/audit}"

# Variables already set in the shell win over .env, so the overrides above
# (and anything you prefix, e.g. HITL_LARGE_RATE_CHANGE_PERCENTAGE_POINTS=1) take effect.
exec uv run --env-file .env "$@"
