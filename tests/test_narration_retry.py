"""Coverage for the single narration-safety recovery attempt."""

from pathlib import Path

import pytest

from storygame.runtime.cloudflare import CloudflareTurnProvider
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.state import RuntimeState
from storygame.runtime.validation import ProposalValidationError
from storygame.story_package.loader import load_story_package

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))
LEAK = "Rebecca's secured office can broadcast the evidence."
CLEAN = "Kristin waits for Rebecca's next move."


def _scene_2c_state() -> RuntimeState:
    state = RuntimeState.bootstrap(PACKAGE)
    scene = next(scene for scene in PACKAGE.scenes if scene.metadata.scene_id == "2C")
    state.current_scene_id = "2C"
    state.phase = scene.metadata.freytag_phase
    state._assert_scene_entry_fact("2C")
    return state


class _ScriptedProvider:
    def __init__(self, *texts: str) -> None:
        self.texts = list(texts)
        self.calls = 0
        self.rejections: list[str] = []

    def __call__(self, _command: str) -> dict[str, object]:
        text = self.texts[self.calls]
        self.calls += 1
        return {"segments": [{"kind": "narration", "text": text}], "selected_knowledge_ids": []}

    def note_rejection(self, code: str | None) -> None:
        self.rejections.append(code or "")


def test_narration_leak_is_retried_once_and_the_turn_commits() -> None:
    state = _scene_2c_state()
    provider = _ScriptedProvider(LEAK, CLEAN)
    before_index = state.turn_index

    result = RuntimeEngine(state, provider).turn("Assess the cost of transmitting our evidence.")

    assert result.segments[0].text == CLEAN
    assert provider.calls == 2
    assert state.turn_index == before_index + 1
    assert state.last_turn_delivery.guard_retry_used is True
    assert state.last_turn_delivery.recovery_used is False


def test_retry_passes_the_rejection_to_the_provider_once() -> None:
    state = _scene_2c_state()
    provider = _ScriptedProvider(LEAK, CLEAN)

    RuntimeEngine(state, provider).turn("Assess the cost of transmitting our evidence.")

    assert len(provider.rejections) == 1
    assert provider.rejections == ["narration_known_term_leak"]


def test_two_rejections_still_fail_the_turn_and_restore_state() -> None:
    state = _scene_2c_state()
    provider = _ScriptedProvider(LEAK, LEAK)
    before = state.snapshot()

    with pytest.raises(ProposalValidationError) as caught:
        RuntimeEngine(state, provider).turn("Assess the cost of transmitting our evidence.")

    assert caught.value.code == "narration_known_term_leak"
    assert provider.calls == 2
    assert state.turn_index == before.turn_index
    assert state.facts == before.facts


def test_clean_reply_is_not_retried() -> None:
    state = _scene_2c_state()
    provider = _ScriptedProvider(CLEAN)

    RuntimeEngine(state, provider).turn("Assess the cost of transmitting our evidence.")

    assert provider.calls == 1
    assert provider.rejections == []


def test_effect_validation_errors_are_not_retried(monkeypatch: pytest.MonkeyPatch) -> None:
    state = _scene_2c_state()
    provider = _ScriptedProvider(CLEAN, CLEAN)
    engine = RuntimeEngine(state, provider)
    error = ProposalValidationError("effect failure", code="effect_failure")
    monkeypatch.setattr(engine.validator, "validate_effects", lambda *_args: (_ for _ in ()).throw(error))

    with pytest.raises(ProposalValidationError, match="effect failure"):
        engine.turn("Assess the cost of transmitting our evidence.")

    assert provider.calls == 1
    assert provider.rejections == []


def test_cloudflare_note_reaches_only_the_next_prompt(monkeypatch: pytest.MonkeyPatch) -> None:
    state = _scene_2c_state()
    provider = CloudflareTurnProvider(worker_url="https://worker.example/turn", token="", state=state)
    prompts: list[str] = []

    def dispatch(system: str, _context: object) -> object:
        prompts.append(system)
        return {"segments": [{"kind": "narration", "text": "ok"}]}

    monkeypatch.setattr(provider, "_dispatch", dispatch)
    provider.note_rejection("narration_known_term_leak")

    provider("Assess the cost of transmitting our evidence.")
    provider("Assess the cost of transmitting our evidence.")

    assert "Your last reply named something the player has not met yet." in prompts[0]
    assert "secured office" not in prompts[0].casefold()
    assert "narration mentions unavailable knowledge" not in prompts[0]
    assert "Your last reply named something the player has not met yet." not in prompts[1]
