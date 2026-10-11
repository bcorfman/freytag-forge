"""Hermetic coverage for the typed turn-attempt record."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from storygame.runtime.attempt_bundle import AttemptBundle
from storygame.runtime.cloudflare import NarrationProviderError
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.facts import Fact
from storygame.runtime.state import RuntimeState
from storygame.runtime.validation import ProposalValidationError
from storygame.story_package.loader import load_story_package
from storygame.web_demo import create_demo_app

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))


def _state() -> RuntimeState:
    state = RuntimeState.bootstrap(PACKAGE)
    return state


def _provider(text: str):
    def provider(_command: str) -> dict[str, object]:
        return {"segments": [{"kind": "narration", "text": text}]}

    return provider


def test_bundle_round_trip_and_unknown_version_refusal() -> None:
    bundle = AttemptBundle(
        identity={"package_id": "continuity_initiative"},
        pre_state={"scene_id": "1A", "turn_index": 0, "turns_since_scene_entry": 0},
        command={"raw": "Search the drawer.", "normalized": "Search the drawer."},
        outcome="committed",
    )
    assert AttemptBundle.from_json(bundle.to_json()) == bundle
    with pytest.raises(ValidationError, match="unsupported attempt bundle schema version"):
        AttemptBundle.model_validate({**bundle.model_dump(), "schema_version": 2})


def test_accepted_and_rejected_attempts_are_recorded_and_rejection_restores_state() -> None:
    state = _state()
    engine = RuntimeEngine(state, _provider("The drawer remains closed."))
    engine.turn("Search the drawer.")
    assert engine.last_attempt is not None
    assert engine.last_attempt.outcome == "committed"
    assert engine.last_attempt.stages[0].reply is not None

    before = state.snapshot()
    engine.provider = _provider("Rebecca is in the room.")
    with pytest.raises(ProposalValidationError) as caught:
        engine.turn("Search the kitchen.")
    assert caught.value.code == "narration_known_term_leak"
    assert engine.last_attempt is not None
    assert engine.last_attempt.outcome == "rejected"
    assert engine.last_attempt.rejection.code == "narration_known_term_leak"
    assert state.snapshot() == before


def test_operational_failure_is_separate_from_rejection() -> None:
    def provider(_command: str):
        raise NarrationProviderError("worker unavailable", error_code="WORKER_DOWN")

    engine = RuntimeEngine(_state(), provider)
    with pytest.raises(NarrationProviderError):
        engine.turn("Listen to the recording.")
    assert engine.last_attempt is not None
    assert engine.last_attempt.outcome == "operational_failure"
    assert engine.last_attempt.operational_failure.code == "WORKER_DOWN"
    assert engine.last_attempt.rejection is None


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
    assert response.json()["detail"] == "narration mentions an unavailable entity 'rebecca'"
    assert ("attempt_bundle" in response.json()) is enabled
