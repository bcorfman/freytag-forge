from __future__ import annotations

import pytest

from storygame.engine.fact_commit import ValidatedFactCommitter
from storygame.engine.parser import parse_command
from storygame.engine.perception import (
    ObservationResolver,
    observer_context_slice,
    speaker_context_slice,
)
from storygame.engine.world import build_default_state
from storygame.llm.context import build_narration_context


def _commit(state, *facts):
    return ValidatedFactCommitter().commit(
        state,
        [{"op": "assert", "fact": fact} for fact in facts],
        source="phase3_test",
    )


def test_observer_resolver_distinguishes_location_access_and_perception() -> None:
    state = build_default_state(seed=530, genre="fantasy")
    room_id = state.player.location
    _commit(
        state,
        ("concealed", "field_kit", room_id),
        ("light", room_id, "daylight"),
        ("exposed", "field_kit", room_id),
    )

    resolution = ObservationResolver(state).resolve("player", "field_kit")

    assert resolution.exists is True
    assert resolution.location == room_id
    assert resolution.accessible is True
    assert resolution.perceptible is True
    assert resolution.observed is False
    assert resolution.recognized is False
    assert resolution.interpreted is False


def test_concealment_and_environment_can_block_perception() -> None:
    state = build_default_state(seed=531, genre="fantasy")
    room_id = state.player.location
    _commit(state, ("concealed", "field_kit", room_id), ("light", room_id, "dark"))

    resolution = ObservationResolver(state).resolve("player", "field_kit")

    assert resolution.exists is True
    assert resolution.location == room_id
    assert resolution.accessible is True
    assert resolution.perceptible is False


def test_context_slice_excludes_hidden_truth_but_includes_speaker_knowledge() -> None:
    state = build_default_state(seed=532, genre="mystery")
    room_id = state.player.location
    _commit(
        state,
        ("case_fact", "hidden_motive", "The antagonist acted for revenge."),
        ("knows", "daria_stone", "hidden_motive"),
        ("concealed", "case_file", room_id),
    )

    player_slice = observer_context_slice(state, "player")
    speaker_slice = speaker_context_slice(state, "daria_stone")

    assert all("hidden_motive" not in fact for fact in player_slice)
    assert ("knows", "daria_stone", "hidden_motive") in speaker_slice
    assert ("case_fact", "hidden_motive", "The antagonist acted for revenge.") in speaker_slice


def test_narration_context_filters_concealed_items_and_unrelated_npcs() -> None:
    state = build_default_state(seed=533, genre="mystery")
    room_id = state.player.location
    _commit(
        state,
        ("concealed", "arrival_sedan", room_id),
        ("npc_at", "daria_stone", "mansion_hall"),
    )

    payload = build_narration_context(state, parse_command("look"), "hook").as_dict()

    assert "arrival_sedan" not in payload["visible_items"]
    assert "daria_stone" not in payload["visible_npcs"]


def test_evidence_can_move_and_change_state_without_duplicate_placement() -> None:
    state = build_default_state(seed=534, genre="mystery")
    room_id = state.player.location
    other_room = next(room for room in state.world.rooms if room != room_id)
    _commit(state, ("room_item", room_id, "case_file"), ("evidence_state", "case_file", "fresh"))

    _commit(
        state,
        ("room_item", other_room, "case_file"),
        ("evidence_state", "case_file", "water_damaged"),
        ("evidence_contaminated", "case_file", "rain"),
    )

    assert state.world_facts.query("room_item", None, "case_file") == (("room_item", other_room, "case_file"),)
    assert not state.world_facts.holds("evidence_state", "case_file", "fresh")
    assert state.world_facts.holds("evidence_state", "case_file", "water_damaged")
    assert state.world_facts.holds("evidence_contaminated", "case_file", "rain")


def test_discovery_requires_observation_and_records_interpretation() -> None:
    state = build_default_state(seed=535, genre="mystery")
    room_id = state.player.location
    _commit(
        state,
        ("trace", "case_file", room_id, "rain"),
        ("observed", "player", "case_file"),
        ("recognized", "player", "case_file"),
        ("interpreted", "player", "case_file", "recently soaked"),
        ("discovery", "player", "case_file", "recently soaked"),
    )

    assert ("discovery", "player", "case_file", "recently soaked") in observer_context_slice(state, "player")

    with pytest.raises(ValueError, match="requires observation"):
        ObservationResolver(state).validate_discovery("player", "arrival_sedan", "unrelated")
