from __future__ import annotations

import json
import re
from collections import deque
from pathlib import Path
from random import Random
from typing import Any, Protocol, TextIO

from rich.console import Console

from storygame.engine.freeform import DEFAULT_FREEFORM_ADAPTER, FreeformProposalAdapter, resolve_freeform_roleplay
from storygame.engine.impact import assess_player_command, requires_high_impact_confirmation
from storygame.engine.mystery import caseboard_lines, room_item_groups
from storygame.engine.parser import ActionKind, parse_command
from storygame.engine.simulation import advance_turn
from storygame.engine.state import Event, GameState
from storygame.engine.world import build_default_state
from storygame.llm.adapters import Narrator, OllamaAdapter, OpenAIAdapter
from storygame.llm.coherence import build_default_coherence_gate
from storygame.llm.context import build_narration_context
from storygame.llm.output_editor import OutputEditor, build_output_editor
from storygame.llm.story_director import StoryDirector
from storygame.memory import MAX_MEMORY_NOTES, MemoryStore, SqliteVectorMemory, normalize_tag
from storygame.persistence.savegame_sqlite import SqliteSaveStore
from storygame.plot.freytag import get_phase


def _room_distance(state: GameState, start_room_id: str, target_room_id: str) -> int | None:
    if start_room_id not in state.world.rooms or target_room_id not in state.world.rooms:
        return None
    if start_room_id == target_room_id:
        return 0
    visited = {start_room_id}
    frontier = deque([(start_room_id, 0)])
    while frontier:
        room_id, distance = frontier.popleft()
        room = state.world.rooms[room_id]
        for _direction, next_room_id in room.exits.items():
            if next_room_id in visited:
                continue
            if next_room_id == target_room_id:
                return distance + 1
            visited.add(next_room_id)
            frontier.append((next_room_id, distance + 1))
    return None


def _signal_hint(state: GameState) -> str:
    map_rooms = tuple(state.world_package.get("map", {}).get("rooms", ()))
    if not map_rooms:
        return ""
    source_room = map_rooms[-1]
    if source_room not in state.world.rooms:
        return ""

    room = state.world.rooms[state.player.location]
    if not room.exits:
        return ""
    if room.id == source_room:
        return "Signal: The objective signal source is directly beneath this location."

    best_distance: int | None = None
    best_directions: list[str] = []
    for direction, destination in room.exits.items():
        distance = _room_distance(state, destination, source_room)
        if distance is None:
            continue
        if best_distance is None or distance < best_distance:
            best_distance = distance
            best_directions = [direction]
            continue
        if distance == best_distance:
            best_directions.append(direction)

    if not best_directions:
        return "Signal: The tone is muffled here; no clear path stands out."

    direction_text = "/".join(sorted(best_directions))
    return f"Signal: Echoes refract through stone, but the resonance is stronger toward {direction_text}."


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


def _room_lines(state: GameState) -> str:
    room = state.world.rooms[state.player.location]
    pieces = [room.name, room.description]
    signal_hint = _signal_hint(state)
    actionable_items, junk_count = room_item_groups(state, room)
    if actionable_items:
        visible_items = tuple(_humanize_token(item) for item in actionable_items)
        pieces.append(f"You can see {_joined_with_and(visible_items)}.")
    if junk_count > 0:
        suffix = "item" if junk_count == 1 else "items"
        verb = "is" if junk_count == 1 else "are"
        pieces.append(f"There {verb} {junk_count} other unremarkable {suffix} nearby.")
    if room.exits:
        exits = tuple(sorted(room.exits.keys()))
        if len(exits) == 1:
            pieces.append(f"The only exit is to the {exits[0]}.")
        else:
            pieces.append(f"Exits lead {_joined_with_and([f'to the {direction}' for direction in exits])}.")
    if room.npc_ids:
        visible_npcs = tuple(_humanize_token(npc) for npc in room.npc_ids)
        verb = "is" if len(visible_npcs) == 1 else "are"
        pieces.append(f"{_joined_with_and(list(visible_npcs)).title()} {verb} here.")
    if signal_hint:
        pieces.append(signal_hint.replace("Signal: ", ""))
    return "\n".join(pieces)


def _setup_phase_lines(state: GameState, story_director: StoryDirector | None = None) -> list[str]:
    director = StoryDirector("openai") if story_director is None else story_director
    return director.compose_opening(state)


_PROCEED_WORDS = {"proceed", "confirm", "yes", "y"}
_CANCEL_WORDS = {"cancel", "abort", "no", "n"}


def _clear_pending_high_impact(state: GameState) -> None:
    state.pending_high_impact_command = ""
    state.pending_high_impact_assessment = {}


