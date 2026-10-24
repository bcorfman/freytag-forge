from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

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
    assert row["turns"]
    assert len(row["turns"]) == len(row["commands"])
    assert row["final_true_facts"] == sorted(row["final_true_facts"])
    assert row["repeated_response_streak_max"] >= 1
    assert row["stuck_loop"] is (row["repeated_response_streak_max"] >= 3)
    assert all(
        {
            "turn",
            "scene_before",
            "scene_after",
            "facts_newly_asserted",
            "facts_retracted",
            "committed_reveals",
            "reveal_selection",
            "last_attempt_rejection",
            "transition_cause",
            "request_count_delta",
            "recovery_count_delta",
            "staged_cue_fact_id",
            "staged_handoff_fact_ids",
            "delivered_cue_ids",
            "segments_dropped",
            "repeated_response",
        }
        <= turn.keys()
        for turn in row["turns"]
    )


class _FixedTextProvider:
    def __init__(self, text: str) -> None:
        self.text = text
        self.request_count = 0
        self.recovery_count = 0
        self.last_reveal_selection = {"outcome": "no_eligible_action"}
        self.last_semantic_match = {"ran": False, "matched": None}
        self.authored_handoff = None

    def __call__(self, _command: str) -> dict[str, object]:
        self.request_count += 1
        return {"segments": [{"kind": "narration", "text": self.text}]}


def _run_fixed_text(monkeypatch: pytest.MonkeyPatch, texts: list[str]) -> dict[str, object]:
    state = slice_probe._state(PACKAGE)
    provider = _FixedTextProvider(texts[0])
    calls = 0

    class FakeEngine:
        last_attempt = SimpleNamespace(rejection=None, transition_cause="none")

        def __init__(self, runtime_state, runtime_provider) -> None:
            self.state = runtime_state
            self.provider = runtime_provider

        def turn(self, command: str):
            nonlocal calls
            self.provider(command)
            response = texts[calls]
            calls += 1
            if calls == len(texts):
                self.state.story_complete = True
            return SimpleNamespace(segments=(SimpleNamespace(text=response),))

    monkeypatch.setattr(slice_probe, "RuntimeEngine", FakeEngine)
    commands = iter([f"Command {index}" for index in range(len(texts))])

    def ask(_screen: str, budget):
        return next(commands)

    return slice_probe._run_row(
        PACKAGE, state, provider, ask, slice_probe.SpendBudget(80, cloudflare_limit=80, player_limit=40), "test-row"
    )


def test_repeated_response_streak_reports_stuck_loop(monkeypatch: pytest.MonkeyPatch) -> None:
    row = _run_fixed_text(monkeypatch, ["same"] * 4)
    assert row["stuck_loop"] is True
    assert row["repeated_response_streak_max"] == 4
    assert [turn["repeated_response"] for turn in row["turns"]] == [False, True, True, True]


def test_different_responses_do_not_report_stuck_loop(monkeypatch: pytest.MonkeyPatch) -> None:
    row = _run_fixed_text(monkeypatch, ["one", "two", "three", "four"])
    assert row["stuck_loop"] is False
    assert row["repeated_response_streak_max"] == 1


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
