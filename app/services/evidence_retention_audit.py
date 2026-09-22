"""Prove citation evidence survives without the legacy chunk embeddings.

Phase F only deprecates the old summary/source embeddings once every active
accepted fact carries a self-contained citation: an exact quote, a source
locator, and a provenance document row whose checksum still matches. The audit
is read-only and never deletes or rewrites anything; physical cleanup of the
legacy chunks is planned separately.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


@dataclass(frozen=True)
class RetentionGap:
    kind: str
    fact_id: str
    offering_id: str
    field_path: str
    evidence_id: str | None = None
    detail: str | None = None


@dataclass(frozen=True)
class EvidenceRetentionReport:
    active_found_facts: int
    active_evidence_rows: int
    facts_without_evidence: int
    evidence_without_locator: int
    evidence_without_document: int
    evidence_with_checksum_drift: int
    legacy_source_chunks: int
    legacy_summary_chunks: int
    legacy_embedded_chunks: int
    gaps: tuple[RetentionGap, ...]

    @property
    def ready_to_deprecate_legacy_embeddings(self) -> bool:
        # An empty structured read model proves nothing: the legacy chunks are
        # still the only way to answer, so deprecating them would lose evidence.
        return bool(self.active_found_facts) and not self.gaps

    def as_dict(self) -> dict[str, object]:
        return {
            "active_found_facts": self.active_found_facts,
            "active_evidence_rows": self.active_evidence_rows,
            "facts_without_evidence": self.facts_without_evidence,
            "evidence_without_locator": self.evidence_without_locator,
            "evidence_without_document": self.evidence_without_document,
            "evidence_with_checksum_drift": self.evidence_with_checksum_drift,
            "legacy_source_chunks": self.legacy_source_chunks,
            "legacy_summary_chunks": self.legacy_summary_chunks,
            "legacy_embedded_chunks": self.legacy_embedded_chunks,
            "ready_to_deprecate_legacy_embeddings": (
                self.ready_to_deprecate_legacy_embeddings
            ),
            "gaps": [asdict(item) for item in self.gaps],
        }


_FACTS_WITHOUT_EVIDENCE = text(
    """SELECT f.id, f.offering_id, f.field_path
    FROM tariff_facts AS f
    LEFT JOIN fact_evidence AS e ON e.fact_id = f.id
    WHERE f.is_active AND f.status = 'found' AND e.fact_id IS NULL
    ORDER BY f.offering_id, f.field_path"""
)
_EVIDENCE_ROWS = text(
    """SELECT f.id AS fact_id, f.offering_id, f.field_path, e.evidence_id,
           e.quote, e.locator, e.source_document_id, e.source_checksum,
           d.id AS document_id, d.content_sha256
    FROM tariff_facts AS f
    JOIN fact_evidence AS e ON e.fact_id = f.id
    LEFT JOIN knowledge_documents AS d ON d.id = e.source_document_id
    WHERE f.is_active AND f.status = 'found'
    ORDER BY f.offering_id, f.field_path, e.evidence_id"""
)
_LEGACY_CHUNKS = text(
    """SELECT d.document_kind AS kind,
           count(*) AS chunks,
           count(c.embedding) AS embedded
    FROM knowledge_chunks AS c
    JOIN knowledge_documents AS d ON d.id = c.document_id
    GROUP BY d.document_kind"""
)


class EvidenceRetentionAuditor:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def audit(self) -> EvidenceRetentionReport:
        async with self._sessions() as session:
            return await self._audit(session)

    @staticmethod
    async def _audit(session: AsyncSession) -> EvidenceRetentionReport:
        gaps: list[RetentionGap] = []
        orphan_rows = (await session.execute(_FACTS_WITHOUT_EVIDENCE)).all()
        for row in orphan_rows:
            gaps.append(
                RetentionGap(
                    kind="fact_without_evidence",
                    fact_id=row.id,
                    offering_id=row.offering_id,
                    field_path=row.field_path,
                    detail="accepted fact has no citation row",
                )
            )
        evidence_rows = (await session.execute(_EVIDENCE_ROWS)).all()
        missing_locator = missing_document = checksum_drift = 0
        for row in evidence_rows:
            locator = row.locator if isinstance(row.locator, dict) else {}
            if not row.quote or not row.quote.strip() or not locator:
                missing_locator += 1
                gaps.append(
                    RetentionGap(
                        kind="evidence_without_quote_or_locator",
                        fact_id=row.fact_id,
                        offering_id=row.offering_id,
                        field_path=row.field_path,
                        evidence_id=row.evidence_id,
                        detail="citation is not self-contained without chunk text",
                    )
                )
                continue
            if row.document_id is None:
                missing_document += 1
                gaps.append(
                    RetentionGap(
                        kind="evidence_without_retained_document",
                        fact_id=row.fact_id,
                        offering_id=row.offering_id,
                        field_path=row.field_path,
                        evidence_id=row.evidence_id,
                        detail="source document row is no longer retained",
                    )
                )
                continue
            if (
                row.source_checksum is not None
                and row.content_sha256 is not None
                and row.source_checksum != row.content_sha256
            ):
                checksum_drift += 1
                gaps.append(
                    RetentionGap(
                        kind="evidence_checksum_drift",
                        fact_id=row.fact_id,
                        offering_id=row.offering_id,
                        field_path=row.field_path,
                        evidence_id=row.evidence_id,
                        detail="retained document checksum differs from the citation",
                    )
                )
        chunk_counts = {
            row.kind: (row.chunks, row.embedded)
            for row in (await session.execute(_LEGACY_CHUNKS)).all()
        }
        source_chunks, source_embedded = chunk_counts.get("source", (0, 0))
        summary_chunks, summary_embedded = chunk_counts.get("offering_summary", (0, 0))
        active_found = (
            await session.execute(
                text(
                    "SELECT count(*) FROM tariff_facts "
                    "WHERE is_active AND status = 'found'"
                )
            )
        ).scalar_one()
        if not int(active_found):
            gaps.append(
                RetentionGap(
                    kind="no_active_structured_facts",
                    fact_id="",
                    offering_id="",
                    field_path="",
                    detail=(
                        "no accepted offering is projected, so the legacy chunks "
                        "are still the only evidence path"
                    ),
                )
            )
        return EvidenceRetentionReport(
            active_found_facts=int(active_found),
            active_evidence_rows=len(evidence_rows),
            facts_without_evidence=len(orphan_rows),
            evidence_without_locator=missing_locator,
            evidence_without_document=missing_document,
            evidence_with_checksum_drift=checksum_drift,
            legacy_source_chunks=int(source_chunks),
            legacy_summary_chunks=int(summary_chunks),
            legacy_embedded_chunks=int(source_embedded) + int(summary_embedded),
            gaps=tuple(gaps),
        )
