from __future__ import annotations

from collections import deque
from pathlib import Path
from random import Random
from typing import Protocol, TextIO

from storygame.engine.mystery import caseboard_lines, room_item_groups
from storygame.engine.parser import ActionKind, parse_command
from storygame.engine.simulation import advance_turn
from storygame.engine.state import GameState
from storygame.engine.world import build_default_state
from storygame.llm.adapters import MockNarrator, Narrator, OllamaAdapter, OpenAIAdapter, SilentNarrator
from storygame.llm.context import build_narration_context
from storygame.memory import MAX_MEMORY_NOTES, MemoryStore, SqliteVectorMemory, normalize_tag
from storygame.persistence.savegame_sqlite import SqliteSaveStore
from storygame.plot.freytag import get_phase


def _room_distance(state: GameState, start_room_id: str, target_room_id: str) -> int | None:
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
    source_room = "sanctuary"
    if source_room not in state.world.rooms:
        return ""

    room = state.world.rooms[state.player.location]
    if not room.exits:
        return ""
    if room.id == source_room:
        return "Signal: The resonance source is directly beneath this sanctuary floor."

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
    return "Signal: Echoes refract through stone, but the resonance is stronger toward " f"{direction_text}."


def _opening_briefing_lines(state: GameState) -> tuple[str, ...]:
    return (
        "Before dawn, forged emergency tones emptied the harbor while conspirators raided sealed archive ledgers.",
        "Your mentor was framed for those false alarms; proving the conspiracy is the only way to clear their name.",
        f"Objective: {state.active_goal}",
    )


def _room_lines(state: GameState) -> str:
    room = state.world.rooms[state.player.location]
    pieces = [f"[{room.name}]", room.description]
    signal_hint = _signal_hint(state)
    if signal_hint:
        pieces.append(signal_hint)
    actionable_items, junk_count = room_item_groups(state, room)
    if actionable_items:
        pieces.append("Items: " + ", ".join(actionable_items))
    if junk_count > 0:
        suffix = "item" if junk_count == 1 else "items"
        pieces.append(f"Junk nearby: {junk_count} {suffix}.")
    if room.npc_ids:
        pieces.append("NPCs: " + ", ".join(room.npc_ids))
    if room.exits:
        pieces.append("Exits: " + ", ".join(sorted(room.exits.keys())))
    return "\n".join(pieces)


def _event_lines(events) -> str:
    if not events:
        return ""
    return "\n".join(f"- {event.type}: {event.message_key}" for event in events)


def _write_transcript_line(handle: TextIO | None, line: str) -> None:
    if handle is None:
        return
    handle.write(line + "\n")


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
    ) -> None: ...

    def load_run(self, slot: str) -> tuple[GameState, Random]: ...


def run_turn(
    state: GameState,
    raw: str,
    rng: Random,
    narrator: Narrator,
    debug: bool = False,
    save_store: SaveStore | None = None,
    memory_store: MemoryStore | None = None,
    memory_slot: str = "default",
):
    show_opening_briefing = state.turn_index == 0
    action = parse_command(raw)
    if action.kind == ActionKind.QUIT:
        return state, ["Goodbye."], "", "", False

    if action.kind == ActionKind.SAVE:
        if not action.target:
            return state, ["Usage: save <slot>."], action.raw, "save", True
        if save_store is None:
            return state, ["Save requires --save-db <path>."], action.raw, "save", True
        try:
            save_store.save_run(action.target, state, rng, raw_command=action.raw, action_kind="save")
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

    next_state, events, beat_type, template_key = advance_turn(state, action, rng)
    memory_fragments: tuple[str, ...] = ()
    if memory_store is not None:
        memory_fragments = memory_store.retrieve(memory_slot, _build_memory_tag_set(next_state, action))

    context = build_narration_context(next_state, action, beat_type, memory_fragments)
    try:
        narration = narrator.generate(context)
    except RuntimeError as exc:
        narration = f"[Narrator failed: {exc}]"

    lines: list[str] = []
    if show_opening_briefing:
        lines.extend(_opening_briefing_lines(next_state))
    lines.extend([_room_lines(next_state), _event_lines(events)])
    lines.extend(caseboard_lines(next_state))
    if narration:
        lines.append(narration)

    if debug:
        lines.append(
            f"[debug] turn={next_state.turn_index} phase={get_phase(next_state.progress)} "
            f"tension={next_state.tension:.2f} progress={next_state.progress:.2f} "
            f"beat={beat_type} plot_event={template_key}"
        )
        lines.append(f"[debug] event_types={tuple(event.type for event in events)}")
        lines.append(f"[debug] context_keys={tuple(context.as_dict().keys())}")

    if next_state.progress >= 0.95:
        lines.append("Objective complete.")

    if memory_store is not None:
        memory_store.ingest_events(memory_slot, next_state, events)

    return next_state, [line for line in lines if line], action.raw, beat_type, True


def run_replay(
    seed: int,
    commands: list[str],
    debug: bool = False,
    save_db: Path | None = None,
    memory_db: Path | None = None,
    memory_slot: str = "default",
) -> GameState:
    rng = Random(seed)
    state = build_default_state(seed)
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

    state = build_default_state(args.seed)
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
        print(header)
        _write_transcript_line(transcript_handle, header)

        if args.replay is not None:
            commands = [line.strip() for line in args.replay.read_text().splitlines() if line.strip()]
            for command in commands:
                _write_transcript_line(transcript_handle, f"CMD {command}")
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
                    )
                for line in lines:
                    print(line)
                    _write_transcript_line(transcript_handle, line)
            return

        while True:
            raw = input("> ")
            _write_transcript_line(transcript_handle, f"CMD {raw}")
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
                print(line)
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
