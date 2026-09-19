from __future__ import annotations

import difflib
import html
import json
import re
from collections import defaultdict
from itertools import pairwise
from pathlib import Path

from app.domain.normalization import (
    NormalizedBlock,
    NormalizedBlockType,
    NormalizedDocument,
    NormalizedSourceBundle,
    NormalizedTable,
)
from app.domain.pdf_extraction import PdfExtractionResponse
from app.domain.semantic_extraction import (
    ExtractionReviewItem,
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
        "This report is the normalized document itself with transformations annotated "
        "in place. Unchanged content is shown normally, removed source content is "
        "shown as red strikethrough text, and added normalized content is shown with "
        "a green highlight.",
        "",
        '<span style="background:#ffe6e6;color:#b42318;padding:0.1em 0.25em;">'
        "<del>removed</del></span> &nbsp; "
        '<span style="background:#e6ffed;color:#116329;padding:0.1em 0.25em;">'
        "<ins>added</ins></span>",
        "",
    ]
    for name, acquired, normalized in comparisons:
        parts.extend(("---", "", f"## {name}", ""))
        rendered, changed = _render_annotated_document(acquired, normalized)
        if not changed:
            parts.extend(("**No textual rendering changes.**", ""))
        parts.extend((rendered, ""))
    return "\n".join(parts).rstrip() + "\n"


def render_source_selection(
    bundle: NormalizedSourceBundle,
    result: SourceDiscoveryResult | None,
    *,
    error: Exception | None = None,
) -> str:
    assessments = _assessment_index(result.assessments if result else ())
    parts = [
        "# Source-discovery selection decisions",
        "",
        "This is the normalized content in its original document order with a "
        "source-discovery semantic overlay. The labels are annotations; the content "
        "beneath them remains the normalized source structure.",
        "",
        "- **Green — SELECTED:** relevant, current material eligible for extraction.",
        "- **Orange — SELECTED WITH UNCERTAINTY:** possibly relevant, time-bounded, "
        "or temporally unknown material that remains eligible for extraction.",
        "- **Gray — HISTORICAL:** retained for audit but excluded from current terms.",
        "- **Blue — FUTURE:** retained for audit but excluded from current terms.",
        "- **White — NOT SELECTED / UNASSESSED:** unchanged content without an "
        "accepted current extraction decision.",
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
            (
                "---",
                "",
                f"## {_safe(document.name)}",
                "",
                f"Source: <{document.source_url}>",
                "",
            )
        )
        document_assessment = assessments.get(document.id)
        parts.extend(_discovery_label(document.id, document_assessment))
        table_by_id = {table.id: table for table in document.tables}
        rendered_tables: set[str] = set()
        for block in document.blocks:
            if block.type is NormalizedBlockType.TABLE and block.table_id:
                table = table_by_id.get(block.table_id)
                if table is not None:
                    parts.extend(
                        _render_discovery_table(table, assessments.get(table.id))
                    )
                    rendered_tables.add(table.id)
                continue
            parts.extend(_render_discovery_block(block, assessments.get(block.id)))
        for table in document.tables:
            if table.id not in rendered_tables:
                parts.extend(_render_discovery_table(table, assessments.get(table.id)))
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


