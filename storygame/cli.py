from __future__ import annotations

from dataclasses import replace
import json
import re
from pathlib import Path
from random import Random
from typing import Any, Protocol, TextIO

from rich.console import Console

from storygame.engine.freeform import (
    DEFAULT_FREEFORM_ADAPTER,
    FreeformProposalAdapter,
    resolve_freeform_roleplay,
    resolve_freeform_roleplay_with_proposals,
)
from storygame.engine.impact import assess_player_command, replan_scope_for_assessment, requires_high_impact_confirmation
from storygame.engine.interfaces import parse_action_proposal
from storygame.engine.mystery import caseboard_lines, room_item_groups
from storygame.engine.parser import Action, ActionKind, parse_command
from storygame.engine.simulation import advance_turn
from storygame.engine.facts import apply_fact_ops
from storygame.engine.state import Event, GameState
from storygame.engine.world import build_default_state
from storygame.llm.adapters import Narrator, OllamaAdapter, OpenAIAdapter
from storygame.llm.coherence import build_default_coherence_gate
from storygame.llm.context import build_narration_context
from storygame.llm.narration_state import extract_narration_fact_ops
from storygame.llm.output_editor import OutputEditor, build_output_editor
from storygame.llm.story_director import StoryDirector
from storygame.memory import MAX_MEMORY_NOTES, MemoryStore, SqliteVectorMemory, normalize_tag
from storygame.persistence.savegame_sqlite import SqliteSaveStore
from storygame.plot.freytag import get_phase


def _humanize_token(token: str) -> str:
    return token.replace("_", " ")


def _lowercase_location_phrase(location: str) -> str:
    words = location.split()
    if not words:
        return "the area"
    return f"the {' '.join(word.lower() for word in words)}"


def _with_indefinite_article(phrase: str) -> str:
    cleaned = phrase.strip()
    if not cleaned:
        return cleaned
    first = cleaned[0].lower()
    article = "an" if first in {"a", "e", "i", "o", "u"} else "a"
    return f"{article} {cleaned}"


def _opening_story_editor(paragraphs: list[str]) -> list[str]:
    forbidden = (
        "neutral mystery scene",
        "move the story toward resolution",
        "where you are:",
        "cast:",
    )
    cleaned: list[str] = []
    for paragraph in paragraphs:
        normalized = " ".join(paragraph.split())
        for fragment in forbidden:
            normalized = normalized.replace(fragment, "")
            normalized = normalized.replace(fragment.title(), "")
        normalized = normalized.strip(" ,")
        if normalized.lower().endswith("tasked with."):
            normalized = normalized[: -len("tasked with.")].rstrip(" ,.;")
            normalized = f"{normalized} and forced to take one final case."
        cleaned.append(normalized)
    return [paragraph for paragraph in cleaned if paragraph]


def _joined_with_and(values: tuple[str, ...] | list[str]) -> str:
    if not values:
        return ""
    if len(values) == 1:
        return values[0]
    if len(values) == 2:
        return f"{values[0]} and {values[1]}"
    return f"{', '.join(values[:-1])}, and {values[-1]}"


def _first_sentence(value: str) -> str:
    fragments = re.split(r"(?<=[.!?])\s+", value.strip())
    return fragments[0] if fragments and fragments[0] else value.strip()


def _shorten_line(value: str, max_chars: int) -> str:
    text = value.strip()
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars].rstrip(" ,;:")
    return f"{cut}..."


def _cached_room_presentation(state: GameState, room_id: str) -> dict[str, str]:
    cache = state.world_package.setdefault("room_presentation_cache", {})
    room_cache = cache.get(room_id)
    if room_cache:
        return room_cache

    room = state.world.rooms[room_id]
    long_description = room.description.strip()
    first_sentence = _first_sentence(long_description)
    short_description = _shorten_line(first_sentence, 110)

    generated = {"long": long_description, "short": short_description}
    cache[room_id] = generated
    return generated


def _introduced_npc_ids(state: GameState) -> tuple[str, ...]:
    introduced = state.world_package.setdefault("introduced_npcs", [])
    return tuple(str(npc_id) for npc_id in introduced)


def _remember_npc_introductions(state: GameState, npc_ids: tuple[str, ...]) -> None:
    introduced = list(_introduced_npc_ids(state))
    changed = False
    for npc_id in npc_ids:
        if npc_id not in introduced:
            introduced.append(npc_id)
            changed = True
    if changed:
        state.world_package["introduced_npcs"] = introduced


def _first_name(value: str) -> str:
    words = tuple(part for part in value.split() if part)
    if not words:
        return value
    return words[0]


def _display_name_for_npc(state: GameState, npc_id: str, room_npc_ids: tuple[str, ...]) -> str:
    npc = state.world.npcs[npc_id]
    full_name = npc.name.strip() or _humanize_token(npc_id).title()
    name_words = tuple(part for part in full_name.split() if part)
    if len(name_words) < 2:
        return full_name

    introduced = _introduced_npc_ids(state)
    if npc_id not in introduced:
        return full_name

    first_name = name_words[0]
    same_first_name_count = 0
    for other_npc_id in room_npc_ids:
        other_name = state.world.npcs[other_npc_id].name.strip()
        if _first_name(other_name) == first_name:
            same_first_name_count += 1
    if same_first_name_count > 1:
        return full_name
    return first_name


