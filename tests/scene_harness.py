from __future__ import annotations

from storygame.runtime.candidate_matcher import uniquely_matched_authored_handoff
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.facts import Fact
from storygame.runtime.state import RuntimeState
from storygame.runtime.world_model import apply_scene_placements


def scene_engine(
    package,
    scene_id: str,
    *,
    true_facts: tuple[str, ...] = (),
    turn_index: int = 0,
) -> tuple[RuntimeState, RuntimeEngine]:
    state = RuntimeState.bootstrap(package)
    state.current_scene_id = scene_id
    scene = next(scene for scene in package.scenes if scene.metadata.scene_id == scene_id).metadata
    state.phase = scene.freytag_phase
    state._assert_scene_entry_fact(scene_id)
    state.turn_index = turn_index
    apply_scene_placements(package, state.facts, scene_id)
    for fact_id in true_facts:
        state.facts.assert_fact(Fact(predicate=fact_id, subject="story", value="true"))
    engine = RuntimeEngine(state, lambda _command: {"segments": [{"kind": "narration", "text": "Kristin looks."}]})
    return state, engine


def authored_handoff(engine: RuntimeEngine, state: RuntimeState, command: str):
    engine._activate_pacing()
    candidates = engine.projector.project(state, "player", command).candidates
    return uniquely_matched_authored_handoff(command, candidates)
