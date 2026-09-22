from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.models import OfferingId, ProductType
from app.domain.review import (
    ReviewCorrelation,
    ReviewDecision,
    ReviewDecisionType,
    ReviewReason,
    ReviewSnapshotUpdate,
    ReviewStatus,
    ReviewTask,
)
from app.repositories.monitoring import _snapshot_from_row
from app.repositories.structured_projection import publish_structured_projection


class ReviewConflictError(RuntimeError):
    pass


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _review_from_row(row: object) -> ReviewTask:
    values = row._mapping if hasattr(row, "_mapping") else row
    correlation_values = (
        values["workflow_app_name"],
        values["workflow_user_id"],
        values["workflow_session_id"],
        values["workflow_invocation_id"],
        values["workflow_interrupt_id"],
    )
    correlation = (
        ReviewCorrelation(
            app_name=correlation_values[0],
            user_id=correlation_values[1],
            session_id=correlation_values[2],
            invocation_id=correlation_values[3],
            interrupt_id=correlation_values[4],
        )
        if all(correlation_values)
        else None
    )
    decision = (
        ReviewDecision.model_validate(values["decision"])
        if values["decision"] is not None
        else None
    )
    return ReviewTask(
        # Older rows predate the column; absent context starts a new trace.
        trace_parent=values.get("trace_parent"),
        id=values["id"],
        idempotency_key=values["idempotency_key"],
        run_id=values["run_id"],
        offering_execution_id=values["offering_execution_id"],
        snapshot_id=values["snapshot_id"],
        product=ProductType(values["product"]),
        offering_id=OfferingId(values["offering_id"]),
        reason=ReviewReason(values["reason_code"]),
        issue_scope=values["issue_scope"],
        candidates=tuple(values["candidates"] or ()),
        evidence=values["evidence"] or {},
        status=ReviewStatus(values["status"]),
        correlation=correlation,
        reviewer=values["reviewer"],
        decision=decision,
        comment=values["comment"],
        failure_detail=values["failure_detail"],
        created_at=values["created_at"],
        updated_at=values["updated_at"],
        decided_at=values["decided_at"],
    )


class PostgresReviewRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def create(self, review: ReviewTask) -> ReviewTask:
        if review.status is not ReviewStatus.PENDING:
            raise ValueError("new review must be pending")
        async with self._session_factory() as session, session.begin():
            await session.execute(
                text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
                {
                    "key": (
                        f"review:{review.product.value}:{review.offering_id.value}:"
                        f"{review.issue_scope}"
                    )
                },
            )
            existing = (
                await session.execute(
                    text("SELECT * FROM human_reviews WHERE idempotency_key = :key"),
                    {"key": review.idempotency_key},
                )
            ).first()
            if existing is not None:
                return _review_from_row(existing)
            superseded_rows = tuple(
                (
                    await session.execute(
                        text(
                            """
                            UPDATE human_reviews
                            SET status = 'superseded', updated_at = :created_at
                            WHERE product = :product
                              AND offering_id = :offering_id
                              AND issue_scope = :issue_scope
                              AND status = 'pending'
                            RETURNING id, run_id, offering_execution_id, offering_id
                            """
                        ),
                        {
                            "product": review.product.value,
                            "offering_id": review.offering_id.value,
                            "issue_scope": review.issue_scope,
                            "created_at": review.created_at,
                        },
                    )
                ).all()
            )
            if superseded_rows:
                for superseded in superseded_rows:
                    await self._mark_documents(
                        session,
                        (superseded.run_id,),
                        "superseded",
                        offering_id=OfferingId(superseded.offering_id),
                    )
                    await session.execute(
                        text(
                            """
                            INSERT INTO audit_events (
                                run_id, offering_execution_id, event_type, payload
                            )
                            VALUES (
                                :run_id, :offering_execution_id,
                                'review.superseded', CAST(:payload AS jsonb)
                            )
                            """
                        ),
                        {
                            "run_id": superseded.run_id,
                            "offering_execution_id": (superseded.offering_execution_id),
                            "payload": _json(
                                {
                                    "review_id": str(superseded.id),
                                    "replacement_review_id": str(review.id),
                                }
                            ),
                        },
                    )
            row = (
                await session.execute(
                    text(
                        """
                        INSERT INTO human_reviews (
                            id, run_id, offering_execution_id, snapshot_id,
                            product, offering_id, reason_code, issue_scope,
                            candidates, evidence, status, idempotency_key,
                            created_at, updated_at
                        )
                        VALUES (
                            :id, :run_id, :offering_execution_id, :snapshot_id,
                            :product, :offering_id, :reason_code, :issue_scope,
                            CAST(:candidates AS jsonb), CAST(:evidence AS jsonb),
                            'pending', :idempotency_key, :created_at, :updated_at
                        )
                        RETURNING *
                        """
                    ),
                    {
                        "id": review.id,
                        "run_id": review.run_id,
                        "offering_execution_id": review.offering_execution_id,
                        "snapshot_id": review.snapshot_id,
                        "product": review.product.value,
                        "offering_id": review.offering_id.value,
                        "reason_code": review.reason.value,
                        "issue_scope": review.issue_scope,
                        "candidates": _json(
                            [item.model_dump(mode="json") for item in review.candidates]
                        ),
                        "evidence": _json(review.evidence),
                        "idempotency_key": review.idempotency_key,
                        "created_at": review.created_at,
                        "updated_at": review.updated_at,
                    },
                )
            ).one()
        return _review_from_row(row)

    async def get(self, review_id: UUID) -> ReviewTask | None:
        async with self._session_factory() as session:
            row = (
                await session.execute(
                    text("SELECT * FROM human_reviews WHERE id = :id"),
                    {"id": review_id},
                )
            ).first()
        return _review_from_row(row) if row is not None else None

    async def list(
        self,
        *,
        status: ReviewStatus | None = None,
        product: ProductType | None = None,
        offering_id: OfferingId | None = None,
        run_id: UUID | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[ReviewTask, ...]:
        if not 1 <= limit <= 500:
            raise ValueError("review limit must be between 1 and 500")
        if offset < 0:
            raise ValueError("review offset must be nonnegative")
        if offering_id is not None and offering_id.product is not product:
            raise ValueError("offering requires its product")
        clauses: list[str] = []
        parameters: dict[str, object] = {"limit": limit, "offset": offset}
        for column, value in (
            ("status", status.value if status else None),
            ("product", product.value if product else None),
            ("offering_id", offering_id.value if offering_id else None),
            ("run_id", run_id),
        ):
            if value is not None:
                clauses.append(f"AND {column} = :{column}")
                parameters[column] = value
        async with self._session_factory() as session:
            rows = (
                await session.execute(
                    text(
                        f"""
                        SELECT * FROM human_reviews
                        WHERE idempotency_key IS NOT NULL
                        {" ".join(clauses)}
                        ORDER BY created_at DESC, id DESC
                        LIMIT :limit OFFSET :offset
                        """
                    ),
                    parameters,
                )
            ).all()
        return tuple(_review_from_row(row) for row in rows)

    async def attach_workflow(
        self,
        review_id: UUID,
        correlation: ReviewCorrelation,
        *,
        trace_parent: str | None = None,
    ) -> ReviewTask:
        async with self._session_factory() as session, session.begin():
            row = (
                await session.execute(
                    text(
                        """
                        UPDATE human_reviews
                        SET workflow_app_name = :app_name,
                            workflow_user_id = :user_id,
                            workflow_session_id = :session_id,
                            workflow_invocation_id = :invocation_id,
                            workflow_interrupt_id = :interrupt_id,
                            trace_parent = :trace_parent,
                            updated_at = now()
                        WHERE id = :id AND status = 'pending'
                        RETURNING *
                        """
                    ),
                    {
                        "id": review_id,
                        "trace_parent": trace_parent,
                        **correlation.model_dump(),
                    },
                )
            ).first()
        if row is None:
            raise ReviewConflictError("review is missing or no longer pending")
        return _review_from_row(row)

    async def approve(
        self,
        review_id: UUID,
        decision: ReviewDecision,
        *,
        reviewer: str,
        comment: str | None = None,
    ) -> ReviewTask:
        if decision.decision_type is ReviewDecisionType.REJECT_ALL:
            raise ValueError("approval cannot use reject_all")
        return await self._decide(
            review_id,
            ReviewStatus.APPROVED,
            decision,
            reviewer=reviewer,
            comment=comment,
        )

    async def approve_with_snapshot(
        self,
        review_id: UUID,
        decision: ReviewDecision,
        update: ReviewSnapshotUpdate,
        *,
        reviewer: str,
    ) -> ReviewTask:
        if decision.decision_type is ReviewDecisionType.REJECT_ALL:
            raise ValueError("approval cannot use reject_all")
        normalized_reviewer = reviewer.strip()
        if not normalized_reviewer or len(normalized_reviewer) > 200:
            raise ValueError("reviewer must contain 1 to 200 characters")
        now = datetime.now(UTC)
        async with self._session_factory() as session, session.begin():
            current = await self._lock(session, review_id)
            if current.status is ReviewStatus.APPROVED and current.decision == decision:
                return current
            if current.status is not ReviewStatus.PENDING:
                raise ReviewConflictError("review is no longer pending")
            if current.snapshot_id != update.snapshot_id:
                raise ValueError("snapshot update is outside the review scope")
            snapshot = (
                await session.execute(
                    text(
                        """
                        SELECT id, canonical_sha256, status
                        FROM tariff_snapshots
                        WHERE id = :id
                        FOR UPDATE
                        """
                    ),
                    {"id": update.snapshot_id},
                )
            ).first()
            if snapshot is None:
                raise LookupError(str(update.snapshot_id))
            if snapshot.status != "review_required":
                raise ReviewConflictError("candidate snapshot is no longer reviewable")
            if snapshot.canonical_sha256 != update.expected_canonical_sha256:
                raise ReviewConflictError("candidate snapshot changed during review")
            row = (
                await session.execute(
                    text(
                        """
                        UPDATE human_reviews
                        SET status = 'approved', reviewer = :reviewer,
                            decision = CAST(:decision AS jsonb), decided_at = :now,
                            updated_at = :now
                        WHERE id = :id
                        RETURNING *
                        """
                    ),
                    {
                        "id": review_id,
                        "reviewer": normalized_reviewer,
                        "decision": _json(decision.model_dump(mode="json")),
                        "now": now,
                    },
                )
            ).one()
            await session.execute(
                text(
                    """
                    UPDATE tariff_snapshots
                    SET normalized_tariff = CAST(:normalized_tariff AS jsonb),
                        semantic_extraction = CAST(:semantic_extraction AS jsonb),
                        validation = CAST(:validation AS jsonb),
                        canonical_sha256 = :canonical_sha256
                    WHERE id = :id
                    """
                ),
                {
                    "id": update.snapshot_id,
                    "normalized_tariff": _json(update.normalized_tariff),
                    "semantic_extraction": _json(update.semantic_extraction),
                    "validation": _json(update.validation),
                    "canonical_sha256": update.canonical_sha256,
                },
            )
            unresolved = await session.scalar(
                text(
                    """
                    SELECT EXISTS (
                        SELECT 1 FROM human_reviews
                        WHERE snapshot_id = :snapshot_id
                          AND status <> 'approved'
                    )
                    """
                ),
                {"snapshot_id": update.snapshot_id},
            )
            if update.ready_for_activation and not unresolved:
                await self._activate_snapshot(session, current, update, now)
        return _review_from_row(row)

    async def reject(
        self,
        review_id: UUID,
        *,
        reviewer: str,
        comment: str | None = None,
    ) -> ReviewTask:
        return await self._decide(
            review_id,
            ReviewStatus.REJECTED,
            ReviewDecision(decision_type=ReviewDecisionType.REJECT_ALL),
            reviewer=reviewer,
            comment=comment,
        )

    async def fail(self, review_id: UUID, detail: str) -> ReviewTask:
        return await self._terminal_update(
            review_id,
            ReviewStatus.FAILED,
            failure_detail=detail,
        )

    async def supersede(self, review_id: UUID) -> ReviewTask:
        return await self._terminal_update(review_id, ReviewStatus.SUPERSEDED)

    async def _decide(
        self,
        review_id: UUID,
        status: ReviewStatus,
        decision: ReviewDecision,
        *,
        reviewer: str,
        comment: str | None,
    ) -> ReviewTask:
        normalized_reviewer = reviewer.strip()
        if not normalized_reviewer or len(normalized_reviewer) > 200:
            raise ValueError("reviewer must contain 1 to 200 characters")
        now = datetime.now(UTC)
        async with self._session_factory() as session, session.begin():
            current = await self._lock(session, review_id)
            if current.status is status and current.decision == decision:
                return current
            if current.status is not ReviewStatus.PENDING:
                raise ReviewConflictError("review is no longer pending")
            row = (
                await session.execute(
                    text(
                        """
                        UPDATE human_reviews
                        SET status = :status, reviewer = :reviewer,
                            decision = CAST(:decision AS jsonb), comment = :comment,
                            decided_at = :now, updated_at = :now
                        WHERE id = :id
                        RETURNING *
                        """
                    ),
                    {
                        "id": review_id,
                        "status": status.value,
                        "reviewer": normalized_reviewer,
                        "decision": _json(decision.model_dump(mode="json")),
                        "comment": comment,
                        "now": now,
                    },
                )
            ).one()
            if status is ReviewStatus.REJECTED:
                await self._mark_documents(
                    session,
                    (current.run_id,),
                    "rejected",
                    offering_id=current.offering_id,
                )
                await session.execute(
                    text(
                        """
                        UPDATE tariff_snapshots
                        SET status = 'rejected', accepted_at = NULL
                        WHERE id = :snapshot_id
                          AND status = 'review_required'
                        """
                    ),
                    {"snapshot_id": current.snapshot_id},
                )
                await session.execute(
                    text(
                        """
                        UPDATE offering_executions
                        SET status = 'failed', current_stage = 'review_rejected',
                            failure_count = failure_count + 1,
                            completed_at = COALESCE(completed_at, now()),
                            updated_at = now()
                        WHERE id = :execution_id
                          AND status = 'candidate_review'
                        """
                    ),
                    {"execution_id": current.offering_execution_id},
                )
        return _review_from_row(row)

    async def _terminal_update(
        self,
        review_id: UUID,
        status: ReviewStatus,
        *,
        failure_detail: str | None = None,
    ) -> ReviewTask:
        async with self._session_factory() as session, session.begin():
            current = await self._lock(session, review_id)
            if current.status is status:
                return current
            if current.status is not ReviewStatus.PENDING:
                raise ReviewConflictError("review is no longer pending")
            row = (
                await session.execute(
                    text(
                        """
                        UPDATE human_reviews
                        SET status = :status, failure_detail = :failure_detail,
                            updated_at = now()
                        WHERE id = :id
                        RETURNING *
                        """
                    ),
                    {
                        "id": review_id,
                        "status": status.value,
                        "failure_detail": failure_detail,
                    },
                )
            ).one()
            await self._mark_documents(
                session,
                (current.run_id,),
                ("superseded" if status is ReviewStatus.SUPERSEDED else "rejected"),
                offering_id=current.offering_id,
            )
        return _review_from_row(row)

    @staticmethod
    async def _activate_snapshot(
        session: AsyncSession,
        review: ReviewTask,
        update: ReviewSnapshotUpdate,
        now: datetime,
    ) -> None:
        identity_match = """
            old.bank = candidate.bank
            AND old.product = candidate.product
            AND old.offering_id = candidate.offering_id
            AND old.document_kind = candidate.document_kind
            AND old.document_key = candidate.document_key
            AND old.id <> candidate.id
        """
        await session.execute(
            text(
                f"""
                WITH candidate AS (
                    SELECT * FROM knowledge_documents
                    WHERE run_id = :run_id
                      AND offering_id = :offering_id
                      AND publication_state = 'pending_review'
                ), old_documents AS (
                    SELECT DISTINCT old.id
                    FROM knowledge_documents AS old
                    JOIN candidate ON {identity_match}
                    WHERE old.is_active = true
                )
                UPDATE knowledge_chunks
                SET is_active = false, retired_at = :now, updated_at = :now
                WHERE document_id IN (SELECT id FROM old_documents)
                  AND is_active = true
                """
            ),
            {
                "run_id": review.run_id,
                "offering_id": review.offering_id.value,
                "now": now,
            },
        )
        await session.execute(
            text(
                f"""
                WITH candidate AS (
                    SELECT * FROM knowledge_documents
                    WHERE run_id = :run_id
                      AND offering_id = :offering_id
                      AND publication_state = 'pending_review'
                )
                UPDATE knowledge_documents AS old
                SET is_active = false, publication_state = 'retired',
                    retired_at = :now
                FROM candidate
                WHERE {identity_match}
                  AND old.is_active = true
                """
            ),
            {
                "run_id": review.run_id,
                "offering_id": review.offering_id.value,
                "now": now,
            },
        )
        await session.execute(
            text(
                """
                UPDATE knowledge_documents
                SET is_active = true, publication_state = 'active', retired_at = NULL
                WHERE run_id = :run_id
                  AND offering_id = :offering_id
                  AND publication_state = 'pending_review'
                """
            ),
            {"run_id": review.run_id, "offering_id": review.offering_id.value},
        )
        await session.execute(
            text(
                """
                UPDATE knowledge_chunks AS chunk
                SET is_active = true, retired_at = NULL, updated_at = :now
                FROM knowledge_documents AS document
                WHERE chunk.document_id = document.id
                  AND document.run_id = :run_id
                  AND document.offering_id = :offering_id
                  AND document.publication_state = 'active'
                """
            ),
            {
                "run_id": review.run_id,
                "offering_id": review.offering_id.value,
                "now": now,
            },
        )
        await session.execute(
            text(
                """
                UPDATE tariff_snapshots
                SET status = 'accepted', accepted_at = :now
                WHERE id = :snapshot_id AND status = 'review_required'
                """
            ),
            {"snapshot_id": update.snapshot_id, "now": now},
        )
        accepted_row = (
            await session.execute(
                text("SELECT * FROM tariff_snapshots WHERE id = :id"),
                {"id": update.snapshot_id},
            )
        ).one()
        await session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:lock_key, 0))"),
            {
                "lock_key": (
                    f"publication:{accepted_row.bank.lower()}:"
                    f"{review.product.value}:{review.offering_id.value}"
                )
            },
        )
        await publish_structured_projection(session, _snapshot_from_row(accepted_row))
        await session.execute(
            text(
                """
                UPDATE offering_executions
                SET status = 'succeeded', current_stage = 'review_approved',
                    completed_at = COALESCE(completed_at, :now), updated_at = :now
                WHERE id = :execution_id AND status = 'candidate_review'
                """
            ),
            {"execution_id": review.offering_execution_id, "now": now},
        )
        await session.execute(
            text("DELETE FROM tariff_changes WHERE current_snapshot_id = :snapshot_id"),
            {"snapshot_id": update.snapshot_id},
        )
        if update.changes is not None:
            changes = update.changes
            await session.execute(
                text(
                    """
                    INSERT INTO tariff_changes (
                        id, run_id, product, offering_id, previous_snapshot_id,
                        current_snapshot_id, changes, change_count, created_at
                    )
                    VALUES (
                        :id, :run_id, :product, :offering_id,
                        :previous_snapshot_id, :current_snapshot_id,
                        CAST(:changes AS jsonb), :change_count, :created_at
                    )
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
                        [item.model_dump(mode="json") for item in changes.changes]
                    ),
                    "change_count": len(changes.changes),
                    "created_at": changes.created_at,
                },
            )
        await session.execute(
            text(
                """
                INSERT INTO audit_events (
                    run_id, offering_execution_id, event_type, payload
                )
                VALUES (
                    :run_id, :offering_execution_id,
                    'review.snapshot_activated', CAST(:payload AS jsonb)
                )
                """
            ),
            {
                "run_id": review.run_id,
                "offering_execution_id": review.offering_execution_id,
                "payload": _json({"snapshot_id": str(update.snapshot_id)}),
            },
        )

    @staticmethod
    async def _lock(session: AsyncSession, review_id: UUID) -> ReviewTask:
        row = (
            await session.execute(
                text("SELECT * FROM human_reviews WHERE id = :id FOR UPDATE"),
                {"id": review_id},
            )
        ).first()
        if row is None:
            raise LookupError(str(review_id))
        return _review_from_row(row)

    @staticmethod
    async def _mark_documents(
        session: AsyncSession,
        run_ids: tuple[UUID, ...],
        state: str,
        *,
        offering_id: OfferingId | None = None,
    ) -> None:
        offering_clause = ""
        parameters: dict[str, object] = {"run_ids": list(run_ids), "state": state}
        if offering_id is not None:
            offering_clause = "AND offering_id = :offering_id"
            parameters["offering_id"] = offering_id.value
        await session.execute(
            text(
                f"""
                UPDATE knowledge_documents
                SET publication_state = :state
                WHERE run_id = ANY(:run_ids)
                  AND publication_state = 'pending_review'
                  AND is_active = false
                  {offering_clause}
                """
            ),
            parameters,
        )
