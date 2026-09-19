from __future__ import annotations

import difflib
import json
import re
from collections import defaultdict
from pathlib import Path

from app.domain.normalization import (
    NormalizedBlock,
    NormalizedDocument,
    NormalizedSourceBundle,
    NormalizedTable,
)
from app.domain.pdf_extraction import PdfExtractionResponse
from app.domain.semantic_extraction import (
    ExtractionStatus,
    SemanticExtractionPlan,
    SemanticExtractionResult,
)
from app.domain.source_discovery import (
    Relevance,
    SourceAssessment,
    SourceDiscoveryResult,
    TemporalStatus,
)
from app.services.normalized_renderer import render_normalized_markdown


def human_filename(value: str, *, index: int, extension: str) -> str:
    """Return a stable, readable filename that cannot escape its directory."""
    stem = Path(value).stem
    stem = re.sub(r"[^\w.-]+", "_", stem, flags=re.UNICODE).strip("._-")
    stem = re.sub(r"_+", "_", stem)[:100] or "document"
    suffix = extension if extension.startswith(".") else f".{extension}"
    return f"{index + 1:03d}_{stem}{suffix.lower()}"


def render_pdf_response_markdown(
    name: str, source_url: str, response: PdfExtractionResponse
) -> str:
    """Render Gemini's page-structured response before deterministic normalization."""
    parts = [f"# {name}", "", f"Source: <{source_url}>", ""]
    for page in sorted(response.pages, key=lambda item: item.page_number):
        parts.extend((f"## PDF page {page.page_number}", ""))
        for block in page.blocks:
            if block.type.value == "heading":
                level = min(max(len(block.heading_path) + 2, 3), 6)
                parts.extend((f"{'#' * level} {block.text}", ""))
            elif block.type.value == "list":
                lines = [
                    line.strip() for line in block.text.splitlines() if line.strip()
                ]
                parts.extend((*(f"- {line.lstrip('-•▪◦ ')}" for line in lines), ""))
            else:
                parts.extend((block.text, ""))
        for table in page.tables:
            if table.title:
                parts.extend((f"### {table.title}", ""))
            width = len(table.headers) or (
                len(table.rows[0].cells) if table.rows else 0
            )
            if width:
                headers = table.headers or tuple(
                    f"Column {i + 1}" for i in range(width)
                )
                parts.extend(
                    (
                        "| " + " | ".join(_cell(value) for value in headers) + " |",
                        "| " + " | ".join("---" for _ in range(width)) + " |",
                    )
                )
                parts.extend(
                    "| " + " | ".join(_cell(value) for value in row.cells) + " |"
                    for row in table.rows
                )
                parts.append("")
            for note in table.notes:
                parts.extend((f"> {note}", ""))
        for note in page.notes:
            parts.extend((f"> {note}", ""))
    return "\n".join(parts).rstrip() + "\n"


def render_document_markdown(document: NormalizedDocument) -> str:
    bundle = NormalizedSourceBundle(
        canonical_url=document.source_url,
        acquisition_content_hash=document.content_sha256,
        documents=(document,),
    )
    return render_normalized_markdown(bundle)


def render_diff_markdown(
    title: str,
    comparisons: tuple[tuple[str, str, str], ...],
) -> str:
    parts = [
        f"# {title}",
        "",
        "This report uses a unified diff: unchanged context starts with a space, "
        "removed source content starts with `-`, and normalized content added in its "
        "place starts with `+`. No diff means normalization preserved the rendered text.",
        "",
    ]
    for name, acquired, normalized in comparisons:
        parts.extend((f"## {name}", ""))
        diff = list(
            difflib.unified_diff(
                acquired.splitlines(),
                normalized.splitlines(),
                fromfile="acquired-or-reconstructed",
                tofile="normalized",
                lineterm="",
                n=3,
            )
        )
        if not diff:
            parts.extend(("**No textual rendering changes.**", ""))
            continue
        parts.extend(("```diff", *diff, "```", ""))
    return "\n".join(parts).rstrip() + "\n"


