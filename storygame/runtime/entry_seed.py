"""Deterministic entry-state construction for a loaded story package."""

from __future__ import annotations

from typing import Any

from storygame.runtime.contracts import RuntimeContractError
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.state import RuntimeState
from storygame.runtime.validation import ProposalValidationError
from storygame.runtime.world_model import apply_scene_placements, apply_world_effects, world_for


def bare_state_for_scene(package: Any, scene_id: str) -> RuntimeState:
    """Build a scene-entry state with world setup and no player turns."""

    scene = next((item for item in package.scenes if item.metadata.scene_id == scene_id), None)
    if scene is None:
        raise ValueError(f"scene {scene_id} is not in package {package.story_id}")
    state = RuntimeState(package=package, current_scene_id=scene_id, phase=scene.metadata.freytag_phase)
    state._assert_scene_entry_fact(scene_id)
    world_for(package, state.facts).seed()
    apply_scene_placements(package, state.facts, scene_id)
    apply_world_effects(package, state.facts)
    return state


def _advance_state_to_scene(package: Any, state: RuntimeState, scene_id: str, persona: str) -> tuple[bool, list[dict]]:
    from storygame.personas import (
        PERSONAS,
        _legacy_package,
        _ScriptedProvider,
        _select_canonical,
        _select_thorough,
        _turn_cap,
    )

    selectors = {"thorough": _select_thorough, "canonical": _select_canonical}
    try:
        selector = selectors[persona]
    except KeyError as error:
        raise ValueError(f"unknown entry persona: {persona}") from error
    if scene_id not in {scene.metadata.scene_id for scene in package.scenes}:
        raise ValueError(f"scene {scene_id} is not in package {package.story_id}")
    if state.current_scene_id == scene_id:
        return True, []

    persona_package = _legacy_package(package)
    provider = _ScriptedProvider(persona_package, state)
    engine = RuntimeEngine(state, provider)
    turns: list[dict] = []
    for _ in range(_turn_cap(persona_package)):
        if state.current_scene_id == scene_id:
            return True, turns
        engine._activate_pacing()
        projection = engine.projector.project(state, "player", "")
        selected = selector(persona_package, state, projection.candidates)
        provider.selected = (selected,) if selected else ()
        try:
            engine.turn(PERSONAS[persona])
        except (ProposalValidationError, RuntimeContractError):
            provider.selected = ()
            engine.turn(PERSONAS[persona])

        delivered: list[str] = []
        attempt = engine.last_attempt
        if attempt is not None:
            knowledge_ids = attempt.selected_reveal.knowledge_ids
            for knowledge_id in knowledge_ids:
                storylet_id = persona_package.knowledge_indexes.by_id[knowledge_id].source.storylet_id
                if storylet_id is not None and storylet_id not in delivered:
                    delivered.append(storylet_id)
        if state.turn_records:
            for knowledge_id in state.turn_records[-1].reveal_ids:
                storylet_id = persona_package.knowledge_indexes.by_id[knowledge_id].source.storylet_id
                if storylet_id is not None and storylet_id not in delivered:
                    delivered.append(storylet_id)
        turns.append(
            {
                "scene": state.current_scene_id,
                "transition_cause": attempt.transition_cause if attempt is not None else "none",
                "storylets_delivered": delivered,
            }
        )
    return state.current_scene_id == scene_id, turns


def advance_state_to_scene(package: Any, state: RuntimeState, scene_id: str, persona: str = "thorough") -> None:
    """Advance an existing state to a scene with a deterministic persona."""

    reached, _turns = _advance_state_to_scene(package, state, scene_id, persona)
    if not reached:
        raise RuntimeError(f"scene {scene_id} was not reached by offline {persona} seeding")


def canonical_path_report(package: Any) -> list[dict[str, object]]:
    """Report the canonical persona's deterministic scene-to-scene path."""

    state = RuntimeState.bootstrap(package)
    rows: list[dict[str, object]] = []
    for scene in package.scenes[1:]:
        from_scene = state.current_scene_id
        target_scene = scene.metadata.scene_id
        reached, turns = _advance_state_to_scene(package, state, target_scene, "canonical")
        delivered: list[str] = []
        transition_cause = "none"
        for turn in turns:
            transition_cause = turn["transition_cause"]
            for storylet_id in turn["storylets_delivered"]:
                if storylet_id not in delivered:
                    delivered.append(storylet_id)
        rows.append(
            {
                "from_scene": from_scene,
                "to_scene": target_scene,
                "turns": len(turns),
                "earned": reached and transition_cause == "earned",
                "transition_cause": transition_cause,
                "storylets_delivered": delivered,
                **({} if reached else {"reached": False}),
            }
        )
        if not reached:
            break
    return rows
