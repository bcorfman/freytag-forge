from __future__ import annotations

from storygame.engine.state import Event, GameState
from storygame.plot.freytag import get_phase

TARGET_TENSION = {
    "exposition": 0.25,
    "rising_action": 0.45,
    "climax": 0.82,
    "falling_action": 0.6,
    "resolution": 0.3,
}


def _clamp(value: float) -> float:
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


def apply_tension_events(state: GameState, events: list[Event]) -> GameState:
    delta = sum(event.delta_tension for event in events)
    target = TARGET_TENSION.get(get_phase(state.progress), 0.35)
    smoothed = (state.tension + delta) * 0.65 + target * 0.35
    state.tension = _clamp(round(smoothed, 6))
    return state
