from __future__ import annotations

from pathlib import Path

from bench.core import load_variation, package_and_state
from scripts.ringer.stage7 import three_c_probe as probe
from storygame.runtime.candidate_matcher import _matches_all

ROOT = Path(__file__).resolve().parents[1]


def _package(arm: str):
    variation = load_variation(probe.variation_paths((arm,))[arm])
    package, _state = package_and_state(variation, "3C")
    return package


def _entry_text(package) -> str:
    return next(scene.metadata.entry_text for scene in package.scenes if scene.metadata.scene_id == "3C")


def _matched_ids(package, command: str) -> set[str]:
    return {
        item.id
        for item in package.knowledge_indexes.by_id.values()
        if item.id.startswith("k_sl_3c_")
        if item.action_evidence and _matches_all(item.action_evidence, command)
    }


def test_entry_variation_replaces_plot_entry_text_exactly_once() -> None:
    old_entry, new_entry = probe._entry_replacement()
    plot = (ROOT / "data/stories/continuity-initiative/plot.md").read_text(encoding="utf-8")
    assert plot.count(old_entry) == 1
    assert _entry_text(_package("entry")) == new_entry.removeprefix('entry_text: "').removesuffix('"').replace(
        "\\n", "\n"
    )


def test_first_player_screen_uses_control_or_entry_text() -> None:
    control = _package("control")
    entry = _package("entry")
    control_screen, _ = probe._player_screen(_entry_text(control), [])
    entry_screen, _ = probe._player_screen(_entry_text(entry), [])
    assert control_screen != entry_screen
    assert _entry_text(control).rstrip() in control_screen
    assert _entry_text(entry).rstrip() in entry_screen


def test_recorded_commands_and_negative_controls_match_identically() -> None:
    commands = [item["command"] for item in probe.recorded_commands()]
    commands += [
        "Transmit the evidence.",
        "Send the evidence.",
        "Run away with the evidence.",
        "Show Rebecca the evidence.",
        "Send the evidence package.",
    ]
    control = _package("control")
    entry = _package("entry")
    for command in commands:
        assert _matched_ids(control, command) == _matched_ids(entry, command)

    assert _matched_ids(control, "Send the evidence package.") == {"k_sl_3c_a_r1"}
    for command in commands[-5:-1]:
        assert _matched_ids(control, command) == set()