def _rewrite_known_npc_names(state: GameState, text: str) -> str:
    room = state.world.rooms[state.player.location]
    if "nearby, watching your next move." in text:
        return text
    rewritten = text
    for npc_id in room.npc_ids:
        full_name = state.world.npcs[npc_id].name.strip()
        display_name = _display_name_for_npc(state, npc_id, room.npc_ids)
        if display_name != full_name:
            rewritten = rewritten.replace(full_name, display_name)
    return rewritten


def _room_lines(state: GameState, *, long_form: bool = True) -> str:
    room = state.world.rooms[state.player.location]
    presentation = _cached_room_presentation(state, room.id)
    pieces = [room.name, presentation["long"] if long_form else presentation["short"]]
    actionable_items, junk_count = room_item_groups(state, room)
    if actionable_items:
        visible_items = tuple(_humanize_token(item) for item in actionable_items)
        if room.id == "front_steps" and "ledger_page" in actionable_items:
            pieces.append(
                "You can see a torn ledger page lying half-caught in a crack between the stones near the bottom step."
            )
        else:
            pieces.append(f"You can see {_joined_with_and(visible_items)} within easy reach.")
    if junk_count > 0:
        suffix = "item" if junk_count == 1 else "items"
        verb = "is" if junk_count == 1 else "are"
        pieces.append(f"There {verb} {junk_count} other unremarkable {suffix} nearby.")
    if room.exits:
        exits = tuple(sorted(room.exits.keys()))
        if len(exits) == 1:
            if room.id == "front_steps":
                pieces.append(
                    f"The main entrance from here leads {exits[0]} toward the mansion interior, while the drive behind you remains open."
                )
            else:
                pieces.append(f"The single obvious exit leads {exits[0]}.")
        else:
            pieces.append(f"Exits lead {_joined_with_and([f'to the {direction}' for direction in exits])}.")
    if room.npc_ids:
        visible_npcs = tuple(_display_name_for_npc(state, npc_id, room.npc_ids) for npc_id in room.npc_ids)
        verb = "is" if len(visible_npcs) == 1 else "are"
        pieces.append(f"{_joined_with_and(list(visible_npcs))} {verb} nearby, watching your next move.")
        _remember_npc_introductions(state, room.npc_ids)
    return "\n".join(pieces)


def _setup_phase_lines(state: GameState, story_director: StoryDirector | None = None) -> list[str]:
    director = StoryDirector("openai") if story_director is None else story_director
    return director.compose_opening(state)


def _with_paragraph_spacing(lines: list[str]) -> list[str]:
    if len(lines) <= 1:
        return list(lines)
    spaced: list[str] = []
    for index, line in enumerate(lines):
        spaced.append(line)
        if index < len(lines) - 1:
            spaced.append("")
    return spaced


_PROCEED_WORDS = {"proceed", "confirm", "yes", "y"}
_CANCEL_WORDS = {"cancel", "abort", "no", "n"}


def _clear_pending_high_impact(state: GameState) -> None:
    state.pending_high_impact_command = ""
    state.pending_high_impact_assessment = {}


def _high_impact_warning_lines(assessment: dict[str, Any]) -> list[str]:
    impact_class = str(assessment.get("impact_class", "high")).upper()
    consequences = [str(item).strip() for item in assessment.get("consequences", []) if str(item).strip()]
    lines = [
        f"Goal-breaking action detected ({impact_class}). This would rupture the current story goals, NPC behavior, and event timing.",
    ]
    lines.extend(consequences[:2])
    lines.append("Type PROCEED to continue or CANCEL to abort.")
    return lines


def _record_major_disruption(
    state: GameState,
    events: list[Event],
    raw_command: str,
    assessment: dict[str, Any],
) -> None:
    replan_scope = replan_scope_for_assessment(assessment)
    state.player.flags["story_replan_required"] = True
    state.player.flags["story_bounds_overridden"] = True
    state.world_package["story_replan_context"] = {
        "command": raw_command,
        "impact_class": str(assessment.get("impact_class", "high")),
        "replan_scope": replan_scope,
        "reasons": list(assessment.get("reasons", [])),
        "turn_index": state.turn_index,
    }
    disruption_event = Event(
        type="major_disruption",
        tags=("story", "major_disruption"),
        message_key="Your choice disrupts the planned arc. The world is already reacting.",
        turn_index=state.turn_index,
        metadata={
            "command": raw_command,
            "assessment": dict(assessment),
        },
    )
    events.append(disruption_event)
    state.append_event(disruption_event)


def _public_event_message(message_key: str) -> str:
    message = message_key.strip()
    if not message:
        return ""
    clarification_messages = {
        "look": "",
        "inventory": "",
        "help": "",
        "unknown_command": (
            "I didn't understand that command. Try LOOK, GO <direction>, TALK <name>, TAKE <item>, or INVENTORY."
        ),
        "move_failed_unknown_destination": "You can't go that way.",
        "move_failed_locked_exit": "That way is locked.",
        "take_failed_missing": "You don't see that here.",
        "take_failed_not_portable": "You can't carry that.",
        "talk_failed_missing": "No one by that name is here.",
        "use_failed_missing_item": "You aren't carrying that item.",
    }
    if message in clarification_messages:
        return clarification_messages[message]
    # Hide engine-like keys in normal mode (for example: move_success, take_failed).
    if "_" in message and " " not in message:
        return ""
    return message


