"""The passages a review is about, decided once, when its signal is raised (RV1).

A review signal knows why it was raised: the field's citations, a candidate's
passage, the OCR page, or -- for a field extraction found nothing for -- the
passages that extraction call read. This module turns that knowledge into a
`ReviewEvidenceSet`: at most a couple of display units (a table, a window of a
section, or a single passage), each bounded, stored as references. Nothing
downstream re-guesses relevance from the field's name.

Bounds are code constants (Q3); the rank gap for a second unit comes from
`HITL_DOCUMENT_RANK_GAP`.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from pydantic import ValidationError

from app.domain.review import ReviewEvidenceSet, ReviewEvidenceUnit, ReviewTask
from app.domain.semantic_extraction import EvidenceItem, ExtractionField
from app.services.extraction_planner import (
    build_units,
    field_unit_scores,
    labelled_for,
)

# A table up to this many passages is shown whole; a larger one shows the seed
# rows with this many rows either side, and says how many it left out (R5).
TABLE_WHOLE_ROWS = 30
TABLE_CONTEXT_ROWS = 3
# A section is shown as a window around its seed block (R7, Q8).
SECTION_CONTEXT_BLOCKS = 2
SECTION_MAX_CHARS = 3_000
# One unit per review, a second when it ranks within the rank gap.
UNITS_PER_REVIEW = 2
# A passage is shown whole up to this length: the stored citation's limit (RV11).
PASSAGE_MAX_CHARS = 4_000
# What the model receives with a review pause (R6, Q11).
MODEL_SEED_PASSAGES = 5
MODEL_EXCERPT_CHARS = 600

_TABLE_ITEM = re.compile(r":(?:row|note):")
_WORD = re.compile(r"\w+")
_NEAR_DUPLICATE = 0.8


@dataclass(frozen=True)
class _Unit:
    key: str
    items: tuple[EvidenceItem, ...]
    table: bool

    @property
    def precedence(self) -> int:
        return min(item.precedence for item in self.items)

    @property
    def order(self) -> int:
        return self.items[0].order


def unit_key(item: EvidenceItem) -> tuple[str, bool]:
    """The display unit an item belongs to: its table, else its section."""
    parts = _TABLE_ITEM.split(item.source_item_id, maxsplit=1)
    if len(parts) == 2:
        return f"{item.document_id}|table:{parts[0]}", True
    return f"{item.document_id}|section:{item.section or ''}", False


def _units(catalog: Sequence[EvidenceItem]) -> dict[str, _Unit]:
    grouped: dict[str, list[EvidenceItem]] = {}
    tables: dict[str, bool] = {}
    for item in sorted(catalog, key=lambda item: item.order):
        key, table = unit_key(item)
        grouped.setdefault(key, []).append(item)
        tables[key] = table
    return {
        key: _Unit(key=key, items=tuple(items), table=tables[key])
        for key, items in grouped.items()
    }


def cited_evidence_set(
    catalog: Sequence[EvidenceItem],
    seed_ids: Iterable[str],
    *,
    why: str,
    max_units: int = UNITS_PER_REVIEW,
) -> ReviewEvidenceSet:
    """The units holding the given passages (citations, candidates, OCR pages).

    IDs not in the catalog are kept apart as `unknown_ids` (RV3). Units are
    ranked by how many seeds they hold, then by source precedence, then by
    reading order; near-duplicates (a page table and its PDF copy) count once.
    """
    by_id = {item.evidence_id: item for item in catalog}
    seeds = tuple(dict.fromkeys(seed_ids))
    known = [i for i in seeds if i in by_id]
    unknown = tuple(i for i in seeds if i not in by_id)[:60]
    units = _units(catalog)
    seeded: dict[str, list[str]] = {}
    for evidence_id in known:
        key, _ = unit_key(by_id[evidence_id])
        seeded.setdefault(key, []).append(evidence_id)
    ranked = sorted(
        seeded,
        key=lambda key: (-len(seeded[key]), units[key].precedence, units[key].order),
    )
    ranked = _without_near_duplicates([units[key] for key in ranked])
    return ReviewEvidenceSet(
        units=tuple(
            _bounded(unit, tuple(seeded[unit.key]), why) for unit in ranked[:max_units]
        ),
        unknown_ids=unknown,
    )


def field_evidence_set(
    catalog: Sequence[EvidenceItem],
    field: ExtractionField,
    *,
    read_ids: Iterable[str] | None,
    canonical_url: str | None = None,
    rank_gap: float = 0.05,
) -> ReviewEvidenceSet:
    """Where a field extraction found nothing for would have been read from.

    The passages the field's extraction call read (RV2) -- the whole catalog
    for results that did not record them -- are ranked with the planner's label
    scoring for the field (never the body text). The best unit is shown, and a
    second one when its score is within `rank_gap` of the best (R4); when none
    is and the best is not a table, the second slot goes to the best table. The
    seeds are the unit's items labelled for the field.
    """
    read = set(read_ids) if read_ids is not None else None
    pool = tuple(item for item in catalog if read is None or item.evidence_id in read)
    if not pool:
        return ReviewEvidenceSet()
    scored_units = build_units(pool, canonical_url)
    scores = field_unit_scores(scored_units, field)

    def is_table(unit) -> bool:
        return "|table:" in unit.key

    # Equal label scores are common (every unit of a terms page names "interest
    # rate"); page order then put a navigation section or an FAQ ahead of the
    # tariff table. Ties go to the higher source precedence, then to tables,
    # where tariff values are stated (R03).
    ranked = sorted(
        (unit for unit in scored_units if scores[unit.key] > 0),
        key=lambda unit: (
            unit.related,
            -round(scores[unit.key], 6),
            min(item.precedence for item in unit.items),
            not is_table(unit),
            not unit.canonical,
            unit.order,
        ),
    )
    if not ranked:
        return ReviewEvidenceSet()
    best = scores[ranked[0].key]
    chosen = [ranked[0]] + [
        unit
        for unit in ranked[1:UNITS_PER_REVIEW]
        if scores[unit.key] >= best * (1 - rank_gap)
    ]
    if len(chosen) < UNITS_PER_REVIEW and not is_table(ranked[0]):
        # A headline or calculator section names many fields and outscores the
        # table; the second slot then goes to the best table (R03).
        table = next(
            (unit for unit in ranked[1:] if is_table(unit) and not unit.related),
            None,
        )
        if table is not None:
            chosen.append(table)
    display = _units(catalog)
    picked: list[tuple[_Unit, tuple[str, ...]]] = []
    for unit in chosen:
        seeds = tuple(
            item.evidence_id for item in unit.items if labelled_for(item, field)
        ) or (unit.items[0].evidence_id,)
        key, _ = unit_key(unit.items[0])
        picked.append((display[key], seeds))
    merged: dict[str, tuple[_Unit, list[str]]] = {}
    for unit, seeds in picked:
        merged.setdefault(unit.key, (unit, []))[1].extend(seeds)
    kept = _without_near_duplicates([unit for unit, _ in merged.values()])
    return ReviewEvidenceSet(
        units=tuple(
            _bounded(unit, tuple(dict.fromkeys(merged[unit.key][1])), "batch")
            for unit in kept
        )
    )


def _without_near_duplicates(units: list[_Unit]) -> list[_Unit]:
    """Drop a unit whose words nearly all repeat a unit ranked above it.

    A page's tariff table and its PDF copy say the same thing; showing both
    spends the review's second slot on a copy. The first (higher-ranked) is
    kept; callers rank by seeds, then precedence.
    """
    kept: list[_Unit] = []
    words: list[set[str]] = []
    for unit in units:
        mine = set(_WORD.findall(" ".join(i.content for i in unit.items).casefold()))
        if any(_similar(mine, other) for other in words):
            continue
        kept.append(unit)
        words.append(mine)
    return kept


def _similar(left: set[str], right: set[str]) -> bool:
    if not left or not right:
        return False
    return len(left & right) / len(left | right) >= _NEAR_DUPLICATE


def _bounded(unit: _Unit, seeds: tuple[str, ...], why: str) -> ReviewEvidenceUnit:
    items = unit.items
    positions = {item.evidence_id: index for index, item in enumerate(items)}
    seed_positions = sorted(positions[i] for i in seeds if i in positions)
    if unit.table:
        shown = _table_window(len(items), seed_positions)
        kind = "table"
    elif len(items) == 1:
        shown = [0]
        kind = "passage"
    else:
        shown = _section_window(items, seed_positions)
        kind = "section"
    seeds = tuple(items[index].evidence_id for index in seed_positions)[:60]
    return ReviewEvidenceUnit(
        kind=kind,
        key=unit.key,
        evidence_ids=tuple(items[index].evidence_id for index in shown),
        seed_ids=seeds,
        why=why,
        omitted=len(items) - len(shown),
    )


def _table_window(count: int, seeds: list[int]) -> list[int]:
    if count <= TABLE_WHOLE_ROWS:
        return list(range(count))
    for context in (TABLE_CONTEXT_ROWS, 1, 0):
        shown = sorted(
            {
                index
                for seed in seeds
                for index in range(
                    max(seed - context, 0), min(seed + context + 1, count)
                )
            }
        )
        if len(shown) <= TABLE_WHOLE_ROWS:
            return shown
    return seeds[:TABLE_WHOLE_ROWS]


def _section_window(items: tuple[EvidenceItem, ...], seeds: list[int]) -> list[int]:
    """Seed blocks, then neighbours nearest first, up to 2 either side and 3,000
    characters. A seed is always shown, whatever its length."""
    shown = set(seeds)
    size = sum(len(items[index].content) for index in shown)
    for distance in range(1, SECTION_CONTEXT_BLOCKS + 1):
        for seed in seeds:
            for index in (seed - distance, seed + distance):
                if 0 <= index < len(items) and index not in shown:
                    length = len(items[index].content)
                    if size + length > SECTION_MAX_CHARS:
                        continue
                    shown.add(index)
                    size += length
    return sorted(shown)


def model_excerpts(
    evidence_set: ReviewEvidenceSet,
    evidence_by_id: dict[str, dict],
) -> tuple[dict, ...]:
    """The seed passages the model sees with a review pause: at most 5, each
    trimmed to 600 characters (R6). The reviewer's terminal shows the units."""
    excerpts: list[dict] = []
    for evidence_id in evidence_set.seed_ids:
        raw = evidence_by_id.get(evidence_id)
        if raw is None:
            continue
        excerpts.append(
            {**raw, "content": str(raw.get("content", ""))[:MODEL_EXCERPT_CHARS]}
        )
        if len(excerpts) == MODEL_SEED_PASSAGES:
            break
    return tuple(excerpts)


