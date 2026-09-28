#!/usr/bin/env bash
# Trigger one monitoring run over the HTTP API and report how it ended.
#
# For dry runs and for preparing state between takes. It skips the chat agent,
# which is where most of the model spend goes (every chat turn re-sends the
# durable session), so a run costs only what the pipeline itself calls.
# Anything that has to be seen in the chat is still filmed through ./tariff-chat.
#
# Usage: demo/bin/run-offering.sh <product> <offering_id>
#        demo/bin/run-offering.sh consumer_loan overdraft
set -euo pipefail
cd "$(dirname "$0")/../.."

PRODUCT="${1:?product, e.g. consumer_loan}"
OFFERING="${2:?offering_id, e.g. overdraft}"
API="${API:-http://localhost:8080/api/v1}"
psql() { docker compose -f docker-compose.yml exec -T db psql -U tariff -d tariff_monitor -t -A "$@"; }

run_id="$(curl -sf -X POST "${API}/runs" \
  -H 'Content-Type: application/json' \
  -H "Idempotency-Key: demo-$(date +%s%N)" \
  -d "{\"product\":\"${PRODUCT}\",\"offering_id\":\"${OFFERING}\"}" \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["run"]["id"])')"
printf '%s\n' "run ${run_id} submitted for ${OFFERING}"

last=""
while :; do
  row="$(psql -c "select r.status, coalesce(e.current_stage,'-') from monitoring_runs r
                  left join offering_executions e on e.run_id = r.id where r.id = '${run_id}';")"
  [[ "${row}" != "${last}" ]] && printf '  %s\n' "${row//|/ · }" && last="${row}"
  case "${row%%|*}" in succeeded|failed|awaiting_review|partial_success) break ;; esac
  sleep 5
done

psql -c "select 'offering: '||status||' · stage '||coalesce(current_stage,'-')
                ||' · code '||coalesce(failure_code,'-')
         from offering_executions where run_id='${run_id}';"
psql -c "select 'snapshot: '||status||' · reused batches '
                ||coalesce(semantic_extraction->>'reused_batch_count','-')
                ||' · signals '||coalesce((select string_agg((s->>'field')||' ('||(s->>'reason')||')', ', ')
                                          from jsonb_array_elements(validation->'review_signals') s),'none')
         from tariff_snapshots where run_id='${run_id}';"
psql -c "select 'review: '||issue_scope||' ('||reason_code||') · '||status
         from human_reviews where run_id='${run_id}' order by created_at;"
psql -c "select 'change row: '||change_count||' change(s)' from tariff_changes where run_id='${run_id}';"
psql -c "select 'warnings: '||coalesce(string_agg(distinct w,', '),'none')
         from source_manifests m, jsonb_array_elements_text(coalesce(m.warning_codes,'[]'::jsonb)) w
         where m.run_id='${run_id}';" 2>/dev/null || true
# Pipeline model calls are not stamped with a run id, so count the calls made
# while this run was executing. A chat turn running at the same time would be
# counted too; for a dry run there is none.
psql -c "select 'model calls during this run: '||count(u.*)||' · cost \$'
                ||round(coalesce(sum(u.estimated_cost_usd),0)::numeric,4)
         from monitoring_runs r left join model_call_usage u
           on u.called_at between r.started_at and coalesce(r.completed_at, now())
         where r.id='${run_id}';"
printf '%s\n' "run_id=${run_id}"
