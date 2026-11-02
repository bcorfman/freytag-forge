from __future__ import annotations

from pathlib import Path

import pytest

from scripts.ringer.phase2 import act3c_probe, check_act3c_probe
from storygame.runtime.candidate_matcher import ActionEvidenceCandidate, _matches_all
from storygame.story_package.loader import load_story_package

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = load_story_package(ROOT / "data/stories/continuity-initiative")


@pytest.mark.parametrize(
    ("prefix", "exit_cause", "variant"),
    [
        ("none", "evacuation_clean", "barrier_held"),
        ("clean", "evacuation_clean", "barrier_held"),
        ("costly", "evacuation_costly", "lower_levels_lost"),
        ("stall", "neutral_recovery", "surge_forced_evacuation"),
    ],
)
def test_dry_prefix_reaches_ending_and_passes_checker(
    tmp_path: Path, prefix: str, exit_cause: str, variant: str
) -> None:
    assert act3c_probe.run(tmp_path, prefix, 1, True, False) == 0
    assert check_act3c_probe.check(tmp_path, 1, "dry") == []
    row = __import__("json").loads((tmp_path / "results.json").read_text(encoding="utf-8"))["rows"][0]
    assert row["story_complete"] is True
    assert row["exit_cause"] == exit_cause
    assert variant in row["ending_variants_seen"]


def test_every_scripted_command_matches_only_its_intended_3c_entry() -> None:
    candidates = tuple(
        ActionEvidenceCandidate(id=item.id, required_groups=item.action_evidence)
        for item in PACKAGE.knowledge.knowledge
        if item.id in act3c_probe.KNOWLEDGE_IDS and item.action_evidence
    )
    for prefix, expectations in act3c_probe.SCRIPTED_EXPECTATIONS.items():
        for command, expected_id in expectations:
            matches = [candidate.id for candidate in candidates if _matches_all(candidate.required_groups, command)]
            assert matches == ([] if expected_id is None else [expected_id]), (prefix, command, matches)


def test_stall_dry_route_is_neutral_only_and_selects_no_knowledge() -> None:
    commands, selections = act3c_probe._scripted_route("stall")
    assert commands == list(act3c_probe.NEUTRAL_COMMANDS)
    assert len(commands) == 10
    assert commands == list(act3c_probe.SCRIPTED_PREFIXES["stall"])
    assert selections == [None] * len(act3c_probe.NEUTRAL_COMMANDS)


def test_stall_dry_route_fires_window_and_nudge_at_authored_turns(tmp_path: Path) -> None:
    assert act3c_probe.run(tmp_path, "stall", 1, True, False) == 0
    row = __import__("json").loads((tmp_path / "results.json").read_text(encoding="utf-8"))["rows"][0]
    assert row["window_event_fired_turn"] == 9
    assert row["nudge_event_fired_turn"] == 10
