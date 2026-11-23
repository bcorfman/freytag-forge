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


def advance_state_to_scene(package: Any, state: RuntimeState, scene_id: str) -> None:
    """Advance an existing state to a scene with the deterministic thorough player."""

    if state.current_scene_id == scene_id:
        return
    from storygame.personas import PERSONAS, _legacy_package, _ScriptedProvider, _select_thorough, _turn_cap

    if scene_id not in {scene.metadata.scene_id for scene in package.scenes}:
        raise ValueError(f"scene {scene_id} is not in package {package.story_id}")
    persona_package = _legacy_package(package)
    provider = _ScriptedProvider(persona_package, state)
    engine = RuntimeEngine(state, provider)
    for _ in range(_turn_cap(persona_package)):
        if state.current_scene_id == scene_id:
            return
        engine._activate_pacing()
        projection = engine.projector.project(state, "player", "")
        selected = _select_thorough(persona_package, state, projection.candidates)
        provider.selected = (selected,) if selected else ()
        try:
            engine.turn(PERSONAS["thorough"])
        except (ProposalValidationError, RuntimeContractError):
            provider.selected = ()
            engine.turn(PERSONAS["thorough"])
    if state.current_scene_id != scene_id:
        raise RuntimeError(f"scene {scene_id} was not reached by offline thorough seeding")
