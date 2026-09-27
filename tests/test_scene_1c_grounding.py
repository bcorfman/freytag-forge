from pathlib import Path

import pytest

from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.state import RuntimeState
from storygame.runtime.validation import ProposalValidationError
from storygame.runtime.world_model import apply_scene_placements, world_for
from storygame.story_package.loader import load_story_package

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))


def _scene_1c_state() -> RuntimeState:
    state = RuntimeState.bootstrap(PACKAGE)
    state.current_scene_id = "1C"
    apply_scene_placements(PACKAGE, state.facts, "1C")
    return state


def test_scene_1c_places_the_facility_arrival() -> None:
    state = _scene_1c_state()
    world = world_for(PACKAGE, state.facts)

    assert world.parent("kristin") == "freight_terminal"
    assert world.parent("brandon") == "freight_terminal"
    assert world.parent("kristin_truck") == "freight_terminal"
    assert "brandon" in world.companions("kristin")
    assert "regional_facility" in world.chain("kristin_laptop")

    assert world.move("kristin", "observation_shaft").ok
    assert world.parent("brandon") == "observation_shaft"
    assert not world.move("logistics_terminal", "kristin").ok

    locations = {location.id: location for location in PACKAGE.world.locations}
    for location_id in (
        "facility_perimeter",
        "janus_archive",
        "purge_chamber",
        "detention_level",
        "broadcast_relay",
        "facility_escape",
        "freight_terminal",
    ):
        assert locations[location_id].parent == "regional_facility"


def test_scene_1c_narration_allows_related_facility_areas() -> None:
    state = _scene_1c_state()
    proposal = RuntimeEngine(
        state,
        lambda _command: {
            "segments": [
                {
                    "kind": "narration",
                    "text": "Kristin and Brandon cross the loading docks toward the observation shaft.",
                }
            ],
            "selected_knowledge_ids": [],
        },
    ).turn("Search the loading docks for a way into the service level.")

    assert proposal.segments[0].text == "Kristin and Brandon cross the loading docks toward the observation shaft."


def test_scene_1c_narration_rejects_a_sibling_facility_area() -> None:
    state = _scene_1c_state()
    with pytest.raises(ProposalValidationError) as caught:
        RuntimeEngine(
            state,
            lambda _command: {
                "segments": [{"kind": "narration", "text": "Kristin looks down toward the detention level."}],
                "selected_knowledge_ids": [],
            },
        ).turn("Search the loading docks for a way into the service level.")

    assert caught.value.code == "narration_known_term_leak"
