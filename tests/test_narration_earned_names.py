"""Earned names remain safe when they are outside the current scene projection."""

from __future__ import annotations

from pathlib import Path

import pytest

from storygame.personas import PERSONAS, _legacy_package, _ScriptedProvider, _select_thorough, _turn_cap
from storygame.runtime.contracts import RuntimeContractError
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.knowledge import KnowledgeProjector
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


def _narrate(state: RuntimeState, text: str, grounding: tuple[str, ...] = ()) -> None:
    payload = {
        "segments": [{"kind": "narration", "text": text, "grounding_ids": list(grounding)}],
    }
    RuntimeEngine(state, lambda _player_input: payload).turn("Inspect the alarm panel.")


def test_earned_names_are_accepted_in_later_scene() -> None:
    state = _seeded_3b()

    _narrate(state, "Michelle and Brandon watch the JANUS relay as alarms sound.")


def test_bare_later_scene_rejects_unearned_names() -> None:
    with pytest.raises(ProposalValidationError):
        _narrate(_bare_3b(), "Michelle and Brandon watch the JANUS relay as alarms sound.")


def test_seeded_later_scene_rejects_not_yet_earned_item_name() -> None:
    with pytest.raises(ProposalValidationError):
        _narrate(_seeded_3b(), "Brandon eyes the portable data case in Rebecca's office.")


def test_earned_but_unshown_knowledge_cannot_be_used_as_grounding() -> None:
    state = _seeded_3b()
    projector = KnowledgeProjector()
    earned_ids = {
        item.id
        for item in PACKAGE.knowledge.knowledge
        if KnowledgeProjector._established(item, state) and KnowledgeProjector._visible_to(item, "player")
    }
    shown_ids = {item.id for item in projector.project(state, "player", "").committed_knowledge}
    unshown_id = next(iter(sorted(earned_ids - shown_ids)))
    statement = PACKAGE.knowledge_indexes.by_id[unshown_id].statement

    with pytest.raises(ProposalValidationError, match="segment grounding is not committed or selected knowledge"):
        _narrate(state, statement, (unshown_id,))