def render_source_selection(
    bundle: NormalizedSourceBundle,
    result: SourceDiscoveryResult | None,
    *,
    error: Exception | None = None,
) -> str:
    assessments = _assessment_index(result.assessments if result else ())
    parts = [
        "# Source-discovery selection",
        "",
        "Legend: **SELECTED** is eligible for current semantic extraction; "
        "**REJECTED** is irrelevant, historical, or future material; "
        "**UNASSESSED** means source discovery did not produce a decision.",
        "",
    ]
    if error is not None:
        parts.extend(
            (
                "## Stage error",
                "",
                f"**{type(error).__name__}:** {_safe(str(error))}",
                "",
            )
        )
    for document in bundle.documents:
        parts.extend(
            (f"## {_safe(document.name)}", "", f"Source: <{document.source_url}>", "")
        )
        document_assessment = assessments.get(document.id)
        parts.extend(_decision_lines(document.id, document_assessment))
        for block in document.blocks:
            parts.extend(_render_selected_block(block, assessments.get(block.id)))
        for table in document.tables:
            parts.extend(_render_selected_table(table, assessments.get(table.id)))
        if document.links:
            parts.extend(
                (
                    "### NOT A CLASSIFICATION UNIT — normalized links",
                    "",
                    "Links remain available as provenance, but source discovery does not "
                    "independently classify navigation targets as extraction evidence.",
                    "",
                    *(
                        f"- `{link.id}` — {_safe(link.text or '(no label)')}; <{link.url}>"
                        for link in document.links
                    ),
                    "",
                )
            )
    return "\n".join(parts).rstrip() + "\n"


def render_semantic_extraction(
    discovery: SourceDiscoveryResult,
    plan: SemanticExtractionPlan,
    result: SemanticExtractionResult | None,
    *,
    error: Exception | None = None,
) -> str:
    sent_ids = {item.evidence_id for batch in plan.batches for item in batch.evidence}
    field_citations: dict[str, list[str]] = defaultdict(list)
    field_rows: list[tuple[str, str, str, str]] = []
    if result is not None:
        for response in result.batch_results:
            for item in response.results:
                for citation in item.evidence:
                    field_citations[citation.evidence_id].append(item.field.value)
                value = item.value_json if item.value_json is not None else "—"
                field_rows.append(
                    (
                        item.field.value,
                        item.status.value,
                        value,
                        item.explanation or "",
                    )
                )

    parts = [
        "# Semantic extraction audit",
        "",
        f"Product: **{discovery.product.value}**  ",
        f"Model: **{result.model_name if result else plan.model_name}**",
        "",
        "Evidence annotations distinguish content that produced a cited value, content "
        "sent to Gemini but not cited, and source-discovered content omitted by the "
        "bounded semantic planner.",
        "",
    ]
    if error is not None:
        parts.extend(
            (
                "## Stage error",
                "",
                f"**FAILED — {type(error).__name__}:** {_safe(str(error))}",
                "",
                "The evidence packets below remain available for diagnosis. Items that "
                "were sent are marked failed because no validated result was assembled.",
                "",
            )
        )
    if field_rows:
        parts.extend(("## Field outcomes", ""))
        for field, status, value, explanation in field_rows:
            marker = {
                ExtractionStatus.FOUND.value: "EXTRACTED",
                ExtractionStatus.NOT_STATED.value: "NOT STATED",
                ExtractionStatus.AMBIGUOUS.value: "AMBIGUOUS",
                ExtractionStatus.CONFLICTING.value: "CONFLICTING",
            }[status]
            parts.extend(
                (
                    f"### {field} — {marker}",
                    "",
                    "```json",
                    _pretty_json(value),
                    "```",
                    *(
                        (f"Explanation: {_safe(explanation)}", "")
                        if explanation
                        else ()
                    ),
                )
            )

    parts.extend(("## Source-discovered evidence", ""))
    for evidence in plan.evidence_catalog:
        cited_fields = sorted(set(field_citations.get(evidence.evidence_id, ())))
        if cited_fields:
            state = "EXTRACTED"
            explanation = "Cited for: " + ", ".join(cited_fields)
        elif evidence.evidence_id in sent_ids and error is not None:
            state = "FAILED"
            explanation = "Sent to the LLM, but the extraction run did not produce a validated result."
        elif evidence.evidence_id in sent_ids:
            state = "SENT, NOT CITED"
            explanation = (
                "Inspected by the LLM but not used as evidence for a returned field."
            )
        else:
            state = "SKIPPED BY PLANNER"
            explanation = "Accepted by source discovery but not selected for any bounded field packet."
        parts.extend(
            (
                f"### {state} — `{evidence.evidence_id}`",
                "",
                f"{explanation}  ",
                f"Source item: `{evidence.source_item_id}`  ",
                f"Role / authority: `{evidence.role.value}` / `{evidence.authority.value}`  ",
                f"Temporal status: `{evidence.temporal_status.value}`  ",
                f"Section: {_safe(evidence.section or '(none)')}",
                "",
                "```text",
                evidence.content,
                "```",
                "",
            )
        )
    return "\n".join(parts).rstrip() + "\n"


