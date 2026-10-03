"""Opt-in world capture around a runtime turn."""

from __future__ import annotations

import copy
from collections.abc import Callable
from typing import Any

from storygame.runtime.item_facts import ItemFactsProvider
from storygame.runtime.jev_questions import moves_thing, needs_to_stand, same_or_part, uses_thing
from storygame.runtime.seating import seat_before_use, stand_before_leave
from storygame.runtime.taking import take_before_put
from storygame.runtime.world_model import apply_scene_placements


def _ask_adapter(ask):
    return lambda state, questions: ask(state, questions)


def _json_value(value):
    if isinstance(value, set):
        return sorted(value)
    if isinstance(value, tuple):
        return [_json_value(item) for item in value]
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    return copy.deepcopy(value)


class WorldCapture:
    def __init__(self, provider: ItemFactsProvider, ask: Callable[[object, object], dict | None]) -> None:
        self.provider = provider
        self.ask = ask
        self._command = ""
        self.last_before: dict[str, Any] | None = None
        self.last_after: dict[str, Any] | None = None

    def before_turn(self, command: str) -> dict[str, Any]:
        self._command = command
        package = self.provider.state.package
        world = self.provider._world()
        adapter = _ask_adapter(self.ask)
        standing = stand_before_leave(world, package, command, lambda c, s, r: needs_to_stand(adapter, c, s, r))
        taking = take_before_put(world, package, command, lambda c, t: moves_thing(adapter, c, t))
        seating = (
            seat_before_use(world, package, command, lambda c, t: uses_thing(adapter, c, t))
            if not standing.steps
            else None
        )
        seating_steps = seating.steps if seating else ()
        provider_steps = (*standing.steps, *taking.steps, *seating_steps)
        self.provider.prior_steps = provider_steps
        match_info = {}
        if self.provider.item_facts_mode == "single_call":
            match_info = self.provider.prepare_turn(command)
        record = {
            "command": " ".join((*provider_steps, command)),
            "steps": list(provider_steps),
            "standing_asked": standing.asked,
            "taking_asked": taking.asked,
            "seating_asked": seating.asked if seating else False,
            "asked": {
                "standing": standing.asked,
                "taking": taking.asked,
                "seating": seating.asked if seating else False,
            },
            "issues": [*standing.issues, *taking.issues, *(seating.issues if seating else ())],
            "match_info": _json_value(match_info),
        }
        things_given = list(self.provider._selected_names) if self.provider._selected_names is not None else []
        record["things_given"] = things_given
        record["item_facts_before"] = _json_value(self.provider.facts_for_names(things_given, structural=True))
        self.last_before = record
        return record

    def after_commit(self, command: str, narration: str, *, entered_scene: bool) -> dict[str, Any]:
        raw = self.provider.pending_item_facts()
        adapter = _ask_adapter(self.ask)
        _previous, issues = self.provider.apply_item_facts(
            raw,
            player_input=command,
            story=narration,
            confirm=lambda c, s, q, st, p, k: same_or_part(adapter, c, s, q, st, p, k),
        )
        if entered_scene:
            refusals = apply_scene_placements(
                self.provider.state.package,
                self.provider.state.facts,
                self.provider.state.current_scene_id,
            )
            issues = [
                *issues,
                *(
                    f"scene placement for {refusal.item_id!r} in {refusal.scene_id!r} refused: {refusal.reason}"
                    for refusal in refusals
                ),
            ]
        record = {
            "issues": _json_value(issues),
            "unplaced": _json_value(self.provider.last_item_facts_unplaced()),
            "changed": sorted(self.provider._changed_last_turn),
            "raw": _json_value(raw),
            "match_info": _json_value(self.provider.last_item_facts_match()),
        }
        self.last_after = record
        self.provider.prior_steps = ()
        return record

    def discard(self) -> None:
        self.provider.discard_pending_item_facts()
        self.provider.prior_steps = ()

    def context(self) -> dict[str, Any]:
        names = (
            "_pending_item_facts",
            "_pending_item_facts_present",
            "_held_item_facts",
            "_item_facts_issues",
            "_changed_last_turn",
            "_selected_names",
            "_referred_names",
            "_referred_lines",
            "_last_scene_seeded",
            "_match_offered_names",
            "_fact_effect_snapshot",
            "_last_item_facts_unplaced",
            "_last_item_facts_match",
        )
        result = {name: _json_value(getattr(self.provider, name)) for name in names}
        result["prior_steps"] = _json_value(self.provider.prior_steps)
        result["command"] = self._command
        return result

    def resume(self, context: dict[str, Any]) -> None:
        for name in (
            "_pending_item_facts",
            "_pending_item_facts_present",
            "_held_item_facts",
            "_item_facts_issues",
            "_changed_last_turn",
            "_selected_names",
            "_referred_names",
            "_referred_lines",
            "_last_scene_seeded",
            "_match_offered_names",
            "_fact_effect_snapshot",
            "_last_item_facts_unplaced",
            "_last_item_facts_match",
        ):
            if name in context:
                value = copy.deepcopy(context[name])
                if name in {"_held_item_facts", "_last_item_facts_match"}:
                    value = value or {}
                elif name in {"_changed_last_turn", "_fact_effect_snapshot"}:
                    value = set(value or ())
                elif name in {
                    "_item_facts_issues",
                    "_selected_names",
                    "_referred_names",
                    "_referred_lines",
                    "_last_item_facts_unplaced",
                }:
                    value = value or []
                setattr(self.provider, name, value)
        self.provider.prior_steps = tuple(context.get("prior_steps", ()))
        self._command = context.get("command", "")


def capture_prompt_variant(package) -> dict[str, Any]:
    output_example = (
        '{"segments":[{"kind":"narration","text":"She picks up the lantern. She carries it out to the porch."},'
        '{"kind":"narration","text":"She lights it with a match, and it glows with a warm light."}],'
        '"selected_knowledge_ids":[],"item_facts":{"lantern":{"held_by":"{protagonist}","condition":["lit"]},'
        '"{protagonist}":{"place":"porch"}}}'
    )
    return {
        "include_output_example": True,
        "output_example": output_example,
        "beat_delivery": "details",
        "auto_select_unambiguous_candidates": True,
        "positive_selection_example": False,
        "model_grounding": True,
        "narrow_to_shadow_match": False,
        "constant_rules_in_system": True,
    }


def build_capture_provider(state) -> ItemFactsProvider:
    return ItemFactsProvider.from_environment(
        state,
        prompt_variant=capture_prompt_variant(state.package),
        item_facts={},
        mode="single_call",
        seed_from_package=True,
        held_by=True,
    )
