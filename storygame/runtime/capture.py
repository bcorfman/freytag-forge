"""Opt-in world capture around a runtime turn."""

from __future__ import annotations

import copy
from collections.abc import Callable
from typing import Any

from storygame.runtime.fixed_refusal import fixed_refusal_text, refuse_fixed_move
from storygame.runtime.item_facts import ItemFactsProvider
from storygame.runtime.jev_questions import (
    boards_vehicle,
    moves_thing,
    names_other_action,
    needs_to_stand,
    only_boards_vehicle,
    opens_container,
    relocates_thing,
    same_or_part,
    uses_thing,
)
from storygame.runtime.observation import ObservationRequest
from storygame.runtime.observation_preview import CallMemo, CandidatePreview
from storygame.runtime.observation_verifier import (
    QUESTION_VERSION,
    ObservationVerifier,
    relations_from_context,
)
from storygame.runtime.seating import SeatingResult, board_vehicle, seat_before_use, stand_before_leave
from storygame.runtime.taking import TakingResult, take_before_put
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


_PREVIEW_PROVIDER_FIELDS = (
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
    "_last_item_facts_refused",
    "_last_item_facts_match",
    "prior_steps",
    "prior_notice_steps",
    "command_consumed",
    "observation_request",
    "item_facts_seed_issues",
    "item_facts_match_calls",
    "item_facts_axis_fixes",
    "item_facts_lifted",
    "item_facts_reply_keys",
    "_schema_cache",
)


