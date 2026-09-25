"""Operational metrics for monitoring runs, read from the durable tables.

These are the aggregate, historical numbers: how long runs take, where they
fail, how complete extraction is, how much review they need. They are computed
from `monitoring_runs`, `offering_executions`, `source_manifests`,
`tariff_facts`, `fact_evidence`, `human_reviews`, and `model_call_usage` rather
than from an OpenTelemetry metrics pipeline, because every one of those numbers
is already recorded there, transactionally and without a retention window. A
trace backend answers "what happened in this run"; this answers "what has been
happening", which is the question the audit trail exists for.

Latency deliberately excludes time spent waiting for a human: a run paused for
review is not a slow run, and counting the reviewer's thinking time would make
the number describe the reviewer rather than the system.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


def _rows(result) -> list[dict[str, object]]:
    return [dict(row._mapping) for row in result]


@dataclass(frozen=True)
class RunMetricsRepository:
    """Aggregate reads over the monitoring audit trail. No writes."""

    session_factory: async_sessionmaker[AsyncSession]

    async def _query(
        self, sql: str, start: datetime, end: datetime
    ) -> list[dict[str, object]]:
        async with self.session_factory() as session:
            return _rows(await session.execute(text(sql), {"start": start, "end": end}))

    async def run_outcomes(self, start: datetime, end: datetime):
        """Run counts and wall-clock duration, net of review wait."""
        return await self._query(
            """
            SELECT
                run.product,
                run.trigger_type,
                run.status,
                count(*) AS runs,
                round(avg(
                    extract(epoch FROM (run.completed_at - run.started_at))
                    - coalesce(review.wait_seconds, 0)
                )::numeric, 1) AS avg_active_seconds,
                round(max(
                    extract(epoch FROM (run.completed_at - run.started_at))
                    - coalesce(review.wait_seconds, 0)
                )::numeric, 1) AS max_active_seconds
            FROM monitoring_runs AS run
            LEFT JOIN LATERAL (
                SELECT sum(
                    extract(epoch FROM (
                        coalesce(hr.decided_at, hr.updated_at) - hr.created_at
                    ))
                ) AS wait_seconds
                FROM human_reviews AS hr
                WHERE hr.run_id = run.id
            ) AS review ON true
            WHERE run.started_at >= :start AND run.started_at < :end
              AND run.completed_at IS NOT NULL
            GROUP BY run.product, run.trigger_type, run.status
            ORDER BY run.product, run.trigger_type, run.status
            """,
            start,
            end,
        )

    async def stage_failures(self, start: datetime, end: datetime):
        """Offering executions by terminal stage and failure code."""
        return await self._query(
            """
            SELECT
                product,
                coalesce(failure_code, 'none') AS failure_code,
                coalesce(current_stage, 'unknown') AS stage,
                count(*) AS executions
            FROM offering_executions
            WHERE created_at >= :start AND created_at < :end
            GROUP BY product, failure_code, stage
            ORDER BY executions DESC
            """,
            start,
            end,
        )

    async def document_retrieval(self, start: datetime, end: datetime):
        """Source acquisition outcomes, by the SourceFailureCode taxonomy.

        The reason codes here are the same ones the assignment's controlled
        failure scenarios produce, so this doubles as evidence for them.
        """
        return await self._query(
            """
            SELECT
                status,
                coalesce(reason_code, 'none') AS reason_code,
                count(*) AS sources,
                count(DISTINCT offering_id) AS offerings
            FROM source_manifests
            WHERE created_at >= :start AND created_at < :end
            GROUP BY status, reason_code
            ORDER BY sources DESC
            """,
            start,
            end,
        )

    async def extraction_completeness(self, start: datetime, end: datetime):
        """Per-field found/missing/ambiguous counts over active facts.

        Reported per `field_path` rather than as one percentage: a single number
        hides that one field is reliably absent while the rest are complete.
        """
        return await self._query(
            """
            SELECT
                fact.field_path,
                count(*) FILTER (WHERE fact.status = 'found') AS found,
                count(*) FILTER (WHERE fact.status = 'not_stated') AS not_stated,
                count(*) FILTER (WHERE fact.status = 'ambiguous') AS ambiguous,
                count(*) FILTER (WHERE fact.status = 'conflicting') AS conflicting,
                count(*) AS total,
                round(
                    100.0 * count(*) FILTER (WHERE fact.status = 'found')
                    / nullif(count(*), 0), 1
                ) AS found_pct
            FROM tariff_facts AS fact
            JOIN offering_profiles AS profile
              ON profile.snapshot_id = fact.snapshot_id
            WHERE fact.is_active
              AND profile.accepted_at >= :start AND profile.accepted_at < :end
            GROUP BY fact.field_path
            ORDER BY found_pct NULLS LAST, fact.field_path
            """,
            start,
            end,
        )

    async def evidence_coverage(self, start: datetime, end: datetime):
        """Share of accepted found facts carrying verifiable evidence.

        Evidence is a hard requirement, so this is expected to read 100%; the
        value of the metric is that a regression becomes visible.
        """
        return await self._query(
            """
            SELECT
                count(*) AS found_facts,
                count(*) FILTER (WHERE evidence.fact_id IS NOT NULL)
                    AS facts_with_evidence,
                round(
                    100.0 * count(*) FILTER (WHERE evidence.fact_id IS NOT NULL)
                    / nullif(count(*), 0), 2
                ) AS coverage_pct
            FROM tariff_facts AS fact
            JOIN offering_profiles AS profile
              ON profile.snapshot_id = fact.snapshot_id
            LEFT JOIN LATERAL (
                SELECT fe.fact_id FROM fact_evidence AS fe
                WHERE fe.fact_id = fact.id LIMIT 1
            ) AS evidence ON true
            WHERE fact.is_active AND fact.status = 'found'
              AND profile.accepted_at >= :start AND profile.accepted_at < :end
            """,
            start,
            end,
        )

    async def validation_signals(self, start: datetime, end: datetime):
        """Deterministic validation rejects, by check and by field.

        `detect_review_signals` records every reject it raises into
        `tariff_snapshots.validation`, so the per-check breakdown is a query
        over data the pipeline already writes rather than new instrumentation.
        Counted over all snapshots, accepted or quarantined, because a reject
        that prevented acceptance is exactly what this measures.
        """
        return await self._query(
            """
            SELECT
                signal ->> 'reason' AS reason,
                signal ->> 'field' AS field,
                count(*) AS signals,
                count(DISTINCT snapshot.id) AS snapshots
            FROM tariff_snapshots AS snapshot
            CROSS JOIN LATERAL jsonb_array_elements(
                CASE
                    WHEN jsonb_typeof(snapshot.validation -> 'review_signals')
                         = 'array'
                    THEN snapshot.validation -> 'review_signals'
                    ELSE '[]'::jsonb
                END
            ) AS signal
            WHERE snapshot.created_at >= :start AND snapshot.created_at < :end
            GROUP BY reason, field
            ORDER BY signals DESC
            """,
            start,
            end,
        )

    async def review_activity(self, start: datetime, end: datetime):
        """HITL volume, mix, and how long decisions take."""
        return await self._query(
            """
            SELECT
                reason_code,
                status,
                count(*) AS reviews,
                round(avg(
                    extract(epoch FROM (decided_at - created_at))
                )::numeric, 1) AS avg_decision_seconds
            FROM human_reviews
            WHERE created_at >= :start AND created_at < :end
            GROUP BY reason_code, status
            ORDER BY reviews DESC
            """,
            start,
            end,
        )

    async def review_rate(self, start: datetime, end: datetime):
        return await self._query(
            """
            SELECT
                count(*) AS executions,
                count(*) FILTER (WHERE status = 'candidate_review') AS sent_to_review,
                round(
                    100.0 * count(*) FILTER (WHERE status = 'candidate_review')
                    / nullif(count(*), 0), 1
                ) AS review_rate_pct
            FROM offering_executions
            WHERE created_at >= :start AND created_at < :end
            """,
            start,
            end,
        )

    async def model_reliability(self, start: datetime, end: datetime):
        """Retry pressure and cache effectiveness per stage.

        Retries are recorded as separate logical calls, so `attempt > 1` counts
        how often a bounded retry was actually needed.
        """
        return await self._query(
            """
            SELECT
                stage,
                count(*) AS calls,
                count(*) FILTER (WHERE outcome = 'failed') AS failed,
                count(*) FILTER (WHERE outcome = 'cache_hit') AS cache_hits,
                count(*) FILTER (WHERE attempt > 1) AS retried,
                round(avg(latency_ms)::numeric, 0) AS avg_latency_ms
            FROM model_call_usage
            WHERE called_at >= :start AND called_at < :end
            GROUP BY stage
            ORDER BY calls DESC
            """,
            start,
            end,
        )

    async def change_activity(self, start: datetime, end: datetime):
        return await self._query(
            """
            SELECT
                count(*) AS change_sets,
                sum(jsonb_array_length(
                    CASE WHEN jsonb_typeof(changes) = 'array'
                         THEN changes ELSE '[]'::jsonb END
                )) AS changed_fields
            FROM tariff_changes
            WHERE created_at >= :start AND created_at < :end
            """,
            start,
            end,
        )

    async def transcription_sources(self, start: datetime, end: datetime):
        """Which engine produced the stored evidence, digital path versus OCR.

        `extraction_method` is already persisted per knowledge document and per
        chunk, so the split between Gemini transcription and the OCR fallback is
        a query over data the pipeline writes rather than new instrumentation.
        A non-zero `ocr` row means at least one scanned page was recovered by
        the fallback instead of being dropped.
        """
        return await self._query(
            """
            SELECT
                CASE
                    WHEN extraction_method LIKE 'ocr:%' THEN 'ocr'
                    WHEN extraction_method LIKE 'gemini_pdf:%' THEN 'gemini_pdf'
                    ELSE extraction_method
                END AS transcription_source,
                count(*) AS documents,
                round(avg(quality_score)::numeric, 3) AS avg_quality_score
            FROM knowledge_documents
            WHERE first_seen_at >= :start AND first_seen_at < :end
            GROUP BY transcription_source
            ORDER BY documents DESC
            """,
            start,
            end,
        )

    async def collect(self, start: datetime, end: datetime) -> dict[str, object]:
        return {
            "window": {"from": start.isoformat(), "to": end.isoformat()},
            "run_outcomes": await self.run_outcomes(start, end),
            "stage_failures": await self.stage_failures(start, end),
            "document_retrieval": await self.document_retrieval(start, end),
            "extraction_completeness": await self.extraction_completeness(start, end),
            "evidence_coverage": await self.evidence_coverage(start, end),
            "transcription_sources": await self.transcription_sources(start, end),
            "validation_signals": await self.validation_signals(start, end),
            "review_rate": await self.review_rate(start, end),
            "review_activity": await self.review_activity(start, end),
            "model_reliability": await self.model_reliability(start, end),
            "change_activity": await self.change_activity(start, end),
        }
