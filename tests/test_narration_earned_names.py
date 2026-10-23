"""Earned names remain safe when they are outside the current scene projection."""

from __future__ import annotations

from pathlib import Path

import pytest

from storygame.personas import PERSONAS, _legacy_package, _ScriptedProvider, _select_thorough, _turn_cap
from storygame.runtime.contracts import RuntimeContractError
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.facts import Fact
from storygame.runtime.state import RuntimeState
from storygame.runtime.validation import ProposalValidationError
from storygame.story_package.loader import load_story_package

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))


def _seeded_3b() -> RuntimeState:
    persona_package = _legacy_package(PACKAGE)
    state = RuntimeState.bootstrap(PACKAGE)
    provider = _ScriptedProvider(persona_package, state)
    engine = RuntimeEngine(state, provider)

    for _ in range(_turn_cap(persona_package)):
        if state.current_scene_id == "3B":
            assert state.package is PACKAGE
            return state
        engine._activate_pacing()
        projection = engine.projector.project(state, "player", "")
        selected = _select_thorough(persona_package, state, projection.candidates)
        provider.selected = (selected,) if selected else ()
        try:
            engine.turn(PERSONAS["thorough"])
        except (ProposalValidationError, RuntimeContractError):
            provider.selected = ()
            engine.turn(PERSONAS["thorough"])

    raise AssertionError("thorough player never reached 3B")


def _bare_3b() -> RuntimeState:
    scene = next(scene for scene in PACKAGE.scenes if scene.metadata.scene_id == "3B")
    state = RuntimeState(package=PACKAGE, current_scene_id="3B", phase=scene.metadata.freytag_phase)
    state._assert_scene_entry_fact("3B")
    return state


def _bare_3c() -> RuntimeState:
    scene = next(scene for scene in PACKAGE.scenes if scene.metadata.scene_id == "3C")
    state = RuntimeState(package=PACKAGE, current_scene_id="3C", phase=scene.metadata.freytag_phase)
    state._assert_scene_entry_fact("3C")
    return state


def _narrate(state: RuntimeState, text: str, grounding: tuple[str, ...] = ()) -> None:
    payload = {
        "segments": [{"kind": "narration", "text": text, "grounding_ids": list(grounding)}],
    }
    RuntimeEngine(state, lambda _player_input: payload).turn("Inspect the alarm panel.")


def test_bare_later_scene_rejects_unearned_names() -> None:
    with pytest.raises(ProposalValidationError):
        _narrate(_bare_3b(), "Michelle and Brandon watch the JANUS selection records as alarms sound.")


def test_earned_phase_two_statement_lets_narration_say_phase_two() -> None:
    item = PACKAGE.knowledge_indexes.by_id["k_sl_3c_e_r1"]
    state = _bare_3c()

    for effect in item.establishes:
        value = str(effect.value).lower() if isinstance(effect.value, bool) else str(effect.value)
        state.facts.assert_fact(Fact(predicate=effect.fact_id, subject="story", value=value))
    for prerequisite in item.requires:
        value = str(prerequisite.equals).lower()
        state.facts.assert_fact(Fact(predicate=prerequisite.fact_id, subject="story", value=value))

    text = "The recovered file says Phase Two was meant to provoke conflict among survivors."
    _narrate(state, text)

    with pytest.raises(ProposalValidationError) as exc_info:
        _narrate(_bare_3c(), text)
    assert exc_info.value.code == "protected_narration_leak"
