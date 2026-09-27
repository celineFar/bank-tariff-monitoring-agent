"""Interpretations recorded from the live interpreter, replayed offline (RRS01).

`scripts/record_interpretations.py` runs the live `AdkRequestInterpreter` over
the interpretation case set and writes `recorded_interpretations.json`. A
recording is keyed by the message and the conversation context the
interpreter saw; the catalog and allowed values are constant and left out.

Recordings are kept per case: the live model is not fully deterministic even
at temperature 0, so two cases that open with the same message can get
slightly different first answers, and therefore different contexts later.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from app.domain.interpretation import InterpretationRequest, RequestInterpretation

FIXTURE = Path(__file__).with_name("recorded_interpretations.json")


def recording_key(request: InterpretationRequest) -> str:
    payload = {
        "message": request.message,
        "context": request.context.model_dump(mode="json"),
    }
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def load_recordings(path: Path = FIXTURE) -> dict[str, dict[str, dict]]:
    """{case_id: {recording_key: entry}}."""
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))["cases"]


class RecordedInterpreter:
    """Replays recorded interpretations; an unrecorded request fails loudly.

    With `case_id`, only that case's recordings are used (multi-turn replay);
    without, any case's recording of the same message and context serves.
    """

    def __init__(self, path: Path = FIXTURE, *, case_id: str | None = None) -> None:
        cases = load_recordings(path)
        if case_id is not None:
            self._entries = dict(cases.get(case_id, {}))
        else:
            self._entries = {}
            for entries in cases.values():
                for key, entry in entries.items():
                    self._entries.setdefault(key, entry)
        self.calls = 0

    async def interpret(self, request: InterpretationRequest) -> RequestInterpretation:
        self.calls += 1
        entry = self._entries.get(recording_key(request))
        if entry is None:
            raise LookupError(
                f"no recorded interpretation for {request.message!r}; "
                "run scripts/record_interpretations.py"
            )
        return RequestInterpretation.model_validate(entry["interpretation"])


class RecordingInterpreter:
    """Wraps a live interpreter and keeps what it answered, keyed for replay."""

    def __init__(self, live) -> None:
        self._live = live
        self.entries: dict[str, dict] = {}
        self.stats: list[dict] = []

    async def interpret(self, request: InterpretationRequest) -> RequestInterpretation:
        interpretation = await self._live.interpret(request)
        self.entries[recording_key(request)] = {
            "message": request.message,
            "context": request.context.model_dump(mode="json"),
            "interpretation": interpretation.model_dump(mode="json"),
        }
        call = getattr(self._live, "last_call", None)
        if call is not None:
            self.stats.append(
                {
                    "input_tokens": call.input_tokens,
                    "output_tokens": call.output_tokens,
                    "latency_ms": call.latency_ms,
                }
            )
        return interpretation
