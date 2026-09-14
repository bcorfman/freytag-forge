"""Deadline handoffs must finish bridges whose remaining facts are world-only."""

from __future__ import annotations

from pathlib import Path

from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.facts import Fact
from storygame.runtime.knowledge import KnowledgeProjector
from storygame.runtime.state import RuntimeState
from storygame.story_package.loader import load_story_package
from storygame.story_package.models import ActivationRule, CanonicalRouteEvent, RouteOperation
from tests._legacy_package import legacy_package
from tests.test_canon_journey import PACKAGE, _drive, _ScriptedProvider


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


def test_deliverable_early_then_world_only_deadline_exits_2a() -> None:
    package = legacy_package(PACKAGE, {"k_sl_1a_a_r1"})
    state = RuntimeState.bootstrap(package)
    provider = _GreedyProvider(state)
    engine = RuntimeEngine(state, provider)
    provider.engine = engine

    pre_2a_budget = sum(item.handoff_after_turns for item in package.pacing.scenes[:3]) + 1
    for _ in range(pre_2a_budget):
        if state.current_scene_id == "2A":
            break
        _drive(engine, provider, None)

    assert state.current_scene_id == "2A"
    _drive(engine, provider, None)
    assert provider.selected_history[-1] == ("k_sl_2a_b_r1",)
    provider.choose = False
    window = next(item for item in package.pacing.scenes if item.scene_id == "2A")
    exit_turn = None
    for _ in range(window.handoff_after_turns - 1):
        result = engine.turn("Inspect the restricted corridor entrance.")
        if state.current_scene_id == "2B":
            exit_turn = result
            break

    assert state.current_scene_id == "2B"
    assert _is_true(state, "rebecca_observing_infiltrators")
    assert exit_turn is not None
    bridge_text = next(
        scene.metadata.bridge_text["t_2a_2b"] for scene in package.scenes if scene.metadata.scene_id == "2A"
    )
    assert bridge_text in {segment.text for segment in exit_turn.segments}


def test_staller_from_2a_still_exits_at_its_deadline() -> None:
    package = legacy_package(PACKAGE, {"k_sl_1a_a_r1"})
    state = RuntimeState.bootstrap(package)
    provider = _ScriptedProvider(package)
    engine = RuntimeEngine(state, provider)

    pre_2a_budget = sum(item.handoff_after_turns for item in package.pacing.scenes[:3]) + 1
    for _ in range(pre_2a_budget):
        if state.current_scene_id == "2A":
            break
        _drive(engine, provider, None)

    assert state.current_scene_id == "2A"
    window = next(item for item in package.pacing.scenes if item.scene_id == "2A")
    for _ in range(window.handoff_after_turns):
        _drive(engine, provider, None)
        if state.current_scene_id == "2B":
            break

    assert state.current_scene_id == "2B"
    assert _is_true(state, "false_identities_ready")
    assert _is_true(state, "rebecca_observing_infiltrators")


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
