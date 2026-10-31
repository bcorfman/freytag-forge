from __future__ import annotations

from pathlib import Path

import pytest

from storygame.runtime.capture import WorldCapture
from storygame.runtime.cloudflare import CloudflareTurnProvider
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.item_facts import ItemFactsProvider
from storygame.runtime.observation import ObservationRequest
from storygame.runtime.observation_verifier import ObservationVerifier
from storygame.runtime.state import RuntimeState
from storygame.runtime.validation import ProposalValidationError
from storygame.story_package.loader import load_story_package
from storygame.web_demo import create_demo_app

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))


class _Provider:
    def opening(self) -> dict[str, object]:
        return {"segments": [{"kind": "narration", "text": "The room waits."}]}


def _provider(state: RuntimeState) -> ItemFactsProvider:
    provider = ItemFactsProvider(
        worker_url="https://fake.worker",
        token="",
        state=state,
        item_facts={},
        mode="single_call",
        seed_from_package=True,
        held_by=True,
    )
    provider.observe_automatically = False
    provider.observation_request = ObservationRequest("Inspect the storm drain.", "look", "storm_drain")
    return provider


def _opening_capture(
    provider: ItemFactsProvider,
    scores: list[float],
) -> tuple[WorldCapture, list[dict[str, str]]]:
    prompts: list[dict[str, str]] = []
    score_iter = iter(scores)

    def ask(_state: object, questions: object) -> dict[str, dict[str, float]]:
        score = next(score_iter, 1.0) if isinstance(questions, dict) and "condition_consistent" in questions else 1.0
        return {key: {"noul": score} for key in questions} if isinstance(questions, dict) else {}

    capture = WorldCapture(provider, ask)
    capture.enforcing_verifier = ObservationVerifier(ask, opening_check=True)
    provider.opening_subjects = lambda: ("storm drain",)
    return capture, prompts


def test_flag_off_feedback_is_byte_identical() -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    provider = CloudflareTurnProvider(worker_url="https://fake.worker", token="", state=state)

    provider.note_rejection("observation_unverified", opening_things=("storm drain",))

    assert provider._rejection_note == (
        "Your last reply did not follow the narration rules. "
        "Write this turn again. "
        "Use only the information in the current prompt."
    )


def test_web_demo_sets_both_opening_fact_flags(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    provider = _Provider()
    monkeypatch.setenv("FREYTAG_OPENING_RETRY_FACT", "1")
    monkeypatch.setenv("FREYTAG_OPENING_THINGS_FACT", "1")

    app = create_demo_app(
        store_path=tmp_path / "sessions.sqlite",
        provider_factory=lambda _state: provider,
    )
    from fastapi.testclient import TestClient

    with TestClient(app) as client:
        response = client.post("/api/v1/session", json={"story_id": "continuity_initiative"})

    assert response.status_code == 200
    assert provider.opening_retry_fact is True
    assert provider.opening_things_fact is True


def test_web_demo_leaves_opening_things_fact_off_when_unset(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    provider = _Provider()
    monkeypatch.delenv("FREYTAG_OPENING_RETRY_FACT", raising=False)
    monkeypatch.delenv("FREYTAG_OPENING_THINGS_FACT", raising=False)

    app = create_demo_app(
        store_path=tmp_path / "sessions.sqlite",
        provider_factory=lambda _state: provider,
    )
    from fastapi.testclient import TestClient

    with TestClient(app) as client:
        response = client.post("/api/v1/session", json={"story_id": "continuity_initiative"})

    assert response.status_code == 200
    assert provider.opening_retry_fact is False
    assert provider.opening_things_fact is False


def test_rejected_opening_adds_only_failed_opening_fact_to_second_prompt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    state.current_scene_id = "1B"
    provider = _provider(state)
    provider.opening_retry_fact = True
    provider.opening_things_fact = False
    capture, prompts = _opening_capture(provider, [0.0, 1.0])
    replies = iter(
        (
            {
                "segments": [
                    {"kind": "narration", "text": "The storm drain is slightly ajar."},
                ],
                "selected_knowledge_ids": [],
                "item_facts": {},
            },
            {
                "segments": [{"kind": "narration", "text": "The storm drain remains outside."}],
                "selected_knowledge_ids": [],
                "item_facts": {},
            },
        )
    )

    monkeypatch.setattr(
        CloudflareTurnProvider,
        "_request_item_facts",
        lambda _provider, _payload: {"refers": ["storm drain"], "same_as": {}},
    )

    def request(_provider: CloudflareTurnProvider, payload: dict[str, object]) -> object:
        prompts.append({"system": str(payload["system"])})
        return next(replies)

    monkeypatch.setattr(CloudflareTurnProvider, "_request", request)

    engine = RuntimeEngine(state, provider, capture=capture)
    engine.narration_validator.validate = lambda *_args: None
    result = engine.turn("Inspect the storm drain.")

    assert result.narration.startswith("The storm drain remains outside.")
    assert len(prompts) == 2
    retry_prompt = prompts[1]["system"]
    assert "The storm drain has no open or closed state and nothing inside it." in retry_prompt
    assert "slightly" not in retry_prompt
    assert "ajar" not in retry_prompt
    assert len(prompts) == 2


def test_relation_only_failure_keeps_generic_feedback(monkeypatch: pytest.MonkeyPatch) -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    provider = _provider(state)
    provider.opening_retry_fact = True
    provider.observation_request = ObservationRequest("Inspect the storm drain.", "look", "storm_drain")
    capture, _prompts = _opening_capture(provider, [])
    capture.enforcing_verifier = ObservationVerifier(
        capture.ask,
        opening_check=False,
    )

    provider.note_rejection("observation_unverified", opening_things=())

    assert provider._rejection_note == (
        "Your last reply did not follow the narration rules. "
        "Write this turn again. "
        "Use only the information in the current prompt."
    )


def test_rejected_opening_still_resumes_and_restores_after_two_attempts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    provider = _provider(state)
    provider.opening_retry_fact = True
    capture, prompts = _opening_capture(provider, [0.0, 0.0])
    replies = iter(
        {
            "segments": [{"kind": "narration", "text": "The storm drain is ajar."}],
            "selected_knowledge_ids": [],
            "item_facts": {},
        }
        for _ in range(2)
    )
    monkeypatch.setattr(
        CloudflareTurnProvider,
        "_request_item_facts",
        lambda _provider, _payload: {"refers": ["storm drain"], "same_as": {}},
    )

    def request(_provider: CloudflareTurnProvider, payload: dict[str, object]) -> object:
        prompts.append({"system": str(payload["system"])})
        return next(replies)

    monkeypatch.setattr(CloudflareTurnProvider, "_request", request)
    calls: list[str] = []
    original_resume = capture.resume
    original_discard = capture.discard
    monkeypatch.setattr(capture, "resume", lambda context: calls.append("resume") or original_resume(context))
    monkeypatch.setattr(capture, "discard", lambda: calls.append("discard") or original_discard())

    engine = RuntimeEngine(state, provider, capture=capture)
    engine.narration_validator.validate = lambda *_args: None
    with pytest.raises(ProposalValidationError) as caught:
        engine.turn("Inspect the storm drain.")

    assert caught.value.code == "observation_unverified"
    assert calls == ["discard", "resume"]
    assert len(prompts) == 2
