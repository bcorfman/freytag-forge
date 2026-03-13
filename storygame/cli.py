from __future__ import annotations

import json
import re
from collections import deque
from pathlib import Path
from random import Random
from typing import Protocol, TextIO

from rich.console import Console

from storygame.engine.freeform import DEFAULT_FREEFORM_ADAPTER, FreeformProposalAdapter, resolve_freeform_roleplay
from storygame.engine.mystery import caseboard_lines, room_item_groups
from storygame.engine.parser import ActionKind, parse_command
from storygame.engine.simulation import advance_turn
from storygame.engine.state import GameState
from storygame.engine.world import build_default_state
from storygame.llm.adapters import MockNarrator, Narrator, OllamaAdapter, OpenAIAdapter, SilentNarrator
from storygame.llm.coherence import build_default_coherence_gate
from storygame.llm.context import build_narration_context
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
    if room.npc_ids:
        visible_npcs = tuple(_humanize_token(npc) for npc in room.npc_ids)
        verb = "is" if len(visible_npcs) == 1 else "are"
        pieces.append(f"{_joined_with_and(list(visible_npcs)).title()} {verb} here.")
    if room.exits:
        exits = tuple(sorted(room.exits.keys()))
        if len(exits) == 1:
            pieces.append(f"The only exit is to the {exits[0]}.")
        else:
            pieces.append(f"Exits lead {_joined_with_and([f'to the {direction}' for direction in exits])}.")
    if signal_hint:
        pieces.append(signal_hint.replace("Signal: ", ""))
    return "\n".join(pieces)


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
    if mode == "mock":
        return MockNarrator()
    if mode == "openai":
        return OpenAIAdapter()
    if mode == "ollama":
        return OllamaAdapter()
    return SilentNarrator()


def _build_memory_tag_set(state: GameState, action) -> tuple[str, ...]:
    room = state.world.rooms[state.player.location]
    action_target = normalize_tag(action.target) if action.target else ""
    goal_words = tuple(normalize_tag(word) for word in state.active_goal.split() if word)[:2]
    base_tags = (
        f"room_{state.player.location}",
        f"beat_{state.beat_history[-1]}" if state.beat_history else "beat_unknown",
        f"goal_{goal_words[0]}" if goal_words else "goal",
    )
    npc_tags = tuple(f"npc_{npc}" for npc in room.npc_ids)
    return tuple(sorted(set(base_tags + (action_target,) + npc_tags)))[:MAX_MEMORY_NOTES]


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
):
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

    if action.kind == ActionKind.UNKNOWN:
        freeform = resolve_freeform_roleplay(state, action.raw, freeform_adapter)
        next_state = freeform["state"]
        events = [freeform["event"]]
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
        next_state, events, beat_type, template_key = advance_turn(state, action, rng)
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

    return next_state, [line for line in lines if line], action.raw, beat_type, True


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
) -> GameState:
    rng = Random(seed)
    state = build_default_state(seed, genre=genre, session_length=session_length, tone=tone)
    narrator: Narrator = MockNarrator()
    save_store: SqliteSaveStore | None = SqliteSaveStore(save_db) if save_db is not None else None
    memory_store: SqliteVectorMemory | None = SqliteVectorMemory(memory_db) if memory_db is not None else None
    try:
        for command in commands:
            state, _output, _action, _beat, _continued = run_turn(
                state,
                command,
                rng,
                narrator,
                debug=debug,
                save_store=save_store,
                memory_store=memory_store,
                memory_slot=memory_slot,
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
        choices=("mock", "none", "openai", "ollama"),
        default="mock",
        help="Narration mode. 'none' keeps engine-only output.",
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
        header = _room_lines(state)
        _emit_cli_line(console, header)
        _write_transcript_line(transcript_handle, header)

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