class WorldCapture:
    def __init__(
        self,
        provider: ItemFactsProvider,
        ask: Callable[[object, object], dict | None],
        fixed_refusal: bool = False,
        *,
        engine_refusal: bool = False,
    ) -> None:
        self.provider = provider
        self.ask = ask
        self.fixed_refusal = fixed_refusal
        self.engine_refusal = engine_refusal
        self.shadow_verifier: ObservationVerifier | None = None
        self.enforcing_verifier: ObservationVerifier | None = None
        self._command = ""
        self.last_before: dict[str, Any] | None = None
        self.last_after: dict[str, Any] | None = None
        self._pending_preview: CandidatePreview | None = None

    def before_turn(self, command: str) -> dict[str, Any]:
        self._pending_preview = None
        if self.enforcing_verifier is not None:
            self.enforcing_verifier.begin_turn()
        self._command = command
        package = self.provider.state.package
        world = self.provider._world()
        adapter = _ask_adapter(self.ask)
        observe_automatically = self.provider.observe_automatically
        if observe_automatically:
            self.provider.observation_request = None
            self.provider._referred_names = []
        fixed = (
            refuse_fixed_move(
                world,
                package,
                command,
                lambda c, t: relocates_thing(adapter, c, t),
                in_scope=lambda item_id: self.provider._name_in_scene_scope(world, world.name(item_id)),
            )
            if self.fixed_refusal
            else None
        )
        refusal_issues = list(fixed.issues if fixed else ())
        other_action = False
        if self.engine_refusal and fixed and fixed.refused:
            joined = " and ".join(fixed.refused)
            other_action = names_other_action(adapter, command, joined)
            if other_action is None:
                refusal_issues.append("other-action question unanswered")
        engine_refusal = (
            fixed_refusal_text(package, fixed.refused, other_action)
            if self.engine_refusal and fixed and fixed.refused
            else ""
        )
        if fixed and fixed.refused:
            standing = SeatingResult(command, (), False, ())
            taking = TakingResult(command, (), False, ())
            boarding = SeatingResult(command, (), False, ())
            seating = SeatingResult(command, (), False, ())
        else:
            standing = stand_before_leave(world, package, command, lambda c, s, r: needs_to_stand(adapter, c, s, r))
            taking = take_before_put(world, package, command, lambda c, t: moves_thing(adapter, c, t))
            boarding = board_vehicle(
                world,
                package,
                command,
                lambda c, v: boards_vehicle(adapter, c, v),
                lambda c, v: only_boards_vehicle(adapter, c, v),
            )
            seating = (
                seat_before_use(world, package, command, lambda c, t: uses_thing(adapter, c, t))
                if not standing.steps and not boarding.steps
                else None
            )
        fixed_steps = fixed.steps if fixed else ()
        already_aboard_in_observation = observe_automatically and boarding.already_aboard
        boarding_steps = () if already_aboard_in_observation else boarding.steps
        seating_steps = seating.steps if seating else ()
        provider_steps = (*fixed_steps, *standing.steps, *boarding_steps, *taking.steps, *seating_steps)
        self.provider.prior_steps = provider_steps
        self.provider.prior_notice_steps = () if already_aboard_in_observation else boarding.notice_steps
        self.provider.command_consumed = boarding.command_consumed and not already_aboard_in_observation
        command_record = (
            " ".join((*fixed_steps, *standing.steps, boarding.command, *taking.steps, *seating_steps))
            if self.provider.command_consumed
            else " ".join((*provider_steps, command))
        )
        match_info = {}
        if self.provider.item_facts_mode == "single_call" and not engine_refusal and not self.provider.command_consumed:
            match_info = self.provider.prepare_turn(command)
        if observe_automatically and not (fixed and fixed.refused):
            self._set_observation_request(command, boarding, adapter)
        record = {
            "command": command_record,
            "steps": list(provider_steps),
            "fixed_refusal_steps": list(fixed_steps),
            "fixed_refusal_asked": fixed.asked if fixed else False,
            "fixed_refusal_issues": refusal_issues,
            "engine_refusal": engine_refusal,
            "standing_steps": list(standing.steps),
            "boarding_steps": list(boarding_steps),
            "boarding_command_consumed": self.provider.command_consumed,
            "taking_steps": list(taking.steps),
            "seating_steps": list(seating_steps),
            "standing_asked": standing.asked,
            "boarding_asked": boarding.asked,
            "taking_asked": taking.asked,
            "seating_asked": seating.asked if seating else False,
            "standing_issues": list(standing.issues),
            "boarding_issues": list(boarding.issues),
            "taking_issues": list(taking.issues),
            "seating_issues": list(seating.issues if seating else ()),
            "asked": {
                "standing": standing.asked,
                "boarding": boarding.asked,
                "taking": taking.asked,
                "seating": seating.asked if seating else False,
                "fixed_refusal": fixed.asked if fixed else False,
            },
            "issues": [
                *refusal_issues,
                *standing.issues,
                *boarding.issues,
                *taking.issues,
                *(seating.issues if seating else ()),
            ],
            "match_info": _json_value(match_info),
        }
        things_given = list(self.provider._selected_names) if self.provider._selected_names is not None else []
        record["things_given"] = things_given
        record["item_facts_before"] = _json_value(self.provider.facts_for_names(things_given, structural=True))
        self.last_before = record
        return record

    def _set_observation_request(self, command: str, boarding: SeatingResult, adapter) -> None:
        world = self.provider._world()
        focus_id = boarding.vehicle_id
        kind = "enter" if focus_id is not None else "look"
        if focus_id is None:
            for name in self.provider._referred_names:
                entity_id = self.provider._resolve_scoped_entity(world, name) or world.resolve(name)
                if entity_id is None:
                    continue
                if any(
                    world.is_a(entity_id, entity_kind)
                    for entity_kind in ("thing", "container", "supporter", "area", "vehicle")
                ):
                    focus_id = entity_id
                    break
        if focus_id is None:
            return
        if world.is_a(focus_id, "container") and opens_container(adapter, command, world.name(focus_id)) is True:
            kind = "open"
        self.provider.observation_request = ObservationRequest(command, kind, focus_id)

    @staticmethod
    def _descendants(world, root_id: str) -> set[str]:
        found = set()
        pending = list(world.contents(root_id))
        while pending:
            entity_id = pending.pop()
            if entity_id in found:
                continue
            found.add(entity_id)
            pending.extend(world.contents(entity_id))
        return found

    def _moved_unrelated(self, before_parents, candidate_world, context) -> tuple[str, ...]:
        request = self.provider.observation_request
        excluded = {self.provider.state.package.world.protagonist_id}
        if request is not None and request.focus is not None:
            excluded.add(request.focus)
        if context is not None:
            for thing in context.visible_things:
                entity_id = candidate_world.resolve(thing.name)
                if entity_id is not None:
                    excluded.add(entity_id)
                    excluded.update(self._descendants(candidate_world, entity_id))
        moved = []
        for entity_id, old_parent in before_parents.items():
            if entity_id in excluded or not candidate_world.is_a(entity_id, "thing"):
                continue
            new_parent = candidate_world.parent(entity_id)
            if old_parent is not None and new_parent is not None and old_parent != new_parent:
                moved.append(candidate_world.name(entity_id))
        return tuple(sorted(set(moved)))

    def preview_commit(
        self,
        command: str,
        narration: str,
        candidate_state,
        *,
        entered_scene: bool,
    ) -> CandidatePreview:
        if self.enforcing_verifier is None or self.provider.observation_request is None:
            return CandidatePreview(
                required=False,
                accepted=True,
                outcome="not_required",
                failure=None,
                verdicts=(),
                moved_unrelated=(),
                changed=(),
                facts_after=None,
                command=command,
                narration=narration,
                memo=CallMemo(),
            )

        raw = self.provider.pending_item_facts()
        original_state = self.provider.state
        original_fields = {name: getattr(self.provider, name) for name in _PREVIEW_PROVIDER_FIELDS}
        saved_fields = {name: copy.deepcopy(getattr(self.provider, name)) for name in _PREVIEW_PROVIDER_FIELDS}
        memo = CallMemo()
        context = None
        report = None
        changed = ()
        facts_after = None
        moved_unrelated = ()
        try:
            self.provider.state = candidate_state
            self.provider._schema_cache = {}
            self.provider.item_facts_call_memo = memo
            before_world = self.provider._world()
            before_parents = {
                entity_id: before_world.parent(entity_id)
                for entity_id in before_world.entity_ids()
                if before_world.is_a(entity_id, "thing")
            }
            adapter = _ask_adapter(self.ask)

            def confirm(c, s, q, st, p, k):
                return memo.remember(
                    "confirm",
                    [c, s, q, st, p, k],
                    lambda: same_or_part(adapter, c, s, q, st, p, k),
                )

            _previous, issues = self.provider.apply_item_facts(
                raw,
                player_input=command,
                story=narration,
                confirm=confirm,
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
            context = self.provider._observation_context()
            candidate_world = self.provider._world()
            moved_unrelated = self._moved_unrelated(before_parents, candidate_world, context)
            relations = relations_from_context(context) if context is not None else ()
            if relations:
                report = self.enforcing_verifier.verify(narration, relations)
                if report is None:
                    raise RuntimeError("observation verifier returned no report")
            changed = tuple(sorted(self.provider._changed_last_turn))
            things_given = set(self.last_before.get("things_given", ())) if self.last_before is not None else set()
            facts_after = _json_value(
                self.provider.facts_for_names(things_given | self.provider._changed_last_turn, structural=True)
            )
        finally:
            self.provider.state = original_state
            for name, value in saved_fields.items():
                original = original_fields[name]
                if name == "_schema_cache":
                    setattr(self.provider, name, original)
                elif isinstance(original, dict):
                    original.clear()
                    original.update(value)
                    setattr(self.provider, name, original)
                elif isinstance(original, list):
                    original.clear()
                    original.extend(value)
                    setattr(self.provider, name, original)
                elif isinstance(original, set):
                    original.clear()
                    original.update(value)
                    setattr(self.provider, name, original)
                else:
                    setattr(self.provider, name, original)
            self.provider.item_facts_call_memo = None

        if report is None:
            required = True
            accepted = not moved_unrelated
            if moved_unrelated:
                outcome = "unrelated_move"
                failure = "unrelated_move"
            else:
                outcome = "not_required"
                failure = None
            verdicts = ()
        else:
            required = True
            accepted = report.accepted and not moved_unrelated
            if report.accepted and moved_unrelated:
                outcome = "unrelated_move"
                failure = "unrelated_move"
            else:
                outcome = report.outcome
                failure = (
                    report.failure if report.failure is not None else ("rejected" if not report.accepted else None)
                )
            verdicts = tuple(
                {
                    "thing": verdict.relation.thing,
                    "verdict": verdict.verdict,
                    "score": verdict.score,
                }
                for verdict in report.verdicts
            )
        preview = CandidatePreview(
            required=required,
            accepted=accepted,
            outcome=outcome,
            failure=failure,
            verdicts=verdicts,
            moved_unrelated=moved_unrelated,
            changed=changed,
            facts_after=facts_after,
            command=command,
            narration=narration,
            memo=memo,
        )
        self._pending_preview = preview
        return preview

    def take_preview(self, command: str, narration: str) -> CandidatePreview | None:
        preview = self._pending_preview
        self._pending_preview = None
        if preview is not None and preview.command == command and preview.narration == narration:
            return preview
        return None

    def after_commit(self, command: str, narration: str, *, entered_scene: bool) -> dict[str, Any]:
        preview = self.take_preview(command, narration)
        raw = self.provider.pending_item_facts()
        adapter = _ask_adapter(self.ask)
        narration_prompt = dict(self.provider.last_prompt) if self.provider.last_prompt is not None else None
        observation_shadow = None
        if self.shadow_verifier is not None and self.provider.observation_request is not None:
            try:
                context = self.provider._observation_context()
                if context is not None:
                    self.shadow_verifier.begin_turn()
                    report = self.shadow_verifier.verify(narration, relations_from_context(context))
                    observation_shadow = {
                        "outcome": report.outcome,
                        "requests": report.requests,
                        "elapsed_s": report.elapsed_s,
                        "failure": report.failure,
                        "question_version": QUESTION_VERSION,
                        "accepted": report.accepted,
                        "verdicts": [
                            {
                                "thing": verdict.relation.thing,
                                "verdict": verdict.verdict,
                                "score": verdict.score,
                            }
                            for verdict in report.verdicts
                        ],
                    }
            except Exception as error:
                observation_shadow = {
                    "outcome": "shadow_error",
                    "requests": 0,
                    "elapsed_s": 0.0,
                    "failure": type(error).__name__,
                    "question_version": QUESTION_VERSION,
                    "accepted": False,
                    "verdicts": [],
                }
        if preview is not None and preview.required:
            self.provider.item_facts_call_memo = preview.memo
        try:

            def confirm(c, s, q, st, p, k):
                if preview is not None and preview.required:
                    return preview.memo.remember(
                        "confirm",
                        [c, s, q, st, p, k],
                        lambda: same_or_part(adapter, c, s, q, st, p, k),
                    )
                return same_or_part(adapter, c, s, q, st, p, k)

            _previous, issues = self.provider.apply_item_facts(
                raw,
                player_input=command,
                story=narration,
                confirm=confirm,
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
        finally:
            if preview is not None and preview.required:
                self.provider.item_facts_call_memo = None
        things_given = (
            set(self.last_before.get("things_given", ()))
            if self.last_before is not None
            else set(preview.facts_after)
            if preview is not None and isinstance(preview.facts_after, dict)
            else set()
        )
        facts_after = self.provider.facts_for_names(things_given | self.provider._changed_last_turn, structural=True)
        record = {
            "issues": _json_value(issues),
            "unplaced": _json_value(self.provider.last_item_facts_unplaced()),
            "refused": _json_value(self.provider.last_item_facts_refused()),
            "changed": sorted(self.provider._changed_last_turn),
            "raw": _json_value(raw),
            "match_info": _json_value(self.provider.last_item_facts_match()),
            "narration_prompt": narration_prompt,
            "facts_after": _json_value(facts_after),
        }
        if observation_shadow is not None:
            record["observation_shadow"] = _json_value(observation_shadow)
        if preview is not None and preview.required:
            record["observation_preview"] = {
                "outcome": preview.outcome,
                "failure": preview.failure,
                "accepted": preview.accepted,
                "changed": list(preview.changed),
                "verdicts": _json_value(preview.verdicts),
            }
            record["observation_diverged"] = tuple(
                sorted(self.provider._changed_last_turn)
            ) != preview.changed or record["facts_after"] != _json_value(preview.facts_after)
        self.last_after = record
        self.provider.prior_steps = ()
        self.provider.prior_notice_steps = ()
        self.provider.command_consumed = False
        return record

    def discard(self) -> None:
        self._pending_preview = None
        self.provider.discard_pending_item_facts()
        self.provider.prior_steps = ()
        self.provider.prior_notice_steps = ()
        self.provider.command_consumed = False

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
            "_last_item_facts_refused",
            "_last_item_facts_match",
        )
        result = {name: _json_value(getattr(self.provider, name)) for name in names}
        result["prior_steps"] = _json_value(self.provider.prior_steps)
        result["prior_notice_steps"] = _json_value(self.provider.prior_notice_steps)
        result["command_consumed"] = self.provider.command_consumed
        result["command"] = self._command
        if self._pending_preview is not None:
            result["observation_preview"] = self._pending_preview.to_json()
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
            "_last_item_facts_refused",
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
                    "_last_item_facts_refused",
                }:
                    value = value or []
                setattr(self.provider, name, value)
        self.provider.prior_steps = tuple(context.get("prior_steps", ()))
        self.provider.prior_notice_steps = tuple(context.get("prior_notice_steps", ()))
        self.provider.command_consumed = bool(context.get("command_consumed", False))
        self._command = context.get("command", "")
        self._pending_preview = (
            CandidatePreview.from_json(context["observation_preview"]) if "observation_preview" in context else None
        )


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


def build_capture_provider(state, *, mark_fixed=False) -> ItemFactsProvider:
    return ItemFactsProvider.from_environment(
        state,
        prompt_variant=capture_prompt_variant(state.package),
        item_facts={},
        mode="single_call",
        seed_from_package=True,
        held_by=True,
        mark_fixed=mark_fixed,
    )
