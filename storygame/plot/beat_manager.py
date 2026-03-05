from __future__ import annotations

from dataclasses import dataclass

from storygame.plot.freytag import get_phase


@dataclass(frozen=True)
class Beat:
    type: str
    tags: tuple[str, ...]
    required_entities: tuple[str, ...] = ()


_PHASE_BEATS: dict[str, tuple[str, ...]] = {
    "exposition": ("hook", "inciting_incident", "goal_reveal"),
    "rising_action": ("complication", "revelation", "escalation", "setback"),
    "climax": ("confrontation", "irreversible_choice"),
    "falling_action": ("consequence", "escape", "unraveling"),
    "resolution": ("closure", "epilogue"),
}


def _allowed_beats(progress: float) -> tuple[str, ...]:
    phase = get_phase(progress)
    return _PHASE_BEATS[phase]


def select_beat(state, rng) -> Beat:
    candidates = list(_allowed_beats(state.progress))
    if len(state.beat_history) >= 1:
        last_beat = state.beat_history[-1]
        candidates = [candidate for candidate in candidates if candidate != last_beat] or candidates
    index = rng.randrange(len(candidates))
    selection = candidates[index]
    return Beat(type=selection, tags=(selection, get_phase(state.progress)))
