from pathlib import Path

import pytest

from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.facts import Fact
from storygame.runtime.state import RuntimeState
from storygame.runtime.validation import ProposalValidationError
from storygame.runtime.world_model import apply_scene_placements, world_for
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
    assert apply_scene_placements(PACKAGE, state.facts, "2A") == ()
    if scene_id != "2A":
        assert apply_scene_placements(PACKAGE, state.facts, scene_id) == ()
    world = world_for(PACKAGE, state.facts)

    assert world.parent("inspection_console") == "infrastructure_corridors"
    assert not world.move("inspection_console", "kristin").ok


def test_scene_2a_rejects_narration_about_unearned_corridor_access() -> None:
    state = _scene_2a_state()
    assert apply_scene_placements(PACKAGE, state.facts, "2A") == ()
    with pytest.raises(ProposalValidationError):
        RuntimeEngine(
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


def test_scene_2a_inspection_window_comes_from_the_supervisor_incident() -> None:
    state = _scene_2a_state()
    engine = RuntimeEngine(
        state,
        lambda _command: {"segments": [{"kind": "narration", "text": "The inspection continues."}]},
    )

    for _ in range(5):
        engine.turn("Explain the cooling-water fault to the supervisor.")

    assert Fact(predicate="inspection_window_missed", subject="story", value="true") in state.facts.asserted
    assert Fact(predicate="cover_suspected", subject="story", value="true") not in state.facts.asserted
