from __future__ import annotations

from pathlib import Path

from storygame.personas import _ScriptedProvider
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.state import RuntimeSnapshot, RuntimeState
from storygame.story_package.loader import load_story_package
from tests.test_continuity_1c_incident import _assert_fact, _facts, _state

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))
TURN_BUDGET = 14
BASE_2A_ENTRY = next(scene.metadata.entry_text for scene in PACKAGE.scenes if scene.metadata.scene_id == "2A")


def _engine() -> tuple[RuntimeState, RuntimeEngine, _ScriptedProvider]:
    state = _state()
    _assert_fact(state, "facility_proof")
    _assert_fact(state, "false_identities_ready")
    _assert_fact(state, "rebecca_observing_infiltrators")
    _assert_fact(state, "facility_perimeter_reached")
    state.active_event_ids.add("SL-2A-C")
    provider = _ScriptedProvider(PACKAGE, state)
    return state, RuntimeEngine(state, provider), provider


def _turn(
    engine: RuntimeEngine,
    provider: _ScriptedProvider,
    command: str,
    selected: str | None = None,
) -> object:
    provider.selected = (selected,) if selected else ()
    before = _facts(engine.state)
    result = engine.turn(command)
    cue_fact_id = engine.state.last_turn_delivery.cue_fact_id
    assert cue_fact_id is None or cue_fact_id not in before
    return result


def _texts(result: object) -> tuple[str, ...]:
    return tuple(segment.text for segment in result.segments)  # type: ignore[union-attr]


def _finish_2a(engine: RuntimeEngine, provider: _ScriptedProvider, confrontation_id: str) -> object:
    engine.state.active_event_ids.add("SL-2A-C")
    command = {
        "k_sl_2a_c_r3": "Use the copied prisoner numbers to explain the cooling-water inspection to the supervisor.",
        "k_sl_2a_c_r4": "Use the known service route to explain the inspection approach to the supervisor.",
        "k_sl_2a_a_r1": "Explain the cooling-water risk to the supervisor.",
    }[confrontation_id]
    return _turn(
        engine,
        provider,
        command,
        confrontation_id,
    )


def _advance_to_2b(engine: RuntimeEngine, provider: _ScriptedProvider) -> None:
    for _ in range(7):
        if engine.state.current_scene_id != "2A":
            break
        _turn(engine, provider, "Check the restricted corridor for a safe passage.")


def _copy_numbers_run(*, restore_after_outcome: bool = False) -> tuple[RuntimeState, tuple[str, ...]]:
    state, engine, provider = _engine()
    _turn(engine, provider, "Watch the processing line for Michelle.", "k_sl_1c_b_r2")
    outcome = _turn(engine, provider, "Copy the prisoner numbers.", "k_sl_1c_c_copy_numbers")
    if restore_after_outcome:
        restored = RuntimeState.bootstrap(PACKAGE)
        restored.restore_snapshot(RuntimeSnapshot.model_validate_json(state.snapshot().model_dump_json()))
        provider = _ScriptedProvider(PACKAGE, restored)
        state, engine = restored, RuntimeEngine(restored, provider)
    confrontation = _finish_2a(engine, provider, "k_sl_2a_c_r3")
    _advance_to_2b(engine, provider)
    assert state.current_scene_id == "2B"
    assert any(text.startswith("Kristin still has the copied prisoner numbers.") for text in _texts(outcome))
    assert "processing_numbers_copied" in _facts(state)
    assert "restricted_corridor_access" in _facts(state)
    assert "processing_numbers_used_in_confrontation" in _facts(state)
    assert state.turn_index <= TURN_BUDGET
    return state, _texts(confrontation)


def _missed_window_run(*, restore_after_miss: bool = False) -> tuple[RuntimeState, tuple[str, ...]]:
    state, engine, provider = _engine()
    _turn(engine, provider, "Watch the processing line for Michelle.", "k_sl_1c_b_r2")
    for command in (
        "Inspect the loading docks for a security route.",
        "Listen to the ventilation system for a change.",
        "Examine the observation shaft for movement.",
        "Check the terminal doors for a safe exit.",
    ):
        _turn(engine, provider, command)
    assert "transfer_window_missed" in _facts(state)
    assert not {
        "processing_numbers_copied",
        "service_level_access_known",
        "facility_infiltration_needed",
    } & _facts(state)
    if restore_after_miss:
        restored = RuntimeState.bootstrap(PACKAGE)
        restored.restore_snapshot(RuntimeSnapshot.model_validate_json(state.snapshot().model_dump_json()))
        state = restored
        provider = _ScriptedProvider(PACKAGE, state)
        engine = RuntimeEngine(state, provider)
    recovery = _turn(engine, provider, "Follow Brandon through the service entrance.", "k_sl_1c_d_r1")
    confrontation = _finish_2a(engine, provider, "k_sl_2a_a_r1")
    _advance_to_2b(engine, provider)
    assert state.current_scene_id == "2B"
    assert "transfer_window_missed" in _facts(state)
    assert "service_level_access_known" in _facts(state)
    assert "processing_numbers_copied" not in _facts(state)
    assert "Kristin and Brandon know the service approach." not in _texts(recovery)
    assert BASE_2A_ENTRY in _texts(recovery)
    assert state.turn_index <= TURN_BUDGET
    return state, _texts(confrontation)


def test_slice_a_copy_numbers_traversal_and_2b_advantage() -> None:
    state, _ = _copy_numbers_run()
    assert state.current_scene_id == "2B"


def test_slice_b_secure_route_and_2b_advantage() -> None:
    state, engine, provider = _engine()
    _turn(engine, provider, "Watch the processing line for Michelle.", "k_sl_1c_b_r2")
    outcome = _turn(engine, provider, "Ask Brandon about the transfer route.", "k_sl_1c_c_secure_route")
    _finish_2a(engine, provider, "k_sl_2a_c_r4")
    _advance_to_2b(engine, provider)
    assert state.current_scene_id == "2B"
    assert {"service_level_access_known", "evidence_gap_processing_numbers", "trust_brandon"} <= _facts(state)
    assert "processing_numbers_copied" not in _facts(state)
    assert any("Kristin and Brandon know the service approach." in text for text in _texts(outcome))
    assert state.turn_index <= TURN_BUDGET


def test_slice_c_missed_window_recovery_has_base_2a_entry() -> None:
    state, _ = _missed_window_run()
    assert state.current_scene_id == "2B"


def test_slice_d_save_load_matches_uninterrupted_copy_and_missed_window() -> None:
    missed, missed_texts = _missed_window_run()
    missed_loaded, missed_loaded_texts = _missed_window_run(restore_after_miss=True)
    assert missed_loaded.current_scene_id == missed.current_scene_id == "2B"
    assert missed_loaded_texts == missed_texts
    assert missed_loaded.facts == missed.facts
    copied, copied_texts = _copy_numbers_run()
    copied_loaded, copied_loaded_texts = _copy_numbers_run(restore_after_outcome=True)
    assert copied_loaded.current_scene_id == copied.current_scene_id == "2B"
    assert copied_loaded_texts == copied_texts
    assert copied_loaded.facts == copied.facts
