from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.ringer.phase1 import act3a_probe, check_act3a_probe
from storygame.story_package.loader import load_story_package

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = load_story_package(ROOT / "data/stories/continuity-initiative")


@pytest.mark.parametrize("ledger", ["transmit", "rescue"])
def test_dry_run_reaches_3b_and_passes_checker(tmp_path: Path, ledger: str) -> None:
    assert act3a_probe.run(tmp_path, ledger, 1, True, False) == 0
    assert check_act3a_probe.check(tmp_path, 1, "dry") == []
    row = json.loads((tmp_path / "results.json").read_text())["rows"][0]
    assert row["final_scene"] == "3B"
    assert row["final_true_facts"] == sorted(row["final_true_facts"])
    assert bool(row["entry_variant_seen"]) is (ledger == "rescue")


def test_rescue_entry_variant_is_real_package_text() -> None:
    state = act3a_probe._state(PACKAGE, "rescue")
    scene = next(item for item in PACKAGE.scenes if item.metadata.scene_id == "3A")
    expected = next(
        variant.text for variant in scene.metadata.entry_variants if "committed_to_rescue" in variant.requires
    )
    assert expected in act3a_probe._entry_screen(PACKAGE, state)
    transmit = act3a_probe._entry_screen(PACKAGE, act3a_probe._state(PACKAGE, "transmit"))
    assert expected not in transmit


def test_checker_rejects_stale_cue_and_wrong_scene(tmp_path: Path) -> None:
    assert act3a_probe.run(tmp_path, "transmit", 1, True, False) == 0
    path = tmp_path / "results.json"
    artifact = json.loads(path.read_text())
    row = artifact["rows"][0]
    row["stale_cues"][0]["stale"] = True
    row["scene"] = "3B"
    path.write_text(json.dumps(artifact))
    errors = check_act3a_probe.check(tmp_path, 1, "dry")
    assert any("stale cue" in error for error in errors)
    assert any("scene must be '3A'" in error for error in errors)


def test_live_mode_without_confirm_refuses(tmp_path: Path) -> None:
    with pytest.raises(SystemExit, match="requires --confirm"):
        act3a_probe.run(tmp_path, "transmit", 1, False, False)
