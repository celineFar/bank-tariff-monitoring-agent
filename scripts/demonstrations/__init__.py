"""Deliverable demonstrations with machine-checked success criteria.

Each scenario in this package maps to one numbered deliverable in
``Project Documents/System Description.md`` section 7. A scenario prints the
steps it performed and then evaluates named criteria, so a run is either a pass
or a fail rather than a wall of output a reviewer has to interpret.

A scenario may group its steps into named sections, so that a recorded
walkthrough shows the input it was given, the work it performed on that input,
and the result, rather than a single undifferentiated list.

Scenarios are deterministic and offline by default. They exercise the real
application services against a disposable ``_test`` database, either on
synthetic fixture data or by replaying a recorded live run (see
``scripts/demonstrations/capture.py``), so a live demonstration does not depend
on the bank's website, on network conditions, or on model credits.
"""

from __future__ import annotations

from dataclasses import dataclass, field

DEFAULT_SECTION = "Steps"


@dataclass(frozen=True)
class Criterion:
    """One thing that must be true for the demonstration to count as a pass."""

    name: str
    expectation: str
    passed: bool
    observed: str


@dataclass(frozen=True)
class Line:
    text: str
    numbered: bool


@dataclass
class Section:
    title: str
    lines: list[Line] = field(default_factory=list)


@dataclass
class ScenarioResult:
    deliverable: str
    title: str
    sections: list[Section] = field(default_factory=list)
    criteria: list[Criterion] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def section(self, title: str) -> None:
        self.sections.append(Section(title=title))

    def step(self, message: str) -> None:
        """Add a numbered step to the current section."""
        self._current.lines.append(Line(text=message, numbered=True))

    def detail(self, message: str) -> None:
        """Add an unnumbered supporting line, such as a quoted source value."""
        self._current.lines.append(Line(text=message, numbered=False))

    def note(self, message: str) -> None:
        self.notes.append(message)

    def check(self, name: str, expectation: str, passed: bool, observed: str) -> None:
        self.criteria.append(
            Criterion(
                name=name,
                expectation=expectation,
                passed=bool(passed),
                observed=observed,
            )
        )

    @property
    def steps(self) -> tuple[str, ...]:
        return tuple(
            line.text
            for section in self.sections
            for line in section.lines
            if line.numbered
        )

    @property
    def passed(self) -> bool:
        return bool(self.criteria) and all(item.passed for item in self.criteria)

    @property
    def _current(self) -> Section:
        if not self.sections:
            self.sections.append(Section(title=DEFAULT_SECTION))
        return self.sections[-1]


def render_markdown(result: ScenarioResult) -> str:
    """Render one scenario as a document to screenshot or attach to a report."""
    passed = sum(item.passed for item in result.criteria)
    lines = [
        f"# {result.deliverable} — {result.title}",
        "",
        f"**{'PASS' if result.passed else 'FAIL'} — {passed}/{len(result.criteria)} "
        "criteria**",
    ]
    number = 0
    for section in result.sections:
        lines.extend(["", f"## {section.title}", ""])
        for line in section.lines:
            if line.numbered:
                number += 1
                lines.append(f"{number}. {line.text}")
            else:
                # A detail indents itself with four spaces per nesting level.
                depth = (len(line.text) - len(line.text.lstrip())) // 4
                lines.append("    " * (depth + 1) + f"- {line.text.strip()}")
    if result.notes:
        lines.extend(["", "## Notes", ""])
        lines.extend(f"- {note}" for note in result.notes)
    lines.extend(
        [
            "",
            "## Success criteria",
            "",
            "| | Criterion | Expected | Observed |",
            "| --- | --- | --- | --- |",
        ]
    )
    for item in result.criteria:
        lines.append(
            f"| {'PASS' if item.passed else 'FAIL'} | {item.name} "
            f"| {item.expectation} | {item.observed} |"
        )
    return "\n".join(lines) + "\n"


def render(result: ScenarioResult) -> str:
    lines = [
        "",
        "=" * 78,
        f"{result.deliverable}  {result.title}",
        "=" * 78,
    ]
    number = 0
    for section in result.sections:
        lines.extend(["", section.title, "-" * len(section.title)])
        for line in section.lines:
            if line.numbered:
                number += 1
                lines.append(f"{number:>2}. {line.text}")
            else:
                lines.append(f"    {line.text}")
    if result.notes:
        lines.extend(["", "Notes", "-----"])
        lines.extend(f"  - {note}" for note in result.notes)
    lines.extend(["", "Success criteria", "----------------"])
    for item in result.criteria:
        lines.append(f"[{'PASS' if item.passed else 'FAIL'}] {item.name}")
        lines.append(f"       expected: {item.expectation}")
        lines.append(f"       observed: {item.observed}")
    lines.append("")
    lines.append(
        f"RESULT: {'PASS' if result.passed else 'FAIL'} "
        f"({sum(item.passed for item in result.criteria)}"
        f"/{len(result.criteria)} criteria)"
    )
    return "\n".join(lines)
