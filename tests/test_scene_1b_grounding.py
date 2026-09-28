from pathlib import Path

from storygame.runtime.facts import Fact
from storygame.runtime.state import RuntimeState
from storygame.runtime.world_model import (
    apply_scene_placements,
    apply_world_effects,
    world_for,
)
from storygame.story_package.loader import load_story_package

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))


def _scene_1b_state() -> RuntimeState:
    state = RuntimeState.bootstrap(PACKAGE)
    state.current_scene_id = "1B"
    apply_scene_placements(PACKAGE, state.facts, "1B")
    return state


def test_scene_1b_places_the_drop_and_truck() -> None:
    state = _scene_1b_state()
    world = world_for(PACKAGE, state.facts)

    for item_id in ("transit_card", "number_sequence", "michelle_photograph"):
        assert world.parent(item_id) == "park_bench"
        assert world.relation(item_id) == "under"
        assert not world.is_hidden(item_id)

    assert world.parent("kristin_truck") == "los_angeles_park"
    assert "los_angeles_park" in world.chain("kristin_laptop")


def test_identified_brandon_accompanies_kristin_into_the_truck() -> None:
    state = _scene_1b_state()
    world = world_for(PACKAGE, state.facts)

    assert world.parent("brandon") == "los_angeles_park"
    state.facts.assert_fact(Fact(predicate="brandon_identified", subject="story", value="true"))
    apply_world_effects(PACKAGE, state.facts)

    assert world.move("kristin", "kristin_truck").ok
    assert world.parent("brandon") == "kristin_truck"


def test_unidentified_brandon_stays_in_the_park() -> None:
    state = _scene_1b_state()
    world = world_for(PACKAGE, state.facts)

    assert world.parent("brandon") == "los_angeles_park"
    assert world.move("kristin", "kristin_truck").ok
    assert world.parent("brandon") == "los_angeles_park"
