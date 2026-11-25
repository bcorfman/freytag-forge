"""Replay the clock-owned portion of a runtime turn on an isolated state copy."""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any

from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.state import TurnDelivery


@dataclass(frozen=True)
class PacingReplay:
    """Pacing events and knowledge made deliverable by a null-action turn."""

    fired_event_ids: tuple[str, ...]
    null_grounding_ids: tuple[str, ...]


def replay_pacing(engine: RuntimeEngine) -> PacingReplay:
    """Replay both pacing passes for the next turn without touching the live engine."""

    live_state = engine.state
    scratch_state = copy.deepcopy(live_state)
    scratch_state.turn_index += 1
    scratch_state.last_turn_delivery = TurnDelivery()
    scratch_engine = RuntimeEngine(
        scratch_state,
        engine.provider,
        projector=engine.projector,
        refusal_mode=engine.refusal_mode,
    )
    scratch_engine._activate_pacing(realize_complications=True, defer_guarded_events=True)
    scratch_engine._activate_pacing(realize_complications=True)

    fired_event_ids = tuple(
        event.id
        for event in live_state.package.pacing.events
        if event.id not in live_state.fired_event_ids and event.id in scratch_state.fired_event_ids
    )
    null_grounding_ids = _delivered_knowledge_ids(live_state.package.pacing.events, fired_event_ids)
    return PacingReplay(fired_event_ids=fired_event_ids, null_grounding_ids=null_grounding_ids)


def _delivered_knowledge_ids(events: Any, fired_event_ids: tuple[str, ...]) -> tuple[str, ...]:
    fired = set(fired_event_ids)
    result: list[str] = []
    for event in events:
        if event.id not in fired:
            continue
        for knowledge_id in event.delivers:
            if knowledge_id not in result:
                result.append(knowledge_id)
    return tuple(result)
