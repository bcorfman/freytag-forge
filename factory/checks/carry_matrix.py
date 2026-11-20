"""Search every carried entry state for a path to an earned scene exit."""

from __future__ import annotations

import argparse
import json
import multiprocessing
import os
import sys
import time
from collections.abc import Mapping, Sequence
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from storygame.personas import (
    PERSONAS,
    _legacy_package,
    _resolution_complete,
    _ScriptedProvider,
    _select_thorough,
)
from storygame.runtime.contracts import RuntimeContractError
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.facts import Fact
from storygame.runtime.state import RuntimeSnapshot, RuntimeState
from storygame.runtime.validation import ProposalValidationError
from storygame.story_package.loader import load_story_package
from storygame.story_package.models import ActivationRule, FactPredicate, StoryPackage

WORLD_STATE_PREDICATES = (
    "wk_parent",
    "wk_relation",
    "wk_place_text",
    "wk_hidden",
    "world_effects_applied",
)
# Measured on 2026-11-20: the largest successful search used 13 new points;
# three times that measurement, with the required minimum of 30, is 39.
DEFAULT_SEARCH_BUDGET = 39
_EXIT_CAUSES = {"forced", "timer"}


class CarryMatrixTooLarge(RuntimeError):
    """Raised when a scene's merged entry-state set exceeds its safety cap."""

    def __init__(self, scene: str, count: int) -> None:
        self.scene = scene
        self.count = count
        super().__init__(f"carry matrix has more than the allowed number of states in {scene}: {count}")


@dataclass(frozen=True)
class StuckCell:
    scene: str
    entry_index: int
    choices: tuple[str, ...]
    label: str
    reason: str
    turns: int
    carried: tuple[str, ...]


@dataclass
class CarryReport:
    mode: str
    entry_states: dict[str, int]
    branches: dict[str, int]
    searches: int
    turns: int
    memo_hits: int
    stuck: list[StuckCell]
    seconds: float
    seconds_by_scene: dict[str, float]
    search_budget: int = DEFAULT_SEARCH_BUDGET
    max_search_points: int = 0
    not_run: list[str] = field(default_factory=list)
    entry_choices: dict[str, tuple[tuple[str, ...], ...]] = field(default_factory=dict, repr=False)

    def lines(self) -> list[str]:
        lines = [
            f"STUCK {cell.scene} entry#{cell.entry_index} after "
            f"{' + '.join(cell.choices) if cell.choices else 'default path'} {cell.label} {cell.reason} "
            f"at turn {cell.turns}; carried: {', '.join(cell.carried)}"
            for cell in self.stuck
        ]
        if self.not_run:
            stopped_after = self.stuck[0].scene if self.stuck else "unknown"
            lines.append(f"NOT RUN {' '.join(self.not_run)} (stopped after stuck {stopped_after})")
        return lines


@dataclass(frozen=True)
class _Entry:
    snapshot: RuntimeSnapshot
    choices: tuple[str, ...]


@dataclass(frozen=True)
class _Point:
    snapshot: RuntimeSnapshot
    handoff_ids: tuple[tuple[str, ...], ...] = ()


@dataclass(frozen=True)
class _Step:
    candidate_id: str | None

    @property
    def label(self) -> str:
        return self.candidate_id if self.candidate_id is not None else "wait"


@dataclass(frozen=True)
class _PathStep:
    point: _Point
    step: _Step


@dataclass(frozen=True)
class _MemoGood:
    exit_point: _Point
    path: tuple[_PathStep, ...]


@dataclass(frozen=True)
class _SearchResult:
    outcome: str
    path: tuple[_PathStep, ...] = ()
    exit_point: _Point | None = None
    turns: int = 0
    points_used: int = 0


@dataclass(frozen=True)
class _Applied:
    outcome: str
    point: _Point | None
    turns: int


@dataclass
class _WorkerStats:
    searches: int = 0
    turns: int = 0
    memo_hits: int = 0
    max_search_points: int = 0


def _stats_since(before: _WorkerStats, after: _WorkerStats) -> _WorkerStats:
    return _WorkerStats(
        after.searches - before.searches,
        after.turns - before.turns,
        after.memo_hits - before.memo_hits,
        after.max_search_points,
    )


