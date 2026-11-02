"""The kitchen picture is a plain "photograph"; 1B's photograph never clashes with it (scene scoping)."""

from __future__ import annotations

from pathlib import Path

from storygame.audit import audit_package
from storygame.runtime.facts import Fact
from storygame.runtime.reference_resolution import resolve_references
from storygame.runtime.state import RuntimeState
from storygame.runtime.world_model import apply_scene_placements, apply_world_effects
from storygame.story_package.loader import load_story_package

ROOT = Path("data/stories/continuity-initiative")
PACKAGE = load_story_package(ROOT)


def _kitchen_things():
    return {item.id: item for item in PACKAGE.world.items}


def test_the_kitchen_picture_is_a_plain_lake_photograph():
    item = _kitchen_things()["lake_photograph"]
    assert item.name == "lake photograph"
    assert "lake_snapshot" not in _kitchen_things()
    story_text = "\n".join(
        (ROOT / name).read_text(encoding="utf-8")
        for name in ("plot.md", "world.yaml", "knowledge.yaml", "storylets.md", "storylet-routes.yaml")
    )
    # `canonical_transition_snapshot` is an unrelated structural key in storylet-routes.yaml.
    assert "snapshot" not in story_text.replace("canonical_transition_snapshot", "").casefold()


def test_no_possessive_owner_was_added_to_quiet_the_audit():
    items = _kitchen_things()
    for item_id in ("michelle_tea_mug", "michelle_reading_glasses", "manuscript_pages", "kitchen_calendar"):
        assert "'s " not in items[item_id].name and items[item_id].owner is None
    assert items["lake_photograph"].owner is None and items["truck_radio"].owner is None
    statements = [entry.statement for entry in PACKAGE.knowledge.knowledge if "truck radio" in entry.statement]
    assert statements and all("Kristin's truck radio" not in statement for statement in statements)


def test_the_audit_finds_no_ambiguous_owned_thing():
    findings = audit_package(ROOT)["findings"]
    assert [item for item in findings if item["check"] == "ambiguous_owned_item"] == []


def test_photograph_is_not_ambiguous_in_the_kitchen():
    state = RuntimeState.bootstrap(PACKAGE)
    result = resolve_references(state, "Look at the photograph.")
    assert result.question is None


def test_photograph_is_not_ambiguous_at_the_park_bench_either():
    state = RuntimeState.bootstrap(PACKAGE)
    state.current_scene_id = "1B"
    state.phase = next(scene.metadata.freytag_phase for scene in PACKAGE.scenes if scene.metadata.scene_id == "1B")
    state.facts.assert_fact(Fact(predicate="bench_clues_recovered", subject="story", value="true"))
    apply_world_effects(PACKAGE, state.facts)
    apply_scene_placements(PACKAGE, state.facts, "1B")
    result = resolve_references(state, "Look at the photograph.")
    assert result.question is None
