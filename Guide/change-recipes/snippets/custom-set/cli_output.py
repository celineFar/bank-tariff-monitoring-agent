from uuid import uuid4

from google.adk.events import Event

from app import cli


def _progress(kind: str, **extra) -> Event:
    return Event(
        author="tool",
        partial=True,
        custom_metadata={
            "kind": "monitoring_progress",
            "progress": {
                "kind": kind,
                "run_id": str(uuid4()),
                "product": "consumer_loan",
                "offering_id": "overdraft",
                **extra,
            },
        },
    )


def test_offering_outcomes_are_printed(capsys) -> None:
    renderer = cli.ProgressRenderer()
    renderer.render(_progress("offering_succeeded"))
    renderer.render(_progress("offering_review"))
    output = capsys.readouterr().out
    assert "✓ overdraft accepted" in output
    assert "● overdraft needs review" in output


def test_stage_label_renamed(capsys) -> None:
    renderer = cli.ProgressRenderer()
    renderer.render(
        _progress("stage_completed", stage="semantic_extraction", elapsed_ms=1200)
    )
    assert "Extracting tariff fields with Gemini" in capsys.readouterr().out
