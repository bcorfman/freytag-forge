from __future__ import annotations

from dataclasses import dataclass

from storygame.engine.scene_state import scene_snapshot
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

_ROLE_BEATS: dict[str, tuple[str, ...]] = {
    "orientation": ("hook", "inciting_incident", "goal_reveal"),
    "pressure": ("complication", "escalation", "setback"),
    "reveal": ("revelation", "goal_reveal"),
    "confrontation": ("confrontation", "irreversible_choice"),
    "aftermath": ("consequence", "escape", "unraveling"),
    "closure": ("closure", "epilogue"),
}


def _allowed_beats(progress: float) -> tuple[str, ...]:
    phase = get_phase(progress)
    return _PHASE_BEATS[phase]


def select_beat(state, rng) -> Beat:
    scene = scene_snapshot(state)
    phase = str(scene["beat_phase"]) or get_phase(state.progress)
    role = str(scene["beat_role"])
    candidates = list(_PHASE_BEATS.get(phase, _allowed_beats(state.progress)))
    preferred = [candidate for candidate in _ROLE_BEATS.get(role, ()) if candidate in candidates]
    if preferred:
        candidates = preferred
    if len(state.beat_history) >= 1:
        last_beat = state.beat_history[-1]
        candidates = [candidate for candidate in candidates if candidate != last_beat] or candidates
    index = rng.randrange(len(candidates))
    selection = candidates[index]
    return Beat(type=selection, tags=(selection, phase))
