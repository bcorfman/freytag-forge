from __future__ import annotations

import json
from pathlib import Path

from factory.checks import gap_delta

STORY_ROOT = Path("data/stories/continuity-initiative")


def test_all_anchors_and_two_anchor_snapshot() -> None:
    anchors = gap_delta.all_anchors(STORY_ROOT)

    assert anchors == sorted(set(anchors))
    assert "t_1a_1b" in anchors
    assert "i_2c_rebecca_corridor" in anchors

    snap = gap_delta.snapshot(STORY_ROOT, ["t_1a_1b", "i_2c_rebecca_corridor"])
    assert set(snap) == {"t_1a_1b", "i_2c_rebecca_corridor"}
    assert all(values == sorted(values) for values in snap.values())
    assert all("|" in item for values in snap.values() for item in values)


def test_new_and_resolved_results_treat_missing_anchors_as_empty() -> None:
    baseline = {"old": ["rule|subject"], "same": ["keep|it"]}
    current = {"new": ["rule|subject"], "same": ["keep|it", "new|subject"]}

    assert gap_delta.new_results(baseline, current) == {
        "new": ["rule|subject"],
        "same": ["new|subject"],
    }
    assert gap_delta.resolved_results(baseline, current) == {"old": ["rule|subject"]}


def test_snapshot_records_value_errors() -> None:
    snap = gap_delta.snapshot(STORY_ROOT, ["not-a-real-anchor"])

    assert "__errors__" in snap
    assert snap["__errors__"][0].startswith("not-a-real-anchor|")


def test_save_load_and_cli_exit_codes(tmp_path: Path, monkeypatch, capsys) -> None:
    baseline_path = tmp_path / "baseline.json"
    baseline = {"anchor": ["rule|subject"]}
    gap_delta.save_baseline(baseline, baseline_path)
    assert baseline_path.read_text(encoding="utf-8").endswith("\n")
    assert json.loads(baseline_path.read_text(encoding="utf-8")) == baseline
    assert gap_delta.load_baseline(baseline_path) == baseline

    current = {"anchor": ["rule|subject"]}
    monkeypatch.setattr(gap_delta, "snapshot", lambda root, anchors=None: current)
    assert gap_delta.main(["compare", "--root", str(tmp_path), "--baseline", str(baseline_path)]) == 0
    assert capsys.readouterr().out == ""

    current = {"anchor": ["rule|subject", "new|subject"]}
    assert gap_delta.main(["compare", "--root", str(tmp_path), "--baseline", str(baseline_path)]) == 1
    assert capsys.readouterr().out == "NEW anchor new|subject\n"

    current = {"__errors__": ["anchor|broken"]}
    assert gap_delta.main(["compare", "--root", str(tmp_path), "--baseline", str(baseline_path)]) == 1
    assert capsys.readouterr().out == "NEW __errors__ anchor|broken\nRESOLVED anchor rule|subject\n"
