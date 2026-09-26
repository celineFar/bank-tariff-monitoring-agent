"""Remembered review decisions (semantic-extraction fix, SE12).

A reviewer answers a field once. The answer is kept against the call that
produced the field and against the field's result, so a later run that sees
the same call, or the same result, reuses it instead of asking again.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from typing import Any, Protocol

from pydantic import TypeAdapter
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.semantic_extraction import (
    ExtractionField,
    RememberedReviewDecision,
    ValidatedFieldResult,
)


def result_fingerprint(
    field: ExtractionField,
    status: str,
    value: Any,
    evidence_ids: Sequence[str],
) -> str:
    """The identity of one field result: status, value and cited evidence.

    Evidence IDs are content-based, so the same IDs mean the same evidence. A
    value may be given as the model's `value_json` string or as a parsed value;
    both reduce to the same canonical JSON.
    """
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except ValueError:
            pass
    canonical = json.dumps(
        TypeAdapter(Any).dump_python(value, mode="json"),
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        default=str,
    )
    material = "\x1f".join((field.value, status, canonical, *sorted(set(evidence_ids))))
    return hashlib.sha256(material.encode()).hexdigest()


class ReviewDecisionMemory(Protocol):
    async def find(
        self,
        *,
        offering_id: str,
        field: ExtractionField,
        prompt_fingerprints: Sequence[str],
        result_fingerprints: Sequence[str],
    ) -> RememberedReviewDecision | None: ...

    async def remember(self, decision: RememberedReviewDecision) -> None: ...


class InMemoryReviewDecisionMemory:
    def __init__(self) -> None:
        self.decisions: list[RememberedReviewDecision] = []

    async def find(
        self,
        *,
        offering_id: str,
        field: ExtractionField,
        prompt_fingerprints: Sequence[str],
        result_fingerprints: Sequence[str],
    ) -> RememberedReviewDecision | None:
        for decision in reversed(self.decisions):
            if decision.offering_id != offering_id or decision.field is not field:
                continue
            if decision.result_fingerprint in result_fingerprints or (
                decision.prompt_fingerprint is not None
                and decision.prompt_fingerprint in prompt_fingerprints
            ):
                return decision
        return None

    async def remember(self, decision: RememberedReviewDecision) -> None:
        self.decisions = [
            existing
            for existing in self.decisions
            if (existing.offering_id, existing.field, existing.result_fingerprint)
            != (decision.offering_id, decision.field, decision.result_fingerprint)
        ]
        self.decisions.append(decision)


class PostgresReviewDecisionMemory:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def find(
        self,
        *,
        offering_id: str,
        field: ExtractionField,
        prompt_fingerprints: Sequence[str],
        result_fingerprints: Sequence[str],
    ) -> RememberedReviewDecision | None:
        if not prompt_fingerprints and not result_fingerprints:
            return None
        async with self._session_factory() as session:
            row = (
                await session.execute(
                    text(
                        """
                        SELECT offering_id, field, prompt_fingerprint,
                               result_fingerprint, decision, reviewer, review_id
                        FROM review_decision_memory
                        WHERE offering_id = :offering_id AND field = :field
                          AND (result_fingerprint = ANY(:results)
                               OR prompt_fingerprint = ANY(:prompts))
                        ORDER BY created_at DESC, id DESC
                        LIMIT 1
                        """
                    ),
                    {
                        "offering_id": offering_id,
                        "field": field.value,
                        "results": list(result_fingerprints),
                        "prompts": list(prompt_fingerprints),
                    },
                )
            ).first()
        if row is None:
            return None
        return RememberedReviewDecision(
            offering_id=row.offering_id,
            field=ExtractionField(row.field),
            prompt_fingerprint=row.prompt_fingerprint,
            result_fingerprint=row.result_fingerprint,
            decision=ValidatedFieldResult.model_validate(row.decision),
            reviewer=row.reviewer,
            review_id=str(row.review_id) if row.review_id else None,
        )

    async def remember(self, decision: RememberedReviewDecision) -> None:
        async with self._session_factory() as session, session.begin():
            await session.execute(
                text(
                    """
                    INSERT INTO review_decision_memory (
                        offering_id, field, prompt_fingerprint, result_fingerprint,
                        decision, reviewer, review_id
                    )
                    VALUES (
                        :offering_id, :field, :prompt_fingerprint,
                        :result_fingerprint, CAST(:decision AS jsonb), :reviewer,
                        CAST(:review_id AS uuid)
                    )
                    ON CONFLICT ON CONSTRAINT review_decision_memory_result_uq
                    DO UPDATE SET
                        prompt_fingerprint = EXCLUDED.prompt_fingerprint,
                        decision = EXCLUDED.decision,
                        reviewer = EXCLUDED.reviewer,
                        review_id = EXCLUDED.review_id,
                        created_at = now()
                    """
                ),
                {
                    "offering_id": decision.offering_id,
                    "field": decision.field.value,
                    "prompt_fingerprint": decision.prompt_fingerprint,
                    "result_fingerprint": decision.result_fingerprint,
                    "decision": decision.decision.model_dump_json(),
                    "reviewer": decision.reviewer,
                    "review_id": decision.review_id,
                },
            )