@dataclass(frozen=True)
class _MainResult:
    entry: _Entry
    result: _SearchResult
    stats: _WorkerStats


@dataclass(frozen=True)
class _DeviationResult:
    label: str
    outcome: str
    turns: int
    exit_point: _Point | None = None


@dataclass(frozen=True)
class _DeviationBatchResult:
    results: tuple[_DeviationResult, ...]
    stats: _WorkerStats


def _model_scene(value: BaseModel) -> str | None:
    for name in ("source_scene_id", "scene_id"):
        scene = getattr(value, name, None)
        if isinstance(scene, str):
            return scene
    metadata = getattr(value, "metadata", None)
    scene = getattr(metadata, "scene_id", None)
    return scene if isinstance(scene, str) else None


def _read_map(package: StoryPackage) -> dict[str | None, set[str]]:
    reads: dict[str | None, set[str]] = {}

    def add(scene: str | None, fact_ids: Sequence[str]) -> None:
        reads.setdefault(scene, set()).update(fact_ids)

    def visit(value: Any, enclosing_scene: str | None = None, reads_enabled: bool = True) -> None:
        if isinstance(value, BaseModel):
            scene = _model_scene(value) or enclosing_scene
            if reads_enabled and isinstance(value, FactPredicate):
                add(scene, (value.fact_id,))
            elif reads_enabled and isinstance(value, ActivationRule):
                add(scene, (*value.all_facts_true, *value.any_of))
            for field_name in type(value).model_fields:
                visit(getattr(value, field_name), scene, reads_enabled and field_name != "effects")
            return
        if isinstance(value, Mapping):
            for key, item in value.items():
                visit(key, enclosing_scene, reads_enabled)
                visit(item, enclosing_scene, reads_enabled)
            return
        if isinstance(value, (tuple, list, set, frozenset)):
            for item in value:
                visit(item, enclosing_scene, reads_enabled)

    visit(package)
    return reads


def read_fact_ids(package: StoryPackage) -> frozenset[str]:
    return frozenset(fact_id for fact_ids in _read_map(package).values() for fact_id in fact_ids)


def reads_by_scene(package: StoryPackage) -> dict[str | None, frozenset[str]]:
    return {scene: frozenset(fact_ids) for scene, fact_ids in _read_map(package).items()}


def forward_reads(package: StoryPackage, scene: str) -> frozenset[str]:
    """Return reads in this scene and later scenes, plus scene-agnostic reads."""

    order = [window.scene_id for window in package.pacing.scenes]
    try:
        start = order.index(scene)
    except ValueError as error:
        raise ValueError(f"unknown carry-matrix scene: {scene}") from error
    by_scene = reads_by_scene(package)
    return frozenset(set(by_scene.get(None, ())).union(*(by_scene.get(scene_id, ()) for scene_id in order[start:])))


def _flag_value(fact: Fact) -> str | None:
    return fact.value if fact.value is not None else fact.object


def _sort_key(value: tuple[object, ...]) -> tuple[str, ...]:
    return tuple("" if item is None else str(item) for item in value)


def state_key(state: RuntimeState, read_ids: frozenset[str]) -> tuple:
    """Keep true forward-read flags and all world-model assertions."""

    keys = [
        fact.key
        for fact in state.facts.asserted
        if (fact.predicate in read_ids and _flag_value(fact) == "true") or fact.predicate in WORLD_STATE_PREDICATES
    ]
    return tuple(sorted(keys, key=_sort_key))


def _true_read_fact_ids(state: RuntimeState, read_ids: frozenset[str]) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                fact.predicate
                for fact in state.facts.asserted
                if fact.predicate in read_ids and _flag_value(fact) == "true"
            }
        )
    )


def _state_from_snapshot(package: StoryPackage, snapshot: RuntimeSnapshot) -> RuntimeState:
    state = RuntimeState(package=package, current_scene_id=snapshot.current_scene_id, phase=snapshot.phase)
    state.restore_snapshot(snapshot)
    return state


def _transition_targets(package: StoryPackage) -> dict[str, str]:
    return {transition.id: transition.target_scene_id for transition in package.pacing.transitions}


def _current_scene_records(state: RuntimeState, targets: Mapping[str, str]) -> tuple:
    records = state.turn_records
    entry_record = -1
    for index, record in enumerate(records):
        if record.transition_id is not None and targets.get(record.transition_id) == state.current_scene_id:
            entry_record = index
    return records[entry_record + 1 :]


