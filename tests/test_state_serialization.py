from __future__ import annotations

from storygame.persistence.savegame_sqlite import deserialize_state, serialize_state
from tests.fast_fixtures import make_persistence_state


def _payload_from(factory=make_persistence_state, *, seed: int = 1) -> dict:
    """Build serializer payloads through an injectable narrow-state factory."""

    return serialize_state(factory(seed=seed))


def test_serialize_state_canonicalizes_stale_player_inventory_without_sqlite() -> None:
    state = make_persistence_state(seed=15)
    state.player.inventory = state.player.inventory + ("note",)

    payload = serialize_state(state)

    assert ["holding", "player", "note"] in payload["world_facts"]


def test_deserialize_state_rebuilds_fact_backed_projection_from_legacy_payload() -> None:
    state_factory = make_persistence_state
    state = state_factory(seed=16)
    payload = _payload_from(state_factory, seed=16)
    payload["world_facts"] = []
    payload["active_goal"] = "Question the witness in the next room."
    payload["player"] = {
        "location": "next_room",
        "inventory": ["note"],
        "flags": {"legacy_loaded": True},
    }
    payload["room_items"] = {room_id: [] for room_id in state.world.rooms}
    payload["last_judge_decision"] = {
        "decision_id": "judge-1",
        "status": "accepted",
        "judge": "critic",
        "rationale": "looks good",
    }
    payload["pending_high_impact_command"] = "break the pact"
    payload["pending_high_impact_assessment"] = {"impact_class": "critical"}

    loaded_state = deserialize_state(payload, state_factory=lambda **_kwargs: state_factory(seed=16))

    assert loaded_state.player.location == "next_room"
    assert loaded_state.player.inventory == ("note",)
    assert loaded_state.player.flags["legacy_loaded"] is True
    assert loaded_state.active_goal == "Question the witness in the next room."
    assert loaded_state.world_facts.holds("at", "player", "next_room")
    assert loaded_state.world_facts.holds("holding", "player", "note")
    assert loaded_state.world_facts.holds("flag", "player", "legacy_loaded")
    assert loaded_state.last_judge_decision["decision_id"] == "judge-1"
    assert loaded_state.pending_high_impact_command == "break the pact"


def test_deserialize_state_normalizes_absent_judge_decision_and_pending_assessment() -> None:
    state_factory = make_persistence_state
    payload = _payload_from(state_factory, seed=17)
    payload["world_facts"] = []
    payload["last_judge_decision"] = None
    payload["pending_high_impact_assessment"] = "ignored"

    loaded_state = deserialize_state(payload, state_factory=lambda **_kwargs: state_factory(seed=17))

    assert loaded_state.last_judge_decision is None
    assert loaded_state.pending_high_impact_assessment == {}