def _event_lines(events, debug: bool = False) -> str:
    if not events:
        return ""
    if debug:
        return "\n".join(f"- {event.type}: {event.message_key}" for event in events)
    public_lines = [_public_event_message(event.message_key) for event in events]
    return "\n".join(message for message in public_lines if message)


def _raw_input_requests_goal(raw_input: str) -> bool:
    lowered = raw_input.lower()
    return re.search(r"\b(goal|goals|objective|objectives)\b", lowered) is not None


def _should_prefer_proposal_resolution(
    raw_input: str,
    fallback_action: Action,
    planner_dialog_payload: dict[str, Any] | None,
    planner_action_payload: dict[str, Any] | None,
) -> bool:
    if planner_action_payload is None or planner_dialog_payload is None:
        return False
    if fallback_action.kind in {ActionKind.HELP, ActionKind.QUIT, ActionKind.SAVE, ActionKind.LOAD}:
        return False

    lowered = raw_input.strip().lower()
    intent = str(planner_action_payload.get("intent", "")).strip().lower()
    speaker = str(planner_dialog_payload.get("speaker", "")).strip().lower()

    conversational_intents = {"ask_about", "greet", "apologize", "threaten", "read_case_file", "inspect", "knock"}
    if intent in conversational_intents:
        return True
    if fallback_action.kind == ActionKind.TALK:
        return True
    if speaker not in {"", "narrator", "player"}:
        return True
    return bool(re.search(r"\b(ask|tell|say|speak|talk|who|what|why|how)\b", lowered) or "," in lowered)


def _context_goal_for_turn(raw_input: str, goal: str, turn_index: int) -> str:
    if turn_index <= 0:
        return goal
    if _raw_input_requests_goal(raw_input):
        return goal
    return ""


def _freeform_unavailable_lines(detail: str = "") -> list[str]:
    line = "Story response unavailable: LLM planning is required for this turn."
    if detail:
        return [f"{line} {detail}"]
    return [line]


def _has_bounded_dialogue_event(events: list[Event], debug: bool = False) -> bool:
    if debug:
        return False
    for event in events:
        message = _public_event_message(event.message_key)
        if ' says: "' in message:
            action_proposal = event.metadata.get("action_proposal", {})
            arguments = action_proposal.get("arguments", {}) if isinstance(action_proposal, dict) else {}
            planner_source = str(arguments.get("planner_source", "")).strip().lower()
            if planner_source == "fallback":
                continue
            return True
    return False


def _suppress_repeated_goal_copy(lines: list[str], raw_input: str, active_goal: str) -> list[str]:
    if _raw_input_requests_goal(raw_input):
        return lines

    lowered_goal = active_goal.lower().strip()
    filtered: list[str] = []
    for line in lines:
        lowered = line.lower()
        if "first practical objective" in lowered or "immediate objective" in lowered:
            continue
        if lowered_goal and lowered_goal in lowered and ("goal" in lowered or "objective" in lowered):
            continue
        filtered.append(line)
    return filtered


def _contains_repeated_goal_copy(text: str, raw_input: str, active_goal: str) -> bool:
    if _raw_input_requests_goal(raw_input):
        return False
    lowered = text.lower()
    if "first practical objective" in lowered or "immediate objective" in lowered:
        return True
    lowered_goal = active_goal.lower().strip()
    return bool(lowered_goal and lowered_goal in lowered and ("goal" in lowered or "objective" in lowered))


def _should_render_room_block(
    previous_state: GameState,
    next_state: GameState,
    action: Action,
) -> bool:
    if action.kind == ActionKind.LOOK:
        return True
    return previous_state.player.location != next_state.player.location


def _write_transcript_line(handle: TextIO | None, line: str) -> None:
    if handle is None:
        return
    handle.write(line + "\n")


def _emit_cli_line(console: Console, line: str) -> None:
    for paragraph in line.split("\n"):
        console.print(paragraph, highlight=False, markup=False, overflow="fold")


def _inventory_lines(state: GameState) -> list[str]:
    items = tuple(_humanize_token(item) for item in state.player.inventory)
    if not items:
        return ["You are carrying nothing."]
    lines = ["You are carrying:"]
    lines.extend(items)
    return lines


def _sanitize_narration_for_player(narration: str, debug: bool) -> str:
    if debug:
        return narration
    if re.search(r"\bbeat at\b", narration.lower()):
        return ""
    return narration


def _narration_references_action(narration: str, action_raw: str) -> bool:
    narration_tokens = {token for token in re.findall(r"[a-z0-9]+", narration.lower()) if len(token) >= 4}
    action_tokens = {
        token
        for token in re.findall(r"[a-z0-9]+", action_raw.lower())
        if len(token) >= 4 and token not in {"look", "talk", "speak", "move", "north", "south", "east", "west"}
    }
    if not action_tokens:
        return True
    return bool(narration_tokens.intersection(action_tokens))


