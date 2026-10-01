from pathlib import Path

import pytest

from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.facts import Fact
from storygame.runtime.state import RuntimeState
from storygame.runtime.world_model import apply_scene_placements, apply_world_effects, world_for
from storygame.story_package.loader import load_story_package

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))


def _scene_2a_state() -> RuntimeState:
    state = RuntimeState.bootstrap(PACKAGE)
    state.current_scene_id = "2A"
    state.phase = next(scene.metadata.freytag_phase for scene in PACKAGE.scenes if scene.metadata.scene_id == "2A")
    state._assert_scene_entry_fact("2A")
    return state


@pytest.mark.parametrize("scene_id", ["2A", "3B", "3C"])
def test_inspection_console_is_fixed_in_the_infrastructure_corridors(scene_id: str) -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    assert apply_scene_placements(PACKAGE, state.facts, scene_id) == ()
    world = world_for(PACKAGE, state.facts)

    assert world.parent("inspection_console") == "infrastructure_corridors"
    assert not world.move("inspection_console", "kristin").ok


def test_scene_2a_accepts_narration_about_following_the_corridors() -> None:
    state = _scene_2a_state()
    assert apply_scene_placements(PACKAGE, state.facts, "2A") == ()
    state.facts.assert_fact(Fact(predicate="false_identities_ready", subject="story", value="true"))
    state.facts.assert_fact(Fact(predicate="facility_perimeter_reached", subject="story", value="true"))
    assert apply_world_effects(PACKAGE, state.facts) == ()

    proposal = RuntimeEngine(
        state,
        lambda _command: {
            "segments": [
                {
                    "kind": "narration",
                    "text": "Kristin follows the infrastructure corridors to the inspection console.",
                }
            ],
            "selected_knowledge_ids": [],
        },
    ).turn("Check the inspection console for water-pressure readings.")

    assert proposal.segments[0].text == "Kristin follows the infrastructure corridors to the inspection console."


def test_scene_2a_scrutiny_waits_for_false_identities() -> None:
    def drive(state: RuntimeState) -> None:
        engine = RuntimeEngine(
            state,
            lambda _command: {"segments": [{"kind": "narration", "text": "Search the servers."}]},
        )
        for _ in range(3):
            engine.turn("Search the servers for the leaked files.")

    without_cover = _scene_2a_state()
    drive(without_cover)
    assert (
        Fact(predicate="identity_scrutiny_visible", subject="story", value="true") not in without_cover.facts.asserted
    )

    with_cover = _scene_2a_state()
    with_cover.facts.assert_fact(Fact(predicate="false_identities_ready", subject="story", value="true"))
    with_cover.facts.assert_fact(Fact(predicate="facility_perimeter_reached", subject="story", value="true"))
    drive(with_cover)
    assert Fact(predicate="identity_scrutiny_visible", subject="story", value="true") in with_cover.facts.asserted
