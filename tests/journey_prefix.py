"""Shared default-policy prefixes for the whole-game journey tests."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from storygame.personas import (
    PERSONAS,
    _legacy_package,
    _resolution_complete,
    _ScriptedProvider,
    _select_thorough,
    _turn_cap,
)
from storygame.runtime.contracts import RuntimeContractError
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.state import RuntimeSnapshot, RuntimeState
from storygame.runtime.validation import ProposalValidationError
from storygame.story_package.loader import load_story_package

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))
PLAYED = _legacy_package(PACKAGE)


@dataclass(frozen=True)
class PrefixCheckpoint:
    snapshot: RuntimeSnapshot
    picked: tuple[str, ...]
    forced_exits: tuple[tuple[str, str], ...]
    scenes: tuple[str, ...]
    entry_texts: tuple[str, ...]
    provider_selected: tuple[str, ...]
    provider_handoff_ids: tuple[tuple[str, ...], ...]
    default_selection: str | None


@dataclass(frozen=True)
class DefaultWalk:
    checkpoints: tuple[PrefixCheckpoint, ...]
    final_snapshot: RuntimeSnapshot
    picked: tuple[str, ...]
    forced_exits: tuple[tuple[str, str], ...]
    scenes: tuple[str, ...]
    entry_texts: tuple[str, ...]


@dataclass
class JourneyRun:
    state: RuntimeState
    picked: list[str]
    forced_exits: list[tuple[str, str]]
    scenes: list[str]
    entry_texts: list[str]


def _siblings() -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for item in PLAYED.knowledge.knowledge:
        if item.source.storylet_id:
            result.setdefault(item.source.storylet_id, []).append(item.id)
    return result


def _blocked_for(preferred: tuple[str, ...]) -> set[str]:
    siblings = _siblings()
    blocked = {
        sibling
        for item_id in preferred
        for sibling in siblings[PLAYED.knowledge_indexes.by_id[item_id].source.storylet_id]
        if sibling not in preferred
    }
    recovery_ids = {
        item.id
        for item in PLAYED.knowledge.knowledge
        if item.source.storylet_id
        in {incident.recovery_storylet_id for incident in PLAYED.incidents if incident.recovery_storylet_id}
    }
    if set(preferred) & recovery_ids:
        for incident in PLAYED.incidents:
            if incident.scene_id != "1C":
                continue
            blocked.update(
                item.id
                for item in PLAYED.knowledge.knowledge
                if item.source.storylet_id in {outcome.storylet_id for outcome in incident.outcomes}
            )
    return blocked


def _offered(engine: RuntimeEngine, state: RuntimeState, blocked: set[str]):
    engine._activate_pacing()
    return tuple(
        candidate
        for candidate in engine.projector.project(state, "player", "").candidates
        if candidate.id not in blocked
    )


def _turn(
    engine: RuntimeEngine,
    provider: _ScriptedProvider,
    state: RuntimeState,
    picked: list[str],
    forced_exits: list[tuple[str, str]],
    scenes: list[str],
    entry_texts: list[str],
    preferred: tuple[str, ...],
    blocked: set[str],
    offered=None,
) -> None:
    if offered is None:
        offered = _offered(engine, state, blocked)
    wanted = next((item_id for item_id in preferred if any(c.id == item_id for c in offered)), None)
    selected = wanted or _select_thorough(PLAYED, state, offered)
    provider.selected = (selected,) if selected else ()
    scene_before = state.current_scene_id
    try:
        result = engine.turn(PERSONAS["thorough"])
    except (ProposalValidationError, RuntimeContractError):
        provider.selected = ()
        selected = None
        engine.turn(PERSONAS["thorough"])
    if selected and engine.last_attempt.outcome == "committed":
        picked.append(selected)
    if state.current_scene_id != scene_before:
        scenes.append(state.current_scene_id)
        if state.current_scene_id == "2A":
            entry_texts.extend(segment.text for segment in result.segments)
        if engine.last_attempt.transition_cause in ("forced", "timer"):
            forced_exits.append((scene_before, engine.last_attempt.transition_cause))


@lru_cache(maxsize=1)
def _default_walk() -> DefaultWalk:
    state = RuntimeState.bootstrap(PLAYED)
    provider = _ScriptedProvider(PLAYED, state)
    engine = RuntimeEngine(state, provider)
    picked: list[str] = []
    forced_exits: list[tuple[str, str]] = []
    scenes = [state.current_scene_id]
    entry_texts: list[str] = []
    checkpoints: list[PrefixCheckpoint] = []
    for _ in range(_turn_cap(PLAYED)):
        if _resolution_complete(state):
            break
        offered = _offered(engine, state, set())
        selected = _select_thorough(PLAYED, state, offered)
        checkpoints.append(
            PrefixCheckpoint(
                snapshot=state.snapshot(),
                picked=tuple(picked),
                forced_exits=tuple(forced_exits),
                scenes=tuple(scenes),
                entry_texts=tuple(entry_texts),
                provider_selected=provider.selected,
                provider_handoff_ids=tuple(provider.handoff_ids),
                default_selection=selected,
            )
        )
        _turn(
            engine,
            provider,
            state,
            picked,
            forced_exits,
            scenes,
            entry_texts,
            (),
            set(),
            offered,
        )
    return DefaultWalk(
        checkpoints=tuple(checkpoints),
        final_snapshot=state.snapshot(),
        picked=tuple(picked),
        forced_exits=tuple(forced_exits),
        scenes=tuple(scenes),
        entry_texts=tuple(entry_texts),
    )


def run(preferred: tuple[str, ...] = ()) -> JourneyRun:
    """Replay only the suffix after the first policy decision divergence."""

    blocked = _blocked_for(preferred)
    default = _default_walk()
    # The decision replay must use the checkpoint's restored state and engine,
    # rather than constructing a new state for each candidate projection.
    state = RuntimeState.bootstrap(PLAYED)
    provider = _ScriptedProvider(PLAYED, state)
    engine = RuntimeEngine(state, provider)
    checkpoint_index = None
    for index, checkpoint in enumerate(default.checkpoints):
        state.restore_snapshot(checkpoint.snapshot)
        offered = _offered(engine, state, blocked)
        wanted = next((item_id for item_id in preferred if any(c.id == item_id for c in offered)), None)
        desired_selection = wanted or _select_thorough(PLAYED, state, offered)
        if desired_selection != checkpoint.default_selection:
            checkpoint_index = index
            break

    if checkpoint_index is None:
        state.restore_snapshot(default.final_snapshot)
        return JourneyRun(
            state=state,
            picked=list(default.picked),
            forced_exits=list(default.forced_exits),
            scenes=list(default.scenes),
            entry_texts=list(default.entry_texts),
        )

    checkpoint = default.checkpoints[checkpoint_index]
    state.restore_snapshot(checkpoint.snapshot)
    provider.selected = checkpoint.provider_selected
    provider.handoff_ids = list(checkpoint.provider_handoff_ids)
    picked = list(checkpoint.picked)
    forced_exits = list(checkpoint.forced_exits)
    scenes = list(checkpoint.scenes)
    entry_texts = list(checkpoint.entry_texts)
    for _ in range(checkpoint_index, _turn_cap(PLAYED)):
        if _resolution_complete(state):
            break
        _turn(engine, provider, state, picked, forced_exits, scenes, entry_texts, preferred, blocked)
    return JourneyRun(state, picked, forced_exits, scenes, entry_texts)