def _ensure_action_grounded_narration(narration: str, action: Action) -> str:
    if not narration:
        return narration
    if action.kind in {ActionKind.LOOK, ActionKind.HELP, ActionKind.INVENTORY, ActionKind.SAVE, ActionKind.LOAD}:
        return narration
    if _narration_references_action(narration, action.raw):
        return narration
    return f'You act on "{action.raw}". {narration}'


def _should_discard_failed_narration(
    judge_decision: dict[str, Any],
    coherence_telemetry: dict[str, Any],
) -> bool:
    return (
        str(judge_decision["status"]) == "failed"
        and str(coherence_telemetry["hard_fail_reason"]) == "BUDGET_WALL_CLOCK_TIMEOUT"
    )


def _contains_normalized_line(lines: list[str], target: str) -> bool:
    normalized_target = " ".join(target.split()).lower()
    if not normalized_target:
        return False
    return any(normalized_target in " ".join(line.split()).lower() for line in lines)


def _has_similar_narration(lines: list[str], target: str) -> bool:
    target_tokens = {token for token in re.findall(r"[a-z0-9]+", target.lower()) if len(token) >= 4}
    if len(target_tokens) < 6:
        return _contains_normalized_line(lines, target)
    for line in lines:
        line_tokens = {token for token in re.findall(r"[a-z0-9]+", line.lower()) if len(token) >= 4}
        if not line_tokens:
            continue
        overlap = len(target_tokens.intersection(line_tokens))
        ratio = overlap / len(target_tokens)
        if ratio >= 0.65:
            return True
    return False


def _transcript_command_echo(raw_command: str) -> str:
    return f">{raw_command.strip().upper()}"


def _write_transcript_command_echo(handle: TextIO | None, raw_command: str) -> None:
    _write_transcript_line(handle, "")
    _write_transcript_line(handle, _transcript_command_echo(raw_command))


def _target_from_proposal(action_proposal: dict[str, Any]) -> str:
    targets = tuple(str(target).strip().lower() for target in action_proposal.get("targets", ()) if str(target).strip())
    if not targets:
        return ""
    return targets[0]


def _action_from_proposal(raw: str, action_proposal: dict[str, Any]) -> Action:
    intent = str(action_proposal.get("intent", "")).strip().lower()
    target = _target_from_proposal(action_proposal)

    if intent in {"look"}:
        return Action(ActionKind.LOOK, raw=raw)
    if intent in {"inventory", "inv"}:
        return Action(ActionKind.INVENTORY, raw=raw)
    if intent in {"help", "hint"}:
        return Action(ActionKind.HELP, raw=raw)
    if intent in {"go", "move", "travel", "walk"} and target:
        return Action(ActionKind.MOVE, target=target, raw=raw)
    if intent in {"take", "get", "grab", "pick_up", "pickup", "acquire"} and target:
        return Action(ActionKind.TAKE, target=target, raw=raw)
    if intent in {"talk", "speak"} and target:
        return Action(ActionKind.TALK, target=target, raw=raw)
    if intent in {"use"} and target:
        secondary = str(action_proposal.get("arguments", {}).get("target", "")).strip().lower()
        combined = f"{target}:{secondary}" if secondary else target
        return Action(ActionKind.USE, target=combined, raw=raw)
    return Action(ActionKind.UNKNOWN, raw=raw)


def _build_narrator(mode: str) -> Narrator:
    if mode == "openai":
        return OpenAIAdapter()
    if mode == "ollama":
        return OllamaAdapter()
    raise ValueError("Narrator mode must be 'openai' or 'ollama'.")


def _build_memory_tag_set(state: GameState, action) -> tuple[str, ...]:
    room = state.world.rooms[state.player.location]
    action_target = normalize_tag(action.target) if action.target else ""
    goal_words = tuple(normalize_tag(word) for word in state.active_goal.split() if word)[:2]
    ordered_tags: list[str] = [
        f"beat_{state.beat_history[-1]}" if state.beat_history else "beat_unknown",
        f"goal_{goal_words[0]}" if goal_words else "goal",
    ]
    if action_target:
        ordered_tags.append(action_target)
        ordered_tags.append(f"npc_{action_target}")
    for npc in room.npc_ids:
        ordered_tags.append(npc)
        ordered_tags.append(f"npc_{npc}")
    ordered_tags.append(f"room_{state.player.location}")

    deduped: list[str] = []
    for tag in ordered_tags:
        if tag and tag not in deduped:
            deduped.append(tag)
    return tuple(deduped[:MAX_MEMORY_NOTES])


class SaveStore(Protocol):
    def save_run(
        self,
        slot: str,
        state: GameState,
        rng: Random,
        raw_command: str = "save",
        action_kind: str = "save",
        beat_type: str | None = None,
        template_key: str | None = None,
        transcript: list[str] | None = None,
        judge_decision: dict[str, str] | None = None,
    ) -> None: ...

    def load_run(self, slot: str) -> tuple[GameState, Random]: ...


def _judge_decision_for_persistence(state: GameState) -> dict[str, str] | None:
    if state.last_judge_decision is None:
        return None
    if state.last_judge_decision.get("status") != "accepted":
        return None
    return state.last_judge_decision