def render_source_selection_diff(
    bundle: NormalizedSourceBundle,
    result: SourceDiscoveryResult | None,
    *,
    error: Exception | None = None,
) -> str:
    """Render normalized source structure with selection decisions inline."""
    assessments = _assessment_index(result.assessments if result else ())
    parts = [
        "# Source-discovery selection diff",
        "",
        "This report preserves the normalized document order and Markdown structure. "
        "Green content is retained for semantic extraction, orange content is retained "
        "with uncertainty, and red strikethrough content is removed from extraction "
        "evidence. The text itself is not rewritten.",
        "",
        '<span style="background:#e6ffed;color:#116329;padding:0.1em 0.25em;">'
        "retained</span> &nbsp; "
        '<span style="background:#fff4e5;color:#b54708;padding:0.1em 0.25em;">'
        "retained with uncertainty</span> &nbsp; "
        '<span style="background:#ffe6e6;color:#b42318;padding:0.1em 0.25em;">'
        "<del>removed</del></span>",
        "",
    ]
    if error is not None:
        parts.extend(
            (
                "## Stage error",
                "",
                f"**{type(error).__name__}:** {_safe(str(error))}",
                "",
                "No completed selection exists; content below is shown without a "
                "keep/remove decision.",
                "",
            )
        )
    for document in bundle.documents:
        parts.extend(
            (
                "---",
                "",
                f"## {_safe(document.name)}",
                "",
                f"Source: <{document.source_url}>",
                "",
            )
        )
        table_by_id = {table.id: table for table in document.tables}
        rendered_tables: set[str] = set()
        for block in document.blocks:
            if block.type is NormalizedBlockType.TABLE and block.table_id:
                table = table_by_id.get(block.table_id)
                if table is not None:
                    parts.extend(
                        _render_source_diff_table(
                            table,
                            assessments.get(table.id),
                            decisions_available=result is not None,
                        )
                    )
                    rendered_tables.add(table.id)
                continue
            parts.extend(
                (
                    _render_source_diff_block(
                        block,
                        assessments.get(block.id),
                        decisions_available=result is not None,
                    ),
                    "",
                )
            )
        for table in document.tables:
            if table.id not in rendered_tables:
                parts.extend(
                    _render_source_diff_table(
                        table,
                        assessments.get(table.id),
                        decisions_available=result is not None,
                    )
                )
    return "\n".join(parts).rstrip() + "\n"


