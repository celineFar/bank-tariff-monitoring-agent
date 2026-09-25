from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select, text, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.knowledge import (
    EmbeddedKnowledgeDocument,
    IndexWriteResult,
    chunk_content_sha256,
    chunk_id,
    document_version_id,
)
from app.domain.models import OfferingId, ProductType
from app.domain.monitoring import (
    ClaimedRun,
    MonitoringRun,
    OfferingExecution,
    OfferingPublication,
    OfferingRunStatus,
    PublicationResult,
    RunCommand,
    RunFailureCode,
    RunStatus,
    RunSubmissionResult,
    RunTrigger,
    SnapshotAttempt,
    SnapshotChangeSet,
    SnapshotStatus,
)
from app.repositories.knowledge_store import (
    KnowledgeChunkRecord,
    KnowledgeDocumentRecord,
    PostgresKnowledgeStore,
)
from app.repositories.structured_projection import publish_structured_projection
from app.services.telemetry import inject_trace_context

_RUN_COLUMNS = """
    id,
    trigger_type,
    product,
    offering_id,
    query,
    status,
    idempotency_key,
    queued_at,
    started_at,
    completed_at,
    error_code,
    failure_detail,
    summary
"""


class RunNotFoundError(LookupError):
    pass


class InvalidRunTransitionError(RuntimeError):
    pass


class PublicationError(RuntimeError):
    pass


def _json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def _run_from_row(row: object) -> MonitoringRun:
    values = row._mapping if hasattr(row, "_mapping") else row
    command = RunCommand(
        product=ProductType(values["product"]),
        offering_id=(
            OfferingId(values["offering_id"])
            if values["offering_id"] is not None
            else None
        ),
        trigger=RunTrigger(values["trigger_type"]),
        query=values["query"],
    )
    return MonitoringRun(
        id=values["id"],
        command=command,
        status=RunStatus(values["status"]),
        idempotency_key=values["idempotency_key"],
        queued_at=values["queued_at"],
        started_at=values["started_at"],
        completed_at=values["completed_at"],
        failure_code=values["error_code"],
        failure_detail=values["failure_detail"],
        summary=values["summary"] or {},
    )


def _offering_from_row(row: object) -> OfferingExecution:
    values = row._mapping if hasattr(row, "_mapping") else row
    return OfferingExecution(
        id=values["id"],
        run_id=values["run_id"],
        product=ProductType(values["product"]),
        offering_id=OfferingId(values["offering_id"]),
        status=OfferingRunStatus(values["status"]),
        current_stage=values["current_stage"],
        started_at=values["started_at"],
        completed_at=values["completed_at"],
        source_count=values["source_count"],
        document_count=values["document_count"],
        chunk_count=values["chunk_count"],
        warning_count=values["warning_count"],
        failure_count=values["failure_count"],
        review_count=values["review_count"],
        failure_code=values["failure_code"],
        failure_detail=values["failure_detail"],
    )


def _snapshot_from_row(row: object) -> SnapshotAttempt:
    values = row._mapping if hasattr(row, "_mapping") else row
    return SnapshotAttempt(
        id=values["id"],
        run_id=values["run_id"],
        offering_execution_id=values["offering_execution_id"],
        bank=values["bank"],
        product=ProductType(values["product"]),
        offering_id=OfferingId(values["offering_id"]),
        status=SnapshotStatus(values["status"]),
        normalized_tariff=values["normalized_tariff"],
        evidence=tuple(values["evidence"] or ()),
        semantic_extraction=values["semantic_extraction"] or {},
        validation=values["validation"] or {},
        canonical_sha256=values["canonical_sha256"],
        previous_accepted_snapshot_id=values["previous_accepted_snapshot_id"],
        created_at=values["created_at"],
        accepted_at=values["accepted_at"],
    )


def _change_from_row(row: object) -> SnapshotChangeSet:
    values = row._mapping if hasattr(row, "_mapping") else row
    return SnapshotChangeSet(
        id=values["id"],
        run_id=values["run_id"],
        product=ProductType(values["product"]),
        offering_id=OfferingId(values["offering_id"]),
        previous_snapshot_id=values["previous_snapshot_id"],
        current_snapshot_id=values["current_snapshot_id"],
        changes=tuple(values["changes"] or ()),
        created_at=values["created_at"],
    )


def _snapshot_scope(
    product: ProductType | None,
    offering_id: OfferingId | None,
) -> tuple[str, dict[str, object]]:
    if offering_id is not None and product is None:
        raise ValueError("offering_id requires product")
    if offering_id is not None and offering_id.product is not product:
        raise ValueError("offering does not belong to product")
    clauses: list[str] = []
    parameters: dict[str, object] = {}
    if product is not None:
        clauses.append("AND product = :product")
        parameters["product"] = product.value
    if offering_id is not None:
        clauses.append("AND offering_id = :offering_id")
        parameters["offering_id"] = offering_id.value
    return "\n".join(clauses), parameters


def _change_scope(
    product: ProductType | None,
    offering_id: OfferingId | None,
) -> tuple[str, dict[str, object]]:
    return _snapshot_scope(product, offering_id)


def _validate_read_bounds(
    start_at: datetime | None,
    end_at: datetime | None,
    limit: int,
) -> None:
    for value in (start_at, end_at):
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("read bounds must be timezone-aware")
    if start_at is not None and end_at is not None and end_at < start_at:
        raise ValueError("end_at must not precede start_at")
    if limit < 1 or limit > 1000:
        raise ValueError("limit must be between 1 and 1000")


def _time_filter(
    column: str,
    start_at: datetime | None,
    end_at: datetime | None,
    parameters: dict[str, object],
) -> str:
    clauses: list[str] = []
    if start_at is not None:
        clauses.append(f"AND {column} >= :start_at")
        parameters["start_at"] = start_at
    if end_at is not None:
        clauses.append(f"AND {column} <= :end_at")
        parameters["end_at"] = end_at
    return "\n".join(clauses)


class PostgresRunRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def submit(
        self,
        command: RunCommand,
        *,
        idempotency_key: str | None = None,
    ) -> RunSubmissionResult:
        normalized_key = idempotency_key.strip() if idempotency_key else None
        if idempotency_key is not None and not normalized_key:
            raise ValueError("idempotency key must not be blank")
        if normalized_key is not None and len(normalized_key) > 200:
            raise ValueError("idempotency key must contain at most 200 characters")

        async with self._session_factory() as session, session.begin():
            if normalized_key is not None:
                await self._lock(session, f"idempotency:{normalized_key}")
                existing = await self._find_by_idempotency_key(session, normalized_key)
                if existing is not None:
                    return RunSubmissionResult(
                        run=existing,
                        created=False,
                        reused_reason=RunFailureCode.IDEMPOTENCY_REUSED,
                    )

            await self._lock(session, f"run-family:{command.product.value}")
            active = await self._find_active(session, command)
            if active is not None:
                return RunSubmissionResult(
                    run=active,
                    created=False,
                    reused_reason=RunFailureCode.ACTIVE_RUN_EXISTS,
                )

            run_id = uuid4()
            row = (
                await session.execute(
                    text(
                        f"""
                        INSERT INTO monitoring_runs (
                            id,
                            trigger_type,
                            product,
                            offering_id,
                            query,
                            status,
                            idempotency_key,
                            trace_parent,
                            queued_at,
                            created_at,
                            updated_at
                        )
                        VALUES (
                            :id,
                            :trigger_type,
                            :product,
                            :offering_id,
                            :query,
                            'queued',
                            :idempotency_key,
                            :trace_parent,
                            now(),
                            now(),
                            now()
                        )
                        RETURNING {_RUN_COLUMNS}
                        """
                    ),
                    {
                        "id": run_id,
                        # Captured in the triggering process so the worker can
                        # continue this run's trace rather than start a new one.
                        "trace_parent": inject_trace_context(),
                        "trigger_type": command.trigger.value,
                        "product": command.product.value,
                        "offering_id": (
                            command.offering_id.value
                            if command.offering_id is not None
                            else None
                        ),
                        "query": command.query,
                        "idempotency_key": normalized_key,
                    },
                )
            ).one()
            return RunSubmissionResult(run=_run_from_row(row), created=True)

    async def get(self, run_id: UUID) -> MonitoringRun | None:
        async with self._session_factory() as session:
            row = (
                await session.execute(
                    text(
                        f"""
                        SELECT {_RUN_COLUMNS}
                        FROM monitoring_runs
                        WHERE id = :run_id
                        """
                    ),
                    {"run_id": run_id},
                )
            ).first()
        return _run_from_row(row) if row is not None else None

    async def list_by_status(
        self,
        status: RunStatus,
        *,
        limit: int = 100,
    ) -> tuple[MonitoringRun, ...]:
        if not 1 <= limit <= 500:
            raise ValueError("run limit must be between 1 and 500")
        async with self._session_factory() as session:
            rows = (
                await session.execute(
                    text(
                        f"""
                        SELECT {_RUN_COLUMNS}
                        FROM monitoring_runs
                        WHERE status = :status
                        ORDER BY queued_at, id
                        LIMIT :limit
                        """
                    ),
                    {"status": status.value, "limit": limit},
                )
            ).all()
        return tuple(_run_from_row(row) for row in rows)

    async def claim_next(self, worker_id: str) -> ClaimedRun | None:
        normalized_worker = worker_id.strip()
        if not normalized_worker or len(normalized_worker) > 200:
            raise ValueError("worker_id must contain 1 to 200 characters")

        async with self._session_factory() as session, session.begin():
            row = (
                await session.execute(
                    text(
                        f"""
                        WITH candidate AS (
                            SELECT id
                            FROM monitoring_runs
                            WHERE status = 'queued'
                            ORDER BY queued_at, id
                            FOR UPDATE SKIP LOCKED
                            LIMIT 1
                        )
                        UPDATE monitoring_runs AS run
                        SET
                            status = 'running',
                            started_at = now(),
                            claimed_at = now(),
                            claimed_by = :worker_id,
                            updated_at = now()
                        FROM candidate
                        WHERE run.id = candidate.id
                        RETURNING {_RUN_COLUMNS.replace("id,", "run.id,", 1)},
                            run.trace_parent
                        """
                    ),
                    {"worker_id": normalized_worker},
                )
            ).first()
        if row is None:
            return None
        return ClaimedRun(
            run=_run_from_row(row),
            worker_id=normalized_worker,
            trace_parent=row.trace_parent,
        )

    async def claim(self, run_id: UUID, owner: str) -> ClaimedRun | None:
        """Claim one specific queued run; `None` when it is not queued any more.

        The chat node uses this for the run it just submitted, so exactly one
        process executes it even when a worker is polling the same queue.
        """
        normalized_owner = owner.strip()
        if not normalized_owner or len(normalized_owner) > 200:
            raise ValueError("owner must contain 1 to 200 characters")
        async with self._session_factory() as session, session.begin():
            row = (
                await session.execute(
                    text(
                        f"""
                        UPDATE monitoring_runs
                        SET
                            status = 'running',
                            started_at = now(),
                            claimed_at = now(),
                            claimed_by = :owner,
                            updated_at = now()
                        WHERE id = :run_id
                          AND status = 'queued'
                        RETURNING {_RUN_COLUMNS}, trace_parent
                        """
                    ),
                    {"run_id": run_id, "owner": normalized_owner},
                )
            ).first()
        if row is None:
            return None
        return ClaimedRun(
            run=_run_from_row(row),
            worker_id=normalized_owner,
            trace_parent=row.trace_parent,
        )

    async def fail_interrupted(
        self,
        *,
        owner_prefix: str,
        before: datetime | None = None,
    ) -> int:
        """Fail `running` runs claimed by a process that is known to be gone.

        Like `recover_abandoned`, but scoped to one owner family (for example
        `cli:host:`) and recorded as `run.interrupted`, because the caller has
        positive knowledge that the owner died rather than a lease timing out.
        """
        prefix = owner_prefix.strip()
        if not prefix or len(prefix) > 200:
            raise ValueError("owner_prefix must contain 1 to 200 characters")
        if before is not None and (before.tzinfo is None or before.utcoffset() is None):
            raise ValueError("before must be timezone-aware")
        escaped = prefix.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        parameters: dict[str, object] = {"pattern": f"{escaped}%"}
        before_clause = ""
        if before is not None:
            before_clause = "AND claimed_at < :before"
            parameters["before"] = before
        async with self._session_factory() as session, session.begin():
            run_ids = tuple(
                (
                    await session.execute(
                        text(
                            f"""
                            SELECT id
                            FROM monitoring_runs
                            WHERE status = 'running'
                              AND claimed_by LIKE :pattern ESCAPE '\\'
                              {before_clause}
                            FOR UPDATE SKIP LOCKED
                            """
                        ),
                        parameters,
                    )
                ).scalars()
            )
            if not run_ids:
                return 0
            await session.execute(
                text(
                    """
                    UPDATE offering_executions
                    SET
                        status = 'failed',
                        completed_at = now(),
                        failure_count = failure_count + 1,
                        failure_code = 'run.interrupted',
                        failure_detail = 'The process executing the run exited',
                        updated_at = now()
                    WHERE run_id = ANY(:run_ids)
                      AND status IN ('pending', 'running')
                    """
                ),
                {"run_ids": list(run_ids)},
            )
            await session.execute(
                text(
                    """
                    UPDATE monitoring_runs
                    SET
                        status = 'failed',
                        completed_at = now(),
                        error_code = 'run.interrupted',
                        failure_detail = 'The process executing the run exited',
                        updated_at = now()
                    WHERE id = ANY(:run_ids)
                    """
                ),
                {"run_ids": list(run_ids)},
            )
            await session.execute(
                text(
                    """
                    INSERT INTO audit_events (run_id, event_type, reason_code, payload)
                    SELECT id, 'run.interrupted', 'run.interrupted',
                           CAST(:payload AS jsonb)
                    FROM unnest(CAST(:run_ids AS uuid[])) AS id
                    """
                ),
                {"run_ids": list(run_ids), "payload": _json({"owner_prefix": prefix})},
            )
        return len(run_ids)

    async def recover_abandoned(self, *, before: datetime) -> int:
        if before.tzinfo is None or before.utcoffset() is None:
            raise ValueError("before must be timezone-aware")
        async with self._session_factory() as session, session.begin():
            run_ids = tuple(
                (
                    await session.execute(
                        text(
                            """
                            SELECT id
                            FROM monitoring_runs
                            WHERE status = 'running'
                              AND claimed_at < :before
                            FOR UPDATE SKIP LOCKED
                            """
                        ),
                        {"before": before},
                    )
                ).scalars()
            )
            if not run_ids:
                return 0
            await session.execute(
                text(
                    """
                    UPDATE offering_executions
                    SET
                        status = 'failed',
                        completed_at = now(),
                        failure_count = failure_count + 1,
                        failure_code = 'run.abandoned',
                        failure_detail = 'Worker lease expired',
                        updated_at = now()
                    WHERE run_id = ANY(:run_ids)
                      AND status IN ('pending', 'running')
                    """
                ),
                {"run_ids": list(run_ids)},
            )
            await session.execute(
                text(
                    """
                    UPDATE monitoring_runs
                    SET
                        status = 'failed',
                        completed_at = now(),
                        error_code = 'run.abandoned',
                        failure_detail = 'Worker lease expired',
                        updated_at = now()
                    WHERE id = ANY(:run_ids)
                    """
                ),
                {"run_ids": list(run_ids)},
            )
        return len(run_ids)

    async def finish(
        self,
        run_id: UUID,
        status: RunStatus,
        *,
        failure_code: str | None = None,
        failure_detail: str | None = None,
        summary: dict[str, object] | None = None,
    ) -> MonitoringRun:
        if not status.is_terminal:
            raise ValueError("run can only be finished with a terminal status")
        if failure_detail is not None and len(failure_detail) > 2000:
            raise ValueError("failure detail must contain at most 2000 characters")

        async with self._session_factory() as session, session.begin():
            row = (
                await session.execute(
                    text(
                        f"""
                        UPDATE monitoring_runs
                        SET
                            status = :status,
                            completed_at = now(),
                            error_code = :failure_code,
                            failure_detail = :failure_detail,
                            summary = CAST(:summary AS jsonb),
                            updated_at = now()
                        WHERE id = :run_id
                          AND status = 'running'
                        RETURNING {_RUN_COLUMNS}
                        """
                    ),
                    {
                        "run_id": run_id,
                        "status": status.value,
                        "failure_code": failure_code,
                        "failure_detail": failure_detail,
                        "summary": _json(summary or {}),
                    },
                )
            ).first()
            if row is None:
                exists = await session.scalar(
                    text("SELECT EXISTS(SELECT 1 FROM monitoring_runs WHERE id = :id)"),
                    {"id": run_id},
                )
                if not exists:
                    raise RunNotFoundError(str(run_id))
                raise InvalidRunTransitionError(
                    f"run {run_id} is not in running status"
                )
        return _run_from_row(row)

    async def pause_for_review(
        self,
        run_id: UUID,
        *,
        summary: dict[str, object],
    ) -> MonitoringRun:
        async with self._session_factory() as session, session.begin():
            row = (
                await session.execute(
                    text(
                        f"""
                        UPDATE monitoring_runs
                        SET status = 'awaiting_review',
                            summary = CAST(:summary AS jsonb),
                            claimed_by = NULL,
                            claimed_at = NULL,
                            updated_at = now()
                        WHERE id = :run_id AND status = 'running'
                        RETURNING {_RUN_COLUMNS}
                        """
                    ),
                    {"run_id": run_id, "summary": _json(summary)},
                )
            ).first()
            if row is None:
                raise InvalidRunTransitionError(f"run {run_id} cannot pause for review")
        return _run_from_row(row)

    async def finish_after_review(
        self,
        run_id: UUID,
        status: RunStatus,
        *,
        summary: dict[str, object],
    ) -> MonitoringRun:
        if not status.is_terminal:
            raise ValueError("review completion requires terminal run status")
        async with self._session_factory() as session, session.begin():
            row = (
                await session.execute(
                    text(
                        f"""
                        UPDATE monitoring_runs
                        SET status = :status, completed_at = now(),
                            summary = CAST(:summary AS jsonb), updated_at = now()
                        WHERE id = :run_id AND status = 'awaiting_review'
                        RETURNING {_RUN_COLUMNS}
                        """
                    ),
                    {
                        "run_id": run_id,
                        "status": status.value,
                        "summary": _json(summary),
                    },
                )
            ).first()
            if row is None:
                raise InvalidRunTransitionError(
                    f"run {run_id} cannot finish after review"
                )
        return _run_from_row(row)

    async def record_audit(
        self,
        run_id: UUID,
        event_type: str,
        *,
        offering_execution_id: UUID | None = None,
        reason_code: str | None = None,
        payload: dict[str, object] | None = None,
    ) -> None:
        normalized_type = event_type.strip()
        if not normalized_type or len(normalized_type) > 200:
            raise ValueError("audit event type must contain 1 to 200 characters")
        async with self._session_factory() as session, session.begin():
            await session.execute(
                text(
                    """
                    INSERT INTO audit_events (
                        run_id, offering_execution_id, event_type, reason_code, payload
                    )
                    VALUES (
                        :run_id, :offering_execution_id, :event_type, :reason_code,
                        CAST(:payload AS jsonb)
                    )
                    """
                ),
                {
                    "run_id": run_id,
                    "offering_execution_id": offering_execution_id,
                    "event_type": normalized_type,
                    "reason_code": reason_code,
                    "payload": _json(payload or {}),
                },
            )

    async def create_offering_execution(
        self,
        run_id: UUID,
        product: ProductType,
        offering_id: OfferingId,
    ) -> OfferingExecution:
        if offering_id.product is not product:
            raise ValueError("offering does not belong to product")
        execution_id = uuid4()
        async with self._session_factory() as session, session.begin():
            row = (
                await session.execute(
                    text(
                        """
                        INSERT INTO offering_executions (
                            id,
                            run_id,
                            product,
                            offering_id,
                            status
                        )
                        VALUES (
                            :id,
                            :run_id,
                            :product,
                            :offering_id,
                            'pending'
                        )
                        ON CONFLICT (run_id, offering_id)
                        DO UPDATE SET updated_at = offering_executions.updated_at
                        RETURNING *
                        """
                    ),
                    {
                        "id": execution_id,
                        "run_id": run_id,
                        "product": product.value,
                        "offering_id": offering_id.value,
                    },
                )
            ).one()
        return _offering_from_row(row)

    async def start_offering_execution(
        self, offering_execution_id: UUID, *, stage: str = "starting"
    ) -> OfferingExecution:
        async with self._session_factory() as session, session.begin():
            row = (
                await session.execute(
                    text(
                        """
                        UPDATE offering_executions
                        SET
                            status = 'running',
                            current_stage = :stage,
                            started_at = COALESCE(started_at, now()),
                            updated_at = now()
                        WHERE id = :id
                          AND status IN ('pending', 'running')
                        RETURNING *
                        """
                    ),
                    {"id": offering_execution_id, "stage": stage},
                )
            ).first()
        if row is None:
            raise InvalidRunTransitionError(
                f"offering execution {offering_execution_id} cannot be started"
            )
        return _offering_from_row(row)

    async def list_offering_executions(
        self, run_id: UUID
    ) -> tuple[OfferingExecution, ...]:
        async with self._session_factory() as session:
            rows = (
                await session.execute(
                    text(
                        """
                        SELECT * FROM offering_executions
                        WHERE run_id = :run_id
                        ORDER BY started_at NULLS LAST, offering_id
                        """
                    ),
                    {"run_id": run_id},
                )
            ).all()
        return tuple(_offering_from_row(row) for row in rows)

    async def fail_offering_execution(
        self,
        offering_execution_id: UUID,
        *,
        stage: str,
        failure_code: str,
        failure_detail: str | None = None,
        audit_payload: dict[str, object] | None = None,
    ) -> OfferingExecution:
        if len(stage) > 100 or not stage.strip():
            raise ValueError("stage must contain 1 to 100 characters")
        if len(failure_code) > 100 or not failure_code.strip():
            raise ValueError("failure_code must contain 1 to 100 characters")
        if failure_detail is not None and len(failure_detail) > 2000:
            raise ValueError("failure_detail must contain at most 2000 characters")
        async with self._session_factory() as session, session.begin():
            row = (
                await session.execute(
                    text(
                        """
                        UPDATE offering_executions
                        SET
                            status = 'failed',
                            current_stage = :stage,
                            completed_at = now(),
                            failure_count = failure_count + 1,
                            failure_code = :failure_code,
                            failure_detail = :failure_detail,
                            updated_at = now()
                        WHERE id = :id
                          AND status IN ('pending', 'running')
                        RETURNING *
                        """
                    ),
                    {
                        "id": offering_execution_id,
                        "stage": stage.strip(),
                        "failure_code": failure_code.strip(),
                        "failure_detail": failure_detail,
                    },
                )
            ).first()
            if row is None:
                raise InvalidRunTransitionError(
                    f"offering execution {offering_execution_id} cannot fail"
                )
            await session.execute(
                text(
                    """
                    INSERT INTO audit_events (
                        run_id,
                        offering_execution_id,
                        event_type,
                        reason_code,
                        payload
                    )
                    VALUES (
                        :run_id,
                        :offering_execution_id,
                        'offering.failed',
                        :reason_code,
                        CAST(:payload AS jsonb)
                    )
                    """
                ),
                {
                    "run_id": row.run_id,
                    "offering_execution_id": offering_execution_id,
                    "reason_code": failure_code.strip(),
                    "payload": _json(audit_payload or {"stage": stage.strip()}),
                },
            )
        return _offering_from_row(row)

    @staticmethod
    async def _lock(session: AsyncSession, key: str) -> None:
        await session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:lock_key, 0))"),
            {"lock_key": key},
        )

    @staticmethod
    async def _find_by_idempotency_key(
        session: AsyncSession, key: str
    ) -> MonitoringRun | None:
        row = (
            await session.execute(
                text(
                    f"""
                    SELECT {_RUN_COLUMNS}
                    FROM monitoring_runs
                    WHERE idempotency_key = :key
                    """
                ),
                {"key": key},
            )
        ).first()
        return _run_from_row(row) if row is not None else None

    @staticmethod
    async def _find_active(
        session: AsyncSession, command: RunCommand
    ) -> MonitoringRun | None:
        parameters: dict[str, object] = {"product": command.product.value}
        scope_clause = ""
        if command.offering_id is not None:
            scope_clause = "AND (offering_id IS NULL OR offering_id = :offering_id)"
            parameters["offering_id"] = command.offering_id.value
        row = (
            await session.execute(
                text(
                    f"""
                    SELECT {_RUN_COLUMNS}
                    FROM monitoring_runs
                    WHERE product = :product
                      AND status IN ('queued', 'running', 'awaiting_review')
                      {scope_clause}
                    ORDER BY queued_at, id
                    LIMIT 1
                    """
                ),
                parameters,
            )
        ).first()
        return _run_from_row(row) if row is not None else None


class PostgresSnapshotRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def get(self, snapshot_id: UUID) -> SnapshotAttempt | None:
        async with self._session_factory() as session:
            row = (
                await session.execute(
                    text("SELECT * FROM tariff_snapshots WHERE id = :id"),
                    {"id": snapshot_id},
                )
            ).first()
        return _snapshot_from_row(row) if row is not None else None

    async def save_attempt(self, snapshot: SnapshotAttempt) -> UUID:
        async with self._session_factory() as session, session.begin():
            return await _insert_snapshot(session, snapshot)

    async def get_latest_accepted(
        self,
        *,
        bank: str,
        product: ProductType,
        offering_id: OfferingId,
        before_run_id: UUID | None = None,
    ) -> SnapshotAttempt | None:
        if offering_id.product is not product:
            raise ValueError("offering does not belong to product")
        before_clause = ""
        parameters: dict[str, object] = {
            "bank": bank.lower(),
            "product": product.value,
            "offering_id": offering_id.value,
        }
        if before_run_id is not None:
            before_clause = """
                AND snapshot.created_at < (
                    SELECT queued_at
                    FROM monitoring_runs
                    WHERE id = :before_run_id
                )
            """
            parameters["before_run_id"] = before_run_id
        async with self._session_factory() as session:
            row = (
                await session.execute(
                    text(
                        f"""
                        SELECT snapshot.*
                        FROM tariff_snapshots AS snapshot
                        WHERE snapshot.bank = :bank
                          AND snapshot.product = :product
                          AND snapshot.offering_id = :offering_id
                          AND snapshot.status = 'accepted'
                          {before_clause}
                        ORDER BY snapshot.accepted_at DESC, snapshot.id DESC
                        LIMIT 1
                        """
                    ),
                    parameters,
                )
            ).first()
        return _snapshot_from_row(row) if row is not None else None

    async def save_changes(self, changes: SnapshotChangeSet) -> UUID:
        async with self._session_factory() as session, session.begin():
            await _insert_changes(session, changes)
        return changes.id

    async def list_latest_accepted(
        self,
        *,
        bank: str,
        product: ProductType | None = None,
        offering_id: OfferingId | None = None,
    ) -> tuple[SnapshotAttempt, ...]:
        scope_sql, parameters = _snapshot_scope(product, offering_id)
        parameters["bank"] = bank.lower()
        async with self._session_factory() as session:
            rows = (
                await session.execute(
                    text(
                        f"""
                        SELECT DISTINCT ON (snapshot.offering_id) snapshot.*
                        FROM tariff_snapshots AS snapshot
                        WHERE snapshot.bank = :bank
                          AND snapshot.status = 'accepted'
                          {scope_sql}
                        ORDER BY
                            snapshot.offering_id,
                            snapshot.accepted_at DESC,
                            snapshot.id DESC
                        """
                    ),
                    parameters,
                )
            ).all()
        return tuple(_snapshot_from_row(row) for row in rows)

    async def has_newer_pending_review(
        self,
        *,
        bank: str,
        product: ProductType,
        offering_id: OfferingId,
        accepted_at: datetime | None,
    ) -> bool:
        if offering_id.product is not product:
            raise ValueError("offering does not belong to product")
        after_sql = ""
        parameters: dict[str, object] = {
            "bank": bank.lower(),
            "product": product.value,
            "offering_id": offering_id.value,
        }
        if accepted_at is not None:
            after_sql = "AND created_at > :accepted_at"
            parameters["accepted_at"] = accepted_at
        async with self._session_factory() as session:
            found = await session.scalar(
                text(
                    f"""
                    SELECT EXISTS (
                        SELECT 1
                        FROM tariff_snapshots
                        WHERE bank = :bank
                          AND product = :product
                          AND offering_id = :offering_id
                          AND status IN ('candidate', 'review_required')
                          {after_sql}
                    )
                    """
                ),
                parameters,
            )
        return bool(found)

    async def list_accepted_history(
        self,
        *,
        bank: str,
        product: ProductType | None = None,
        offering_id: OfferingId | None = None,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
        limit: int,
    ) -> tuple[SnapshotAttempt, ...]:
        _validate_read_bounds(start_at, end_at, limit)
        scope_sql, parameters = _snapshot_scope(product, offering_id)
        parameters.update({"bank": bank.lower(), "limit": limit})
        time_sql = _time_filter("accepted_at", start_at, end_at, parameters)
        async with self._session_factory() as session:
            rows = (
                await session.execute(
                    text(
                        f"""
                        SELECT *
                        FROM tariff_snapshots
                        WHERE bank = :bank
                          AND status = 'accepted'
                          {scope_sql}
                          {time_sql}
                        ORDER BY accepted_at DESC, id DESC
                        LIMIT :limit
                        """
                    ),
                    parameters,
                )
            ).all()
        return tuple(_snapshot_from_row(row) for row in rows)

    async def list_changes(
        self,
        *,
        product: ProductType | None = None,
        offering_id: OfferingId | None = None,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
        limit: int,
    ) -> tuple[SnapshotChangeSet, ...]:
        _validate_read_bounds(start_at, end_at, limit)
        scope_sql, parameters = _change_scope(product, offering_id)
        parameters["limit"] = limit
        time_sql = _time_filter("created_at", start_at, end_at, parameters)
        async with self._session_factory() as session:
            rows = (
                await session.execute(
                    text(
                        f"""
                        SELECT *
                        FROM tariff_changes
                        WHERE true
                          {scope_sql}
                          {time_sql}
                        ORDER BY created_at DESC, id DESC
                        LIMIT :limit
                        """
                    ),
                    parameters,
                )
            ).all()
        return tuple(_change_from_row(row) for row in rows)

    async def get_latest_change_before(
        self,
        *,
        product: ProductType | None = None,
        offering_id: OfferingId | None = None,
        before: datetime,
    ) -> SnapshotChangeSet | None:
        _validate_read_bounds(None, before, 1)
        scope_sql, parameters = _change_scope(product, offering_id)
        parameters["before"] = before
        async with self._session_factory() as session:
            row = (
                await session.execute(
                    text(
                        f"""
                        SELECT *
                        FROM tariff_changes
                        WHERE created_at < :before
                          {scope_sql}
                        ORDER BY created_at DESC, id DESC
                        LIMIT 1
                        """
                    ),
                    parameters,
                )
            ).first()
        return _change_from_row(row) if row is not None else None


class PostgresOfferingPublicationRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def publish(self, publication: OfferingPublication) -> PublicationResult:
        snapshot = publication.snapshot
        final_status = _publication_status(snapshot.status)
        now = datetime.now(UTC)

        async with self._session_factory() as session, session.begin():
            await session.execute(
                text("SELECT pg_advisory_xact_lock(hashtextextended(:lock_key, 0))"),
                {
                    "lock_key": (
                        f"publication:{snapshot.bank.lower()}:"
                        f"{snapshot.product.value}:{snapshot.offering_id.value}"
                    )
                },
            )
            execution = (
                await session.execute(
                    text(
                        """
                        SELECT id, run_id, product, offering_id, status
                        FROM offering_executions
                        WHERE id = :id
                        FOR UPDATE
                        """
                    ),
                    {"id": publication.offering_execution_id},
                )
            ).first()
            if execution is None:
                raise PublicationError("offering execution does not exist")
            if (
                execution.run_id != snapshot.run_id
                or execution.product != snapshot.product.value
                or execution.offering_id != snapshot.offering_id.value
            ):
                raise PublicationError("offering execution scope does not match")
            if execution.status not in {"pending", "running"}:
                raise PublicationError(
                    f"offering execution cannot publish from {execution.status}"
                )

            document_results = tuple(
                [
                    await _upsert_document(
                        session,
                        document,
                        now,
                        activate=snapshot.status is SnapshotStatus.ACCEPTED,
                    )
                    for document in publication.documents
                ]
            )
            snapshot_id = await _insert_snapshot(session, snapshot)
            if snapshot.status is SnapshotStatus.ACCEPTED:
                await publish_structured_projection(session, snapshot)
            for manifest in publication.manifests:
                await session.execute(
                    text(
                        """
                        INSERT INTO source_manifests (
                            id,
                            run_id,
                            offering_execution_id,
                            product,
                            offering_id,
                            source_url,
                            final_url,
                            document_key,
                            document_id,
                            content_sha256,
                            status,
                            selected,
                            reason_code,
                            warning_codes,
                            metadata
                        )
                        VALUES (
                            :id,
                            :run_id,
                            :offering_execution_id,
                            :product,
                            :offering_id,
                            :source_url,
                            :final_url,
                            :document_key,
                            :document_id,
                            :content_sha256,
                            :status,
                            :selected,
                            :reason_code,
                            CAST(:warning_codes AS jsonb),
                            CAST(:metadata AS jsonb)
                        )
                        ON CONFLICT (id)
                        DO UPDATE SET
                            final_url = EXCLUDED.final_url,
                            document_key = EXCLUDED.document_key,
                            document_id = EXCLUDED.document_id,
                            content_sha256 = EXCLUDED.content_sha256,
                            status = EXCLUDED.status,
                            selected = EXCLUDED.selected,
                            reason_code = EXCLUDED.reason_code,
                            warning_codes = EXCLUDED.warning_codes,
                            metadata = EXCLUDED.metadata
                        """
                    ),
                    {
                        "id": manifest.id,
                        "run_id": manifest.run_id,
                        "offering_execution_id": manifest.offering_execution_id,
                        "product": manifest.product.value,
                        "offering_id": manifest.offering_id.value,
                        "source_url": str(manifest.source_url),
                        "final_url": (
                            str(manifest.final_url)
                            if manifest.final_url is not None
                            else None
                        ),
                        "document_key": manifest.document_key,
                        "document_id": manifest.document_id,
                        "content_sha256": manifest.content_sha256,
                        "status": manifest.status.value,
                        "selected": manifest.selected,
                        "reason_code": manifest.reason_code,
                        "warning_codes": _json(list(manifest.warning_codes)),
                        "metadata": _json(manifest.metadata),
                    },
                )
            if publication.changes is not None:
                await _insert_changes(session, publication.changes)

            chunk_count = sum(
                len(document.chunks) for document in publication.documents
            )
            review_count = int(final_status is OfferingRunStatus.CANDIDATE_REVIEW)
            failure_count = int(final_status is OfferingRunStatus.FAILED)
            await session.execute(
                text(
                    """
                    UPDATE offering_executions
                    SET
                        status = :status,
                        current_stage = 'published',
                        completed_at = now(),
                        source_count = :source_count,
                        document_count = :document_count,
                        chunk_count = :chunk_count,
                        warning_count = :warning_count,
                        failure_count = :failure_count,
                        review_count = :review_count,
                        updated_at = now()
                    WHERE id = :id
                    """
                ),
                {
                    "id": publication.offering_execution_id,
                    "status": final_status.value,
                    "source_count": len(publication.manifests),
                    "document_count": len(publication.documents),
                    "chunk_count": chunk_count,
                    "warning_count": sum(
                        len(manifest.warning_codes)
                        for manifest in publication.manifests
                    ),
                    "failure_count": failure_count,
                    "review_count": review_count,
                },
            )
            await session.execute(
                text(
                    """
                    INSERT INTO audit_events (
                        run_id,
                        offering_execution_id,
                        event_type,
                        payload
                    )
                    VALUES (
                        :run_id,
                        :offering_execution_id,
                        'offering.published',
                        CAST(:payload AS jsonb)
                    )
                    """
                ),
                {
                    "run_id": snapshot.run_id,
                    "offering_execution_id": publication.offering_execution_id,
                    "payload": _json(
                        {
                            "snapshot_id": str(snapshot.id),
                            "snapshot_status": snapshot.status.value,
                            "documents": len(publication.documents),
                            "chunks": chunk_count,
                            "manifests": len(publication.manifests),
                            "changes": (
                                len(publication.changes.changes)
                                if publication.changes is not None
                                else 0
                            ),
                            "metadata": publication.audit_metadata,
                        }
                    ),
                },
            )
            if publication.audit_metadata.get("provenance_changed") is True:
                await session.execute(
                    text(
                        """
                        INSERT INTO audit_events (
                            run_id,
                            offering_execution_id,
                            event_type,
                            payload
                        )
                        VALUES (
                            :run_id,
                            :offering_execution_id,
                            'snapshot.provenance_changed',
                            CAST(:payload AS jsonb)
                        )
                        """
                    ),
                    {
                        "run_id": snapshot.run_id,
                        "offering_execution_id": publication.offering_execution_id,
                        "payload": _json({"snapshot_id": str(snapshot.id)}),
                    },
                )

        return PublicationResult(
            snapshot_id=snapshot_id,
            document_results=document_results,
            offering_status=final_status,
        )


