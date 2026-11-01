from __future__ import annotations

from pathlib import Path

import pytest

from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.facts import Fact
from storygame.runtime.state import RuntimeSnapshot, RuntimeState
from storygame.runtime.world_model import apply_scene_placements, world_for
from storygame.story_package.loader import load_story_package

PACKAGE_ROOT = Path("data/stories/continuity-initiative")
PACKAGE = load_story_package(PACKAGE_ROOT)


def _state() -> RuntimeState:
    state = RuntimeState.bootstrap(PACKAGE)
    state.current_scene_id = "1C"
    state.phase = next(scene.metadata.freytag_phase for scene in PACKAGE.scenes if scene.metadata.scene_id == "1C")
    state._assert_scene_entry_fact("1C")
    state.active_event_ids.update({"SL-1C-A", "SL-1C-B", "SL-1C-C"})
    apply_scene_placements(PACKAGE, state.facts, "1C")
    return state


def _facts(state: RuntimeState) -> set[str]:
    return {fact.predicate for fact in state.facts.asserted if fact.subject == "story" and fact.value == "true"}


def _assert_fact(state: RuntimeState, fact_id: str) -> None:
    state.facts.assert_fact(Fact(predicate=fact_id, subject="story", value="true"))


def _provider(knowledge_id: str | None = None, text: str = "Kristin inspects the terminal."):
    def provide(_player_input: str) -> dict[str, object]:
        segment: dict[str, object] = {"kind": "narration", "text": text}
        payload: dict[str, object] = {"segments": [segment]}
        if knowledge_id is not None:
            segment["grounding_ids"] = [knowledge_id]
            payload["selected_knowledge_ids"] = [knowledge_id]
        return payload

    return provide


def test_real_package_declares_incident_outcomes_and_recovery() -> None:
    incident_ids = {incident.id for incident in PACKAGE.incidents}
    assert {
        "i_1c_freight_transfer",
        "i_2a_real_leak",
        "i_2b_audit",
        "i_2c_rebecca_corridor",
    } <= incident_ids
    incident = next(item for item in PACKAGE.incidents if item.id == "i_1c_freight_transfer")
    assert incident.id == "i_1c_freight_transfer"
    assert {outcome.id for outcome in incident.outcomes} == {"copy_numbers", "secure_route"}
    assert incident.recovery_storylet_id == "SL-1C-D"
    assert {connection.id for connection in PACKAGE.connections} == {"house_to_outside", "outside_to_house"}


def test_real_package_loads_with_house_connections_and_service_level_command_falls_through() -> None:
    assert {connection.id for connection in load_story_package(PACKAGE_ROOT).connections} == {
        "house_to_outside",
        "outside_to_house",
    }
    state = _state()
    calls: list[str] = []

    def recording_provider(command: str):
        calls.append(command)
        return _provider()(command)

    RuntimeEngine(state, recording_provider).turn("Go to the service level")

    assert calls == ["Go to the service level"]
    assert state.turn_index == 1
    assert state.current_scene_id == "1C"


def test_free_observation_establishes_only_observation_facts() -> None:
    state = _state()
    _assert_fact(state, "facility_proof")
    engine = RuntimeEngine(state, _provider("k_sl_1c_b_r2", "Kristin watches the processing line for Michelle."))

    engine.turn("Watch the processing line for Michelle.")

    assert {"captives_confirmed_alive", "michelle_possible_sighting"} <= _facts(state)
    assert not {"processing_numbers_copied", "service_level_access_known", "facility_infiltration_needed"} & _facts(
        state
    )


def _outcome_state() -> RuntimeState:
    state = _state()
    _assert_fact(state, "facility_proof")
    _assert_fact(state, "captives_confirmed_alive")
    return state


def test_copy_numbers_outcome_moves_record_and_enters_2a() -> None:
    state = _outcome_state()
    RuntimeEngine(
        state,
        _provider(
            "k_sl_1c_c_copy_numbers",
            "Kristin copies the prisoner numbers and matches them to missing-person records.",
        ),
    ).turn("Copy the prisoner numbers.")

    assert {"processing_numbers_copied", "facility_infiltration_needed"} <= _facts(state)
    assert "evidence_gap_processing_numbers" not in _facts(state)
    assert state.current_scene_id == "2A"
    assert world_for(PACKAGE, state.facts).parent("prisoner_number_record") == "kristin"


def test_secure_route_outcome_asserts_route_gap_trust_and_enters_2a() -> None:
    state = _outcome_state()
    RuntimeEngine(
        state,
        _provider(
            "k_sl_1c_c_secure_route",
            "Brandon explains the transfer route and opens the service entrance with the transit token.",
        ),
    ).turn("Ask Brandon about the transfer route.")

    assert {"service_level_access_known", "evidence_gap_processing_numbers", "trust_brandon"} <= _facts(state)
    assert "processing_numbers_copied" not in _facts(state)
    assert state.current_scene_id == "2A"


def test_outcomes_are_exclusive() -> None:
    state = _outcome_state()
    RuntimeEngine(
        state,
        _provider(
            "k_sl_1c_c_copy_numbers",
            "Kristin copies the prisoner numbers and matches them to missing-person records.",
        ),
    ).turn("Copy the prisoner numbers.")
    before = state.snapshot()

    with pytest.raises(Exception, match="not eligible"):
        RuntimeEngine(
            state,
            _provider(
                "k_sl_1c_c_secure_route",
                "Brandon explains the transfer route and opens the service entrance with the transit token.",
            ),
        ).turn("Ask Brandon about the transfer route.")
    assert state.snapshot() == before


def test_missed_window_withdraws_without_advantage_past_deadline() -> None:
    state = _state()
    engine = RuntimeEngine(state, _provider())
    for _ in range(12):
        engine.turn("Inspect the terminal for signs of activity.")

    assert "transfer_window_missed" in _facts(state)
    assert not {"processing_numbers_copied", "service_level_access_known"} & _facts(state)
    assert "facility_infiltration_needed" in _facts(state)
    assert state.current_scene_id == "2A"
    assert state.turn_index >= 8


def test_recovery_requires_missed_window_and_completes_scene() -> None:
    state = _outcome_state()
    recovery = _provider(
        "k_sl_1c_d_r1", "Brandon leads Kristin through the service entrance while the sweep closes in."
    )
    with pytest.raises(Exception, match="not eligible"):
        RuntimeEngine(state, recovery).turn("Follow Brandon through the service entrance.")

    state = _state()
    engine = RuntimeEngine(state, _provider())
    for _ in range(5):
        engine.turn("Inspect the terminal for signs of activity.")
    RuntimeEngine(state, recovery).turn("Follow Brandon through the service entrance.")

    assert {
        "service_level_access_known",
        "evidence_gap_processing_numbers",
        "facility_infiltration_needed",
        "trust_brandon",
        "terminal_sweep_closing",
    } <= _facts(state)
    assert state.current_scene_id == "2A"


def test_save_restore_after_outcome_keeps_facts() -> None:
    state = _outcome_state()
    RuntimeEngine(
        state,
        _provider(
            "k_sl_1c_c_secure_route",
            "Brandon explains the transfer route and opens the service entrance with the transit token.",
        ),
    ).turn("Ask Brandon about the transfer route.")
    saved = RuntimeSnapshot.model_validate_json(state.snapshot().model_dump_json())
    restored = _state()
    restored.restore_snapshot(saved)
    assert {"service_level_access_known", "evidence_gap_processing_numbers", "trust_brandon"} <= _facts(restored)