def _identity_key(state: RuntimeState, scene: str, read_ids: frozenset[str], targets: Mapping[str, str]) -> tuple:
    """Identity used by SEARCH; the record suffix mirrors what later turns read."""

    entered = state.scene_entered_at_turn
    records = _current_scene_records(state, targets)
    recent = tuple(
        (record.id, tuple(record.reveal_ids), tuple(record.deadline_event_ids), record.transition_id)
        for record in records[-2:]
    )
    earlier = records[:-2]
    reveal_ids = tuple(sorted({item for record in earlier for item in record.reveal_ids}))
    deadline_ids = tuple(sorted({item for record in earlier for item in record.deadline_event_ids}))
    cue_stages = tuple(
        sorted(
            (stage.fact_id, stage.stage, stage.last_turn - entered, stage.visit_entered_at - entered)
            for stage in state.cue_stages
        )
    )
    return (
        state.turn_index - entered,
        state_key(state, read_ids),
        tuple(sorted(state.active_event_ids)),
        tuple(sorted(state.fired_event_ids)),
        cue_stages,
        state.staged_cue_fact_id,
        state.staged_cue_stage,
        tuple(state.staged_handoff_fact_ids),
        tuple(state.delivered_cue_ids),
        recent,
        reveal_ids,
        deadline_ids,
        scene,
    )


