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


def boards_vehicle(ask, command: str, vehicle_name: str) -> bool | None:
    questions = {
        "boards_vehicle": {
            "type": "noul",
            "instructions": (
                "Decide whether the command has the player go to the vehicle to use it. "
                "A command that only says go to the vehicle means the player gets in. "
                "The command can have the player get into it. "
                "The command can have the player sit in it. "
                "The command can have the player drive it."
            ),
            "criteria": {
                "true": (
                    "The command has the player go to the vehicle to use it. "
                    "A command that only says go to the vehicle means the player gets in. "
                    "The command has the player get into it. "
                    "The command has the player sit in it. "
                    "The command has the player drive it."
                ),
                "false": (
                    "The command is not boarding if it only walks over to or walks up to the vehicle. "
                    "It is not boarding if it only approaches, looks at, touches, or talks about the vehicle. "
                    "It is not boarding if it leaves the vehicle."
                ),
            },
        }
    }
    return _answer(ask, {"command": command, "vehicle": vehicle_name}, questions, "boards_vehicle")


def opens_container(ask, command: str, container_name: str) -> bool | None:
    questions = {
        "opens_container": {
            "type": "noul",
            "instructions": (
                "Decide whether the command has the player open the container. "
                "This includes a command to look inside it by opening it."
            ),
            "criteria": {
                "true": (
                    "The command has the player open the container. "
                    "The command can have the player look inside it by opening it."
                ),
                "false": ("The command only looks at, closes, touches, moves, carries, or talks about the container."),
            },
        }
    }
    return _answer(ask, {"command": command, "container": container_name}, questions, "opens_container")


def searches_underneath(ask, command: str, thing_name: str) -> bool | None:
    questions = {
        "searches_underneath": {
            "type": "noul",
            "instructions": (
                "Decide whether the command has the player search, feel, reach, or look under, beneath, "
                "or below the thing."
            ),
            "criteria": {
                "true": ("The command has the player search, feel, reach, or look under, beneath, or below the thing."),
                "false": (
                    "The command only looks at, opens, touches, moves, carries, talks about, or goes to the thing. "
                    "It only looks inside the thing without looking under, beneath, or below it."
                ),
            },
        }
    }
    return _answer(ask, {"command": command, "thing": thing_name}, questions, "searches_underneath")


def only_boards_vehicle(ask, command: str, vehicle_name: str) -> bool | None:
    questions = {
        "only_boards_vehicle": {
            "type": "noul",
            "instructions": "Decide whether the command asks for nothing more than getting to or into the vehicle.",
            "criteria": {
                "true": "The command only goes to, gets into, or sits in the vehicle.",
                "false": "The command also asks for another action, such as driving, searching, looking, or talking.",
            },
        }
    }
    return _answer(ask, {"command": command, "vehicle": vehicle_name}, questions, "only_boards_vehicle")


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


def relocates_thing(ask, command: str, thing_name: str) -> bool | None:
    questions = {
        "relocates_thing": {
            "type": "noul",
            "instructions": (
                "Relocating a thing means the command lifts it, picks it up, carries it, drags it, pushes it, "
                "slides it, takes it out or off of where it is, removes it, detaches it, or puts it somewhere else. "
                "It also means it tilts it, tips it over, rotates it, turns it around, rolls it, nudges it, shifts it, "
                "or repositions it."
            ),
            "criteria": {
                "true": (
                    "The command makes the player relocate this thing. A command that lifts this thing and then puts "
                    "it back where it was, or lowers it back into place, still relocates it."
                ),
                "false": (
                    "The command uses the thing where it is: opening, closing, sitting in, looking at, reading, or "
                    "searching it. It also covers a command that moves some other thing onto, into, off, or out of "
                    "this thing. If this thing is only "
                    "the place another thing is taken from or put on, such as "
                    "retrieving a laptop from the passenger seat or putting a laptop on the workstation, it does not "
                    "count as relocating this thing. A part used as designed is not relocating the thing: a door swung "
                    "open or shut, a drawer slid open or shut, a lid opened, or a screen tilted back on its own hinge."
                ),
            },
        }
    }
    return _answer(ask, {"command": command, "thing": thing_name}, questions, "relocates_thing")


def names_other_action(ask, command: str, things_text: str) -> bool | None:
    questions = {
        "names_other_action": {
            "type": "noul",
            "instructions": (
                "Decide whether the command asks the player to do anything besides moving the named fixed things, "
                'such as another action or another object. A second object joined by "and" counts as something '
                'other than moving these fixed things, even when one verb covers both objects, as in "Carry the '
                'crate and my bag outside."'
            ),
            "criteria": {
                "true": "The command also asks for something other than moving these fixed things.",
                "false": "The command only asks to move these fixed things.",
            },
        }
    }
    return _answer(ask, {"command": command, "thing": things_text}, questions, "names_other_action")


def reaches_reveals(ask, command: str, candidates) -> set[str]:
    """Return reveal ids whose authored action the command clearly performs."""

    limited = list(candidates)[:6]
    questions = {}
    for candidate in limited:
        candidate_id, sentence = candidate[:2]
        names = tuple(dict.fromkeys(candidate[2] if len(candidate) > 2 else ()))[:12]
        name_context = (
            f" These all mean the same thing as the words in the sentence: {'; '.join(names)}." if names else ""
        )
        statement_context = f" The story says: {sentence}."
        questions[candidate_id] = {
            "type": "noul",
            "instructions": (
                "Decide whether the command itself does what the sentence says, or clearly means the same "
                "place, thing, and act. Return true only for the whole action."
                f"{name_context}{statement_context}"
            ),
            "criteria": {
                "true": (
                    f"The command itself does this action, or clearly means the same place, thing, and act: {sentence}"
                ),
                "false": (
                    f"The command is about a different thing, only talks or thinks about it, or does only part "
                    f"of the action without its key place or thing: {sentence}"
                ),
            },
        }
    if not questions:
        return set()
    try:
        answers = ask({"command": command}, questions)
    except Exception:
        return set()
    if not isinstance(answers, dict):
        return set()
    matched = set()
    for candidate_id in questions:
        try:
            if noul_yes(answers.get(candidate_id)) is True:
                matched.add(candidate_id)
        except Exception:
            return set()
    return matched


def reaches_reveal_contract(ask, command: str, candidate_id: str, contract, sentence: str) -> bool | None:
    """Ask whether a command performs one authored reveal action."""

    questions = {
        candidate_id: {
            "type": "noul",
            "instructions": (
                f"The required act is: {contract.act} "
                f"The command must do that act to one of these names: {', '.join(contract.targets)}. "
                f"The story says: {sentence}. "
                f"These do it: {'; '.join(contract.positive)}. "
                f"These do not: {'; '.join(contract.near_miss)}."
            ),
            "criteria": {
                "true": (
                    f"The command does this act to one of these names: {', '.join(contract.targets)}. "
                    f"The act is: {contract.act}"
                ),
                "false": (
                    f"The command does not do this act to one of these names: {', '.join(contract.targets)}. "
                    f"The act is: {contract.act}"
                ),
            },
        }
    }
    return _answer(ask, {"command": command}, questions, candidate_id)


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
