"""Load a recorded acquisition-to-extraction run for replay in a demonstration.

``scripts/demonstrate_end_to_end.py`` writes every stage of a live run to
``end-to-end/run_NNN``: the page as it was fetched, the normalized source
bundle, the source-discovery decision, and the semantic extraction the model
returned. Replaying one of those recordings lets a demonstration show the real
input text and the real model output without a network call, a browser, or
model spend, while everything downstream of extraction still executes for real.

A recording is a snapshot of the schemas in force when it was written. Older
runs stay on disk as the audit trail, so a recording that no longer validates
is skipped rather than raising: the newest readable run wins.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path

from pydantic import BaseModel, ValidationError

from app.domain.acquisition import PageArtifact
from app.domain.normalization import NormalizedSourceBundle
from app.domain.semantic_extraction import (
    SemanticExtractionPlan,
    SemanticExtractionResult,
)
from app.domain.source_discovery import SourceDiscoveryResult
from scripts.demonstrations.support import DemonstrationError

DEFAULT_ROOT = Path("end-to-end")
_RUN_DIRECTORY = re.compile(r"^run_(\d+)$")
_ARTIFACT = Path("acquisition/source files/page_artifact.json")
_BUNDLE = Path("normalization/normalized_bundle.json")
_DISCOVERY = Path("source-discovery/result.json")
_PLAN = Path("semantic-extraction/plan.json")
_EXTRACTION = Path("semantic-extraction/result.json")


@dataclass(frozen=True)
class SourceText:
    """One piece of captured source text, addressed the way evidence cites it."""

    item_id: str
    kind: str
    document: str
    locator: str
    text: str


@dataclass(frozen=True)
class Capture:
    """One recorded run, loaded into the same models the pipeline uses."""

    directory: Path
    source_url: str
    artifact: PageArtifact
    bundle: NormalizedSourceBundle
    discovery: SourceDiscoveryResult
    plan: SemanticExtractionPlan
    extraction: SemanticExtractionResult

    @property
    def name(self) -> str:
        return self.directory.name

    def source_text(self, item_id: str) -> SourceText | None:
        """Return the captured text an evidence item cites, or None if absent."""
        return self._index.get(item_id)

    @cached_property
    def _index(self) -> dict[str, SourceText]:
        """Index the evidence catalog: the exact text handed to the extractor."""
        names = {document.id: document.name for document in self.bundle.documents}
        index: dict[str, SourceText] = {}
        for item in self.extraction.evidence_catalog:
            index[item.source_item_id] = SourceText(
                item_id=item.source_item_id,
                kind=_kind(item.source_item_id),
                document=names.get(item.document_id, item.document_id),
                locator=_locator(item.locator),
                text=item.content,
            )
        return index


def _kind(source_item_id: str) -> str:
    if ":note:" in source_item_id:
        return "table note"
    if ":row:" in source_item_id:
        return "table row"
    return "content block"


def _locator(locator) -> str:
    if locator.pdf_page is not None:
        return f"page {locator.pdf_page}"
    return locator.css_selector or locator.block_id or locator.source_type.value


def load_capture(name: str | None = None, *, root: Path = DEFAULT_ROOT) -> Capture:
    """Load one recorded run: the named one, or the newest readable one."""
    if not root.is_dir():
        raise DemonstrationError(
            f"no recorded runs under {root}/. Run "
            "`scripts/demonstrate_end_to_end.py <url>` to record one."
        )
    if name is not None:
        directory = root / name
        if not directory.is_dir():
            raise DemonstrationError(f"no recorded run at {directory}")
        capture = _load(directory)
        if capture is None:
            raise DemonstrationError(
                f"{directory} is incomplete or predates the current schema"
            )
        return capture

    candidates = sorted(
        (child for child in root.iterdir() if _RUN_DIRECTORY.fullmatch(child.name)),
        key=lambda child: int(_RUN_DIRECTORY.fullmatch(child.name).group(1)),
        reverse=True,
    )
    for directory in candidates:
        capture = _load(directory)
        if capture is not None:
            return capture
    raise DemonstrationError(
        f"none of the {len(candidates)} recorded run(s) under {root}/ is complete "
        "and readable against the current schema. Record a new one with "
        "`scripts/demonstrate_end_to_end.py <url>`."
    )


def _load(directory: Path) -> Capture | None:
    parts = (
        (_ARTIFACT, PageArtifact),
        (_BUNDLE, NormalizedSourceBundle),
        (_DISCOVERY, SourceDiscoveryResult),
        (_PLAN, SemanticExtractionPlan),
        (_EXTRACTION, SemanticExtractionResult),
    )
    loaded = []
    for relative, model in parts:
        path = directory / relative
        if not path.is_file():
            return None
        try:
            loaded.append(model.model_validate_json(path.read_text(encoding="utf-8")))
        except ValidationError:
            return None
    artifact, bundle, discovery, plan, extraction = loaded
    return Capture(
        directory=directory,
        source_url=_source_url(directory, artifact),
        artifact=artifact,
        bundle=bundle,
        discovery=discovery,
        plan=plan,
        extraction=extraction,
    )


def _source_url(directory: Path, artifact: BaseModel) -> str:
    path = directory / "source_url.txt"
    if path.is_file():
        return path.read_text(encoding="utf-8").strip()
    return str(artifact.canonical_url)