async def _insert_snapshot(session: AsyncSession, snapshot: SnapshotAttempt) -> UUID:
    inserted = (
        await session.execute(
            text(
                """
                INSERT INTO tariff_snapshots (
                    id,
                    run_id,
                    offering_execution_id,
                    bank,
                    product,
                    offering_id,
                    status,
                    normalized_tariff,
                    evidence,
                    semantic_extraction,
                    validation,
                    canonical_sha256,
                    previous_accepted_snapshot_id,
                    created_at,
                    accepted_at
                )
                VALUES (
                    :id,
                    :run_id,
                    :offering_execution_id,
                    :bank,
                    :product,
                    :offering_id,
                    :status,
                    CAST(:normalized_tariff AS jsonb),
                    CAST(:evidence AS jsonb),
                    CAST(:semantic_extraction AS jsonb),
                    CAST(:validation AS jsonb),
                    :canonical_sha256,
                    :previous_accepted_snapshot_id,
                    :created_at,
                    :accepted_at
                )
                ON CONFLICT (run_id, offering_id) DO NOTHING
                RETURNING id
                """
            ),
            {
                "id": snapshot.id,
                "run_id": snapshot.run_id,
                "offering_execution_id": snapshot.offering_execution_id,
                "bank": snapshot.bank.lower(),
                "product": snapshot.product.value,
                "offering_id": snapshot.offering_id.value,
                "status": snapshot.status.value,
                "normalized_tariff": _json(snapshot.normalized_tariff),
                "evidence": _json(list(snapshot.evidence)),
                "semantic_extraction": _json(snapshot.semantic_extraction),
                "validation": _json(snapshot.validation),
                "canonical_sha256": snapshot.canonical_sha256,
                "previous_accepted_snapshot_id": (
                    snapshot.previous_accepted_snapshot_id
                ),
                "created_at": snapshot.created_at,
                "accepted_at": snapshot.accepted_at,
            },
        )
    ).scalar_one_or_none()
    if inserted is not None:
        return inserted
    existing = await session.scalar(
        text(
            """
            SELECT id
            FROM tariff_snapshots
            WHERE run_id = :run_id
              AND offering_id = :offering_id
            """
        ),
        {
            "run_id": snapshot.run_id,
            "offering_id": snapshot.offering_id.value,
        },
    )
    if existing != snapshot.id:
        raise PublicationError("run/offering already has a different snapshot attempt")
    return existing


