from __future__ import annotations

from pathlib import Path
from random import Random
from typing import TextIO

from storygame.engine.parser import ActionKind, parse_command
from storygame.engine.simulation import advance_turn
from storygame.engine.state import GameState
from storygame.engine.world import build_default_state
from storygame.llm.adapters import MockNarrator, Narrator, SilentNarrator
from storygame.llm.context import build_narration_context
from storygame.plot.freytag import get_phase


def _room_lines(state: GameState) -> str:
    room = state.world.rooms[state.player.location]
    pieces = [f"[{room.name}]", room.description]
    if room.item_ids:
        pieces.append("Items: " + ", ".join(room.item_ids))
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


def run_turn(state: GameState, raw: str, rng: Random, narrator: Narrator, debug: bool = False):
    action = parse_command(raw)
    if action.kind == ActionKind.QUIT:
        return state, ["Goodbye."], "", "", False

    next_state, events, beat_type, template_key = advance_turn(state, action, rng)
    context = build_narration_context(next_state, action, beat_type)
    narration = narrator.generate(context)

    lines = [_room_lines(next_state), _event_lines(events)]
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

    return next_state, [line for line in lines if line], action.raw, beat_type, True


def run_replay(seed: int, commands: list[str], debug: bool = False) -> GameState:
    rng = Random(seed)
    state = build_default_state(seed)
    narrator: Narrator = MockNarrator()
    for command in commands:
        state, _output, _action, _beat, _continued = run_turn(
            state,
            command,
            rng,
            narrator,
            debug=debug,
        )
    return state


def main(argv: list[str] | None = None) -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Freytag text adventure")
    parser.add_argument("--seed", type=int, default=123, help="Random seed for deterministic play")
    parser.add_argument("--replay", type=Path, default=None, help="Replay commands from a file")
    parser.add_argument("--debug", action="store_true", help="Print phase and beat diagnostics")
    parser.add_argument("--transcript", type=Path, default=None, help="Write transcript to a file")
    parser.add_argument(
        "--narrator",
        choices=("mock", "none"),
        default="mock",
        help="Narration mode. 'none' keeps engine-only output.",
    )

    args = parser.parse_args(argv)

    state = build_default_state(args.seed)
    rng = Random(args.seed)
    narrator: Narrator = MockNarrator() if args.narrator == "mock" else SilentNarrator()

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
            )
            for line in lines:
                print(line)
                _write_transcript_line(transcript_handle, line)
            if action_raw.lower() in {"quit", "exit", "leave"}:
                break
            if not continued:
                break
    finally:
        if transcript_handle is not None:
            transcript_handle.close()


if __name__ == "__main__":
    main()
