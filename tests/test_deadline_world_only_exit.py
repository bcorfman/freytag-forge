"""Deadline handoffs must finish bridges whose remaining facts are world-only."""

from __future__ import annotations

from pathlib import Path

from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.facts import Fact
from storygame.runtime.knowledge import KnowledgeProjector
from storygame.runtime.state import RuntimeState
from storygame.story_package.loader import load_story_package
from storygame.story_package.models import ActivationRule, CanonicalRouteEvent, RouteOperation
from tests.test_canon_journey import _ScriptedProvider


def _is_true(state: RuntimeState, fact_id: str) -> bool:
    return Fact(predicate=fact_id, subject="story", value="true") in state.facts.asserted


class _GreedyProvider(_ScriptedProvider):
    """Select the offered candidate that completes the most pending bridge facts."""

    def __init__(self, state: RuntimeState) -> None:
        super().__init__(state.package)
        self.state = state
        self.engine: RuntimeEngine | None = None
        self.choose = True
        self.selected_history: list[tuple[str, ...]] = []

    def __call__(self, player_input: str) -> dict[str, object]:
        if self.choose:
            projection = KnowledgeProjector().project(self.state, "player", player_input)
            missing = set(self.engine._bridge_missing_fact_ids()) if self.engine else set()
            candidate = min(
                projection.candidates,
                key=lambda item: (
                    -sum(
                        operation.op == "assert" and operation.fact_id in missing
                        for operation in self.package.knowledge_indexes.by_id[item.id].establishes
                    ),
                    item.id,
                ),
                default=None,
            )
            self.selected = [candidate.id] if candidate else []
        else:
            self.selected = []
        self.selected_history.append(tuple(self.selected))
        return super().__call__(player_input)


def test_resolution_deadline_does_not_stage_world_only_bridge_fact() -> None:
    package = load_story_package(Path("data/stories/continuity-initiative"))
    bridge = CanonicalRouteEvent(
        id="world_only_resolution_bridge",
        scene_id="3C",
        activation=ActivationRule(all_facts_true=("rebecca_observing_infiltrators",)),
        operations=(RouteOperation(op="assert", fact_id="resolution_complete", value=True),),
    )
    routes = package.storylet_routes.model_copy(update={"bridge_events": (bridge,)})
    package = package.model_copy(update={"storylet_routes": routes})
    state = RuntimeState.bootstrap(package)
    state.current_scene_id = "3C"
    state.phase = next(scene.metadata.freytag_phase for scene in package.scenes if scene.metadata.scene_id == "3C")
    state._assert_scene_entry_fact("3C")
    window = next(item for item in package.pacing.scenes if item.scene_id == "3C")
    state.turn_index = window.handoff_after_turns - 1
    engine = RuntimeEngine(state, lambda _input: {"segments": [{"kind": "narration", "text": "The situation holds."}]})

    engine.turn("Inspect the final control panel.")

    assert state.current_scene_id == "3C"
    assert state.staged_handoff_fact_ids == ()
    assert not _is_true(state, "rebecca_observing_infiltrators")
    assert state.last_turn_delivery.handoff_staged is False