def run_turn(
    state: GameState,
    raw: str,
    rng: Random,
    narrator: Narrator,
    debug: bool = False,
    save_store: SaveStore | None = None,
    memory_store: MemoryStore | None = None,
    memory_slot: str = "default",
    freeform_adapter: FreeformProposalAdapter = DEFAULT_FREEFORM_ADAPTER,
    output_editor: OutputEditor | None = None,
    story_director: StoryDirector | None = None,
    narrator_mode: str = "openai",
    _confirmed_high_impact: bool = False,
    _confirmed_assessment: dict[str, Any] | None = None,
):
    raw_input = raw.strip()
    lowered_input = raw_input.lower()
    if state.pending_high_impact_command:
        if lowered_input in _PROCEED_WORDS:
            confirmed_command = state.pending_high_impact_command
            confirmed_assessment = dict(state.pending_high_impact_assessment)
            resumed_state = state.clone()
            _clear_pending_high_impact(resumed_state)
            return run_turn(
                resumed_state,
                confirmed_command,
                rng,
                narrator,
                debug=debug,
                save_store=save_store,
                memory_store=memory_store,
                memory_slot=memory_slot,
                freeform_adapter=freeform_adapter,
                output_editor=output_editor,
                story_director=story_director,
                narrator_mode=narrator_mode,
                _confirmed_high_impact=True,
                _confirmed_assessment=confirmed_assessment,
            )
        if lowered_input in _CANCEL_WORDS:
            canceled_state = state.clone()
            _clear_pending_high_impact(canceled_state)
            return canceled_state, ["Action canceled. Story plan remains unchanged."], raw_input, "impact_gate", True
        return (
            state,
            ["A high-impact action is pending confirmation. Type PROCEED to continue or CANCEL to abort."],
            raw_input,
            "impact_gate",
            True,
        )

    control_action = parse_command(raw)
    if control_action.kind == ActionKind.QUIT:
        return state, ["Goodbye."], "", "", False

    if control_action.kind == ActionKind.SAVE:
        if not control_action.target:
            return state, ["Usage: save <slot>."], control_action.raw, "save", True
        if save_store is None:
            return state, ["Save requires --save-db <path>."], control_action.raw, "save", True
        try:
            save_store.save_run(
                control_action.target,
                state,
                rng,
                raw_command=control_action.raw,
                action_kind="save",
                judge_decision=_judge_decision_for_persistence(state),
            )
            return state, [f"Saved to slot '{control_action.target}'."], control_action.raw, "save", True
        except Exception as exc:
            return state, [f"Failed to save: {exc}"], control_action.raw, "save", True

    if control_action.kind == ActionKind.LOAD:
        if not control_action.target:
            return state, ["Usage: load <slot>."], control_action.raw, "load", True
        if save_store is None:
            return state, ["Load requires --save-db <path>."], control_action.raw, "load", True
        try:
            state, loaded_rng = save_store.load_run(control_action.target)
            rng.setstate(loaded_rng.getstate())
            return (
                state,
                [_room_lines(state, long_form=True), f"Loaded from slot '{control_action.target}'."],
                control_action.raw,
                "load",
                True,
            )
        except ValueError as exc:
            return state, [f"Could not load slot '{control_action.target}': {exc}"], control_action.raw, "load", True
        except Exception as exc:
            return state, [f"Failed to load: {exc}"], control_action.raw, "load", True

    editor = build_output_editor(narrator_mode) if output_editor is None else output_editor
    director = StoryDirector(narrator_mode, editor) if story_director is None else story_director
    preturn_state = state
    replan_event = None
    if state.player.flags.get("story_replan_required", False):
        preturn_state = state.clone()
        replan_event = director.replan_if_needed(preturn_state)
    if replan_event is not None:
        preturn_state.append_event(replan_event)

    planner_dialog_payload: dict[str, Any] | None = None
    planner_action_payload: dict[str, Any] | None = None
    planner_parse_error = ""
    fallback_action = parse_command(raw)
    effective_action = fallback_action
    freeform_policy_debug: dict[str, Any] | None = None
    prefer_proposal_resolution = False
    try:
        planner_dialog_payload, planner_action_payload = freeform_adapter.propose(preturn_state, raw_input)
        normalized_action_payload = parse_action_proposal(planner_action_payload)
        planner_action_payload = normalized_action_payload
        prefer_proposal_resolution = _should_prefer_proposal_resolution(
            raw_input,
            fallback_action,
            planner_dialog_payload,
            normalized_action_payload,
        )
        proposal_action = _action_from_proposal(raw_input, normalized_action_payload)
        if proposal_action.kind != ActionKind.UNKNOWN and not prefer_proposal_resolution:
            effective_action = proposal_action
    except Exception as exc:
        planner_parse_error = str(exc)

    impact_assessment = (
        _confirmed_assessment
        if _confirmed_assessment is not None
        else assess_player_command(state, effective_action.raw, effective_action)
    )
    if not _confirmed_high_impact and requires_high_impact_confirmation(impact_assessment):
        blocked_state = state.clone()
        blocked_state.pending_high_impact_command = effective_action.raw
        blocked_state.pending_high_impact_assessment = dict(impact_assessment)
        return blocked_state, _high_impact_warning_lines(impact_assessment), effective_action.raw, "impact_gate", True

    requires_freeform_resolution = (
        effective_action.kind == ActionKind.UNKNOWN
        or prefer_proposal_resolution
        or (fallback_action.kind == ActionKind.TALK and planner_dialog_payload is None and planner_action_payload is None)
    )
    if requires_freeform_resolution:
        if planner_dialog_payload is not None and planner_action_payload is not None:
            freeform = resolve_freeform_roleplay_with_proposals(
                preturn_state,
                raw_input,
                planner_dialog_payload,
                planner_action_payload,
            )
        else:
            detail = planner_parse_error.strip()
            if detail.startswith("FREEFORM_PLANNER_UNAVAILABLE:"):
                return state.clone(), _freeform_unavailable_lines(detail.removeprefix("FREEFORM_PLANNER_UNAVAILABLE:").strip()), raw_input, "freeform_roleplay", True
            return state.clone(), _freeform_unavailable_lines(detail), raw_input, "freeform_roleplay", True
        next_state = freeform["state"]
        events = list(freeform["events"])
        freeform_policy_debug = {
            "action_proposal": dict(freeform["action_proposal"]),
            "state_update_envelope": dict(freeform["state_update_envelope"]),
            "fact_ops": list(freeform["event"].metadata.get("fact_ops", [])),
            "planner_error": planner_parse_error,
            "proposal_first": prefer_proposal_resolution,
            "story_delta": {
                "progress": freeform["event"].delta_progress,
                "tension": freeform["event"].delta_tension,
            },
        }
        if replan_event is not None:
            events.insert(0, replan_event)
        beat_type = "freeform_roleplay"
        template_key = "freeform_roleplay"
        effective_action = _action_from_proposal(raw_input, freeform["action_proposal"])
    else:
        next_state, events, beat_type, template_key = advance_turn(preturn_state, effective_action, rng)
        if replan_event is not None:
            events.insert(0, replan_event)

    memory_fragments: tuple[str, ...] = ()
    if memory_store is not None:
        memory_fragments = memory_store.retrieve(memory_slot, _build_memory_tag_set(next_state, effective_action))

    context = build_narration_context(next_state, effective_action, beat_type, memory_fragments)
    context = replace(
        context,
        goal=_context_goal_for_turn(raw_input, context.goal, next_state.turn_index),
    )
    gate = build_default_coherence_gate()
    judge_decision = {
        "status": "failed",
        "total_score": 0,
        "threshold": 80,
        "round_index": 1,
        "critic_ids": (),
        "rubric_components": {},
        "decision_id": "judge-error",
    }
    coherence_telemetry = {
        "critique_rounds": 0,
        "token_spend": {"narrator": 0, "critics": 0},
        "elapsed_ms": 0,
        "hard_fail_reason": "NARRATOR_RUNTIME_ERROR",
    }
    try:
        coherence_result = gate.generate_with_gate(narrator, context)
        narration = coherence_result["narration"]
        judge_decision = coherence_result["judge_decision"]
        coherence_telemetry = coherence_result["telemetry"]
    except RuntimeError as exc:
        error_code = str(exc)
        if error_code == "CONTRACT_INVALID_AGENT_PROPOSAL":
            narration = ""
        elif error_code == "CONTRACT_INVALID_REVISION_DIRECTIVE":
            try:
                narration = str(narrator.generate(context)).strip()
            except Exception as fallback_exc:  # noqa: BLE001
                narration = f"[Narrator failed: {fallback_exc}]"
        else:
            narration = f"[Narrator failed: {exc}]"

    if _should_discard_failed_narration(judge_decision, coherence_telemetry):
        narration = ""

    if _confirmed_high_impact:
        _record_major_disruption(next_state, events, effective_action.raw, impact_assessment)

    narration = _sanitize_narration_for_player(narration, debug=debug)
    narration_fact_ops = extract_narration_fact_ops(next_state, narration)
    if narration_fact_ops:
        apply_fact_ops(next_state, narration_fact_ops)
        narration_event = Event(
            type="narration_commit",
            turn_index=next_state.turn_index,
            metadata={
                "fact_ops": narration_fact_ops,
                "source": "accepted_narration",
                "narration": narration,
            },
        )
        next_state.append_event(narration_event)
        events.append(narration_event)
        if freeform_policy_debug is not None:
            freeform_policy_debug["narration_fact_ops"] = list(narration_fact_ops)
    narration = _ensure_action_grounded_narration(narration, effective_action)

    preserve_bounded_dialogue = beat_type == "freeform_roleplay" and _has_bounded_dialogue_event(events, debug=debug)
    if preserve_bounded_dialogue:
        narration = ""

    if narration:
        room_name = next_state.world.rooms[next_state.player.location].name
        turn_text = narration.strip()
        if turn_text and not turn_text.lower().startswith(room_name.lower()):
            turn_text = f"{room_name}\n{turn_text}"
        lines: list[str] = [turn_text]
    else:
        lines = []
        if _should_render_room_block(state, next_state, effective_action):
            lines.append(
                _room_lines(
                    next_state,
                    long_form=effective_action.kind == ActionKind.LOOK,
                )
            )
        if effective_action.kind == ActionKind.INVENTORY:
            lines.extend(_inventory_lines(next_state))
        event_line = _event_lines(events, debug=debug)
        if event_line:
            lines.append(event_line)

    if debug:
        lines.extend(caseboard_lines(next_state))

    if debug:
        lines.append(
            f"[debug] turn={next_state.turn_index} phase={get_phase(next_state.progress)} "
            f"tension={next_state.tension:.2f} progress={next_state.progress:.2f} "
            f"beat={beat_type} plot_event={template_key}"
        )
        lines.append(f"[debug] event_types={tuple(event.type for event in events)}")
        context_keys = tuple(context.as_dict().keys()) if context is not None else ("freeform_roleplay",)
        lines.append(f"[debug] context_keys={context_keys}")
        if freeform_policy_debug is not None:
            proposal = freeform_policy_debug["action_proposal"]
            envelope = freeform_policy_debug["state_update_envelope"]
            lines.append(
                "[debug] freeform_policy "
                f"intent={proposal.get('intent', '')} "
                f"targets={tuple(proposal.get('targets', ())) } "
                f"reasons={tuple(envelope.get('reasons', ())) } "
                f"fact_ops={tuple(freeform_policy_debug['fact_ops'])} "
                f"story_delta={freeform_policy_debug['story_delta']}"
            )
        lines.append(
            f"[debug] judge_status={judge_decision['status']} total={judge_decision['total_score']} "
            f"threshold={judge_decision['threshold']} round={judge_decision['round_index']} "
            f"critics={judge_decision['critic_ids']} components={judge_decision['rubric_components']} "
            f"decision_id={judge_decision['decision_id']}"
        )
        lines.append(
            f"[debug] coherence_budget rounds={coherence_telemetry['critique_rounds']} "
            f"tokens={coherence_telemetry['token_spend']} elapsed_ms={coherence_telemetry['elapsed_ms']} "
            f"hard_fail_reason={coherence_telemetry['hard_fail_reason']}"
        )
        debug_trace = {
            "turn": next_state.turn_index,
            "phase": str(get_phase(next_state.progress)),
            "tension": round(next_state.tension, 4),
            "progress": round(next_state.progress, 4),
            "beat": beat_type,
            "plot_event": template_key,
            "events": [event.type for event in events],
            "freeform_policy": freeform_policy_debug,
            "judge": {
                "status": judge_decision["status"],
                "total_score": judge_decision["total_score"],
                "threshold": judge_decision["threshold"],
                "round_index": judge_decision["round_index"],
                "critic_ids": list(judge_decision["critic_ids"]),
                "rubric_components": judge_decision["rubric_components"],
                "decision_id": judge_decision["decision_id"],
            },
            "coherence": coherence_telemetry,
        }
        lines.append("[debug-json] " + json.dumps(debug_trace, sort_keys=True))

    if next_state.progress >= 0.95:
        lines.append("Objective complete.")

    if memory_store is not None:
        memory_store.ingest_events(memory_slot, next_state, events)

    next_state.last_judge_decision = {
        "decision_id": str(judge_decision["decision_id"]),
        "status": str(judge_decision["status"]),
        "judge": "director",
        "rationale": str(judge_decision.get("rationale", "")),
    }

    lines = [_rewrite_known_npc_names(next_state, line) for line in lines if line]
    lines = _suppress_repeated_goal_copy(lines, raw_input, next_state.active_goal)
    if not lines:
        lines = [_room_lines(next_state, long_form=True)] if effective_action.kind == ActionKind.LOOK else [""]
        lines = [line for line in lines if line]

    reviewed_lines = director.review_turn(next_state, [line for line in lines if line], events, debug)
    reviewed_lines = [_rewrite_known_npc_names(next_state, line) for line in reviewed_lines if line]
    reviewed_lines = _suppress_repeated_goal_copy(reviewed_lines, raw_input, next_state.active_goal)
    if (
        narration
        and not _contains_repeated_goal_copy(narration, raw_input, next_state.active_goal)
        and not _has_similar_narration(reviewed_lines, narration)
    ):
        reviewed_lines.append(_rewrite_known_npc_names(next_state, narration))
    return next_state, reviewed_lines, effective_action.raw, beat_type, True