class _SearchWorker:
    def __init__(self, package: StoryPackage, scene: str, read_ids: frozenset[str], search_budget: int) -> None:
        self.package = package
        self.scene = scene
        self.read_ids = read_ids
        self.search_budget = search_budget
        self.targets = _transition_targets(package)
        self.good: dict[tuple, _MemoGood] = {}
        self.bad: set[tuple] = set()
        self.stats = _WorkerStats()
        self._state: RuntimeState | None = None
        self._provider: _ScriptedProvider | None = None
        self._engine: RuntimeEngine | None = None

    def _restore(self, point: _Point) -> None:
        if self._state is None:
            self._state = _state_from_snapshot(self.package, point.snapshot)
            self._provider = _ScriptedProvider(self.package, self._state)
            self._engine = RuntimeEngine(self._state, self._provider)
        else:
            self._state.restore_snapshot(point.snapshot)
        assert self._provider is not None
        self._provider.handoff_ids = list(point.handoff_ids)

    def _point(self) -> _Point:
        assert self._state is not None and self._provider is not None
        return _Point(self._state.snapshot(), tuple(self._provider.handoff_ids))

    def _ordered_steps(self, point: _Point) -> tuple[_Step, ...]:
        self._restore(point)
        assert self._engine is not None and self._state is not None
        self._engine._activate_pacing()
        offered = tuple(self._engine.projector.project(self._state, "player", "").candidates)
        selected = _select_thorough(self.package, self._state, offered)
        ids = [candidate.id for candidate in offered]
        ordered: list[str | None] = []
        if selected is not None:
            ordered.append(selected)
        ordered.extend(candidate_id for candidate_id in ids if candidate_id != selected)
        ordered.append(None)
        return tuple(_Step(candidate_id) for candidate_id in ordered)

    def _apply(self, point: _Point, step: _Step) -> _Applied:
        self._restore(point)
        assert self._engine is not None and self._provider is not None and self._state is not None
        before_turn = point.snapshot.turn_index
        self._engine._activate_pacing()
        offered = {candidate.id for candidate in self._engine.projector.project(self._state, "player", "").candidates}
        if step.candidate_id is not None and step.candidate_id not in offered:
            return _Applied("rejected", None, self._scene_turns(point))
        self._provider.selected = (step.candidate_id,) if step.candidate_id is not None else ()
        try:
            self._engine.turn(PERSONAS["thorough"])
        except (ProposalValidationError, RuntimeContractError):
            self._restore(point)
            return _Applied("rejected", None, self._scene_turns(point))
        if self._state.current_scene_id == self.scene and self._state.turn_index == before_turn:
            self._restore(point)
            return _Applied("rejected", None, self._scene_turns(point))
        self.stats.turns += 1
        cause = self._engine.last_attempt.transition_cause if self._engine.last_attempt is not None else "none"
        if self._state.current_scene_id != self.scene or (
            self.scene == self.package.pacing.scenes[-1].scene_id
            and (_resolution_complete(self._state) or self._state.story_complete)
        ):
            outcome = cause if cause in _EXIT_CAUSES else "earned"
        else:
            outcome = "continue"
        return _Applied(outcome, self._point(), self._scene_turns(self._point()))

    @staticmethod
    def _scene_turns(point: _Point) -> int:
        return point.snapshot.turn_index - point.snapshot.scene_entered_at_turn

    def _remember(self, path: tuple[_PathStep, ...], exit_point: _Point) -> None:
        for index, path_step in enumerate(path):
            key = _identity_key(self._state_from_point(path_step.point), self.scene, self.read_ids, self.targets)
            self.good.setdefault(key, _MemoGood(exit_point, path[index:]))

    def _state_from_point(self, point: _Point) -> RuntimeState:
        return _state_from_snapshot(self.package, point.snapshot)

    def search(self, start: _Point) -> _SearchResult:
        self.stats.searches += 1
        budget_used = 0

        def visit(point: _Point, active: set[tuple]) -> _SearchResult:
            nonlocal budget_used
            state = self._state_from_point(point)
            key = _identity_key(state, self.scene, self.read_ids, self.targets)
            if key in self.good:
                self.stats.memo_hits += 1
                memo = self.good[key]
                return _SearchResult("earned", memo.path, memo.exit_point, self._scene_turns(point), budget_used)
            if key in self.bad:
                self.stats.memo_hits += 1
                return _SearchResult("no_path", turns=self._scene_turns(point), points_used=budget_used)
            if key in active:
                return _SearchResult("no_path", turns=self._scene_turns(point), points_used=budget_used)
            if budget_used >= self.search_budget:
                return _SearchResult("budget", turns=self._scene_turns(point), points_used=budget_used)
            budget_used += 1
            active = {*active, key}
            limit = next(
                window.handoff_after_turns + 3 for window in self.package.pacing.scenes if window.scene_id == self.scene
            )
            if self._scene_turns(point) >= limit:
                self.bad.add(key)
                return _SearchResult("no_path", turns=self._scene_turns(point), points_used=budget_used)
            saw_budget = False
            for step in self._ordered_steps(point):
                applied = self._apply(point, step)
                if applied.outcome == "rejected":
                    continue
                path_step = _PathStep(point, step)
                if applied.outcome == "earned":
                    assert applied.point is not None
                    path = (path_step,)
                    self._remember(path, applied.point)
                    return _SearchResult("earned", path, applied.point, applied.turns, budget_used)
                if applied.outcome in _EXIT_CAUSES:
                    continue
                assert applied.point is not None
                result = visit(applied.point, active)
                if result.outcome == "earned":
                    path = (path_step, *result.path)
                    self._remember(path, result.exit_point)  # type: ignore[arg-type]
                    return _SearchResult("earned", path, result.exit_point, result.turns, budget_used)
                saw_budget = saw_budget or result.outcome == "budget"
            if saw_budget:
                return _SearchResult("budget", turns=self._scene_turns(point), points_used=budget_used)
            self.bad.add(key)
            return _SearchResult("no_path", turns=self._scene_turns(point), points_used=budget_used)

        result = visit(start, set())
        if result.outcome == "earned":
            self.stats.max_search_points = max(self.stats.max_search_points, result.points_used)
        return result

    def deviations(self, path: tuple[_PathStep, ...]) -> tuple[_DeviationResult, ...]:
        results: list[_DeviationResult] = []
        for path_step in path:
            point_turn = self._scene_turns(path_step.point)
            label_prefix = f"t{point_turn}"
            for step in self._ordered_steps(path_step.point):
                if step == path_step.step:
                    continue
                label = f"{label_prefix}:{step.label}"
                applied = self._apply(path_step.point, step)
                if applied.outcome == "rejected":
                    continue
                if applied.outcome == "earned":
                    results.append(_DeviationResult(label, "earned", applied.turns, applied.point))
                    continue
                if applied.outcome in _EXIT_CAUSES:
                    results.append(_DeviationResult(label, applied.outcome, applied.turns))
                    continue
                assert applied.point is not None
                search = self.search(applied.point)
                results.append(_DeviationResult(label, search.outcome, search.turns, search.exit_point))
        return tuple(results)


