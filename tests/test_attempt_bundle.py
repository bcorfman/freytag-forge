"""Hermetic coverage for the typed turn-attempt record."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from storygame.runtime.attempt_bundle import AttemptBundle
from storygame.runtime.cloudflare import NarrationProviderError
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.facts import Fact
from storygame.runtime.state import RuntimeSnapshot, RuntimeState, TurnRecord
from storygame.runtime.validation import REJECTED_TURN_MESSAGE, ProposalValidationError
from storygame.story_package.loader import load_story_package
from storygame.story_package.models import ActivationRule, CanonicalRouteEvent, FactPredicate, RouteOperation
from storygame.web_demo import create_demo_app

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))


def _state() -> RuntimeState:
    state = RuntimeState.bootstrap(PACKAGE)
    return state


def _provider(text: str, reveal_selection: dict[str, object] | None = None):
    def provider(_command: str) -> dict[str, object]:
        return {"segments": [{"kind": "narration", "text": text}]}

    if reveal_selection is not None:
        provider.last_reveal_selection = reveal_selection
    return provider


def test_bundle_round_trip_and_unknown_version_refusal() -> None:
    bundle = AttemptBundle(
        identity={"package_id": "continuity_initiative"},
        pre_state={"scene_id": "1A", "turn_index": 0, "turns_since_scene_entry": 0},
        command={"raw": "Search the drawer.", "normalized": "Search the drawer."},
        outcome="committed",
    )
    assert AttemptBundle.from_json(bundle.to_json()) == bundle
    old_bundle_dict = bundle.model_dump()
    old_bundle_dict.pop("reveal_selection")
    loaded_old_bundle = AttemptBundle.model_validate(old_bundle_dict)
    assert loaded_old_bundle.reveal_selection is None
    assert AttemptBundle.from_json(loaded_old_bundle.to_json()) == loaded_old_bundle
    with pytest.raises(ValidationError, match="unsupported attempt bundle schema version"):
        AttemptBundle.model_validate({**bundle.model_dump(), "schema_version": 2})


def test_accepted_and_rejected_attempts_are_recorded_and_rejection_restores_state() -> None:
    state = _state()
    engine = RuntimeEngine(
        state,
        _provider(
            "The drawer remains closed.",
            {"outcome": "exact_match", "matched": "k_drawer", "universe_size": 4, "shortlist_size": 1},
        ),
    )
    engine.turn("Search the drawer.")
    assert engine.last_attempt is not None
    assert engine.last_attempt.outcome == "committed"
    assert engine.last_attempt.stages[0].reply is not None
    assert engine.last_attempt.reveal_selection is not None
    assert engine.last_attempt.reveal_selection.outcome == "exact_match"
    assert engine.last_attempt.reveal_selection.matched == "k_drawer"
    assert engine.last_attempt.reveal_selection.universe_size == 4
    assert engine.last_attempt.reveal_selection.shortlist_size == 1

    before = state.snapshot()
    engine.provider = _provider(
        "Rebecca is in the room.",
        {"outcome": "no_eligible_action", "universe_size": 2, "shortlist_size": 0},
    )
    with pytest.raises(ProposalValidationError) as caught:
        engine.turn("Search the kitchen.")
    assert caught.value.code == "narration_known_term_leak"
    assert engine.last_attempt is not None
    assert engine.last_attempt.outcome == "rejected"
    assert engine.last_attempt.rejection.code == "narration_known_term_leak"
    assert engine.last_attempt.reveal_selection is not None
    assert engine.last_attempt.reveal_selection.outcome == "no_eligible_action"
    assert engine.last_attempt.reveal_selection.universe_size == 2
    assert engine.last_attempt.reveal_selection.shortlist_size == 0
    assert state.snapshot() == before


def test_provider_without_reveal_selection_attribute_records_none() -> None:
    engine = RuntimeEngine(_state(), _provider("The room stays quiet."))

    engine.turn("Search the drawer.")

    assert engine.last_attempt is not None
    assert engine.last_attempt.reveal_selection is None


def test_operational_failure_is_separate_from_rejection() -> None:
    def provider(_command: str):
        raise NarrationProviderError("worker unavailable", error_code="WORKER_DOWN")

    provider.last_reveal_selection = {
        "outcome": "provider_error",
        "matched": None,
        "universe_size": 3,
        "shortlist_size": 2,
    }
    engine = RuntimeEngine(_state(), provider)
    with pytest.raises(NarrationProviderError):
        engine.turn("Listen to the recording.")
    assert engine.last_attempt is not None
    assert engine.last_attempt.outcome == "operational_failure"
    assert engine.last_attempt.operational_failure.code == "WORKER_DOWN"
    assert engine.last_attempt.rejection is None
    assert engine.last_attempt.reveal_selection is not None
    assert engine.last_attempt.reveal_selection.outcome == "provider_error"
    assert engine.last_attempt.reveal_selection.universe_size == 3
    assert engine.last_attempt.reveal_selection.shortlist_size == 2


def test_real_staged_handoff_is_recorded_as_forced() -> None:
    state = _state()
    for predicate in ("michelle_lead_actionable", "patrol_return_pressure", "memory_card_recovered"):
        state.facts.assert_fact(Fact(predicate=predicate, subject="story", value="true"))
    state.staged_handoff_fact_ids = ("continuity_initiative_known",)
    state.turn_index = 8
    engine = RuntimeEngine(state, _provider("The room stays quiet."))

    engine.turn("Search the kitchen.")

    assert state.current_scene_id == "1B"
    assert engine.last_attempt.transition_cause == "forced"


def test_late_earned_exit_is_recorded_as_earned() -> None:
    state = _state()
    for predicate in ("michelle_lead_actionable", "patrol_return_pressure"):
        state.facts.assert_fact(Fact(predicate=predicate, subject="story", value="true"))
    window = next(item for item in PACKAGE.pacing.scenes if item.scene_id == "1A")
    state.turn_index = window.handoff_after_turns + 1
    state.scene_entered_at_turn = 0
    knowledge = PACKAGE.knowledge_indexes.by_id["k_sl_1a_b_r0"]

    def provider(_command: str) -> dict[str, object]:
        return {
            "segments": [
                {
                    "kind": "narration",
                    "text": knowledge.delivery_text or knowledge.statement,
                    "grounding_ids": ["k_sl_1a_b_r0"],
                }
            ],
            "selected_knowledge_ids": ["k_sl_1a_b_r0"],
        }

    engine = RuntimeEngine(state, provider)

    engine.turn("Search the gap beneath the drawer.")

    assert state.current_scene_id == "1B"
    assert engine.last_attempt.transition_cause == "earned"
    assert engine.last_attempt.committed_delta.scene_from == "1A"
    assert engine.last_attempt.committed_delta.scene_to == "1B"

    forced_state = _state()
    for predicate in (
        "michelle_lead_actionable",
        "patrol_return_pressure",
        "memory_card_recovered",
    ):
        forced_state.facts.assert_fact(Fact(predicate=predicate, subject="story", value="true"))
    forced_state.turn_index = window.handoff_after_turns + 1
    forced_state.scene_entered_at_turn = 0
    forced_state.staged_handoff_fact_ids = ("continuity_initiative_known",)
    forced_engine = RuntimeEngine(forced_state, _provider("The patrol closes in."))

    forced_engine.turn("Search the kitchen.")

    assert forced_state.current_scene_id == "1B"
    assert forced_engine.last_attempt.transition_cause == "forced"


def test_authored_exit_at_deadline_is_recorded_as_earned() -> None:
    state = _state()
    for predicate in (
        "continuity_initiative_known",
        "michelle_lead_actionable",
        "patrol_return_pressure",
        "memory_card_recovered",
    ):
        state.facts.assert_fact(Fact(predicate=predicate, subject="story", value="true"))
    window = next(item for item in PACKAGE.pacing.scenes if item.scene_id == "1A")
    state.turn_index = window.handoff_after_turns
    state.scene_entered_at_turn = 0
    engine = RuntimeEngine(state, _provider("The house is watched."))

    engine.turn("Inspect the kitchen.")

    assert state.current_scene_id == "1B"
    # The authored transition runs before the deadline backstop. This fixture
    # satisfies that transition, so the observed branch is earned.
    assert engine.last_attempt.transition_cause == "earned"
    assert engine.last_attempt.committed_delta.scene_from == "1A"
    assert engine.last_attempt.committed_delta.scene_to == "1B"


def test_authored_transition_on_a_no_reveal_turn_is_earned() -> None:
    state = _state()
    for predicate in (
        "drawer_gap_pointed_out",
        "memory_card_recovered",
        "continuity_initiative_known",
        "michelle_lead_actionable",
        "michelle_warning_known",
        "patrol_return_pressure",
    ):
        state.facts.assert_fact(Fact(predicate=predicate, subject="story", value="true"))
    state.turn_index = 8
    state.scene_entered_at_turn = 0
    window = next(item for item in PACKAGE.pacing.scenes if item.scene_id == "1A")
    assert state.turn_index - state.scene_entered_at_turn < window.handoff_after_turns
    assert state.turn_index - state.scene_entered_at_turn >= window.min_turns

    engine = RuntimeEngine(state, _provider("The room stays quiet."))

    engine.turn("Search the kitchen.")

    assert state.current_scene_id == "1B"
    assert engine.last_attempt.transition_cause == "earned"
    assert engine.last_attempt.selected_reveal.knowledge_ids == ()
    assert engine.last_attempt.committed_delta.scene_from == "1A"
    assert engine.last_attempt.committed_delta.scene_to == "1B"


def test_deadline_backstop_then_exit_is_timer() -> None:
    event = CanonicalRouteEvent(
        id="resolution_1a_exit_fact",
        scene_id="1A",
        activation=ActivationRule(),
        operations=(RouteOperation(op="assert", fact_id="deadline_exit_fact", value=True),),
        realization_storylets=("never_realized",),
        fallback_text="The deadline passes.",
    )
    transition = next(item for item in PACKAGE.pacing.transitions if item.id == "t_1a_1b").model_copy(
        update={"triggers": (FactPredicate(fact_id="deadline_exit_fact", equals=True),)}
    )
    pacing = PACKAGE.pacing.model_copy(
        update={
            "transitions": tuple(
                transition if item.id == transition.id else item for item in PACKAGE.pacing.transitions
            )
        }
    )
    routes = PACKAGE.storylet_routes.model_copy(
        update={"resolution_events": (*PACKAGE.storylet_routes.resolution_events, event)}
    )
    package = PACKAGE.model_copy(update={"pacing": pacing, "storylet_routes": routes})
    state = RuntimeState.bootstrap(package)
    window = next(item for item in package.pacing.scenes if item.scene_id == "1A")
    state.turn_index = window.handoff_after_turns - 1
    state.turn_records = [TurnRecord(id=f"turn_{i}") for i in range(state.turn_index)]
    engine = RuntimeEngine(state, _provider("The room stays quiet."))

    engine.turn("Search the kitchen.")

    assert state.current_scene_id == "1A"
    assert state.turn_records[-1].deadline_event_ids == ("resolution_1a_exit_fact",)
    engine.turn("Search the kitchen.")

    assert state.current_scene_id == "1B"
    assert engine.last_attempt.transition_cause == "timer"


def test_turn_record_deadline_ids_round_trip_and_old_dict_loads() -> None:
    state = _state()
    state.turn_records.append(TurnRecord(id="turn_1", deadline_event_ids=("resolution_x",)))
    restored = RuntimeSnapshot.model_validate_json(state.snapshot().model_dump_json())
    state.restore_snapshot(restored)
    assert state.turn_records[-1].deadline_event_ids == ("resolution_x",)
    assert TurnRecord.model_validate({"id": "turn_old"}).deadline_event_ids == ()


def test_deadline_history_does_not_leak_between_visits() -> None:
    state = _state()
    state.turn_index = 3
    state.scene_entered_at_turn = 2
    state.turn_records = [
        TurnRecord(id="turn_1", deadline_event_ids=("resolution_old",)),
        TurnRecord(id="turn_2"),
        TurnRecord(id="turn_3", transition_id="t_1a_1b"),
    ]
    engine = RuntimeEngine(state, _provider("The room stays quiet."))

    assert engine._deadline_transition_cause(state.snapshot()) == "earned"


def test_deadline_history_longer_than_the_bound_degrades_to_earned() -> None:
    state = _state()
    state.turn_index = 25
    state.scene_entered_at_turn = 0
    state.turn_records = [TurnRecord(id=f"turn_{i}") for i in range(25)]
    engine = RuntimeEngine(state, _provider("The room stays quiet."))

    assert engine._deadline_transition_cause(state.snapshot()) == "earned"


class _WebProvider:
    last_prompt = {"system": "system prompt", "user": "user prompt"}

    def opening(self):
        return {"segments": [{"kind": "narration", "text": "A quiet opening."}]}

    def __call__(self, _command: str):
        return {"segments": [{"kind": "narration", "text": "Rebecca is in the room."}]}


@pytest.mark.parametrize("enabled", [False, True])
def test_web_rejection_exposes_bundle_only_with_prompt_gate(monkeypatch, tmp_path, enabled: bool) -> None:
    if enabled:
        monkeypatch.setenv("FREYTAG_EXPOSE_PROMPT", "1")
    else:
        monkeypatch.delenv("FREYTAG_EXPOSE_PROMPT", raising=False)
    app = create_demo_app(store_path=tmp_path / f"{enabled}.sqlite", provider_factory=lambda _state: _WebProvider())
    with TestClient(app) as client:
        session = client.post("/api/v1/session", json={"story_id": "continuity_initiative"})
        response = client.post(
            "/api/v1/turn",
            json={"session_id": session.json()["session_id"], "player_input": "Search the kitchen."},
        )
    assert response.status_code == 409
    assert response.headers["X-Freytag-Rejection-Code"] == "narration_known_term_leak"
    expected_detail = "narration mentions an unavailable entity 'rebecca'" if enabled else REJECTED_TURN_MESSAGE
    assert response.json()["detail"] == expected_detail
    assert ("attempt_bundle" in response.json()) is enabled
