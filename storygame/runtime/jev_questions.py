"""Story-agnostic question builders for structured Jev evaluations."""

from __future__ import annotations

from collections.abc import Callable

from storygame.runtime.jev import noul_yes


def _answer(ask: Callable[[object, object], dict | None], state, questions, key: str) -> bool | None:
    try:
        answers = ask(state, questions)
        return noul_yes(answers[key]) if isinstance(answers, dict) and key in answers else None
    except Exception:
        return None


def uses_thing(ask, command: str, thing_name: str) -> bool | None:
    questions = {
        "uses_thing": {
            "type": "noul",
            "instructions": (
                "Using a thing means working on it: reading it, typing on it, "
                "searching its files, or working with what is on its screen. "
                "Opening, closing, turning it on or off, moving, carrying, "
                "picking it up, and putting it down are not using it."
            ),
            "criteria": {
                "true": "The command means working on the thing or working with what is on its screen.",
                "false": (
                    "The command only opens, closes, turns the thing on or off, moves, carries, "
                    "picks up, or puts down the thing."
                ),
            },
        }
    }
    return _answer(ask, {"command": command, "thing": thing_name}, questions, "uses_thing")


def moves_thing(ask, command: str, thing_name: str) -> bool | None:
    questions = {
        "moves_thing": {
            "type": "noul",
            "instructions": (
                "Moving a thing means the command puts it somewhere, places it, stores it, "
                "or hands it to someone. The player must hold it first."
            ),
            "criteria": {
                "true": "The command puts, places, stores, or hands over the thing.",
                "false": (
                    "The command already says to pick up or take the thing, or it only looks at, "
                    "reads, searches, or talks about the thing."
                ),
            },
        }
    }
    return _answer(ask, {"command": command, "thing": thing_name}, questions, "moves_thing")


def needs_to_stand(ask, command: str, seat_name: str, within_reach) -> bool | None:
    questions = {
        "needs_to_stand": {
            "type": "noul",
            "instructions": (
                "The player's character is sitting in the seat. Decide if the command needs "
                "another place or a thing outside within_reach."
            ),
            "criteria": {
                "true": "The command means going to another place or acting on a thing outside within_reach.",
                "false": (
                    "The command only acts on things in within_reach, or only talks, looks, or listens from the seat."
                ),
            },
        }
    }
    return _answer(
        ask,
        {"command": command, "seat": seat_name, "within_reach": list(within_reach)},
        questions,
        "needs_to_stand",
    )


def same_or_part(ask, command: str, story: str, question: str, statement: str, player, known) -> bool | None:
    questions = {
        "same_or_part": {
            "type": "noul",
            "instructions": f"{question} Use story, player and known to decide what is most likely.",
            "criteria": {
                "true": f"Most likely, {statement}.",
                "false": f"Most likely, this is not so: {statement}.",
            },
        }
    }
    return _answer(
        ask,
        {"command": command, "story": story, "player": player, "known": known},
        questions,
        "same_or_part",
    )
