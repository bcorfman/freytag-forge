from pathlib import Path

import pytest

from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.facts import Fact
from storygame.runtime.item_facts import ItemFactsProvider
from storygame.runtime.state import RuntimeState
from storygame.runtime.validation import ProposalValidationError
from storygame.runtime.world_model import apply_scene_placements
from storygame.story_package.loader import load_story_package

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))


def _scene_state(scene_id: str) -> RuntimeState:
    state = RuntimeState.bootstrap(PACKAGE)
    state.current_scene_id = scene_id
    state.phase = next(scene.metadata.freytag_phase for scene in PACKAGE.scenes if scene.metadata.scene_id == scene_id)
    state._assert_scene_entry_fact(scene_id)
    return state


def _narrate(state: RuntimeState, text: str, command: str = "Search the room.") -> None:
    RuntimeEngine(
        state,
        lambda _command: {"segments": [{"kind": "narration", "text": text}]},
    ).turn(command)


def _rejects(state: RuntimeState, text: str) -> ProposalValidationError:
    with pytest.raises(ProposalValidationError) as caught:
        _narrate(state, text)
    return caught.value


def test_1a_drawer_pointer_does_not_guard_the_gap() -> None:
    state = _scene_state("1A")
    state.facts.assert_fact(Fact(predicate="drawer_gap_pointed_out", subject="story", value="true"))

    _narrate(
        state,
        (
            "Kristin pulls open the drawer with her fingers. Her eyes are drawn to the thin gap beneath the drawer's "
            "lower edge."
        ),
        "Pull open the drawer with my fingers.",
    )
    error = _rejects(state, "Kristin finds Michelle's memory card taped beneath the drawer.")
    assert error.code == "narration_known_term_leak"


def test_1a_card_remains_guarded_while_drawer_gap_wording_is_allowed() -> None:
    _narrate(_scene_state("1A"), "Kristin notices the thin gap beneath the drawer.")

    error = _rejects(_scene_state("1A"), "Kristin picks up the card.")
    assert error.code == "narration_known_term_leak"


def test_1c_alias_and_phase_boundaries_are_narrow() -> None:
    _narrate(
        _scene_state("1C"),
        "Kristin asks Brandon where they can enter the facility without being seen.",
        "Ask Brandon where we can enter the facility without being seen.",
    )

    error = _rejects(_scene_state("1C"), "Brandon says the plan needs deeper access.")
    assert error.code == "narration_known_term_leak"

    _narrate(_scene_state("1C"), "The next phase of the search starts at the shaft.")
    error = _rejects(_scene_state("1C"), "It was Phase Two all along.")
    assert error.code == "protected_narration_leak"


def test_1a_scene_entry_allows_forced_entry_wording() -> None:
    _narrate(_scene_state("1A"), "The back door has been forced, and Kristin takes in the splintered lock.")


def test_servers_are_scoped_to_the_hideout_item() -> None:
    _narrate(_scene_state("1C"), "Kristin looks over the servers in the control room.")

    state = _scene_state("2A")
    apply_scene_placements(PACKAGE, state.facts, "2A")
    provider = ItemFactsProvider(
        worker_url="https://worker.example/turn",
        token="",
        state=state,
        item_facts={},
        mode="single_call",
        seed_from_package=True,
    )
    assert provider._resolve_name(provider._world(), "servers") == "hideout_servers"
    _narrate(
        state,
        "Kristin sorts through the servers in Brandon's hideout.",
        "Search the servers for the leaked files.",
    )


def test_unrelated_future_alias_remains_guarded() -> None:
    error = _rejects(_scene_state("1A"), "The restricted infrastructure corridors are dangerous.")
    assert error.code == "narration_known_term_leak"
