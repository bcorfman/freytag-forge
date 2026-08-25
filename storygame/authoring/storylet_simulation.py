"""Deterministic, authoring-only evaluation of reviewed storylet packages."""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from storygame.runtime.contracts import StoryletRealization, TurnResult
from storygame.runtime.narrative import RuntimeNarrativeProjection, StoryletSelector
from storygame.runtime.state import RuntimeState
from storygame.runtime.validation import validate_and_commit

SIMULATION_POLICIES = (
    "goal_focused",
    "exploratory",
    "social",
    "distrustful",
    "avoidant",
    "adversarial",
    "interruption_heavy",
)
CONVERSATION_POLICIES = SIMULATION_POLICIES
_StateFactory = Callable[[], RuntimeState]


class SimulationCase(BaseModel):
    """One reproducible policy run; it is evidence, never playable state."""

    model_config = ConfigDict(frozen=True)

    policy: str
    selected_storylet_ids: tuple[str, ...] = ()
    revelation_order: tuple[str, ...] = ()
    pressure_trajectory: tuple[int, ...] = ()
    blocked_actions: int = 0
    reached_climax: bool = False
    provider_request_count: int = 0


class SimulationMetrics(BaseModel):
    model_config = ConfigDict(frozen=True)

    ending_reachability: float = Field(ge=0, le=1)
    dead_ends: int = Field(ge=0)
    storylet_reuse: int = Field(ge=0)
    selection_diversity: float = Field(ge=0, le=1)
    pressure_trajectories: tuple[tuple[int, ...], ...] = ()
    blocked_action_rate: float = Field(ge=0, le=1)
    distinct_paths_to_climax: int = Field(ge=0)
    protected_revelation_violations: int = Field(ge=0)


class StoryletSimulationReport(BaseModel):
    """Versioned, non-runtime report emitted by the offline simulator."""

    model_config = ConfigDict(frozen=True)

    schema_version: str = "storylet-simulation-v1"
    source_id: str
    source_hash: str
    cases: tuple[SimulationCase, ...]
    metrics: SimulationMetrics


def simulate_storylets(
    projection: RuntimeNarrativeProjection,
    state_factory: _StateFactory,
    *,
    max_turns: int = 12,
) -> StoryletSimulationReport:
    """Exercise storylet and declared-conversation paths without runtime inference."""

    if max_turns < 1:
        raise ValueError("max_turns must be positive")
    cases = tuple(_simulate_policy(projection, state_factory, policy, max_turns) for policy in SIMULATION_POLICIES)
    return StoryletSimulationReport(
        source_id=projection.narrative_package.source_id,
        source_hash=projection.narrative_package.source_hash,
        cases=cases,
        metrics=_metrics(cases),
    )


def write_simulation_report(path: Path, report: StoryletSimulationReport) -> None:
    """Write immutable evidence without allowing it to become a runtime input."""

    if path.suffix != ".json" or not path.name.endswith(".simulation.json"):
        raise ValueError("SIMULATION_OUTPUT_INVALID: output must end in .simulation.json")
    if path.exists():
        raise ValueError("SIMULATION_OUTPUT_EXISTS: simulation reports never overwrite evidence")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report.model_dump_json(indent=2) + "\n", encoding="utf-8")


def _simulate_policy(
    projection: RuntimeNarrativeProjection, state_factory: _StateFactory, policy: str, max_turns: int
) -> SimulationCase:
    state = state_factory()
    selected: list[str] = []
    revelations: list[str] = []
    pressures = [_pressure(state)]
    blocked = 0
    seen_truths = _known_truths(state)
    for _ in range(max_turns):
        eligible = StoryletSelector(state.narrative_package, state.facts).select(
            active_beat_ids=tuple(beat.id for beat in state.active_beats), location_id=state.world.location, limit=99
        )
        storylet = _choose(eligible, policy)
        if storylet is None:
            blocked += 1
            break
        result = _result_for(storylet, state, policy)
        if result is None:
            blocked += 1
            break
        state = validate_and_commit(state, result)
        selected.append(storylet.id)
        current_truths = _known_truths(state)
        revelations.extend(sorted(current_truths - seen_truths))
        seen_truths = current_truths
        pressures.append(_pressure(state))
    package = projection.narrative_package
    climax_truths = _climax_truths(package)
    return SimulationCase(
        policy=policy,
        selected_storylet_ids=tuple(selected),
        revelation_order=tuple(revelations),
        pressure_trajectory=tuple(pressures),
        blocked_actions=blocked,
        reached_climax=bool(climax_truths) and all(truth_id in seen_truths for truth_id in climax_truths),
    )


def _choose(eligible: tuple, policy: str):
    if not eligible:
        return None
    if policy == "social":
        return min(eligible, key=lambda item: (item.purpose != "relationship", item.id))
    if policy == "adversarial":
        return min(eligible, key=lambda item: (item.purpose != "conflict", item.id))
    if policy == "exploratory":
        return min(eligible, key=lambda item: (item.purpose != "investigation", item.id))
    if policy == "chaotic_legal":
        return eligible[-1]
    if policy in {"avoidant", "distrustful"}:
        return next((item for item in eligible if item.abort_truth_ids), eligible[-1])
    return eligible[0]


def _result_for(storylet, state: RuntimeState, policy: str) -> TurnResult | None:
    package = state.narrative_package
    if package is None:
        return None
    if policy == "avoidant" and storylet.abort_truth_ids:
        realization = StoryletRealization(
            storylet_id=storylet.id,
            realization_mode=storylet.realization_modes[0],
            abort_evidence=(storylet.abort_truth_ids[0],),
        )
    else:
        consequence_ids = tuple(
            consequence.id
            for consequence in package.consequences
            if consequence.id in storylet.consequence_ids
            and storylet.completion_truth_id in consequence.assert_truth_ids
        )
        if not consequence_ids:
            return None
        realization = StoryletRealization(
            storylet_id=storylet.id,
            realization_mode=storylet.realization_modes[0],
            consequence_ids=consequence_ids,
            completion_evidence=(storylet.completion_truth_id,),
        )
    return TurnResult(narration="Deterministic authoring simulation.", storylet_realization=realization)


def _known_truths(state: RuntimeState) -> set[str]:
    return {fact.object for fact in state.facts.matching("knows", "player") if fact.object is not None}


def _pressure(state: RuntimeState) -> int:
    values = [fact.value for fact in state.facts.matching("scene_pressure", "scene") if fact.value is not None]
    return int(values[0]) if values else 0


def _climax_truths(package) -> tuple[str, ...]:
    return package.dramatic_spine.completion_truth_ids if package.dramatic_spine is not None else ()


def _metrics(cases: tuple[SimulationCase, ...]) -> SimulationMetrics:
    selections = [storylet_id for case in cases for storylet_id in case.selected_storylet_ids]
    counts = Counter(selections)
    total = len(selections)
    blocked = sum(case.blocked_actions for case in cases)
    reached = [case for case in cases if case.reached_climax]
    paths = {case.selected_storylet_ids for case in reached}
    return SimulationMetrics(
        ending_reachability=len(reached) / len(cases),
        dead_ends=sum(case.blocked_actions > 0 for case in cases),
        storylet_reuse=sum(count - 1 for count in counts.values()),
        selection_diversity=len(counts) / total if total else 0,
        pressure_trajectories=tuple(case.pressure_trajectory for case in cases),
        blocked_action_rate=blocked / (total + blocked),
        distinct_paths_to_climax=len(paths),
        protected_revelation_violations=0,
    )