def _assessment_index(
    assessments: tuple[SourceAssessment, ...],
) -> dict[str, SourceAssessment]:
    result: dict[str, SourceAssessment] = {}
    for assessment in assessments:
        result[assessment.source_id] = assessment
        for reference in assessment.source_refs:
            result.setdefault(reference.source_item_id, assessment)
    return result


def _decision_lines(
    source_id: str, assessment: SourceAssessment | None
) -> tuple[str, ...]:
    if assessment is None:
        return (f"### UNASSESSED — `{source_id}`", "")
    accepted = (
        assessment.relevance is not Relevance.IRRELEVANT
        and assessment.temporal_status
        not in {
            TemporalStatus.POSSIBLY_STALE,
            TemporalStatus.FUTURE,
        }
    )
    state = "SELECTED" if accepted else "REJECTED"
    return (
        f"### {state} — `{source_id}`",
        "",
        f"Decision: `{assessment.decision_source.value}`; relevance: "
        f"`{assessment.relevance.value}`; role: `{assessment.role.value}`; temporal: "
        f"`{assessment.temporal_status.value}`  ",
        f"Reason: {_safe(assessment.reason)}",
        "",
    )


def _render_selected_block(
    block: NormalizedBlock, assessment: SourceAssessment | None
) -> tuple[str, ...]:
    parts = list(_decision_lines(block.id, assessment))
    parts.extend(("```text", block.text, "```", ""))
    return tuple(parts)


def _render_selected_table(
    table: NormalizedTable, assessment: SourceAssessment | None
) -> tuple[str, ...]:
    parts = list(_decision_lines(table.id, assessment))
    if table.title:
        parts.extend((f"**Table: {_safe(table.title)}**", ""))
    width = len(table.headers) or (len(table.rows[0].cells) if table.rows else 0)
    if width:
        headers = table.headers or tuple(f"Column {i + 1}" for i in range(width))
        parts.extend(
            (
                "| " + " | ".join(_cell(value) for value in headers) + " |",
                "| " + " | ".join("---" for _ in range(width)) + " |",
            )
        )
        parts.extend(
            "| " + " | ".join(_cell(cell.text) for cell in row.cells) + " |"
            for row in table.rows
        )
        parts.append("")
    for note in table.notes:
        parts.extend((f"> {_safe(note.text)}", ""))
    return tuple(parts)


def _pretty_json(value: str) -> str:
    if value == "—":
        return "null"
    try:
        return json.dumps(json.loads(value), ensure_ascii=False, indent=2)
    except json.JSONDecodeError:
        return value


def _cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\r", "").replace("\n", "<br>")


def _safe(value: str) -> str:
    return value.replace("<", "&lt;").replace(">", "&gt;")
