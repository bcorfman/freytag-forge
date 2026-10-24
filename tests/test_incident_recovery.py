from __future__ import annotations

from pathlib import Path

from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.reveal_eligibility import explain_reveal
from storygame.runtime.state import RuntimeSnapshot, RuntimeState
from storygame.story_package.loader import load_story_package

FIXTURE = Path(__file__).parent / "fixtures" / "stories" / "lighthouse-incident"


def _state() -> RuntimeState:
    return RuntimeState.bootstrap(load_story_package(FIXTURE))


def _provider(knowledge_id: str | None = None, text: str = "Ada waits."):
    def provide(_player_input: str):
        segment = {"kind": "narration", "text": text}
        payload = {"segments": [segment]}
        if knowledge_id is not None:
            segment["grounding_ids"] = [knowledge_id]
            payload["selected_knowledge_ids"] = [knowledge_id]
        return payload

    return provide


def _facts(state: RuntimeState) -> set[str]:
    return {fact.predicate for fact in state.facts.asserted if fact.subject == "story" and fact.value == "true"}


def test_recovery_is_ineligible_before_window_and_eligible_after_it_fires() -> None:
    state = _state()
    recovery = state.package.knowledge_indexes.by_id["k_recover_chart"]
    assert explain_reveal(state, "player", recovery).eligible is False

    engine = RuntimeEngine(state, _provider())
    engine.turn("Wait.")
    engine.turn("Wait again.")
    assert "tide_has_turned" in _facts(state)
    assert explain_reveal(state, "player", recovery).reason == "eligible"


def test_recovery_reuses_outcome_at_cost_and_transitions_same_turn_without_floor() -> None:
    state = _state()
    engine = RuntimeEngine(state, _provider())
    engine.turn("Wait.")
    engine.turn("Wait again.")
    assert state.current_scene_id == "1A"

    RuntimeEngine(state, _provider("k_recover_chart", "Ada recovers the chart at a cost.")).turn("Recover the chart.")

    assert {"chart_copied", "chart_page_torn", "recovery_cost_paid", "incident_outcome_resolved"} <= _facts(state)
    assert state.current_scene_id == "1B"
    assert state.turn_index - state.scene_entered_at_turn == 0
    assert state.package.incidents[0].outcomes[0].id == "copy_chart"


def test_recovery_and_normal_outcome_are_mutually_ineligible() -> None:
    recovery_state = _state()
    recovery_engine = RuntimeEngine(recovery_state, _provider())
    recovery_engine.turn("Wait.")
    recovery_engine.turn("Wait again.")
    recovery_engine = RuntimeEngine(recovery_state, _provider("k_recover_chart", "Ada recovers the chart at a cost."))
    recovery_engine.turn("Recover the chart.")
    assert explain_reveal(
        recovery_state, "player", recovery_state.package.knowledge_indexes.by_id["k_copy_chart"]
    ).reason in {"storylet_spent", "already_established", "source_inactive"}

    normal_state = _state()
    RuntimeEngine(normal_state, _provider("k_copy_chart", "Ada copies the chart.")).turn("Copy the chart.")
    assert explain_reveal(
        normal_state, "player", normal_state.package.knowledge_indexes.by_id["k_recover_chart"]
    ).reason in {"storylet_spent", "already_established", "source_inactive"}


def test_normal_outcome_does_not_assert_recovery_cost() -> None:
    state = _state()
    RuntimeEngine(state, _provider("k_copy_chart", "Ada copies the chart.")).turn("Copy the chart.")
    assert "recovery_cost_paid" not in _facts(state)


def test_missed_window_still_grants_nothing_and_keeps_scene_open() -> None:
    state = _state()
    engine = RuntimeEngine(state, _provider())
    for command in ("Wait.", "Wait again.", "Keep waiting."):
        engine.turn(command)
    assert state.current_scene_id == "1A"
    assert "tide_has_turned" in _facts(state)
    assert not {"chart_copied", "boat_route_known", "chart_page_torn", "recovery_cost_paid"} & _facts(state)


def test_save_restore_after_recovery_preserves_facts_and_does_not_refire() -> None:
    state = _state()
    engine = RuntimeEngine(state, _provider())
    engine.turn("Wait.")
    engine.turn("Wait again.")
    RuntimeEngine(state, _provider("k_recover_chart", "Ada recovers the chart at a cost.")).turn("Recover the chart.")
    saved = RuntimeSnapshot.model_validate_json(state.snapshot().model_dump_json())
    restored = _state()
    restored.restore_snapshot(saved)
    before = restored.snapshot()
    assert "SL-1A-B" in restored.fired_event_ids
    assert "recovery_cost_paid" in _facts(restored)
    assert restored.snapshot() == before
