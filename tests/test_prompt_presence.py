from __future__ import annotations

from storygame.runtime.cloudflare import CloudflareTurnProvider
from tests import test_richer_2c, test_richer_3a


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