async def _insert_changes(session: AsyncSession, changes: SnapshotChangeSet) -> None:
    await session.execute(
        text(
            """
            INSERT INTO tariff_changes (
                id,
                run_id,
                product,
                offering_id,
                previous_snapshot_id,
                current_snapshot_id,
                changes,
                change_count,
                created_at
            )
            VALUES (
                :id,
                :run_id,
                :product,
                :offering_id,
                :previous_snapshot_id,
                :current_snapshot_id,
                CAST(:changes AS jsonb),
                :change_count,
                :created_at
            )
            ON CONFLICT (current_snapshot_id)
            DO UPDATE SET
                changes = EXCLUDED.changes,
                change_count = EXCLUDED.change_count
            """
        ),
        {
            "id": changes.id,
            "run_id": changes.run_id,
            "product": changes.product.value,
            "offering_id": changes.offering_id.value,
            "previous_snapshot_id": changes.previous_snapshot_id,
            "current_snapshot_id": changes.current_snapshot_id,
            "changes": _json(
                [change.model_dump(mode="json") for change in changes.changes]
            ),
            "change_count": len(changes.changes),
            "created_at": changes.created_at,
        },
    )


async def _upsert_document(
    session: AsyncSession,
    document: EmbeddedKnowledgeDocument,
    now: datetime,
    *,
    activate: bool,
) -> IndexWriteResult:
    PostgresKnowledgeStore._validate_embeddings(document)
    version_id = document_version_id(document)
    incoming_chunk_ids = tuple(chunk_id(document, chunk) for chunk in document.chunks)
    await session.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:document_identity, 0))"),
        {
            "document_identity": "\x1f".join(
                (
                    document.bank.lower(),
                    document.product.value,
                    document.offering_id.value if document.offering_id else "",
                    document.document_kind.value,
                    document.document_key,
                )
            )
        },
    )
    document_created = (
        await session.scalar(
            select(KnowledgeDocumentRecord.id).where(
                KnowledgeDocumentRecord.id == version_id
            )
        )
        is None
    )
    existing_chunk_ids = set(
        (
            await session.scalars(
                select(KnowledgeChunkRecord.id).where(
                    KnowledgeChunkRecord.id.in_(incoming_chunk_ids)
                )
            )
        ).all()
    )
    await session.execute(
        insert(KnowledgeDocumentRecord)
        .values(
            id=version_id,
            run_id=document.run_id,
            last_seen_run_id=document.run_id,
            bank=document.bank.lower(),
            product=document.product.value,
            offering_id=(
                document.offering_id.value if document.offering_id is not None else None
            ),
            document_kind=document.document_kind.value,
            document_key=document.document_key,
            document_name=document.document_name,
            source_url=str(document.source_url),
            final_url=str(document.final_url),
            mime_type=document.mime_type,
            content_sha256=document.content_sha256,
            retrieved_at=document.retrieved_at,
            extraction_method=document.extraction_method,
            quality_score=document.quality_score,
            extra_metadata=document.metadata,
            is_active=activate,
            publication_state="active" if activate else "pending_review",
            first_seen_at=now,
            last_seen_at=now,
            retired_at=None,
        )
        .on_conflict_do_update(
            index_elements=[KnowledgeDocumentRecord.id],
            set_={
                "last_seen_run_id": document.run_id,
                "document_name": document.document_name,
                "source_url": str(document.source_url),
                "final_url": str(document.final_url),
                "mime_type": document.mime_type,
                "retrieved_at": document.retrieved_at,
                "extraction_method": document.extraction_method,
                "quality_score": document.quality_score,
                "metadata": document.metadata,
                "last_seen_at": now,
                **(
                    {
                        "is_active": True,
                        "publication_state": "active",
                        "retired_at": None,
                    }
                    if activate
                    else {}
                ),
            },
        )
    )
    superseded_ids = tuple(
        (
            await session.scalars(
                select(KnowledgeDocumentRecord.id).where(
                    KnowledgeDocumentRecord.bank == document.bank.lower(),
                    KnowledgeDocumentRecord.product == document.product.value,
                    KnowledgeDocumentRecord.offering_id
                    == (
                        document.offering_id.value
                        if document.offering_id is not None
                        else None
                    ),
                    KnowledgeDocumentRecord.document_kind
                    == document.document_kind.value,
                    KnowledgeDocumentRecord.document_key == document.document_key,
                    KnowledgeDocumentRecord.id != version_id,
                    KnowledgeDocumentRecord.is_active.is_(True),
                )
            )
        ).all()
        if activate
        else ()
    )
    retired_chunks = 0
    if superseded_ids:
        result = await session.execute(
            update(KnowledgeChunkRecord)
            .where(
                KnowledgeChunkRecord.document_id.in_(superseded_ids),
                KnowledgeChunkRecord.is_active.is_(True),
            )
            .values(is_active=False, retired_at=now, updated_at=now)
        )
        retired_chunks += result.rowcount
        await session.execute(
            update(KnowledgeDocumentRecord)
            .where(KnowledgeDocumentRecord.id.in_(superseded_ids))
            .values(is_active=False, publication_state="retired", retired_at=now)
        )
    for identifier, chunk in zip(incoming_chunk_ids, document.chunks, strict=True):
        await session.execute(
            insert(KnowledgeChunkRecord)
            .values(
                id=identifier,
                document_id=version_id,
                ordinal=chunk.ordinal,
                page_start=chunk.page_start,
                page_end=chunk.page_end,
                section=chunk.section,
                language=chunk.language,
                content=chunk.content,
                content_sha256=chunk_content_sha256(chunk.content),
                extraction_method=chunk.extraction_method,
                quality_score=chunk.quality_score,
                extra_metadata=chunk.metadata,
                embedding=list(chunk.embedding),
                is_active=activate,
                retired_at=None,
                created_at=now,
                updated_at=now,
            )
            .on_conflict_do_update(
                index_elements=[KnowledgeChunkRecord.id],
                set_={
                    "content": chunk.content,
                    "content_sha256": chunk_content_sha256(chunk.content),
                    "language": chunk.language,
                    "extraction_method": chunk.extraction_method,
                    "quality_score": chunk.quality_score,
                    "metadata": chunk.metadata,
                    "embedding": list(chunk.embedding),
                    **({"is_active": True, "retired_at": None} if activate else {}),
                    "updated_at": now,
                },
            )
        )
    if activate:
        result = await session.execute(
            update(KnowledgeChunkRecord)
            .where(
                KnowledgeChunkRecord.document_id == version_id,
                KnowledgeChunkRecord.id.not_in(incoming_chunk_ids),
                KnowledgeChunkRecord.is_active.is_(True),
            )
            .values(is_active=False, retired_at=now, updated_at=now)
        )
        retired_chunks += result.rowcount
    chunks_created = len(set(incoming_chunk_ids) - existing_chunk_ids)
    return IndexWriteResult(
        document_id=version_id,
        document_created=document_created,
        chunks_created=chunks_created,
        chunks_updated=len(incoming_chunk_ids) - chunks_created,
        chunks_retired=retired_chunks,
        versions_retired=len(superseded_ids),
    )


def _publication_status(status: SnapshotStatus) -> OfferingRunStatus:
    if status is SnapshotStatus.ACCEPTED:
        return OfferingRunStatus.SUCCEEDED
    if status in {SnapshotStatus.CANDIDATE, SnapshotStatus.REVIEW_REQUIRED}:
        return OfferingRunStatus.CANDIDATE_REVIEW
    return OfferingRunStatus.FAILED