def run_replay(
    seed: int,
    commands: list[str],
    genre: str = "mystery",
    session_length: int | str = "medium",
    tone: str = "neutral",
    debug: bool = False,
    save_db: Path | None = None,
    memory_db: Path | None = None,
    memory_slot: str = "default",
    narrator: Narrator | None = None,
    narrator_mode: str = "openai",
) -> GameState:
    rng = Random(seed)
    state = build_default_state(seed, genre=genre, session_length=session_length, tone=tone)
    active_narrator: Narrator = _build_narrator(narrator_mode) if narrator is None else narrator
    save_store: SqliteSaveStore | None = SqliteSaveStore(save_db) if save_db is not None else None
    memory_store: SqliteVectorMemory | None = SqliteVectorMemory(memory_db) if memory_db is not None else None
    try:
        for command in commands:
            state, _output, _action, _beat, _continued = run_turn(
                state,
                command,
                rng,
                active_narrator,
                debug=debug,
                save_store=save_store,
                memory_store=memory_store,
                memory_slot=memory_slot,
                narrator_mode=narrator_mode,
            )
            if not _continued:
                break
    finally:
        if save_store is not None:
            save_store.close()
        if memory_store is not None:
            memory_store.close()
    return state


def main(argv: list[str] | None = None) -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Freytag text adventure")
    parser.add_argument("--seed", type=int, default=123, help="Random seed for deterministic play")
    parser.add_argument(
        "--genre",
        choices=(
            "sci-fi",
            "mystery",
            "romance",
            "adventure",
            "action",
            "suspense",
            "drama",
            "fantasy",
            "horror",
            "thriller",
        ),
        default="mystery",
        help="Story genre used for startup curve selection.",
    )
    parser.add_argument(
        "--session-length",
        choices=("short", "medium", "long"),
        default="medium",
        help="Session-length bucket used for startup curve selection.",
    )
    parser.add_argument(
        "--tone",
        choices=("neutral", "dark", "light", "romantic", "tense", "mysterious", "epic"),
        default="neutral",
        help="Optional tone preference used for outline selection.",
    )
    parser.add_argument("--replay", type=Path, default=None, help="Replay commands from a file")
    parser.add_argument("--save-db", type=Path, default=None, help="SQLite save file path")
    parser.add_argument("--memory-db", type=Path, default=None, help="SQLite vector memory file path")
    parser.add_argument("--memory-slot", default="default", help="Memory slot key for retrieval and storage")
    parser.add_argument("--debug", action="store_true", help="Print phase and beat diagnostics")
    parser.add_argument(
        "--autosave-slot",
        default=None,
        help="Auto-save state each turn to this slot (optional).",
    )
    parser.add_argument("--transcript", type=Path, default=None, help="Write transcript to a file")
    parser.add_argument(
        "--narrator",
        choices=("openai", "ollama"),
        default="openai",
        help="Narration mode.",
    )

    args = parser.parse_args(argv)
    console = Console()

    state = build_default_state(
        args.seed,
        genre=args.genre,
        session_length=args.session_length,
        tone=args.tone,
    )
    rng = Random(args.seed)
    narrator: Narrator = _build_narrator(args.narrator)
    output_editor = build_output_editor(args.narrator)
    story_director = StoryDirector(args.narrator, output_editor)
    save_store: SqliteSaveStore | None = SqliteSaveStore(args.save_db) if args.save_db is not None else None
    memory_store: SqliteVectorMemory | None = SqliteVectorMemory(args.memory_db) if args.memory_db is not None else None
    autosave_slot = args.autosave_slot
    memory_slot = args.memory_slot

    transcript_path = args.transcript
    if transcript_path is None and args.replay is not None:
        transcript_path = Path("runs") / f"replay_seed_{args.seed}.txt"

    transcript_handle: TextIO | None = None
    if transcript_path is not None:
        transcript_path.parent.mkdir(parents=True, exist_ok=True)
        transcript_handle = transcript_path.open("w", encoding="utf-8")

    try:
        setup_lines = story_director.compose_opening(state)
        for line in _with_paragraph_spacing(setup_lines):
            _emit_cli_line(console, line)
            _write_transcript_line(transcript_handle, line)

        if args.replay is not None:
            commands = [line.strip() for line in args.replay.read_text().splitlines() if line.strip()]
            for command in commands:
                _write_transcript_command_echo(transcript_handle, command)
                state, lines, _action, _beat, _ = run_turn(
                    state,
                    command,
                    rng,
                    narrator,
                    debug=args.debug,
                    save_store=save_store,
                    memory_store=memory_store,
                    memory_slot=memory_slot,
                    output_editor=output_editor,
                    story_director=story_director,
                    narrator_mode=args.narrator,
                )
                if autosave_slot is not None and save_store is not None:
                    save_store.save_run(
                        autosave_slot,
                        state,
                        rng,
                        raw_command=command,
                        action_kind="autosave",
                        judge_decision=_judge_decision_for_persistence(state),
                    )
                for line in lines:
                    _emit_cli_line(console, line)
                    _write_transcript_line(transcript_handle, line)
            return

        while True:
            raw = input("> ")
            _write_transcript_command_echo(transcript_handle, raw)
            state, lines, action_raw, _, continued = run_turn(
                state,
                raw,
                rng,
                narrator,
                debug=args.debug,
                save_store=save_store,
                memory_store=memory_store,
                memory_slot=memory_slot,
                output_editor=output_editor,
                story_director=story_director,
                narrator_mode=args.narrator,
            )
            for line in lines:
                _emit_cli_line(console, line)
                _write_transcript_line(transcript_handle, line)
            if action_raw.lower() in {"quit", "exit", "leave"}:
                break
            if not continued:
                break

            if autosave_slot is not None and save_store is not None:
                save_store.save_run(
                    autosave_slot,
                    state,
                    rng,
                    raw_command=raw,
                    action_kind="autosave",
                    judge_decision=_judge_decision_for_persistence(state),
                )
    finally:
        if transcript_handle is not None:
            transcript_handle.close()
        if save_store is not None:
            save_store.close()
        if memory_store is not None:
            memory_store.close()


if __name__ == "__main__":
    main()
