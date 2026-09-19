from __future__ import annotations

import difflib
import html
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
    sent_groups: dict[str, list[str]] = defaultdict(list)
    for batch in plan.batches:
        for item in batch.evidence:
            sent_groups[item.evidence_id].append(batch.group)
    sent_ids = set(sent_groups)
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
                    "---",
                    "",
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
    evidence_count = len(plan.evidence_catalog)
    for index, evidence in enumerate(plan.evidence_catalog, start=1):
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
            state = "NOT SENT TO SEMANTIC LLM"
            explanation = (
                "Deterministic planner decision: omitted from all bounded field "
                "packets after relevance ranking and configured item/character limits. "
                "The evidence remains accepted and auditable."
            )
        parts.extend(
            (
                "---",
                "",
                f"### Evidence {index:03d} of {evidence_count:03d}",
                "",
                f"> **{state}**  ",
                f"> {explanation}",
                "",
                "| Metadata | Value |",
                "|---|---|",
                f"| Evidence ID | `{evidence.evidence_id}` |",
                f"| Source item | `{evidence.source_item_id}` |",
                f"| Role | `{evidence.role.value}` |",
                f"| Authority | `{evidence.authority.value}` |",
                f"| Temporal status | `{evidence.temporal_status.value}` |",
                "| Semantic packets | "
                + _cell(
                    ", ".join(sorted(set(sent_groups[evidence.evidence_id])))
                    or "(none)"
                )
                + " |",
                f"| Section | {_cell(_safe(evidence.section or '(none)'))} |",
                "",
                "<details open>",
                "<summary><strong>Source content</strong></summary>",
                "",
                "```text",
                evidence.content,
                "```",
                "",
                "</details>",
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
        return ("---", "", f"### UNASSESSED — `{source_id}`", "")
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
        "---",
        "",
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
