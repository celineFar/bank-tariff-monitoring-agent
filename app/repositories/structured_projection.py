"""Transactional persistence for accepted structured tariff read projections."""

from __future__ import annotations

import json

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.monitoring import SnapshotAttempt, SnapshotStatus
from app.domain.semantic_extraction import ExtractionStatus, SemanticExtractionResult
from app.services.structured_projection import StructuredTariffProjector


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


async def publish_structured_projection(
    session: AsyncSession,
    snapshot: SnapshotAttempt,
    *,
    display_name: str | None = None,
    aliases: tuple[str, ...] = (),
) -> None:
    """Publish the accepted read model inside the caller's snapshot transaction."""
    if snapshot.status is not SnapshotStatus.ACCEPTED:
        raise ValueError("structured projection requires an accepted snapshot")
    extraction = SemanticExtractionResult.model_validate(snapshot.semantic_extraction)
    product = extraction.loan_product
    if product is None:
        raise ValueError("accepted snapshot has no semantic product")
    name = display_name or (
        product.product_name.value
        if product.product_name.status is ExtractionStatus.FOUND
        else snapshot.offering_id.value.replace("_", " ").title()
    )
    projection = StructuredTariffProjector().project(
        snapshot, display_name=name, aliases=aliases
    )
    scope = {
        "bank": snapshot.bank.lower(),
        "product": snapshot.product.value,
        "offering_id": snapshot.offering_id.value,
        "snapshot_id": snapshot.id,
    }
    # The caller holds the offering advisory lock and transaction. Retire only
    # the current offering's active projection, preserving accepted history.
    for table in ("retrieval_units", "tariff_facts"):
        await session.execute(
            text(
                f"UPDATE {table} SET is_active = false WHERE snapshot_id IN "
                "(SELECT snapshot_id FROM offering_profiles WHERE bank = :bank "
                "AND product = :product AND offering_id = :offering_id "
                "AND is_active = true) AND is_active = true"
            ),
            scope,
        )
    await session.execute(
        text(
            """UPDATE offering_profiles SET is_active = false
            WHERE bank = :bank AND product = :product
              AND offering_id = :offering_id AND is_active = true"""
        ),
        scope,
    )
    profile = projection.profile
    await session.execute(
        text(
            """INSERT INTO offering_profiles (
                snapshot_id, bank, product, offering_id, display_name,
                extracted_name, formal_names, aliases, category, purposes,
                variants, property_market, attributes, accepted_at,
                schema_version, is_active
            ) VALUES (
                :snapshot_id, :bank, :product, :offering_id, :display_name,
                :extracted_name, CAST(:formal_names AS jsonb), CAST(:aliases AS jsonb),
                :category, CAST(:purposes AS jsonb), CAST(:variants AS jsonb),
                :property_market, CAST(:attributes AS jsonb), :accepted_at,
                :schema_version, true
            ) ON CONFLICT (snapshot_id) DO NOTHING"""
        ),
        {
            **scope,
            "display_name": profile.display_name,
            "extracted_name": profile.extracted_name,
            "formal_names": _json(profile.formal_names),
            "aliases": _json(profile.aliases),
            "category": profile.category,
            "purposes": _json(profile.purposes),
            "variants": _json(profile.variants),
            "property_market": profile.property_market,
            "attributes": _json(profile.attributes),
            "accepted_at": profile.accepted_at,
            "schema_version": profile.schema_version,
        },
    )
    source_keys = tuple(
        {
            item.source_document_key
            for fact in projection.facts
            for item in fact.evidence
            if item.source_document_key
        }
    )
    cited_urls: dict[str, set[str]] = {}
    for fact in projection.facts:
        for evidence in fact.evidence:
            if evidence.source_document_key:
                cited_urls.setdefault(evidence.source_document_key, set()).add(
                    str(evidence.source_url)
                )
    linked_documents: dict[str, tuple[object, str]] = {}
    if source_keys:
        linked_rows = (
            await session.execute(
                text(
                    """SELECT document_key, id, content_sha256, source_url, final_url
                    FROM knowledge_documents
                    WHERE run_id = :run_id AND offering_id = :offering_id
                      AND document_key = ANY(:source_keys)
                    ORDER BY is_active DESC, retrieved_at DESC"""
                ),
                {
                    "run_id": snapshot.run_id,
                    "offering_id": snapshot.offering_id.value,
                    "source_keys": list(source_keys),
                },
            )
        ).all()
        for row in linked_rows:
            if row.source_url in cited_urls.get(
                row.document_key, ()
            ) or row.final_url in cited_urls.get(row.document_key, ()):
                linked_documents.setdefault(
                    row.document_key, (row.id, row.content_sha256)
                )
    # Reprojection after a process restart is idempotent. Existing immutable
    # fact/evidence rows remain unchanged; only active state is restored.
    await session.execute(
        text(
            "UPDATE offering_profiles SET is_active = true WHERE snapshot_id = :snapshot_id"
        ),
        scope,
    )
    for fact in projection.facts:
        await session.execute(
            text(
                """INSERT INTO tariff_facts (
                    id, snapshot_id, offering_id, field_path, variant_key,
                    status, value_json, number_value, unit, currency,
                    rate_basis, fee_scope, conditions, taxonomy_version, is_active
                ) VALUES (
                    :id, :snapshot_id, :offering_id, :field_path, :variant_key,
                    :status, CAST(:value_json AS jsonb), :number_value, :unit, :currency,
                    :rate_basis, :fee_scope, CAST(:conditions AS jsonb),
                    :taxonomy_version, true
                ) ON CONFLICT (id) DO UPDATE SET is_active = true"""
            ),
            {
                "id": fact.fact_id,
                "snapshot_id": fact.snapshot_id,
                "offering_id": fact.offering_id.value,
                "field_path": fact.field_path.value,
                "variant_key": fact.variant_key,
                "status": fact.status.value,
                "value_json": _json(fact.value) if fact.value is not None else None,
                "number_value": fact.number,
                "unit": fact.unit,
                "currency": fact.currency,
                "rate_basis": fact.rate_basis.value if fact.rate_basis else None,
                "fee_scope": fact.fee_scope,
                "conditions": _json(fact.conditions),
                "taxonomy_version": fact.taxonomy_version,
            },
        )
        for evidence in fact.evidence:
            await session.execute(
                text(
                    """INSERT INTO fact_evidence (
                        fact_id, evidence_id, quote, source_url, source_item_id,
                        source_document_key, source_document_id, source_checksum,
                        locator, authority
                    ) VALUES (
                        :fact_id, :evidence_id, :quote, :source_url, :source_item_id,
                        :source_document_key, :source_document_id, :source_checksum,
                        CAST(:locator AS jsonb), :authority
                    ) ON CONFLICT (fact_id, evidence_id) DO NOTHING"""
                ),
                {
                    "fact_id": fact.fact_id,
                    "evidence_id": evidence.evidence_id,
                    "quote": evidence.quote,
                    "source_url": str(evidence.source_url),
                    "source_item_id": evidence.source_item_id,
                    "source_document_key": evidence.source_document_key,
                    "source_document_id": linked_documents.get(
                        evidence.source_document_key, (None, None)
                    )[0],
                    "source_checksum": linked_documents.get(
                        evidence.source_document_key, (None, None)
                    )[1],
                    "locator": _json(evidence.locator),
                    "authority": evidence.authority,
                },
            )
    for unit in projection.units:
        await session.execute(
            text(
                """INSERT INTO retrieval_units (
                    id, snapshot_id, offering_id, kind, field_paths, fact_ids,
                    evidence_ids, language, identity_text, alias_purpose_text,
                    detail_text, content, content_sha256, renderer_version,
                    is_active
                ) VALUES (
                    :id, :snapshot_id, :offering_id, :kind, :field_paths, :fact_ids,
                    :evidence_ids, :language, :identity_text, :alias_purpose_text,
                    :detail_text, :content, :content_sha256, :renderer_version,
                    true
                ) ON CONFLICT (id) DO UPDATE SET is_active = true"""
            ),
            {
                "id": unit.unit_id,
                "snapshot_id": unit.snapshot_id,
                "offering_id": unit.offering_id.value,
                "kind": unit.kind.value,
                "field_paths": [path.value for path in unit.field_paths],
                "fact_ids": list(unit.fact_ids),
                "evidence_ids": list(unit.evidence_ids),
                "language": unit.language,
                "identity_text": unit.identity_text,
                "alias_purpose_text": unit.alias_purpose_text,
                "detail_text": unit.detail_text,
                "content": unit.content,
                "content_sha256": unit.content_sha256,
                "renderer_version": unit.renderer_version,
            },
        )
