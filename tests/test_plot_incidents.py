from __future__ import annotations

from random import Random

from storygame.engine.incidents import load_incident_specs, parse_incident_specs, realize_beat_incident
from storygame.engine.parser import parse_command
from storygame.engine.simulation import advance_turn
from storygame.engine.state import Event
from storygame.engine.world import build_default_state
from storygame.plot.beat_manager import Beat


def _action_event(event_type: str, entities: tuple[str, ...], turn_index: int = 1) -> Event:
    return Event(type=event_type, entities=entities, message_key=event_type, turn_index=turn_index)


def test_timed_incident_fires_for_matching_beat_after_min_turn():
    state = build_default_state(seed=1)
    state.turn_index = 3
    beat = Beat(type="inciting_incident", tags=("inciting_incident", "exposition"))

    next_state, events = realize_beat_incident(
        state,
        beat,
        action_events=(),
        rng=Random(1),
    )

    assert next_state.player.flags.get("incident_market_pickpocket") is True
    assert len(events) == 1
    assert events[0].type == "incident"
    assert "stolen" in events[0].message_key.lower()


def test_trigger_incident_fires_on_keeper_talk_in_archives():
    state = build_default_state(seed=2)
    state.player.location = "archives"
    state.progress = 0.3
    beat = Beat(type="revelation", tags=("revelation", "rising_action"))

    next_state, events = realize_beat_incident(
        state,
        beat,
        action_events=(_action_event("talk", ("keeper",), turn_index=2),),
        rng=Random(2),
    )

    assert next_state.player.flags.get("incident_keeper_detained") is True
    assert len(events) == 1
    assert events[0].type == "incident"
    assert "arrest" in events[0].message_key.lower()


def test_incidents_do_not_repeat_once_flag_is_set():
    state = build_default_state(seed=3)
    state.player.location = "archives"
    state.progress = 0.3
    beat = Beat(type="revelation", tags=("revelation", "rising_action"))

    fired_state, first_events = realize_beat_incident(
        state,
        beat,
        action_events=(_action_event("talk", ("keeper",), turn_index=2),),
        rng=Random(3),
    )
    second_state, second_events = realize_beat_incident(
        fired_state,
        beat,
        action_events=(_action_event("talk", ("keeper",), turn_index=3),),
        rng=Random(3),
    )

    assert first_events
    assert second_events == []
    assert second_state.player.flags.get("incident_keeper_detained") is True


def test_advance_turn_can_emit_trigger_incident_event():
    state = build_default_state(seed=4)
    state.player.location = "archives"
    state.progress = 0.3

    next_state, events, _beat, _template = advance_turn(
        state,
        parse_command("talk keeper"),
        Random(4),
    )

    assert next_state.turn_index == 1
    assert any(event.type == "incident" for event in events)


def test_incident_specs_load_from_yaml():
    specs = load_incident_specs()

    ids = {spec["incident_id"] for spec in specs}
    assert "market_pickpocket" in ids
    assert "keeper_detained" in ids


def test_sequence_trigger_matches_ordered_event_steps_within_window():
    state = build_default_state(seed=5)
    state.turn_index = 4
    state.player.location = "sanctuary"
    state.player.flags["talked_keeper"] = True
    state.event_log = state.event_log.extend(
        (
            Event(type="talk", entities=("keeper",), turn_index=1, message_key="talk"),
            Event(type="take", entities=("wax_stamp",), turn_index=3, message_key="take"),
            Event(type="move", entities=("east", "sanctuary"), turn_index=4, message_key="move"),
        )
    )
    beat = Beat(type="revelation", tags=("revelation", "rising_action"))
    specs = parse_incident_specs(
        {
            "version": 1,
            "incidents": [
                {
                    "id": "forged_warrant",
                    "once_flag": "incident_forged_warrant",
                    "beat_tags": ["revelation"],
                    "message": "A forged warrant appears on the sanctuary door.",
                    "entities": ["warrant"],
                    "effects": {"delta_progress": 0.01, "delta_tension": 0.08},
                    "triggers": {
                        "sequence": {
                            "within_turns": 5,
                            "steps": [
                                {"action_type": "talk", "entity": "keeper"},
                                {"action_type": "take", "entity": "wax_stamp"},
                                {"event": "player_entered_room", "room": "sanctuary"},
                            ],
                        }
                    },
                }
            ],
        }
    )

    next_state, events = realize_beat_incident(state, beat, action_events=(), rng=Random(5), incident_specs=specs)

    assert next_state.player.flags.get("incident_forged_warrant") is True
    assert len(events) == 1
    assert events[0].metadata["incident_id"] == "forged_warrant"


def test_cooldown_blocks_refire_for_non_oneshot_incident():
    state = build_default_state(seed=6)
    state.turn_index = 4
    beat = Beat(type="complication", tags=("complication", "rising_action"))
    specs = parse_incident_specs(
        {
            "version": 1,
            "incidents": [
                {
                    "id": "street_patrol",
                    "once_flag": "",
                    "beat_tags": ["complication"],
                    "message": "A street patrol closes one side of the lane.",
                    "entities": ["watch"],
                    "effects": {"delta_progress": 0.0, "delta_tension": 0.05},
                    "triggers": {
                        "all": [{"location_is": "harbor"}],
                        "cooldown_turns": 3,
                    },
                }
            ],
        }
    )

    fired_state, first_events = realize_beat_incident(
        state,
        beat,
        action_events=(),
        rng=Random(6),
        incident_specs=specs,
    )
    fired_state.turn_index = 5
    cooled_state, second_events = realize_beat_incident(
        fired_state,
        beat,
        action_events=(),
        rng=Random(6),
        incident_specs=specs,
    )
    cooled_state.turn_index = 8
    final_state, third_events = realize_beat_incident(
        cooled_state,
        beat,
        action_events=(),
        rng=Random(6),
        incident_specs=specs,
    )

    assert first_events
    assert second_events == []
    assert third_events
    assert final_state is not None
