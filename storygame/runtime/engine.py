"""One-call V2 turn orchestrator with one shared recovery attempt."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Protocol

from storygame.runtime.context import RuntimeContext, RuntimeContextBuilder
from storygame.runtime.contracts import RuntimeFailure, StateOperation, TurnResult
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
    model_calls: int = 0


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
        movement = _movement_affordance(self.state, player_input)
        item_affordance = _item_affordance(self.state, player_input)
        normalized = movement or item_affordance
        if normalized is not None:
            context.payload["normalized_affordance"] = normalized
        last_error: RuntimeFailure | None = None
        for model_calls, json_object in enumerate((True, False), start=1):
            try:
                raw = self.model.play_turn(context, json_object=json_object)
                result = TurnResult.from_provider(raw)
                if movement is not None and not any(item.path == "world.location" for item in result.operations):
                    result = result.model_copy(
                        update={
                            "operations": result.operations
                            + (StateOperation(kind="set", path="world.location", value=movement),)
                        }
                    )
                if item_affordance is not None:
                    result = _apply_item_affordance(result, item_affordance)
                candidate = validate_and_commit(self.state, result, player_input=player_input)
                self._finalize(candidate, player_input, result, context)
                self.state = candidate
                narration = result.dialogue.dialogue if result.dialogue is not None else result.narration
                return TurnResponse(True, narration, candidate.turn_index, model_calls=model_calls)
            except JsonModeRejected as exc:
                last_error = RuntimeFailure("JSON_MODE_REJECTED", str(exc) or "provider rejected JSON-object mode")
            except RuntimeFailure as exc:
                last_error = exc
            except Exception as exc:
                last_error = RuntimeFailure("MODEL_FAILURE", f"model request failed: {exc}")
            if model_calls == 1 and last_error is not None:
                context = _repair_context(context, last_error)
        failure = RuntimeFailure(
            "RUNTIME_RECOVERY_EXHAUSTED",
            "turn could not be decoded or validated after one recovery",
        )
        if last_error is not None:
            failure.__cause__ = last_error
        return TurnResponse(False, error=failure, model_calls=2)

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


def _item_affordance(state: RuntimeState, player_input: str) -> dict[str, object] | None:
    request = player_input.casefold().strip()
    verbs = ("take ", "pick up ", "get ", "inspect ", "examine ", "look at ")
    verb = next((candidate for candidate in verbs if request.startswith(candidate)), None)
    if verb is None:
        return None
    item_text = request.removeprefix(verb).strip()
    item_text = item_text.removeprefix("the ").removeprefix("a ").removeprefix("an ")
    candidates: list[str] = []
    for item_id, item in state.world.items.items():
        holder = item.get("holder")
        visible = (
            holder == "player"
            or holder == f"location:{state.world.location}"
            or (
                isinstance(holder, str)
                and holder.startswith("npc:")
                and _holder_is_present(state, holder.removeprefix("npc:"))
            )
        )
        if not visible:
            continue
        labels = (item_id.replace("_", " "), str(item.get("name", "")).casefold())
        if any(label and (item_text == label or item_text in label) for label in labels):
            candidates.append(item_id)
    if len(candidates) != 1:
        return None
    item_id = candidates[0]
    if verb in {"take ", "pick up ", "get "}:
        affordances = state.world.items[item_id].get("affordances", ("take",))
        if not isinstance(affordances, (list, tuple, set)) or "take" not in affordances:
            return None
        return {"kind": "take", "item_id": item_id, "instruction": f"Set world.items.{item_id}.holder to player."}
    return {
        "kind": "inspect",
        "item_id": item_id,
        "instruction": f"Describe declared item {item_id} without changing state.",
    }


def _holder_is_present(state: RuntimeState, npc_id: str) -> bool:
    return state.facts.has("at", npc_id, state.world.location) or state.facts.has(
        "present", npc_id, state.world.location
    )


def _apply_item_affordance(result: TurnResult, affordance: dict[str, object]) -> TurnResult:
    if affordance.get("kind") != "take":
        return result
    item_id = affordance.get("item_id")
    if not isinstance(item_id, str) or any(
        operation.path == f"world.items.{item_id}.holder" for operation in result.operations
    ):
        return result
    operation = StateOperation(kind="set", path=f"world.items.{item_id}.holder", value="player")
    return result.model_copy(update={"operations": result.operations + (operation,)})


def _repair_context(context: RuntimeContext, failure: RuntimeFailure) -> RuntimeContext:
    """Give the sole recovery call bounded local feedback without changing state."""
    payload = dict(context.payload)
    payload["recovery_instruction"] = (
        "Your previous response failed local validation: "
        f"{failure.message[:800]}. Return a corrected complete TurnResult object only."
    )
    return replace(context, payload=payload)


def _movement_affordance(state: RuntimeState, player_input: str) -> str | None:
    """Resolve only an unambiguous declared destination into the shared commit contract."""

    navigation = state.world.attributes.get("navigation", {})
    if not isinstance(navigation, dict):
        return None
    routes = navigation.get("routes", [])
    names = navigation.get("names", {})
    if not isinstance(routes, list) or not isinstance(names, dict):
        return None
    request = player_input.casefold().strip()
    candidates: list[str] = []
    for route in routes:
        if not isinstance(route, dict) or route.get("from") != state.world.location:
            continue
        destination = route.get("to")
        if not isinstance(destination, str):
            continue
        labels = [destination, str(names.get(destination, "")), *route.get("aliases", [])]
        if any(_mentions_destination(request, label) for label in labels if label):
            candidates.append(destination)
    return candidates[0] if len(set(candidates)) == 1 else None


def _mentions_destination(request: str, label: str) -> bool:
    normalized = label.casefold().replace("_", " ").strip()
    if request in {normalized, f"go {normalized}", f"go to {normalized}", f"walk to {normalized}"}:
        return True
    return request.startswith("go ") and normalized in request[3:]