_WORKER_PACKAGE: StoryPackage | None = None


def _init_worker() -> None:
    """Keep the package inherited from the parent fork; do not pickle it again."""


def _package_for_worker() -> StoryPackage:
    if _WORKER_PACKAGE is None:
        raise RuntimeError("carry-matrix worker was not initialized")
    return _WORKER_PACKAGE


def _run_main_worker(spec: tuple[str, frozenset[str], int, tuple[_Entry, ...]]) -> tuple[_MainResult, ...]:
    scene, read_ids, search_budget, entries = spec
    worker = _SearchWorker(_package_for_worker(), scene, read_ids, search_budget)
    results: list[_MainResult | None] = [None] * len(entries)
    # A carried deviation usually supplies more of the scene's forward-read
    # facts than the default entry.  Prove those entries first within a worker
    # so their good-point memo can accelerate the default entry in the same
    # process; restore the original order for report indices.
    ordered = sorted(enumerate(entries), key=lambda item: len(item[1].choices), reverse=True)
    for result_index, entry in ordered:
        before = _WorkerStats(worker.stats.searches, worker.stats.turns, worker.stats.memo_hits)
        result = worker.search(_Point(entry.snapshot))
        results[result_index] = _MainResult(entry, result, _stats_since(before, worker.stats))
    return tuple(result for result in results if result is not None)


def _run_deviation_worker(
    spec: tuple[str, frozenset[str], int, tuple[_PathStep, ...]],
) -> _DeviationBatchResult:
    scene, read_ids, search_budget, path = spec
    worker = _SearchWorker(_package_for_worker(), scene, read_ids, search_budget)
    return _DeviationBatchResult(worker.deviations(path), worker.stats)


def _run_tasks(pool: ProcessPoolExecutor | None, function, specs: Sequence):
    if pool is None:
        return [function(spec) for spec in specs]
    return list(pool.map(function, specs))


