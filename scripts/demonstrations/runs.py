"""Allocate the numbered run directories the demonstration scripts write into.

Every invocation of a demonstration script is an audit record of what the code
did at that moment, so a new invocation must never overwrite an earlier one:
each one claims its own ``run_NNN`` directory and the earlier runs stay on disk
as the trail. ``scripts/demonstrate_end_to_end.py`` records its stage-by-stage
capture this way and ``scripts/run_demonstration.py`` its deliverable
transcripts, so both use the same naming here and
``scripts/demonstrations/capture.py`` recognizes it when replaying a capture.
"""

from __future__ import annotations

import re
from pathlib import Path

RUN_DIRECTORY = re.compile(r"^run_(\d+)$")


def run_index(directory: Path) -> int | None:
    """Return the number in a ``run_NNN`` directory name, or None if it is not one."""
    match = RUN_DIRECTORY.fullmatch(directory.name)
    return int(match.group(1)) if match else None


def next_run_directory(path: Path) -> Path:
    """Create and return the next unused ``run_NNN`` directory under ``path``."""
    root = path.resolve()
    root.mkdir(parents=True, exist_ok=True)
    existing_numbers = [
        index
        for child in root.iterdir()
        if child.is_dir() and (index := run_index(child)) is not None
    ]
    first_index = max(existing_numbers, default=0) + 1
    for index in range(first_index, 100_000):
        candidate = root / f"run_{index:03d}"
        try:
            candidate.mkdir()
        except FileExistsError:
            continue
        return candidate
    raise RuntimeError(f"No available numbered run directory below {root}")
