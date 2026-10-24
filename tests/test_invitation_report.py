from __future__ import annotations

from pathlib import Path

from scripts.ringer.affordance import invitation_report
from scripts.ringer.affordance.cue_eligibility_compare import report as cue_report
from storygame.story_package.loader import load_story_package

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))


def _output() -> str:
    return invitation_report.report(PACKAGE)


def _rows(output: str) -> list[str]:
    start = output.index("scene | state | delivery fact")
    end = output.index("\n\nLABEL COUNTS", start)
    return output[start:].splitlines()[1 : len(output[start:end].splitlines())]


def test_report_runs_and_prints_legend_and_limits(capsys) -> None:
    assert invitation_report.main([]) == 0
    output = capsys.readouterr().out
    assert "INVITATION REPORT" in output
    assert "Legend:" in output
    assert "LIMITS" in output
    assert "UNREVIEWED CANDIDATES" in output


def test_every_report_row_has_a_review_label() -> None:
    labels = {"eligible response", "unanswered invitation", "unknown"}
    rows = _rows(_output())
    assert rows
    assert all(row.rsplit(" | ", 1)[-1] in labels for row in rows)


def test_spent_reveal_rows_are_absent_after_cue_change() -> None:
    assert "CUE_SHOWN_BUT_SPENT: 0" in cue_report(PACKAGE)
    assert "unanswered invitation: 0" in _output()


def test_1a_drawer_cue_has_an_eligible_response() -> None:
    delivery = next(item for item in PACKAGE.deliveries if item.scene_id == "1A" and item.cue_text)
    rows = [row for row in _rows(_output()) if f" | {delivery.fact_id} | " in row]
    assert rows
    assert any(row.endswith(" | eligible response") for row in rows)
