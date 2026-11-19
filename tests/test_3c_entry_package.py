from __future__ import annotations

from pathlib import Path

from scripts.ringer.stage7 import three_c_probe as probe
from storygame.runtime.candidate_matcher import _matches_all
from tests.story_source.helpers import compiled_story_copy, load_compiled_copy, patch_source

OLD_ENTRY = (
    "The broadcast chamber lights steadied as Brandon's relay held open. "
    "Outside, Charles's emergency deluge was filling the outer access level and forcing water toward the "
    "maintenance routes; inside, the evidence was ready to leave for good.\n\n"
)
NEW_ENTRY = (
    "The broadcast chamber lights are steady. Brandon's relay is open. Michelle's evidence package is ready to send. "
    "Water is entering the outer access level.\n\n"
)


def _package(arm: str, tmp_path: Path):
    root = compiled_story_copy(tmp_path / arm)
    patch_source(root, "source/scenes/3C.yaml", "entry", OLD_ENTRY if arm == "control" else NEW_ENTRY)
    return load_compiled_copy(root)


def _entry_text(package) -> str:
    return next(scene.metadata.entry_text for scene in package.scenes if scene.metadata.scene_id == "3C")


def _matched_ids(package, command: str) -> set[str]:
    return {
        item.id
        for item in package.knowledge_indexes.by_id.values()
        if item.id.startswith("k_sl_3c_")
        if item.action_evidence and _matches_all(item.action_evidence, command)
    }


def test_entry_variation_replaces_plot_entry_text_exactly_once(tmp_path: Path) -> None:
    assert _entry_text(_package("control", tmp_path)) == OLD_ENTRY
    assert _entry_text(_package("entry", tmp_path)) == NEW_ENTRY


def test_first_player_screen_uses_control_or_entry_text(tmp_path: Path) -> None:
    control = _package("control", tmp_path)
    entry = _package("entry", tmp_path)
    control_screen, _ = probe._player_screen(_entry_text(control), [])
    entry_screen, _ = probe._player_screen(_entry_text(entry), [])
    assert control_screen != entry_screen
    assert _entry_text(control).rstrip() in control_screen
    assert _entry_text(entry).rstrip() in entry_screen


def test_recorded_commands_and_negative_controls_match_identically(tmp_path: Path) -> None:
    commands = [item["command"] for item in probe.recorded_commands()]
    commands += [
        "Transmit the evidence.",
        "Send the evidence.",
        "Run away with the evidence.",
        "Show Rebecca the evidence.",
        "Send the evidence package.",
    ]
    control = _package("control", tmp_path)
    entry = _package("entry", tmp_path)
    for command in commands:
        assert _matched_ids(control, command) == _matched_ids(entry, command)

    assert _matched_ids(control, "Send the evidence package.") == {"k_sl_3c_a_r1"}
    for command in commands[-5:-1]:
        assert _matched_ids(control, command) == set()
