"""Hermetic coverage for the narration-validator retry telemetry flag."""

from pathlib import Path

from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.state import RuntimeState
from storygame.story_package.loader import load_story_package

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))
LEAK = "Rebecca's secured office can broadcast the evidence."
CLEAN = "Kristin waits for Rebecca's next move."


class _ScriptedProvider:
    def __init__(self, *texts: str) -> None:
        self.texts = list(texts)
        self.calls = 0

    def __call__(self, _command: str) -> dict[str, object]:
        text = self.texts[self.calls]
        self.calls += 1
        return {"segments": [{"kind": "narration", "text": text}], "selected_knowledge_ids": []}

    def note_rejection(self, _code: str | None) -> None:
        pass


def _scene_2c_state() -> RuntimeState:
    state = RuntimeState.bootstrap(PACKAGE)
    scene = next(scene for scene in PACKAGE.scenes if scene.metadata.scene_id == "2C")
    state.current_scene_id = "2C"
    state.phase = scene.metadata.freytag_phase
    state._assert_scene_entry_fact("2C")
    return state


def test_guard_retry_sets_guard_retry_without_recovery() -> None:
    state = _scene_2c_state()
    provider = _ScriptedProvider(LEAK, CLEAN)

    RuntimeEngine(state, provider).turn("Assess the cost of transmitting our evidence.")

    assert provider.calls == 2
    assert state.last_turn_delivery.guard_retry_used is True
    assert state.last_turn_delivery.recovery_used is False


def test_accepted_first_reply_keeps_both_retry_flags_false() -> None:
    state = _scene_2c_state()
    provider = _ScriptedProvider(CLEAN)

    RuntimeEngine(state, provider).turn("Assess the cost of transmitting our evidence.")

    assert provider.calls == 1
    assert state.last_turn_delivery.guard_retry_used is False
    assert state.last_turn_delivery.recovery_used is False