def review_passages(
    task: ReviewTask, snapshot_evidence: Sequence[dict[str, Any]]
) -> tuple[dict[str, Any], ...]:
    """The passages a review's references resolve against.

    A review stores references; their content is the snapshot's evidence, which
    never changes after the snapshot is created (RV7). A row written before this
    change carries its own copy (`items`), which is used as is.
    """
    items = task.evidence.get("items")
    if isinstance(items, list):
        return tuple(item for item in items if isinstance(item, dict))
    return tuple(item for item in snapshot_evidence if isinstance(item, dict))


def review_evidence_set(
    task: ReviewTask,
    passages: Sequence[dict[str, Any]],
    *,
    rank_gap: float = 0.05,
) -> ReviewEvidenceSet:
    """The review's stored set; for a row written before sets existed, the set
    the signal would have carried, built from what the row has (R04)."""
    raw = task.evidence.get("set")
    if isinstance(raw, dict):
        try:
            return ReviewEvidenceSet.model_validate(raw)
        except ValidationError:
            pass
    catalog = evidence_items(passages)
    references = [
        reference
        for candidate in task.candidates
        for reference in candidate.evidence_references
    ]
    if references:
        evidence_set = cited_evidence_set(catalog, references, why="candidate")
        # Items stored before evidence became catalog records cannot be grouped
        # into units; each cited one is shown as its own passage.
        stored = {str(raw.get("evidence_id")) for raw in passages}
        loose = [i for i in evidence_set.unknown_ids if i in stored]
        if not loose:
            return evidence_set
        return ReviewEvidenceSet(
            units=(
                *evidence_set.units,
                *(
                    ReviewEvidenceUnit(
                        kind="passage",
                        key=evidence_id,
                        evidence_ids=(evidence_id,),
                        seed_ids=(evidence_id,),
                        why="candidate",
                    )
                    for evidence_id in loose
                ),
            )[:10],
            unknown_ids=tuple(i for i in evidence_set.unknown_ids if i not in stored),
        )
    try:
        field = ExtractionField(task.issue_scope)
    except ValueError:
        return ReviewEvidenceSet()
    return field_evidence_set(catalog, field, read_ids=None, rank_gap=rank_gap)


