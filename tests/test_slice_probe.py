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
    assert row["prefix"] == "none"
    assert row["scripted_turns"] == 0
    assert not any(turn["scripted"] for turn in row["turns"])
    assert row["nudge_seen_turn"] is None
    assert row["withdrawal_seen_turn"] is None


@pytest.mark.parametrize("prefix", ["missed_window", "secure_route"])
def test_dry_run_prefixes_pass_checker_and_do_not_spend_prefix_player_requests(tmp_path: Path, prefix: str) -> None:
    assert slice_probe.run(tmp_path, 1, True, False, prefix) == 0
    assert check_slice_probe.check(tmp_path, 1, "dry") == []
    artifact = json.loads((tmp_path / "results.json").read_text())
    row = artifact["rows"][0]
    assert row["prefix"] == prefix
    assert row["scripted_turns"] == len(slice_probe.PREFIXES[prefix])
    assert [turn["scripted"] for turn in row["turns"][: row["scripted_turns"]]] == [True] * row["scripted_turns"]
    assert not any(turn["scripted"] for turn in row["turns"][row["scripted_turns"] :])
    summary = json.loads((tmp_path / "summary.json").read_text())
    assert summary["player_requests"] == len(row["commands"]) - row["scripted_turns"]
    assert row["nudge_seen_turn"] is None
    assert row["withdrawal_seen_turn"] is None


def test_stall_prefix_passes_checker_and_has_clean_deadline_handoff(tmp_path: Path) -> None:
    assert slice_probe.run(tmp_path, 1, True, False, "stall") == 0
    assert check_slice_probe.check(tmp_path, 1, "dry") == []
    row = json.loads((tmp_path / "results.json").read_text())["rows"][0]
    assert row["final_scene"] == "2B"
    assert row["nudge_seen_turn"] == 6
    assert row["withdrawal_seen_turn"] == 8
    assert row["scripted_turns"] == 8
    assert row["turns"][7]["scene_after"] == "2A"
    summary = json.loads((tmp_path / "summary.json").read_text())
    assert summary["player_requests"] == len(row["commands"]) - row["scripted_turns"]
    forbidden = {
        "processing_numbers_copied",
        "service_level_access_known",
        "evidence_gap_processing_numbers",
        "trust_brandon",
        "terminal_sweep_closing",
    }
    facts_at_turn_8 = {
        fact_id.split("|", 1)[0] for turn in row["turns"][:8] for fact_id in turn["facts_newly_asserted"]
    }
    assert not forbidden & facts_at_turn_8
    assert not any(turn["committed_reveals"] for turn in row["turns"][:8])


def test_missed_window_prefix_closes_window_without_advantage(tmp_path: Path) -> None:
    assert slice_probe.run(tmp_path, 1, True, False, "missed_window") == 0
    row = json.loads((tmp_path / "results.json").read_text())["rows"][0]
    assert "transfer_window_missed|story|None|true" in row["turns"][4]["facts_newly_asserted"]
    assert not any(
        fact_id.startswith(("processing_numbers_copied|", "service_level_access_known|"))
        for turn in row["turns"][:5]
        for fact_id in turn["facts_newly_asserted"]
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
