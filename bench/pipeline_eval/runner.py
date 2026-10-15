"""Hermetic evaluation arms and report rendering."""

from __future__ import annotations

import time
from collections.abc import Callable, Mapping
from typing import Any, Protocol

from storygame.runtime.capture import WorldCapture, build_capture_provider
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.facts import Fact
from storygame.runtime.state import RuntimeState
from storygame.story_package.models import StoryPackage

from .metrics import TurnScore, aggregate, score_turn
from .model import EvalCase, TurnObservation, grounded_state


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

    def __init__(
        self,
        narrator: Callable[[str], dict[str, Any]],
        *,
        refusal_ask: Callable[[object, object], dict | None] | None = None,
    ) -> None:
        self.narrator = narrator
        self.refusal_ask = refusal_ask

    def play(self, case: EvalCase, state: RuntimeState) -> list[TurnObservation]:
        observations: list[TurnObservation] = []
        engine: RuntimeEngine | None = None

        def classifier(state: object, questions: object) -> dict | None:
            nonlocal turn_requests, turn_tokens
            turn_requests += 1
            answer = self.refusal_ask(state, questions) if self.refusal_ask is not None else None
            usage = answer.get("usage") if isinstance(answer, dict) else None
            if isinstance(usage, int):
                turn_tokens += usage
            return answer

        def provider(command: str) -> dict[str, Any]:
            nonlocal turn_requests, turn_tokens, engine_extra_calls_seen
            turn_requests += 1
            if engine is not None:
                reported_extra_calls = max(0, getattr(engine, "refusal_extra_calls", 0))
                engine_extra_calls_seen = max(engine_extra_calls_seen, reported_extra_calls)
            reply = self.narrator(command)
            usage = reply.get("usage", 0) if isinstance(reply.get("usage", 0), int) else 0
            turn_tokens += usage
            return {key: value for key, value in reply.items() if key != "usage"}

        capture = None
        if self.refusal_ask is not None:
            capture = WorldCapture(
                build_capture_provider(state, mark_fixed=True),
                classifier,
                fixed_refusal=True,
                engine_refusal=True,
            )
        engine = RuntimeEngine(state, provider, capture=capture) if capture else RuntimeEngine(state, provider)
        for index, command in enumerate(case.commands):
            turn_requests = 0
            turn_tokens = 0
            engine_extra_calls_seen = 0
            started = time.perf_counter()
            result = engine.turn(command)
            elapsed = time.perf_counter() - started
            attempt = engine.last_attempt
            attempts = getattr(engine, "attempts", ())
            if attempt is None and attempts:
                attempt = attempts[-1]
            delivery = engine.state.last_turn_delivery
            refused_without_provider = (
                turn_requests == 0
                and attempt is not None
                and attempt.outcome == "rejected"
                and not delivery.guard_retry_used
            )
            extra_calls = max(0, engine.refusal_extra_calls - engine_extra_calls_seen)
            requests = 0 if refused_without_provider else turn_requests + extra_calls
            observations.append(
                TurnObservation(
                    state=grounded_state(engine.state),
                    prose=result.narration,
                    revealed_ids=tuple(result.selected_knowledge_ids),
                    forced_progress=(
                        getattr(attempt, "transition_cause", None) == "forced" if attempt is not None else None
                    ),
                    latency_s=elapsed,
                    requests=requests,
                    tokens=turn_tokens,
                )
            )
            if case.save_load_after == index:
                snapshot = state.snapshot()
                restored = RuntimeState.bootstrap(state.package)
                restored.restore_snapshot(snapshot)
                state = restored
                capture = None
                if self.refusal_ask is not None:
                    capture = WorldCapture(
                        build_capture_provider(state, mark_fixed=True),
                        classifier,
                        fixed_refusal=True,
                        engine_refusal=True,
                    )
                engine = RuntimeEngine(state, provider, capture=capture) if capture else RuntimeEngine(state, provider)
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