def evidence_items(passages: Sequence[dict[str, Any]]) -> tuple[EvidenceItem, ...]:
    """Stored evidence as catalog items, in reading order; unreadable rows are
    skipped (they can still be cited by ID, but not grouped into units)."""
    items: list[EvidenceItem] = []
    for index, raw in enumerate(passages):
        try:
            item = EvidenceItem.model_validate(raw)
        except ValidationError:
            continue
        # Rows stored before SE8 have no reading order; their list order is it.
        items.append(
            item if "order" in raw else item.model_copy(update={"order": index})
        )
    return tuple(items)


# --- what the reviewer's terminal shows (RV9, RV11) ------------------------------


@dataclass(frozen=True)
class DisplayPassage:
    evidence_id: str
    content: str
    seed: bool
    section: str | None
    source_url: str | None
    page: int | None


@dataclass(frozen=True)
class DisplayUnit:
    kind: str
    title: str
    passages: tuple[DisplayPassage, ...]
    omitted: int
    why: str


@dataclass(frozen=True)
class ReviewDisplay:
    """A review's units with their passages, for the reviewer (never the model)."""

    units: tuple[DisplayUnit, ...]
    unknown_ids: tuple[str, ...]
    # Every passage of the snapshot, for citing one outside the units (RV13).
    all_passages: tuple[DisplayPassage, ...]
    selected_sources_markdown: str | None = None

    @property
    def shown(self) -> tuple[DisplayPassage, ...]:
        return tuple(p for unit in self.units for p in unit.passages)

    @property
    def seeds(self) -> tuple[DisplayPassage, ...]:
        return tuple(p for p in self.shown if p.seed)


