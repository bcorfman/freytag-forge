from __future__ import annotations

import pytest

from storygame.runtime.cloudflare import NarrationProviderError
from storygame.runtime.engine import ClarificationTurn, RuntimeEngine
from storygame.runtime.reference_resolution import Clarification, ReferenceResult
from storygame.runtime.state import RuntimeSnapshot, RuntimeState
from storygame.runtime.validation import ProposalValidationError
from storygame.story_package.loader import load_story_package
from tests.test_incident_engine import FIXTURE, _provider, _true_facts


def _state() -> RuntimeState:
    return RuntimeState.bootstrap(load_story_package(FIXTURE))


def _rejected_provider(_player_input: str) -> dict[str, object]:
    return {
        "segments": [{"kind": "narration", "text": "Ada waits."}],
        "selected_knowledge_ids": ["k_copy_chart"],
    }


def test_rejected_turns_do_not_advance_the_pressure_event() -> None:
    state = _state()
    engine = RuntimeEngine(state, _rejected_provider)

    for _ in range(2):
        before = state.snapshot()
        with pytest.raises(ProposalValidationError):
            engine.turn("Copy the chart.")
        assert state.snapshot() == before
        assert "tide_turns" not in state.fired_event_ids

    engine = RuntimeEngine(state, _provider())
    engine.turn("Wait.")
    assert "tide_turns" not in state.fired_event_ids
    engine.turn("Wait again.")
    assert "tide_turns" in state.fired_event_ids


def test_clarification_turn_does_not_advance_the_pressure_event(monkeypatch: pytest.MonkeyPatch) -> None:
    state = _state()
    before = state.snapshot()
    clarification = Clarification("Wait by the bench.", "bench", (("keeper_bench", "bench"),), 0)
    monkeypatch.setattr(
        "storygame.runtime.engine.resolve_references",
        lambda *_args, **_kwargs: ReferenceResult(
            command="Wait by the bench.",
            question=clarification,
            outcome="ambiguous",
            original="Wait by the bench.",
            resolutions=(),
        ),
    )

    result = RuntimeEngine(state, _provider()).turn("Wait by the bench.")

    assert isinstance(result, ClarificationTurn)
    assert state.snapshot() == before
    assert "tide_turns" not in state.fired_event_ids


def test_missed_window_grants_nothing_and_does_not_handoff() -> None:
    state = _state()
    engine = RuntimeEngine(state, _provider())

    for command in ("Wait.", "Wait again.", "Keep waiting.", "Wait longer.", "Still wait.", "Wait at turn six."):
        engine.turn(command)

    facts = _true_facts(state)
    assert state.turn_index == 6
    assert state.current_scene_id == "1A"
    assert "tide_turns" in state.fired_event_ids
    assert list(state.fired_event_ids).count("tide_turns") == 1
    assert "tide_has_turned" in facts
    assert not {"chart_copied", "boat_route_known", "chart_page_torn"} & facts
    assert sum(fact.predicate == "tide_has_turned" for fact in state.facts.asserted) == 1


def test_late_recovery_resolves_after_missed_window_and_same_turn_pressure_resolves() -> None:
    late = _state()
    wait = RuntimeEngine(late, _provider())
    wait.turn("Wait.")
    wait.turn("Wait again.")
    RuntimeEngine(late, _provider("k_copy_chart", "Ada copied the chart.")).turn("Copy the chart.")
    assert late.current_scene_id == "1B"
    assert {"chart_copied", "chart_page_torn", "incident_outcome_resolved"} <= _true_facts(late)

    boundary = _state()
    boundary.turn_index = 1
    RuntimeEngine(boundary, _provider("k_copy_chart", "Ada copied the chart.")).turn("Copy the chart.")
    assert boundary.current_scene_id == "1B"
    assert "tide_turns" in boundary.fired_event_ids
    assert {"chart_copied", "chart_page_torn", "incident_outcome_resolved"} <= _true_facts(boundary)


def test_save_restore_after_missed_window_preserves_pressure_and_recovery() -> None:
    state = _state()
    engine = RuntimeEngine(state, _provider())
    engine.turn("Wait.")
    engine.turn("Wait again.")
    saved = RuntimeSnapshot.model_validate_json(state.snapshot().model_dump_json())

    restored = _state()
    restored.restore_snapshot(saved)
    for command in ("Keep waiting.", "Wait longer.", "Still wait.", "Wait at turn six."):
        RuntimeEngine(restored, _provider()).turn(command)
    assert restored.current_scene_id == "1A"
    assert "tide_turns" in restored.fired_event_ids
    assert list(restored.fired_event_ids).count("tide_turns") == 1
    assert sum(fact.predicate == "tide_has_turned" for fact in restored.facts.asserted) == 1

    RuntimeEngine(restored, _provider("k_find_key", "Ada finds the brass key.")).turn("Learn the boat route.")
    assert restored.current_scene_id == "1B"
    assert {"boat_route_known", "incident_outcome_resolved"} <= _true_facts(restored)
    assert "chart_page_torn" not in _true_facts(restored)


def test_provider_transport_error_does_not_advance_the_pressure_event() -> None:
    state = _state()
    before = state.snapshot()

    def transient(_player_input: str) -> object:
        raise NarrationProviderError("temporary service failure", error_code="TRANSIENT")

    with pytest.raises(NarrationProviderError):
        RuntimeEngine(state, transient).turn("Wait.")

    assert state.snapshot() == before
    assert "tide_turns" not in state.fired_event_ids
