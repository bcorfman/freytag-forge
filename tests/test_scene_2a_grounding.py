from pathlib import Path

import pytest

from storygame.runtime.cloudflare import CloudflareTurnProvider
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.facts import Fact
from storygame.runtime.state import RuntimeState
from storygame.runtime.validation import ProposalValidationError
from storygame.runtime.world_model import apply_scene_placements, apply_world_effects, world_for
from storygame.story_package.loader import load_story_package

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))


def _scene_2a_state() -> RuntimeState:
    state = RuntimeState.bootstrap(PACKAGE)
    state.current_scene_id = "2A"
    assert apply_scene_placements(PACKAGE, state.facts, "2A") == ()
    return state


def test_scene_2a_places_the_hideout_and_fixed_servers() -> None:
    state = _scene_2a_state()
    world = world_for(PACKAGE, state.facts)

    assert world.parent("kristin") == "brandon_hideout"
    assert world.parent("brandon") == "brandon_hideout"
    assert world.parent("hideout_servers") == "brandon_hideout"
    assert "brandon" in world.companions("kristin")
    assert not world.move("hideout_servers", "kristin").ok


def test_false_identities_ready_moves_the_group_to_the_facility() -> None:
    state = _scene_2a_state()
    state.facts.assert_fact(Fact(predicate="false_identities_ready", subject="story", value="true"))

    assert apply_world_effects(PACKAGE, state.facts) == ()
    world = world_for(PACKAGE, state.facts)

    assert world.parent("kristin") == "facility_perimeter"
    assert world.parent("brandon") == "facility_perimeter"
    assert "regional_facility" in world.chain("kristin")


def test_scene_2a_narration_uses_hideout_grounding() -> None:
    state = _scene_2a_state()
    proposal = RuntimeEngine(
        state,
        lambda _command: {
            "segments": [
                {
                    "kind": "narration",
                    "text": "Kristin sorts through the servers in Brandon's hideout.",
                }
            ],
            "selected_knowledge_ids": [],
        },
    ).turn("Search the servers for the leaked files.")

    assert proposal.segments[0].text == "Kristin sorts through the servers in Brandon's hideout."


def test_scene_2a_narration_rejects_a_sibling_facility_area() -> None:
    state = _scene_2a_state()
    with pytest.raises(ProposalValidationError) as caught:
        RuntimeEngine(
            state,
            lambda _command: {
                "segments": [{"kind": "narration", "text": "Kristin looks down toward the detention level."}],
                "selected_knowledge_ids": [],
            },
        ).turn("Search the servers for the leaked files.")

    assert caught.value.code == "narration_known_term_leak"


def test_scene_entry_uses_protagonist_placement_parent() -> None:
    state = _scene_2a_state()
    provider = CloudflareTurnProvider(worker_url="https://worker.example/turn", token="", state=state)

    assert provider._scene_entry()["location"] == "Brandon's hideout"

    state.current_scene_id = "1C"
    provider = CloudflareTurnProvider(worker_url="https://worker.example/turn", token="", state=state)
    assert provider._scene_entry()["location"] == "freight terminal"
