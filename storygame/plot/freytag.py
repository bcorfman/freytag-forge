from __future__ import annotations

from enum import StrEnum


class Phase(StrEnum):
    EXPOSITION = "exposition"
    RISING = "rising_action"
    CLIMAX = "climax"
    FALLING = "falling_action"
    RESOLUTION = "resolution"


def get_phase(progress: float) -> str:
    if progress < 0.2:
        return Phase.EXPOSITION
    if progress < 0.6:
        return Phase.RISING
    if progress < 0.8:
        return Phase.CLIMAX
    if progress < 0.95:
        return Phase.FALLING
    return Phase.RESOLUTION
