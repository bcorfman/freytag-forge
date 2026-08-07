from __future__ import annotations

from dataclasses import dataclass

from storygame.plot.beat_policy import BeatPolicy


@dataclass(frozen=True)
class Beat:
    type: str
    tags: tuple[str, ...]
    required_entities: tuple[str, ...] = ()
    selection_reason: str = ""


def select_beat(state, rng) -> Beat:
    decision = BeatPolicy().decide(state)
    return Beat(
        type=decision.beat,
        tags=(decision.beat, decision.phase),
        selection_reason=decision.selection_reason,
    )
