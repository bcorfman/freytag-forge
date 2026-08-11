"""Small, advisory pacing policy. It never selects a player action."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from storygame.authoring.contracts import Beat
from storygame.runtime.state import BeatRuntime


@dataclass(frozen=True)
class PaceDirective:
    beat_id: str
    mode: Literal["open", "nudge", "advance", "escalate", "force_consequence"]
    player_action: None = None


class PacingController:
    def directive(self, beat: Beat, *, turns_active: int, stagnant_turns: int) -> PaceDirective:
        threshold = max(turns_active, stagnant_turns)
        pacing = beat.pacing
        if threshold >= pacing.force_consequence_after:
            mode = "force_consequence"
        elif threshold >= pacing.escalate_after:
            mode = "escalate"
        elif threshold >= pacing.advance_after:
            mode = "advance"
        elif threshold >= pacing.nudge_after:
            mode = "nudge"
        else:
            mode = "open"
        return PaceDirective(beat_id=beat.id, mode=mode)

    def after_turn(self, beat: Beat, *, turns_active: int, stagnant_turns: int, material_progress: bool) -> BeatRuntime:
        return BeatRuntime(
            beat_id=beat.id,
            turns_active=turns_active + 1,
            stagnant_turns=0 if material_progress else stagnant_turns + 1,
        )
