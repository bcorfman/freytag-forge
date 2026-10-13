"""Hermetic evaluation arms and report rendering."""

from __future__ import annotations

import time
from collections.abc import Callable, Mapping
from typing import Any, Protocol

from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.facts import Fact
from storygame.runtime.state import RuntimeState
from storygame.story_package.models import StoryPackage

from .metrics import TurnScore, aggregate, score_turn
from .model import EvalCase, TurnObservation


class Arm(Protocol):
    name: str

    def play(self, case: EvalCase, state: RuntimeState) -> list[TurnObservation]: ...


class ScriptedArm:
    def __init__(self, name: str, observations: Mapping[str, list[TurnObservation]]) -> None:
        self.name = name
        self.observations = observations

    def play(self, case: EvalCase, state: RuntimeState) -> list[TurnObservation]:
        if case.id not in self.observations:
            raise KeyError(case.id)
        return list(self.observations[case.id])


class PipelineArm:
    name = "current"

    def __init__(self, narrator: Callable[[str], dict[str, Any]]) -> None:
        self.narrator = narrator

    def play(self, case: EvalCase, state: RuntimeState) -> list[TurnObservation]:
        observations: list[TurnObservation] = []
        usage = 0

        def provider(command: str) -> dict[str, Any]:
            nonlocal usage
            reply = self.narrator(command)
            usage = reply.get("usage", 0) if isinstance(reply.get("usage", 0), int) else 0
            return {key: value for key, value in reply.items() if key != "usage"}

        engine = RuntimeEngine(state, provider)
        for index, command in enumerate(case.commands):
            started = time.perf_counter()
            result = engine.turn(command)
            elapsed = time.perf_counter() - started
            observations.append(
                TurnObservation(
                    state={},
                    prose=result.narration,
                    revealed_ids=tuple(result.selected_knowledge_ids),
                    latency_s=elapsed,
                    requests=1,
                    tokens=usage,
                )
            )
            if case.save_load_after == index:
                snapshot = state.snapshot()
                restored = RuntimeState.bootstrap(state.package)
                restored.restore_snapshot(snapshot)
                state = restored
                engine = RuntimeEngine(state, provider)
        return observations


def prepare_state(case: EvalCase, package: StoryPackage) -> RuntimeState:
    state = RuntimeState.bootstrap(package)
    scene = next(scene for scene in package.scenes if scene.metadata.scene_id == case.scene)
    state.current_scene_id = case.scene
    state.phase = scene.metadata.freytag_phase
    state._assert_scene_entry_fact(case.scene)
    for predicate in case.setup_facts:
        state.facts.assert_fact(Fact(predicate=predicate, subject="story", value="true"))
    return state


def run_arm(
    arm: Arm,
    cases: tuple[EvalCase, ...],
    package: StoryPackage,
    claim_judge: Callable[[str, str], bool] | None = None,
) -> dict[str, list[TurnScore]]:
    return {
        case.id: [
            score_turn(case.expect, observation, claim_judge=claim_judge)
            for observation in arm.play(case, prepare_state(case, package))
        ]
        for case in cases
    }


def render_report(
    results: Mapping[str, Mapping[str, list[TurnScore]]],
    cases: tuple[EvalCase, ...],
    claim_judge: Callable[[str, str], bool] | None = None,
) -> str:
    lines = ["Pipeline evaluation report"]
    by_id = {case.id: case for case in cases}
    all_scores: dict[str, list[TurnScore]] = {}
    for arm_name, arm_results in results.items():
        lines.append(f"\nArm: {arm_name}")
        arm_scores: list[TurnScore] = []
        for case_id, scores in arm_results.items():
            case = by_id[case_id]
            for turn, score in enumerate(scores, 1):
                lines.append(f"{case.id} [{case.split}] turn {turn}: {score}")
                if case.expect.prose_must_not_assert and claim_judge is None:
                    lines.append("prose unchecked (no claim judge)")
            arm_scores.extend(scores)
        all_scores[arm_name] = arm_scores
        lines.append(f"aggregate: {aggregate(arm_scores, arm_name)}")
    return "\n".join(lines) + "\n"