def render_semantic_extraction(
    bundle: NormalizedSourceBundle,
    discovery: SourceDiscoveryResult,
    plan: SemanticExtractionPlan,
    result: SemanticExtractionResult | None,
    *,
    error: Exception | None = None,
) -> str:
    sent_groups: dict[str, list[str]] = defaultdict(list)
    for batch in plan.batches:
        for item in batch.evidence:
            sent_groups[item.evidence_id].append(batch.group)
    sent_ids = set(sent_groups)
    field_citations: dict[str, list[str]] = defaultdict(list)
    cited_by_source: dict[str, list[tuple[str, str, str]]] = defaultdict(list)
    field_rows: list[tuple[str, str, str, str, bool]] = []
    field_labels: dict[str, str] = {}
    if result is not None:
        review_fields = {item.field.value for item in result.review_items}
        evidence_by_id = {item.evidence_id: item for item in result.evidence_catalog}
        found_fields = sorted(
            {
                item.field.value
                for response in result.batch_results
                for item in response.results
                if item.status is ExtractionStatus.FOUND
            }
        )
        field_labels = {
            field: f"EX-{index:03d}"
            for index, field in enumerate(found_fields, start=1)
        }
        for response in result.batch_results:
            for item in response.results:
                for citation in item.evidence:
                    field_citations[citation.evidence_id].append(item.field.value)
                    evidence = evidence_by_id.get(citation.evidence_id)
                    if evidence is not None and item.status is ExtractionStatus.FOUND:
                        cited_by_source[evidence.source_item_id].append(
                            (
                                field_labels[item.field.value],
                                item.field.value,
                                citation.quote,
                            )
                        )
                value = item.value_json if item.value_json is not None else "—"
                field_rows.append(
                    (
                        item.field.value,
                        item.status.value,
                        value,
                        item.explanation or "",
                        item.field.value in review_fields,
                    )
                )

    parts = [
        "# Semantic extraction audit",
        "",
        f"Product: **{discovery.product.value}**  ",
        f"Model: **{result.model_name if result else plan.model_name}**",
        "",
        "Before Gemini extraction, a deterministic extraction planner groups requested "
        "fields (for example rates, fees, or eligibility), ranks accepted evidence by "
        "its source-discovery role, keywords, and authority precedence, and enforces "
        "configured item/character limits. It does not decide whether a tariff value "
        "is true and it does not use an LLM.",
        "",
        "**NOT SENT TO SEMANTIC LLM** therefore means the evidence was accepted by "
        "source discovery but was not included in any bounded field packet after that "
        "deterministic ranking and size/count limiting. It was not rejected as false "
        "or irrelevant.",
        "",
        "In the document overlays below, only exact quotations cited by successful "
        "`found` results are highlighted. Text that was inspected but not cited remains "
        "visually unchanged.",
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
        for field, status, value, explanation, needs_review in field_rows:
            marker = "NEEDS HUMAN REVIEW" if needs_review else {
                ExtractionStatus.FOUND.value: "EXTRACTED",
                ExtractionStatus.NOT_STATED.value: "NOT STATED",
                ExtractionStatus.AMBIGUOUS.value: "AMBIGUOUS",
                ExtractionStatus.CONFLICTING.value: "CONFLICTING",
            }[status]
            label = field_labels.get(field)
            anchor = f'<a id="{label.lower()}"></a>' if label else ""
            color = "#fee4e2" if needs_review else "#ecfdf3"
            border = "#d92d20" if needs_review else "#12b76a"
            parts.extend(
                (
                    "---",
                    "",
                    anchor,
                    f'<div style="border-left:5px solid {border};background:{color};'
                    f'padding:0.55em 0.8em;"><strong>'
                    f"{f'[{label}] ' if label else ''}{field} — {marker}"
                    "</strong></div>",
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
    parts.extend(("## Extraction overlay", ""))
    if result is not None and field_rows:
        parts.extend(
            ("### Label index", "", "| Label | Field | Status |", "|---|---|---|")
        )
        for field, status, _, _, needs_review in field_rows:
            label = field_labels.get(field, "—")
            rendered_status = "needs_review" if needs_review else status
            parts.append(f"| `{label}` | `{field}` | `{rendered_status}` |")
        parts.append("")
    parts.extend(_render_extraction_documents(bundle, cited_by_source))

    parts.extend(("## Planner audit", ""))
    for evidence in plan.evidence_catalog:
        cited_fields = sorted(set(field_citations.get(evidence.evidence_id, ())))
        packets = ", ".join(sorted(set(sent_groups[evidence.evidence_id]))) or "(none)"
        if cited_fields:
            state = "EXTRACTED: " + ", ".join(cited_fields)
        elif evidence.evidence_id in sent_ids and error is not None:
            state = "FAILED RUN"
        elif evidence.evidence_id in sent_ids:
            state = "SENT, NOT CITED"
        else:
            state = "NOT SENT TO SEMANTIC LLM"
        parts.append(
            f"- `{evidence.evidence_id}` / `{evidence.source_item_id}` — "
            f"**{state}**; packets: {packets}"
        )
    parts.append("")
    return "\n".join(parts).rstrip() + "\n"


def render_pre_validation(result: SemanticExtractionResult) -> str:
    """Render model-produced values before canonical field validation."""
    review_by_field = {item.field: item for item in result.review_items}
    validated = {item.field for item in result.validated_fields}
    parts = [
        "# Pre-validation semantic extraction audit",
        "",
        "This preserves what Gemini produced before canonical field validation. "
        "Green passed validation, red failed and entered human review, and orange "
        "is valid but semantically ambiguous or conflicting.",
        "",
    ]
    for output in result.raw_batch_outputs:
        parts.extend(("---", "", f"## {output.batch_id}: {_safe(output.group)}", ""))
        if output.parsed_response is None:
            parts.extend(
                (
                    '<div style="border-left:5px solid #d92d20;background:#fee4e2;'
                    'padding:0.55em 0.8em;"><strong>BATCH RESPONSE COULD NOT BE '
                    "VALIDATED</strong></div>",
                    "",
                    f"Error: {_safe(output.error or 'unknown parsing error')}",
                    "",
                    "```json",
                    output.raw_response or "(no raw response was returned)",
                    "```",
                    "",
                )
            )
            continue
        for item in output.parsed_response.results:
            review = review_by_field.get(item.field)
            if review is not None:
                label, color, border = "INVALID — HUMAN REVIEW", "#fee4e2", "#d92d20"
            elif item.status in {
                ExtractionStatus.AMBIGUOUS,
                ExtractionStatus.CONFLICTING,
            }:
                label, color, border = item.status.value.upper(), "#fff4e5", "#f79009"
            elif item.field in validated:
                label, color, border = "VALIDATED", "#ecfdf3", "#12b76a"
            else:
                label, color, border = "NOT VALIDATED", "#f2f4f7", "#667085"
            parts.extend(
                (
                    f'<div style="border-left:5px solid {border};background:{color};'
                    f'padding:0.55em 0.8em;margin-top:1em;"><strong>'
                    f"{_safe(item.field.value)} — {label}</strong></div>",
                    "",
                    "```json",
                    _pretty_json(item.value_json if item.value_json is not None else "—"),
                    "```",
                    "",
                )
            )
            if review is not None:
                parts.extend(
                    f"- `{_safe('.'.join(map(str, issue.location)))}`: "
                    f"{_safe(issue.message)} (`{_safe(issue.error_type)}`)"
                    for issue in review.validation_issues
                )
                parts.append("")
    return "\n".join(parts).rstrip() + "\n"


def render_unparsed_pre_validation(
    raw_responses: dict[str, str], error: Exception
) -> str:
    parts = [
        "# Pre-validation semantic extraction audit",
        "",
        '<div style="border-left:5px solid #d92d20;background:#fee4e2;'
        'padding:0.55em 0.8em;"><strong>SYSTEMIC EXTRACTION FAILURE</strong></div>',
        "",
        f"{type(error).__name__}: {_safe(str(error))}",
        "",
        "The raw model responses below were captured before response-schema or "
        "canonical field validation. No usable batch response was produced.",
        "",
    ]
    if not raw_responses:
        parts.extend(("No raw model response was returned.", ""))
    for batch_id, raw_response in raw_responses.items():
        parts.extend(
            (
                "---",
                "",
                f"## {_safe(batch_id)} — INVALID",
                "",
                "```json",
                raw_response,
                "```",
                "",
            )
        )
    return "\n".join(parts).rstrip() + "\n"


def render_review_queue(items: tuple[ExtractionReviewItem, ...]) -> str:
    parts = [
        "# Semantic extraction human-review queue",
        "",
        f"Open review items: **{len(items)}**",
        "",
        "Each item preserves the original model value, validation path, evidence "
        "IDs, batch, and model.",
        "",
    ]
    if not items:
        parts.extend(("No human review is required.", ""))
    for item in items:
        parts.extend(
            (
                "---",
                "",
                f"## {item.field.value}",
                "",
                f"Review ID: `{item.review_id}`  ",
                f"Batch: `{item.batch_id}`  ",
                f"Model: `{item.model_name}`  ",
                "Evidence: "
                + (", ".join(f"`{value}`" for value in item.evidence_ids) or "(none)"),
                "",
                "### Validation problems",
                "",
            )
        )
        parts.extend(
            f"- `{_safe('.'.join(map(str, issue.location)))}`: "
            f"{_safe(issue.message)} (`{_safe(issue.error_type)}`)"
            for issue in item.validation_issues
        )
        parts.extend(("", "### Raw field output", "", "```json"))
        parts.append(
            item.raw_result.model_dump_json(indent=2)
            if item.raw_result is not None
            else item.raw_response or "(no raw field result was parsed)"
        )
        parts.extend(("```", ""))
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


def _discovery_label(
    source_id: str, assessment: SourceAssessment | None
) -> tuple[str, ...]:
    state, color, border = _discovery_appearance(assessment)
    if assessment is None:
        details = "No source-discovery assessment was produced."
    else:
        details = (
            f"{assessment.role.value} · {assessment.relevance.value} · "
            f"{assessment.temporal_status.value} · {assessment.decision_source.value}"
        )
    reason = assessment.reason if assessment is not None else ""
    label = (
        f'<div style="border-left:5px solid {border};background:{color};'
        'padding:0.55em 0.8em;margin:1.2em 0 0.65em 0;">'
        f"<strong>{html.escape(state)}</strong> &nbsp; "
        f"<code>{html.escape(source_id)}</code><br>"
        f"<small>{html.escape(details)}</small>"
        + (f"<br><small>{html.escape(reason)}</small>" if reason else "")
        + "</div>"
    )
    return (label, "")


def _discovery_appearance(
    assessment: SourceAssessment | None,
) -> tuple[str, str, str]:
    if assessment is None:
        return "UNASSESSED", "#ffffff", "#98a2b3"
    if assessment.relevance is Relevance.IRRELEVANT:
        return "NOT SELECTED", "#ffffff", "#d0d5dd"
    if assessment.temporal_status is TemporalStatus.POSSIBLY_STALE:
        return "HISTORICAL — NOT SELECTED", "#f2f4f7", "#667085"
    if assessment.temporal_status is TemporalStatus.FUTURE:
        return "FUTURE — NOT SELECTED", "#eef4ff", "#3e7bfa"
    if (
        assessment.relevance is Relevance.POSSIBLY_RELEVANT
        or assessment.temporal_status
        in {TemporalStatus.UNKNOWN, TemporalStatus.TIME_BOUNDED}
    ):
        return "SELECTED WITH UNCERTAINTY", "#fff4e5", "#f79009"
    return "SELECTED", "#ecfdf3", "#12b76a"


def _render_discovery_block(
    block: NormalizedBlock, assessment: SourceAssessment | None
) -> tuple[str, ...]:
    parts = list(_discovery_label(block.id, assessment))
    _, color, _ = _discovery_appearance(assessment)
    highlight = color if color != "#ffffff" else None
    parts.extend((_render_block_content(block, background=highlight), ""))
    return tuple(parts)


def _render_discovery_table(
    table: NormalizedTable, assessment: SourceAssessment | None
) -> tuple[str, ...]:
    parts = list(_discovery_label(table.id, assessment))
    if table.title:
        parts.extend((f"**Table: {_safe(table.title)}**", ""))
    width = len(table.headers) or (len(table.rows[0].cells) if table.rows else 0)
    if width:
        headers = table.headers or tuple(f"Column {i + 1}" for i in range(width))
        parts.extend(
            (
                "| " + " | ".join(_table_cell(value) for value in headers) + " |",
                "| " + " | ".join("---" for _ in range(width)) + " |",
            )
        )
        parts.extend(
            "| " + " | ".join(_table_cell(cell.text) for cell in row.cells) + " |"
            for row in table.rows
        )
        parts.append("")
    for note in table.notes:
        parts.extend((f"> {_safe(note.text)}", ""))
    return tuple(parts)


def _render_source_diff_block(
    block: NormalizedBlock,
    assessment: SourceAssessment | None,
    *,
    decisions_available: bool,
) -> str:
    color, removed = _source_diff_appearance(
        assessment, decisions_available=decisions_available
    )
    lines = [
        _source_diff_highlight(line, color=color, removed=removed)
        for line in block.text.splitlines()
    ] or [""]
    if block.type is NormalizedBlockType.HEADING:
        level = min(max(len(block.heading_path), 1) + 1, 6)
        return f"{'#' * level} " + "<br>".join(lines)
    if block.type is NormalizedBlockType.LIST:
        return "\n".join(f"- {line}" for line in lines if line.strip())
    if block.type is NormalizedBlockType.CARD and block.fields:
        title = _source_diff_highlight(
            block.fields.get("title", ""), color=color, removed=removed
        )
        body = _source_diff_highlight(
            block.fields.get("body", ""), color=color, removed=removed
        )
        return f"### {title}\n\n{body}".strip()
    return "  \n".join(lines)


def _render_source_diff_table(
    table: NormalizedTable,
    assessment: SourceAssessment | None,
    *,
    decisions_available: bool,
) -> tuple[str, ...]:
    color, removed = _source_diff_appearance(
        assessment, decisions_available=decisions_available
    )
    parts: list[str] = []
    if table.title:
        parts.extend(
            (
                "### "
                + _source_diff_highlight(table.title, color=color, removed=removed),
                "",
            )
        )
    width = len(table.headers) or (len(table.rows[0].cells) if table.rows else 0)
    if width:
        headers = table.headers or tuple(f"Column {index + 1}" for index in range(width))
        parts.extend(
            (
                "| "
                + " | ".join(
                    _cell(
                        _source_diff_highlight(
                            value, color=color, removed=removed
                        )
                    )
                    for value in headers
                )
                + " |",
                "| " + " | ".join("---" for _ in range(width)) + " |",
            )
        )
        for row in table.rows:
            parts.append(
                "| "
                + " | ".join(
                    _cell(
                        _source_diff_highlight(
                            cell.text, color=color, removed=removed
                        )
                    )
                    for cell in row.cells
                )
                + " |"
            )
        parts.append("")
    for note in table.notes:
        parts.extend(
            (
                "> "
                + _source_diff_highlight(note.text, color=color, removed=removed),
                "",
            )
        )
    return tuple(parts)


def _source_diff_appearance(
    assessment: SourceAssessment | None,
    *,
    decisions_available: bool,
) -> tuple[str, bool]:
    if not decisions_available:
        return "#f2f4f7", False
    if assessment is None:
        return "#ffe6e6", True
    if assessment.relevance is Relevance.IRRELEVANT or assessment.temporal_status in {
        TemporalStatus.POSSIBLY_STALE,
        TemporalStatus.FUTURE,
    }:
        return "#ffe6e6", True
    if (
        assessment.relevance is Relevance.POSSIBLY_RELEVANT
        or assessment.temporal_status
        in {TemporalStatus.UNKNOWN, TemporalStatus.TIME_BOUNDED}
    ):
        return "#fff4e5", False
    return "#e6ffed", False


def _source_diff_highlight(value: str, *, color: str, removed: bool) -> str:
    escaped = html.escape(value).replace("\n", "<br>")
    content = f"<del>{escaped}</del>" if removed else escaped
    text_color = "#b42318" if removed else "#116329"
    if color == "#fff4e5":
        text_color = "#b54708"
    if color == "#f2f4f7":
        text_color = "#344054"
    return (
        f'<span style="background:{color};color:{text_color};'
        f'padding:0.08em 0.18em;">{content}</span>'
    )


def _render_extraction_documents(
    bundle: NormalizedSourceBundle,
    cited_by_source: dict[str, list[tuple[str, str, str]]],
) -> tuple[str, ...]:
    parts: list[str] = []
    for document in bundle.documents:
        parts.extend(
            (
                "---",
                "",
                f"## {_safe(document.name)}",
                "",
                f"Source: <{document.source_url}>",
                "",
            )
        )
        table_by_id = {table.id: table for table in document.tables}
        rendered_tables: set[str] = set()
        for block in document.blocks:
            if block.type is NormalizedBlockType.TABLE and block.table_id:
                table = table_by_id.get(block.table_id)
                if table is not None:
                    parts.extend(_render_extraction_table(table, cited_by_source))
                    rendered_tables.add(table.id)
                continue
            annotations = cited_by_source.get(block.id, [])
            parts.extend(
                (
                    _render_block_content(block, annotations=annotations),
                    "",
                )
            )
        for table in document.tables:
            if table.id not in rendered_tables:
                parts.extend(_render_extraction_table(table, cited_by_source))
    return tuple(parts)


def _render_extraction_table(
    table: NormalizedTable,
    cited_by_source: dict[str, list[tuple[str, str, str]]],
) -> tuple[str, ...]:
    parts: list[str] = []
    fallback_notes: list[str] = []
    if table.title:
        parts.extend((f"### {_safe(table.title)}", ""))
    width = len(table.headers) or (len(table.rows[0].cells) if table.rows else 0)
    if width:
        headers = table.headers or tuple(f"Column {i + 1}" for i in range(width))
        parts.extend(
            (
                "| " + " | ".join(_table_cell(value) for value in headers) + " |",
                "| " + " | ".join("---" for _ in range(width)) + " |",
            )
        )
        for row in table.rows:
            annotations = cited_by_source.get(row.id, [])
            rendered_cells: list[str] = []
            matched_labels: set[str] = set()
            for cell in row.cells:
                rendered, matched = _highlight_extracted_text(cell.text, annotations)
                rendered_cells.append(_cell(rendered))
                matched_labels.update(matched)
            expected_labels = {label for label, _, _ in annotations}
            missing = sorted(expected_labels - matched_labels)
            if missing:
                fallback_notes.append(
                    f"`{row.id}`: {', '.join(missing)} cites combined row evidence; "
                    "the exact quote could not be localized to one cell."
                )
            parts.append("| " + " | ".join(rendered_cells) + " |")
        parts.append("")
    for index, note in enumerate(table.notes):
        annotations = cited_by_source.get(f"{table.id}:note:{index}", [])
        rendered, _ = _highlight_extracted_text(note.text, annotations)
        parts.extend((f"> {rendered}", ""))
    if fallback_notes:
        parts.extend(("**Row-level citation labels:**", ""))
        parts.extend(f"- {item}" for item in fallback_notes)
        parts.append("")
    return tuple(parts)


def _render_block_content(
    block: NormalizedBlock,
    *,
    background: str | None = None,
    annotations: list[tuple[str, str, str]] | None = None,
) -> str:
    if annotations:
        rendered, _ = _highlight_extracted_text(block.text, annotations)
        lines = rendered.splitlines() or [rendered]
    elif background:
        lines = [
            _semantic_highlight(line, background) for line in block.text.splitlines()
        ] or [""]
    else:
        lines = [html.escape(line) for line in block.text.splitlines()] or [""]
    if block.type is NormalizedBlockType.HEADING:
        level = min(max(len(block.heading_path), 1) + 1, 6)
        return f"{'#' * level} " + "<br>".join(lines)
    if block.type is NormalizedBlockType.LIST:
        return "\n".join(f"- {line}" for line in lines if line.strip())
    if block.type is NormalizedBlockType.CARD and block.fields:
        title = block.fields.get("title", "")
        body = block.fields.get("body", "")
        if annotations:
            title, _ = _highlight_extracted_text(title, annotations)
            body, _ = _highlight_extracted_text(body, annotations)
        elif background:
            title = _semantic_highlight(title, background)
            body = _semantic_highlight(body, background)
        else:
            title = html.escape(title)
            body = html.escape(body)
        return f"### {title}\n\n{body}".strip()
    return "  \n".join(lines)


def _highlight_extracted_text(
    value: str,
    annotations: list[tuple[str, str, str]],
) -> tuple[str, set[str]]:
    matches: list[tuple[int, int, str, str]] = []
    for label, field, quote in annotations:
        start = 0
        while quote and (found := value.find(quote, start)) >= 0:
            matches.append((found, found + len(quote), label, field))
            start = found + len(quote)
    if not matches:
        return html.escape(value), set()
    boundaries = sorted(
        {0, len(value), *(point for match in matches for point in match[:2])}
    )
    parts: list[str] = []
    matched_labels: set[str] = set()
    for start, end in pairwise(boundaries):
        segment = html.escape(value[start:end])
        covering = [match for match in matches if match[0] <= start and end <= match[1]]
        if not covering:
            parts.append(segment)
            continue
        labels = sorted({match[2] for match in covering})
        fields = sorted({match[3] for match in covering})
        matched_labels.update(labels)
        links = " ".join(
            f'<a href="#{label.lower()}">{html.escape(label)}</a>' for label in labels
        )
        parts.append(
            '<mark style="background:#d1fadf;color:#05603a;padding:0.08em 0.18em;">'
            f'{segment}<sup title="{html.escape(", ".join(fields))}">{links}</sup>'
            "</mark>"
        )
    return "".join(parts), matched_labels


def _semantic_highlight(value: str, background: str) -> str:
    escaped = html.escape(value).replace("\n", "<br>")
    return (
        f'<span style="background:{background};padding:0.08em 0.18em;">{escaped}</span>'
    )


def _table_cell(value: str, *, background: str | None = None) -> str:
    rendered = (
        _semantic_highlight(value, background) if background else html.escape(value)
    )
    return _cell(rendered)


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


def _render_annotated_document(acquired: str, normalized: str) -> tuple[str, bool]:
    before = acquired.splitlines()
    after = normalized.splitlines()
    matcher = difflib.SequenceMatcher(a=before, b=after, autojunk=False)
    lines: list[str] = []
    changed = False
    for (
        operation,
        before_start,
        before_end,
        after_start,
        after_end,
    ) in matcher.get_opcodes():
        old_lines = before[before_start:before_end]
        new_lines = after[after_start:after_end]
        if operation == "equal":
            lines.extend(new_lines)
            continue
        changed = True
        if operation == "delete":
            lines.extend(_removed_line(line) for line in old_lines)
            continue
        if operation == "insert":
            lines.extend(_added_line(line) for line in new_lines)
            continue
        paired = min(len(old_lines), len(new_lines))
        lines.extend(
            _inline_line_diff(old_lines[index], new_lines[index])
            for index in range(paired)
        )
        lines.extend(_removed_line(line) for line in old_lines[paired:])
        lines.extend(_added_line(line) for line in new_lines[paired:])
    return "\n".join(lines), changed


def _inline_line_diff(before: str, after: str) -> str:
    old_tokens = _diff_tokens(before)
    new_tokens = _diff_tokens(after)
    matcher = difflib.SequenceMatcher(a=old_tokens, b=new_tokens, autojunk=False)
    parts: list[str] = []
    for operation, old_start, old_end, new_start, new_end in matcher.get_opcodes():
        old = "".join(old_tokens[old_start:old_end])
        new = "".join(new_tokens[new_start:new_end])
        if operation == "equal":
            parts.append(new)
        elif operation == "delete":
            parts.append(_removed(old))
        elif operation == "insert":
            parts.append(_added(new))
        else:
            parts.extend((_removed(old), _added(new)))
    return "".join(parts)


def _diff_tokens(value: str) -> list[str]:
    return [token for token in re.split(r"(\s+|\|)", value) if token]


def _removed_line(value: str) -> str:
    if not value:
        return ""
    return f"> **Removed during normalization:** {_removed(value)}"


def _added_line(value: str) -> str:
    if not value:
        return ""
    if value.startswith("|") and value.endswith("|"):
        cells = value[1:-1].split("|")
        if all(re.fullmatch(r"\s*:?-{3,}:?\s*", cell) for cell in cells):
            return value
        return "|" + "|".join(_added(cell) for cell in cells) + "|"
    prefix, body = _markdown_prefix(value)
    return prefix + _added(body)


def _markdown_prefix(value: str) -> tuple[str, str]:
    match = re.match(r"^(#{1,6}\s+|>\s+|\s*[-*+]\s+|\s*\d+[.)]\s+)", value)
    if match is None:
        return "", value
    return match.group(1), value[match.end() :]


def _removed(value: str) -> str:
    return (
        '<span style="background:#ffe6e6;color:#b42318;padding:0.1em 0.2em;">'
        f"<del>{html.escape(value)}</del></span>"
    )


def _added(value: str) -> str:
    return (
        '<span style="background:#e6ffed;color:#116329;padding:0.1em 0.2em;">'
        f"<ins>{html.escape(value)}</ins></span>"
    )
