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
    ReviewStatus,
    ReviewTask,
)


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
                            RETURNING id, run_id, offering_execution_id
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
                await self._mark_documents(
                    session,
                    tuple(row.run_id for row in superseded_rows),
                    "superseded",
                )
                for superseded in superseded_rows:
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
                            "offering_execution_id": (
                                superseded.offering_execution_id
                            ),
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
    ) -> tuple[ReviewTask, ...]:
        if not 1 <= limit <= 500:
            raise ValueError("review limit must be between 1 and 500")
        if offering_id is not None and offering_id.product is not product:
            raise ValueError("offering requires its product")
        clauses: list[str] = []
        parameters: dict[str, object] = {"limit": limit}
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
                        {' '.join(clauses)}
                        ORDER BY created_at DESC, id DESC
                        LIMIT :limit
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
                            updated_at = now()
                        WHERE id = :id AND status = 'pending'
                        RETURNING *
                        """
                    ),
                    {"id": review_id, **correlation.model_dump()},
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
                (
                    "superseded"
                    if status is ReviewStatus.SUPERSEDED
                    else "rejected"
                ),
            )
        return _review_from_row(row)

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
    ) -> None:
        await session.execute(
            text(
                """
                UPDATE knowledge_documents
                SET publication_state = :state
                WHERE run_id = ANY(:run_ids)
                  AND publication_state = 'pending_review'
                  AND is_active = false
                """
            ),
            {"run_ids": list(run_ids), "state": state},
        )
