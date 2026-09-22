"""Deliverable demonstrations with machine-checked success criteria.

Each scenario in this package maps to one numbered deliverable in
``Project Documents/System Description.md`` section 7. A scenario prints the
steps it performed and then evaluates named criteria, so a run is either a pass
or a fail rather than a wall of output a reviewer has to interpret.

Scenarios are deterministic and offline by default. They exercise the real
application services against a disposable ``_test`` database and synthetic
fixture data, so a live demonstration does not depend on the bank's website,
on network conditions, or on model credits.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Criterion:
    """One thing that must be true for the demonstration to count as a pass."""

    name: str
    expectation: str
    passed: bool
    observed: str


@dataclass
class ScenarioResult:
    deliverable: str
    title: str
    steps: list[str] = field(default_factory=list)
    criteria: list[Criterion] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def step(self, message: str) -> None:
        self.steps.append(message)

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
    def passed(self) -> bool:
        return bool(self.criteria) and all(item.passed for item in self.criteria)


def render(result: ScenarioResult) -> str:
    lines = [
        "",
        "=" * 78,
        f"{result.deliverable}  {result.title}",
        "=" * 78,
        "",
        "Steps",
        "-----",
    ]
    lines.extend(f"{index:>2}. {step}" for index, step in enumerate(result.steps, 1))
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
