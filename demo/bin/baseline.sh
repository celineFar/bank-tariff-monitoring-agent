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
#
# Restore resets monitoring and chat state only; the model caches and the spend
# ledger survive it. See the restore branch for why.
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
    # Reset monitoring and chat state only. Two kinds of table are left alone:
    #
    # * the caches, because every entry was paid for in model calls, and wiping
    #   them would make each retake re-pay the full extraction; and
    # * the spend ledger, because it is an audit record of what was spent, and a
    #   restore that rolled it back would hide the very spend it exists to show.
    #
    # State is deleted rather than truncated on purpose: the ledger references
    # monitoring_runs ON DELETE SET NULL, so a delete keeps every spend row and
    # only empties its run link, where TRUNCATE ... CASCADE would erase it.
    STATE_TABLES=(fact_evidence retrieval_units tariff_facts offering_profiles
      knowledge_chunks source_manifests human_reviews tariff_changes audit_events
      knowledge_documents tariff_snapshots offering_executions monitoring_runs
      acquisition_snapshots events sessions app_states user_states)
    SCRATCH=tariff_monitor_baseline_scratch
    db() { docker compose -f docker-compose.yml exec -T db "$@"; }

    db dropdb -U tariff --if-exists "${SCRATCH}"
    db createdb -U tariff "${SCRATCH}"
    db pg_restore -U tariff -d "${SCRATCH}" --no-owner < "${DUMP}" 2>/dev/null || true

    {
      printf '%s\n' "BEGIN;"
      for table in "${STATE_TABLES[@]}"; do printf 'DELETE FROM %s;\n' "${table}"; done
      printf '%s\n' "COMMIT;"
    } | db psql -q -v ON_ERROR_STOP=1 -U tariff -d tariff_monitor

    tables=(); for table in "${STATE_TABLES[@]}"; do tables+=(-t "${table}"); done
    db pg_dump -U tariff --data-only --disable-triggers "${tables[@]}" "${SCRATCH}" \
      | db psql -q -v ON_ERROR_STOP=1 -U tariff -d tariff_monitor >/dev/null

    db dropdb -U tariff "${SCRATCH}"
    printf '%s\n' "Restored monitoring and chat state from ${DUMP}; caches and the spend ledger kept."
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
