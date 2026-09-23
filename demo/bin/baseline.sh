#!/usr/bin/env bash
# Capture or restore the demonstration baseline database.
#
# Filming mutates state: a run publishes snapshots, a review records a decision.
# A retake has to start from the same place as the first take, so a bad take is
# discarded rather than worked around. No row is ever edited by hand.
#
# The baseline holds the bank-sourced Overdraft snapshot. Clip 9 must cite the
# bank, so it is always filmed from a restored baseline, never after a mirror run
# has published a snapshot of its own.
set -euo pipefail
cd "$(dirname "$0")/../.."

DUMP="demo/baseline/tariff_monitor_baseline.dump"
mkdir -p demo/baseline

case "${1:-}" in
  capture)
    docker compose -f docker-compose.yml exec -T db \
      pg_dump -U tariff -d tariff_monitor --format=custom > "${DUMP}"
    printf '%s\n' "Captured $(du -h "${DUMP}" | cut -f1) to ${DUMP}"
    ;;
  restore)
    [[ -f "${DUMP}" ]] || { printf '%s\n' "no baseline at ${DUMP}" >&2; exit 1; }
    docker compose -f docker-compose.yml exec -T db \
      pg_restore -U tariff -d tariff_monitor --clean --if-exists --no-owner < "${DUMP}"
    printf '%s\n' "Restored ${DUMP}"
    ;;
  show)
    docker compose -f docker-compose.yml exec -T db psql -U tariff -d tariff_monitor -c "
      select 'runs' kind, status::text state, count(*) from monitoring_runs group by 2
      union all select 'snapshots', status, count(*) from tariff_snapshots group by 2
      union all select 'reviews', status, count(*) from human_reviews group by 2
      union all select 'changes', 'all', count(*) from tariff_changes
      order by 1, 2;"
    ;;
  *)
    printf '%s\n' "Usage: demo/bin/baseline.sh capture|restore|show" >&2
    exit 2
    ;;
esac