def build_review_display(
    task: ReviewTask,
    snapshot_evidence: Sequence[dict[str, Any]],
    *,
    selected_sources_markdown: str | None = None,
) -> ReviewDisplay:
    passages = review_passages(task, snapshot_evidence)
    evidence_set = review_evidence_set(task, passages)
    by_id = {str(raw["evidence_id"]): raw for raw in passages if raw.get("evidence_id")}
    units: list[DisplayUnit] = []
    for unit in evidence_set.units:
        seeds = set(unit.seed_ids)
        shown = tuple(
            _display_passage(by_id[i], seed=i in seeds)
            for i in unit.evidence_ids
            if i in by_id
        )
        if not shown:
            continue
        units.append(
            DisplayUnit(
                kind=unit.kind,
                title=next((p.section for p in shown if p.section), None)
                or unit.key.split("|", 1)[-1],
                passages=shown,
                omitted=unit.omitted,
                why=unit.why,
            )
        )
    return ReviewDisplay(
        units=tuple(units),
        unknown_ids=evidence_set.unknown_ids,
        all_passages=tuple(_display_passage(raw, seed=False) for raw in passages),
        selected_sources_markdown=selected_sources_markdown,
    )


def _display_passage(raw: dict[str, Any], *, seed: bool) -> DisplayPassage:
    locator = raw.get("locator") if isinstance(raw.get("locator"), dict) else {}
    page = locator.get("pdf_page")
    return DisplayPassage(
        evidence_id=str(raw.get("evidence_id")),
        content=str(raw.get("content", ""))[:PASSAGE_MAX_CHARS],
        seed=seed,
        section=str(raw["section"]) if raw.get("section") else None,
        source_url=str(locator["source_url"]) if locator.get("source_url") else None,
        page=page if isinstance(page, int) else None,
    )


class ReviewDisplayService:
    """Loads a review's display through the repositories, for the CLI (RV9)."""

    def __init__(self, reviews: Any, snapshots: Any) -> None:
        self._reviews = reviews
        self._snapshots = snapshots

    async def load(self, review_id: UUID) -> ReviewDisplay | None:
        task = await self._reviews.get(review_id)
        if task is None:
            return None
        snapshot = await self._snapshots.get(task.snapshot_id)
        markdown = getattr(snapshot, "selected_sources_markdown", None)
        read_markdown = getattr(self._snapshots, "selected_sources_markdown", None)
        if markdown is None and snapshot is not None and read_markdown is not None:
            markdown = await read_markdown(snapshot.id)
        return build_review_display(
            task,
            snapshot.evidence if snapshot is not None else (),
            selected_sources_markdown=markdown,
        )