def _high_impact_warning_lines(assessment: dict[str, Any]) -> list[str]:
    impact_class = str(assessment.get("impact_class", "high")).upper()
    consequences = [str(item).strip() for item in assessment.get("consequences", []) if str(item).strip()]
    lines = [
        f"High-impact action detected ({impact_class}). This may alter goals, NPC behavior, and event timing.",
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
    state.player.flags["story_replan_required"] = True
    state.player.flags["story_bounds_overridden"] = True
    state.world_package["story_replan_context"] = {
        "command": raw_command,
        "impact_class": str(assessment.get("impact_class", "high")),
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


def _transcript_command_echo(raw_command: str) -> str:
    return f">{raw_command.strip().upper()}"


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

    action = parse_command(raw)
    if action.kind == ActionKind.QUIT:
        return state, ["Goodbye."], "", "", False

    if action.kind == ActionKind.SAVE:
        if not action.target:
            return state, ["Usage: save <slot>."], action.raw, "save", True
        if save_store is None:
            return state, ["Save requires --save-db <path>."], action.raw, "save", True
        try:
            save_store.save_run(
                action.target,
                state,
                rng,
                raw_command=action.raw,
                action_kind="save",
                judge_decision=_judge_decision_for_persistence(state),
            )
            return state, [f"Saved to slot '{action.target}'."], action.raw, "save", True
        except Exception as exc:
            return state, [f"Failed to save: {exc}"], action.raw, "save", True

    if action.kind == ActionKind.LOAD:
        if not action.target:
            return state, ["Usage: load <slot>."], action.raw, "load", True
        if save_store is None:
            return state, ["Load requires --save-db <path>."], action.raw, "load", True
        try:
            state, loaded_rng = save_store.load_run(action.target)
            rng.setstate(loaded_rng.getstate())
            return (
                state,
                [_room_lines(state), f"Loaded from slot '{action.target}'."],
                action.raw,
                "load",
                True,
            )
        except ValueError as exc:
            return state, [f"Could not load slot '{action.target}': {exc}"], action.raw, "load", True
        except Exception as exc:
            return state, [f"Failed to load: {exc}"], action.raw, "load", True

    impact_assessment = (
        _confirmed_assessment
        if _confirmed_assessment is not None
        else assess_player_command(state, action.raw, action)
    )
    if not _confirmed_high_impact and requires_high_impact_confirmation(impact_assessment):
        blocked_state = state.clone()
        blocked_state.pending_high_impact_command = action.raw
        blocked_state.pending_high_impact_assessment = dict(impact_assessment)
        return blocked_state, _high_impact_warning_lines(impact_assessment), action.raw, "impact_gate", True

    editor = build_output_editor(narrator_mode) if output_editor is None else output_editor
    director = StoryDirector(narrator_mode, editor) if story_director is None else story_director
    preturn_state = state
    replan_event = None
    if state.player.flags.get("story_replan_required", False):
        preturn_state = state.clone()
        replan_event = director.replan_if_needed(preturn_state)
    if replan_event is not None:
        preturn_state.append_event(replan_event)

    if action.kind == ActionKind.UNKNOWN:
        freeform = resolve_freeform_roleplay(preturn_state, action.raw, freeform_adapter)
        next_state = freeform["state"]
        events = [freeform["event"]]
        if replan_event is not None:
            events.insert(0, replan_event)
        beat_type = "freeform_roleplay"
        template_key = "freeform_roleplay"
        context = None
        judge_decision = {
            "status": "accepted",
            "total_score": 100,
            "threshold": 80,
            "round_index": 0,
            "critic_ids": (),
            "rubric_components": {},
            "decision_id": "freeform-policy-approved",
        }
        coherence_telemetry = {
            "critique_rounds": 0,
            "token_spend": {"narrator": 0, "critics": 0},
            "elapsed_ms": 0,
            "hard_fail_reason": "FREEFORM_PATH",
        }
        narration = ""
    else:
        next_state, events, beat_type, template_key = advance_turn(preturn_state, action, rng)
        if replan_event is not None:
            events.insert(0, replan_event)
        memory_fragments: tuple[str, ...] = ()
        if memory_store is not None:
            memory_fragments = memory_store.retrieve(memory_slot, _build_memory_tag_set(next_state, action))

        context = build_narration_context(next_state, action, beat_type, memory_fragments)
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
            narration = f"[Narrator failed: {exc}]"

    if _confirmed_high_impact:
        _record_major_disruption(next_state, events, action.raw, impact_assessment)

    lines: list[str] = [_room_lines(next_state)]
    if action.kind == ActionKind.INVENTORY:
        lines.extend(_inventory_lines(next_state))
    event_line = _event_lines(events, debug=debug)
    if event_line:
        lines.append(event_line)
    if debug:
        lines.extend(caseboard_lines(next_state))
    narration = _sanitize_narration_for_player(narration, debug=debug)
    if narration:
        lines.append(narration)

    if debug:
        lines.append(
            f"[debug] turn={next_state.turn_index} phase={get_phase(next_state.progress)} "
            f"tension={next_state.tension:.2f} progress={next_state.progress:.2f} "
            f"beat={beat_type} plot_event={template_key}"
        )
        lines.append(f"[debug] event_types={tuple(event.type for event in events)}")
        context_keys = tuple(context.as_dict().keys()) if context is not None else ("freeform_roleplay",)
        lines.append(f"[debug] context_keys={context_keys}")
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

    reviewed_lines = director.review_turn(next_state, [line for line in lines if line], events, debug)
    return next_state, reviewed_lines, action.raw, beat_type, True


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
        for line in setup_lines:
            _emit_cli_line(console, line)
            _write_transcript_line(transcript_handle, line)

        if args.replay is not None:
            commands = [line.strip() for line in args.replay.read_text().splitlines() if line.strip()]
            for command in commands:
                _write_transcript_line(transcript_handle, _transcript_command_echo(command))
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
            _write_transcript_line(transcript_handle, _transcript_command_echo(raw))
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