def _chunks(values: Sequence, count: int) -> list[tuple]:
    size = max(1, (len(values) + count - 1) // count)
    return [tuple(values[index : index + size]) for index in range(0, len(values), size)]


def _entry_flags(package: StoryPackage, entry: _Entry, read_ids: frozenset[str]) -> tuple[str, ...]:
    return _true_read_fact_ids(_state_from_snapshot(package, entry.snapshot), read_ids)


def carry_matrix(
    package: StoryPackage,
    *,
    scenes: list[str] | None = None,
    mode: str = "one_branch",
    search_budget: int | None = None,
    max_states_per_scene: int | None = None,
    workers: int | None = None,
) -> CarryReport:
    """Run bounded DFS searches and carry every earned exit into later scenes."""

    started = time.perf_counter()
    if mode not in {"one_branch", "pairwise"}:
        raise ValueError(f"unknown carry-matrix mode: {mode}")
    budget = DEFAULT_SEARCH_BUDGET if search_budget is None else search_budget
    if budget < 1:
        raise ValueError("search_budget must be positive")
    cap = max_states_per_scene if max_states_per_scene is not None else (200 if mode == "one_branch" else 2000)
    if cap < 1:
        raise ValueError("max_states_per_scene must be positive")
    worker_count = workers if workers is not None else min(16, os.cpu_count() or 1)
    if worker_count < 1:
        raise ValueError("workers must be positive")

    played = _legacy_package(package)
    global _WORKER_PACKAGE
    _WORKER_PACKAGE = played
    order = [window.scene_id for window in played.pacing.scenes]
    requested = order if scenes is None else list(dict.fromkeys(scenes))
    unknown = [scene for scene in requested if scene not in order]
    if unknown:
        raise ValueError(f"unknown carry-matrix scene(s): {', '.join(unknown)}")
    selected = [scene for scene in order if scene in requested]
    last_index = max((order.index(scene) for scene in selected), default=-1)
    walked = order[: last_index + 1]
    reads = reads_by_scene(played)
    forward = {
        scene: frozenset(
            set(reads.get(None, ())).union(*(reads.get(later, ()) for later in order[order.index(scene) :]))
        )
        for scene in walked
    }
    entries: dict[str, list[_Entry]] = {scene: [] for scene in walked}
    indexes: dict[str, dict[tuple, int]] = {scene: {} for scene in walked}
    branches = {scene: 0 for scene in walked}
    if walked:
        initial = RuntimeState.bootstrap(played).snapshot()
        key = state_key(_state_from_snapshot(played, initial), forward[walked[0]])
        entries[walked[0]].append(_Entry(initial, ()))
        indexes[walked[0]][key] = 0
        branches[walked[0]] = 1

    def add_entry(scene: str, point: _Point, choices: tuple[str, ...]) -> None:
        if scene not in indexes:
            return
        branches[scene] += 1
        entry = _Entry(point.snapshot, choices)
        key = state_key(_state_from_snapshot(played, point.snapshot), forward[scene])
        existing = indexes[scene].get(key)
        if existing is not None:
            if len(choices) < len(entries[scene][existing].choices):
                entries[scene][existing] = _Entry(entries[scene][existing].snapshot, choices)
            return
        entries[scene].append(entry)
        indexes[scene][key] = len(entries[scene]) - 1
        if len(entries[scene]) > cap:
            raise CarryMatrixTooLarge(scene, len(entries[scene]))

    stuck: list[StuckCell] = []
    not_run: list[str] = []
    seconds_by_scene: dict[str, float] = {}
    searches = turns = memo_hits = max_search_points = 0
    searches_by_scene: dict[str, int] = {}
    turns_by_scene: dict[str, int] = {}
    memo_hits_by_scene: dict[str, int] = {}
    context = multiprocessing.get_context("fork") if "fork" in multiprocessing.get_all_start_methods() else None
    pool = (
        ProcessPoolExecutor(max_workers=worker_count, mp_context=context, initializer=_init_worker)
        if context is not None and worker_count > 1
        else None
    )
    try:
        for scene in walked:
            scene_started = time.perf_counter()
            current_entries = tuple(entries[scene])
            read_ids = forward[scene]
            # Entry states are independent; let every available worker take a batch so
            # expensive scene turns overlap instead of serializing behind four batches.
            main_batch_count = min(worker_count, max(1, len(current_entries)))
            scene_searches = scene_turns = scene_memo_hits = 0
            main_specs = [(scene, read_ids, budget, chunk) for chunk in _chunks(current_entries, main_batch_count)]
            main_results = [main for batch in _run_tasks(pool, _run_main_worker, main_specs) for main in batch]
            deviation_specs: list[tuple[str, frozenset[str], int, tuple[_PathStep, ...]]] = []
            deviation_meta: list[tuple[int, _Entry, tuple[_PathStep, ...]]] = []
            for entry_index, main in enumerate(main_results):
                scene_searches += main.stats.searches
                scene_turns += main.stats.turns
                scene_memo_hits += main.stats.memo_hits
                max_search_points = max(max_search_points, main.stats.max_search_points)
                flags = _entry_flags(played, main.entry, read_ids)
                if main.result.outcome != "earned":
                    stuck.append(
                        StuckCell(
                            scene,
                            entry_index,
                            main.entry.choices,
                            "main",
                            main.result.outcome,
                            main.result.turns,
                            flags,
                        )
                    )
                    continue
                assert main.result.exit_point is not None
                if order.index(scene) + 1 < len(walked):
                    add_entry(order[order.index(scene) + 1], main.result.exit_point, main.entry.choices)
                if (not main.entry.choices or mode == "pairwise") and main.result.path:
                    paths = [main.result.path]
                    if worker_count > 1:
                        batch_count = min(worker_count, max(2, (len(main.result.path) + 3) // 4))
                        paths = list(_chunks(main.result.path, batch_count))
                    for path in paths:
                        deviation_specs.append((scene, read_ids, budget, path))
                        deviation_meta.append((entry_index, main.entry, path))
            deviation_results = _run_tasks(pool, _run_deviation_worker, deviation_specs)
            for (entry_index, entry, _), batch in zip(deviation_meta, deviation_results, strict=True):
                scene_searches += batch.stats.searches
                scene_turns += batch.stats.turns
                scene_memo_hits += batch.stats.memo_hits
                max_search_points = max(max_search_points, batch.stats.max_search_points)
                flags = _entry_flags(played, entry, read_ids)
                for deviation in batch.results:
                    if deviation.outcome == "earned":
                        if order.index(scene) + 1 < len(walked):
                            assert deviation.exit_point is not None
                            choices = (*entry.choices, f"{scene}/{deviation.label}")
                            if len(choices) <= 2:
                                add_entry(order[order.index(scene) + 1], deviation.exit_point, choices)
                        continue
                    stuck.append(
                        StuckCell(
                            scene,
                            entry_index,
                            entry.choices,
                            deviation.label,
                            deviation.outcome,
                            deviation.turns,
                            flags,
                        )
                    )
            searches += scene_searches
            turns += scene_turns
            memo_hits += scene_memo_hits
            searches_by_scene[scene] = scene_searches
            turns_by_scene[scene] = scene_turns
            memo_hits_by_scene[scene] = scene_memo_hits
            seconds_by_scene[scene] = time.perf_counter() - scene_started
            if stuck and mode == "one_branch":
                not_run = walked[walked.index(scene) + 1 :]
                break
    finally:
        if pool is not None:
            pool.shutdown()

    report = CarryReport(
        mode=mode,
        entry_states={scene: len(entries[scene]) for scene in walked},
        branches=branches,
        searches=searches,
        turns=turns,
        memo_hits=memo_hits,
        stuck=stuck,
        seconds=time.perf_counter() - started,
        seconds_by_scene=seconds_by_scene,
        search_budget=budget,
        max_search_points=max_search_points,
        not_run=not_run,
        entry_choices={scene: tuple(entry.choices for entry in entries[scene]) for scene in walked},
    )
    report._searches_by_scene = searches_by_scene
    report._turns_by_scene = turns_by_scene
    report._memo_hits_by_scene = memo_hits_by_scene
    return report


def _json_report(report: CarryReport) -> dict[str, object]:
    return {
        "mode": report.mode,
        "entry_states": report.entry_states,
        "branches": report.branches,
        "searches": report.searches,
        "turns": report.turns,
        "memo_hits": report.memo_hits,
        "stuck": [asdict(cell) for cell in report.stuck],
        "seconds": report.seconds,
        "seconds_by_scene": report.seconds_by_scene,
        "search_budget": report.search_budget,
        "max_search_points": report.max_search_points,
        "not_run": report.not_run,
        "entry_choices": {
            scene: [list(choice) for choice in choices] for scene, choices in report.entry_choices.items()
        },
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--story", default="data/stories/continuity-initiative")
    parser.add_argument("--scene", action="append", dest="scenes")
    parser.add_argument("--mode", choices=("one_branch", "pairwise"), default="one_branch")
    parser.add_argument("--search-budget", type=int)
    parser.add_argument("--workers", type=int)
    parser.add_argument("--json", dest="json_path")
    args = parser.parse_args(argv)
    try:
        package = load_story_package(Path(args.story))
        report = carry_matrix(
            package,
            scenes=args.scenes,
            mode=args.mode,
            search_budget=args.search_budget,
            workers=args.workers,
        )
    except CarryMatrixTooLarge as error:
        print(str(error), file=sys.stderr)
        return 2
    except Exception as error:
        print(str(error) or error.__class__.__name__, file=sys.stderr)
        return 2

    for scene, entry_count in report.entry_states.items():
        print(
            f"{scene}: {entry_count} entry states, {getattr(report, '_searches_by_scene', {}).get(scene, 0)} searches, "
            f"{getattr(report, '_turns_by_scene', {}).get(scene, 0)} turns, "
            f"{sum(cell.scene == scene for cell in report.stuck)} stuck, "
            f"{report.seconds_by_scene.get(scene, 0.0):.3f}s",
            flush=True,
        )
    for line in report.lines():
        print(line, flush=True)
    print(
        f"TOTAL entry_states={sum(report.entry_states.values())} searches={report.searches} turns={report.turns} "
        f"memo_hits={report.memo_hits} search_budget={report.search_budget} "
        f"max_search_points={report.max_search_points} stuck={len(report.stuck)} seconds={report.seconds:.3f}",
        flush=True,
    )
    if args.json_path:
        Path(args.json_path).write_text(json.dumps(_json_report(report), indent=2) + "\n", encoding="utf-8")
    return 1 if report.stuck else 0


if __name__ == "__main__":
    raise SystemExit(main())
