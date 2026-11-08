from __future__ import annotations

from storygame.runtime.cloudflare import CloudflareTurnProvider
from storygame.runtime.state import RuntimeState
from storygame.runtime.world_model import apply_scene_placements
from tests import test_richer_2c, test_richer_3a
from tests.test_speaker_lines import _commit


def _characters(state, command: str) -> str:
    provider = CloudflareTurnProvider(worker_url="", token="", state=state)
    prompt = provider.assemble_turn_prompt(command)["context"]
    text = provider._section_user_prompt(prompt)
    return text.split("CHARACTERS:\n", 1)[1].split("\n\n", 1)[0]


def test_a_participant_who_is_not_in_the_scene_is_not_introduced():
    # Rebecca is a 3A participant only by name: she is not placed on the detention level.
    state, _engine = test_richer_3a._engine()
    characters = _characters(state, "Look at the captives.")
    assert "Kristin Schweitzer" in characters
    assert "Dr. Michelle McGehee" in characters
    assert "Brandon Corfman" in characters
    assert "Rebecca Jenkins" not in characters


def test_a_participant_standing_in_the_scene_is_still_introduced():
    state, _engine = test_richer_2c._engine()
    characters = _characters(state, "Look at Rebecca.")
    assert "Rebecca Jenkins" in characters
    assert "Kristin Schweitzer" in characters
    assert "Brandon Corfman" in characters


def test_an_absent_character_the_player_names_is_introduced_for_that_turn():
    state, _engine = test_richer_3a._engine()
    named = _characters(state, "Ask Michelle about Rebecca.")
    assert "Rebecca Jenkins" in named
    unnamed = _characters(state, "Ask Michelle about the radio.")
    assert "Rebecca Jenkins" not in unnamed


def test_a_character_the_scene_objective_names_is_introduced_even_when_absent():
    # 1A is about finding Michelle, who is not in the room: the objective brings her up.
    package = test_richer_3a.PACKAGE
    state = RuntimeState.bootstrap(package)
    for command in ("Search the kitchen.", "Look around."):
        assert "Dr. Michelle McGehee" in _characters(state, command)


def test_a_character_an_earned_statement_names_is_introduced_even_when_absent():
    # k_sl_3b_d_r1 names Rebecca. In 3B she is not placed, but once the player has earned it the story has brought
    # her up and she is introduced, whatever the command says.
    package = test_richer_3a.PACKAGE
    state = RuntimeState.bootstrap(package)
    state.current_scene_id = "3B"
    state.phase = next(s for s in package.scenes if s.metadata.scene_id == "3B").metadata.freytag_phase
    state._assert_scene_entry_fact("3B")
    apply_scene_placements(package, state.facts, "3B")
    assert "Rebecca Jenkins" not in _characters(state, "Look around.")
    _commit(state, ("k_sl_3b_d_r1",))
    assert "Rebecca Jenkins" in _characters(state, "Look around.")


def test_a_character_no_one_has_brought_up_stays_out():
    # Charles is a later character: nothing the objective, the command or any earned statement says names him in 3A.
    state, _engine = test_richer_3a._engine()
    assert "Charles Jenkins" not in _characters(state, "Look at the captives.")
