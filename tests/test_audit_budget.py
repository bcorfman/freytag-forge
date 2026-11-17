from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from storygame.audit_budget import deep_turn_budget, report
from storygame.story_package.loader import load_story_package
from tests.story_source.helpers import DELETE, compiled_story_copy, load_compiled_copy, patch_source

REAL_PACKAGE = Path("data/stories/continuity-initiative")
FIXTURE = Path("tests/fixtures/deep_turn_budget.json")
# The pins are a regression tripwire, not the limit: a scene may grow to this size before the ratchet fails.
# Brandon: no warning until 6400. The real hard cap (6500, checked below) is unchanged.
RATCHET_TOLERANCE = 6400
KNOWN_OVER_BUDGET = frozenset({"3A", "3B", "3C"})  # O8 in .plans/richer-3a-open-issues-plan.md.


def _package(tmp_path: Path, *, alternate: bool = False, with_knowledge: bool = True):
    root = compiled_story_copy(tmp_path)
    source = root / "source"
    patch_source(
        source, "scenes/1A.yaml", "facts.deep_statement_known", {"purpose": "Kristin knows the deep statement."}
    )
    scene_path = source / "scenes" / "1A.yaml"
    match_path = source / "scenes" / "1A.match.yaml"
    scene = yaml.safe_load(scene_path.read_text(encoding="utf-8"))
    scene["facts"]["deep_statement_known"]["delivery"] = scene["facts"]["continuity_initiative_known"].pop("delivery")
    scene_path.write_text(yaml.safe_dump(scene, sort_keys=False, width=10_000), encoding="utf-8")
    match = yaml.safe_load(match_path.read_text(encoding="utf-8"))
    match["deliveries"]["deep_statement_known"] = match["deliveries"].pop("continuity_initiative_known")
    match_path.write_text(yaml.safe_dump(match, sort_keys=False, width=10_000), encoding="utf-8")
    patch_source(
        source,
        "scenes/1A.yaml",
        "reveals[sl_1a_a].variants.r1.commits",
        {"deep_statement_known": True},
    )
    patch_source(source, "scenes/1A.yaml", "bridge[bridge_1a_actionable_lead].when", ["deep_statement_known"])
    patch_source(source, "scenes/1A.yaml", "beats[kristin_steadies_1a].sets", {"deep_statement_known": True})

    if not with_knowledge:
        patch_source(source, "scenes/1A.yaml", "reveals[sl_1a_a].variants.r1.audience.player_visible", False)
        patch_source(source, "scenes/1A.yaml", "facts.deep_statement_known.delivery", DELETE)
        patch_source(source, "scenes/1A.match.yaml", "deliveries", {})
        patch_source(source, "scenes/1A.yaml", "bridge", [])
    if alternate:
        patch_source(
            source,
            "scenes/1A.yaml",
            "facts.deep_statement_alt_known",
            {"purpose": "Kristin knows the alternate statement."},
        )
        scene = yaml.safe_load(scene_path.read_text(encoding="utf-8"))
        alternate_variant = deepcopy(scene["reveals"][0]["variants"]["r1"])
        alternate_variant["realization_id"] = "SL-1A-A-R2"
        alternate_variant["claim_id"] = "k_sl_1a_a_r1_alt"
        alternate_variant["intent"] = "Connect the evidence another way."
        alternate_variant["says"] = "Kristin recognizes the alternate deep statement."
        alternate_variant["commits"] = {"deep_statement_alt_known": True}
        scene["reveals"][0]["variants"]["alt"] = alternate_variant
        scene_path.write_text(yaml.safe_dump(scene, sort_keys=False, width=10_000), encoding="utf-8")
        match = yaml.safe_load(match_path.read_text(encoding="utf-8"))
        match["claims"]["k_sl_1a_a_r1_alt"] = deepcopy(match["claims"]["k_sl_1a_a_r1"])
        match["claims"]["k_sl_1a_a_r1_alt"]["aliases"] = ["alternate deep statement"]
        match_path.write_text(yaml.safe_dump(match, sort_keys=False, width=10_000), encoding="utf-8")
    return load_compiled_copy(root)


def test_established_knowledge_makes_the_deep_prompt_longer(tmp_path: Path) -> None:
    without_knowledge = deep_turn_budget(_package(tmp_path / "without", with_knowledge=False), "1A")
    with_knowledge = deep_turn_budget(_package(tmp_path / "with"), "1A")

    assert with_knowledge["established_entries"] > without_knowledge["established_entries"]
    assert with_knowledge["narration_chars"] > without_knowledge["narration_chars"]


def test_all_alternates_are_reported_and_make_the_prompt_larger(tmp_path: Path) -> None:
    result = deep_turn_budget(_package(tmp_path, alternate=True), "1A")

    assert result["alternate_pairs"] == ["SL-1A-A", "SL-1A-B", "SL-1A-C", "SL-1A-F", "SL-1A-G", "SL-1A-J"]
    assert result["narration_chars_all_alternates"] > result["narration_chars"]


def test_report_is_deterministic(tmp_path: Path) -> None:
    package = _package(tmp_path)

    assert report(package) == report(package)


def test_real_package_ratchet() -> None:
    if not FIXTURE.exists():
        pytest.fail(f"{FIXTURE} is missing; run python -m storygame.audit_budget --write")
    pinned = json.loads(FIXTURE.read_text(encoding="utf-8"))
    rows = report(REAL_PACKAGE)
    actual = {row["scene_id"]: row for row in rows}

    for scene_id, expected in pinned.get("scenes", {}).items():
        assert scene_id in actual, f"fixture scene {scene_id!r} is not in the current package"
        for key in ("narration_chars", "narration_chars_all_alternates"):
            old_pin = expected[key]
            new_value = actual[scene_id][key]
            ceiling = max(old_pin, RATCHET_TOLERANCE)
            assert new_value <= ceiling, f"{scene_id}: ceiling {ceiling} (old pin {old_pin}), new value {new_value}"

    assert all(row["entry_narration_chars"] <= row["narration_chars"] for row in rows), "entry turn exceeds deep turn"

    expected_scenes = {scene.metadata.scene_id for scene in load_story_package(REAL_PACKAGE).scenes}
    missing = expected_scenes - set(pinned.get("scenes", {}))
    assert not missing, f"fixture is missing scenes {sorted(missing)}; run python -m storygame.audit_budget --write"

    over_budget = {scene_id for scene_id, row in actual.items() if row["narration_chars"] > 6500}
    assert over_budget <= KNOWN_OVER_BUDGET
