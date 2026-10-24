from __future__ import annotations

import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from storygame.runtime.candidate_matcher import uniquely_matched_authored_handoff
from storygame.runtime.facts import FactStore
from storygame.runtime.knowledge import KnowledgeProjector
from storygame.runtime.reveal_eligibility import NOT_REACHABLE, explain_reveal
from storygame.runtime.state import RuntimeState
from storygame.runtime.world_model import world_for
from storygame.story_package import StoryPackageError
from storygame.story_package.loader import load_story_package
from storygame.story_package.models import (
    Audience,
    Item,
    KnowledgeDefinition,
    Location,
    Npc,
    RevealSource,
    RouteOperation,
    WorldSource,
)

PACKAGE_ROOT = Path("data/stories/continuity-initiative")
PACKAGE = load_story_package(PACKAGE_ROOT)
REVEALS = ("k_sl_1a_b_r0", "k_sl_1a_f_r1", "k_sl_1a_f_r2")


def _scene_state() -> RuntimeState:
    state = RuntimeState.bootstrap(PACKAGE)
    state.active_event_ids.update({"SL-1A-E", "SL-1A-F"})
    return state


def test_scene_reveals_require_the_protagonist_to_reach_the_drawer() -> None:
    state = _scene_state()
    world = world_for(PACKAGE, state.facts)
    assert world.move("kristin", "outside_house").ok

    for knowledge_id in REVEALS:
        result = explain_reveal(state, "player", PACKAGE.knowledge_indexes.by_id[knowledge_id])
        assert (result.eligible, result.reason) == (False, NOT_REACHABLE)

    projection = KnowledgeProjector().project(state, "player", "Feel under the drawer.")
    assert not {candidate.id for candidate in projection.candidates} & set(REVEALS)
    assert uniquely_matched_authored_handoff("Feel under the drawer.", projection.candidates) is None
    assert uniquely_matched_authored_handoff("Feel in the gap.", projection.candidates) is None


def test_scene_reveals_are_reachable_at_home_but_not_from_the_truck() -> None:
    state = _scene_state()
    world = world_for(PACKAGE, state.facts)
    result = explain_reveal(state, "player", PACKAGE.knowledge_indexes.by_id[REVEALS[0]])
    assert result.eligible
    projection = KnowledgeProjector().project(state, "player", "Feel under the drawer.")
    handoff = uniquely_matched_authored_handoff("Feel under the drawer.", projection.candidates)
    assert handoff is not None
    assert handoff.candidate.id == REVEALS[0]

    assert world.move("kristin", "outside_house").ok
    assert world.move("kristin", "truck_driver_seat").ok
    result = explain_reveal(state, "player", PACKAGE.knowledge_indexes.by_id[REVEALS[0]])
    assert (result.eligible, result.reason) == (False, NOT_REACHABLE)


def _synthetic_state() -> tuple[RuntimeState, KnowledgeDefinition]:
    world = WorldSource(
        story_id="synthetic",
        protagonist_id="hero",
        locations=(Location(id="room_a", name="Room A"), Location(id="room_b", name="Room B")),
        npcs=(Npc(id="hero", name="Hero"),),
        items=(Item(id="target", name="Target"),),
    )
    package = SimpleNamespace(world=world)
    state = RuntimeState.model_construct(
        package=package,
        current_scene_id="1A",
        phase="exposition",
        active_event_ids={"SL-1A-A"},
        fired_event_ids=set(),
        facts=FactStore(),
    )
    world_model = world_for(package, state.facts)
    assert world_model.place("hero", "room_a").ok
    assert world_model.place("target", "room_a").ok
    item = KnowledgeDefinition(
        id="k_target",
        statement="The target matters.",
        aliases=("target matters",),
        audience=Audience(kind="public", player_visible=True),
        available_in_scenes=("1A",),
        establishes=(RouteOperation(op="assert", fact_id="target_known", value=True),),
        source=RevealSource(kind="storylet_realization", storylet_id="SL-1A-A", realization_id="r1"),
        reach_entity_ids=("target",),
    )
    return state, item


def test_synthetic_reveal_reach_is_story_neutral() -> None:
    state, item = _synthetic_state()
    assert explain_reveal(state, "player", item).eligible
    world = world_for(state.package, state.facts)
    assert world.move("hero", "room_b").ok
    result = explain_reveal(state, "player", item)
    assert (result.eligible, result.reason, result.detail) == (False, NOT_REACHABLE, "target")


def test_loader_rejects_an_unknown_reach_entity(tmp_path: Path) -> None:
    destination = tmp_path / "package"
    shutil.copytree(PACKAGE_ROOT, destination)
    source = destination / "knowledge.yaml"
    catalog = yaml.safe_load(source.read_text())
    item = next(item for item in catalog["knowledge"] if item["id"] == REVEALS[0])
    item["reach_entity_ids"] = ["undeclared_entity"]
    source.write_text(yaml.safe_dump(catalog, sort_keys=False))

    with pytest.raises(StoryPackageError, match="k_sl_1a_b_r0.*undeclared_entity"):
        load_story_package(destination)
