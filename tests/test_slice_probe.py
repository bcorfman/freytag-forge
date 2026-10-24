from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.ringer.phase1 import check_slice_probe, slice_probe
from storygame.story_package.loader import load_story_package

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = load_story_package(ROOT / "data/stories/continuity-initiative")
INCIDENT = PACKAGE.incidents[0]


def test_dry_run_real_package_passes_checker(tmp_path: Path) -> None:
    assert slice_probe.run(tmp_path, 1, True, False) == 0
    assert check_slice_probe.check(tmp_path, 1, "dry") == []
    row = json.loads((tmp_path / "results.json").read_text())["rows"][0]
    assert row["final_scene"] == "2B"
    assert row["exit_cause"] == "copy_numbers"


def test_stale_cue_detector() -> None:
    assert slice_probe.detect_stale_cue("known", {"known"})
    assert not slice_probe.detect_stale_cue("new", {"known"})
    assert not slice_probe.detect_stale_cue(None, {"known"})


def test_exit_cause_classifier_three_declared_outcomes() -> None:
    assert slice_probe.classify_exit_cause({"processing_numbers_copied"}, INCIDENT) == "copy_numbers"
    assert slice_probe.classify_exit_cause({"service_level_access_known"}, INCIDENT) == "secure_route"
    assert (
        slice_probe.classify_exit_cause({"transfer_window_missed", "service_level_access_known"}, INCIDENT)
        == "missed_window_plus_recovery"
    )


def test_cap_exhaustion_writes_failure_without_retry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(slice_probe, "_commands_for", lambda _mode: ([], []))
    assert slice_probe.run(tmp_path, 1, True, False) == 1
    assert (tmp_path / "run-failure.txt").exists()
    assert json.loads((tmp_path / "results.json").read_text())["rows"] == []


def test_live_mode_without_confirm_refuses(tmp_path: Path) -> None:
    with pytest.raises(SystemExit, match="requires --confirm"):
        slice_probe.run(tmp_path, 1, False, False)
