"""One-call V2 turn orchestrator with one shared recovery attempt."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from storygame.runtime.context import RuntimeContext, RuntimeContextBuilder
from storygame.runtime.contracts import RuntimeFailure, TurnResult
from storygame.runtime.pacing import PacingController
from storygame.runtime.state import RuntimeEvent, RuntimeState
from storygame.runtime.validation import validate_and_commit


class TurnModel(Protocol):
    def play_turn(self, context: object, *, json_object: bool) -> object: ...


class JsonModeRejected(Exception):
    """Typed adapter signal that permits the one no-JSON-mode retry."""


@dataclass(frozen=True)
class TurnResponse:
    ok: bool
    narration: str = ""
    turn_index: int = 0
    error: RuntimeFailure | None = None


class RuntimeEngine:
    def __init__(
        self,
        state: RuntimeState,
        model: TurnModel,
        context_builder: RuntimeContextBuilder | None = None,
    ) -> None:
        self.state = state
        self.model = model
        self.context_builder = context_builder or RuntimeContextBuilder()
        self.pacing = PacingController()

    def turn(self, player_input: str) -> TurnResponse:
        context = self.context_builder.build(self.state, player_input)
        last_error: RuntimeFailure | None = None
        for json_object in (True, False):
            try:
                raw = self.model.play_turn(context, json_object=json_object)
                result = TurnResult.from_provider(raw)
                candidate = validate_and_commit(self.state, result)
                self._finalize(candidate, player_input, result, context)
                self.state = candidate
                return TurnResponse(True, result.narration, candidate.turn_index)
            except JsonModeRejected as exc:
                last_error = RuntimeFailure("JSON_MODE_REJECTED", str(exc) or "provider rejected JSON-object mode")
            except RuntimeFailure as exc:
                last_error = exc
            except Exception as exc:
                last_error = RuntimeFailure("MODEL_FAILURE", f"model request failed: {exc}")
        failure = RuntimeFailure(
            "RUNTIME_RECOVERY_EXHAUSTED",
            "turn could not be decoded or validated after one recovery",
        )
        if last_error is not None:
            failure.__cause__ = last_error
        return TurnResponse(False, error=failure)

    def _finalize(
        self,
        state: RuntimeState,
        player_input: str,
        result: TurnResult,
        context: RuntimeContext,
    ) -> None:
        for beat in state.active_beats:
            current = state.beat_runtime[beat.id]
            state.beat_runtime[beat.id] = self.pacing.after_turn(
                beat,
                turns_active=current.turns_active,
                stagnant_turns=current.stagnant_turns,
                material_progress=result.material_progress,
            )
        state.turn_index += 1
        state.recent_events.append(
            RuntimeEvent(
                state.turn_index,
                player_input,
                result.narration,
                tuple(item.model_dump() for item in result.operations),
                tuple(item.model_dump() for item in result.beat_updates),
                context.prompt_version,
                context.token_estimate,
            )
        )
        state.recent_events[:] = state.recent_events[-24:]
        if result.summary_delta:
            state.story_summary = (state.story_summary + " " + result.summary_delta).strip()[-4000:]
