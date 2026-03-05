from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ActionKind(StrEnum):
    LOOK = "look"
    MOVE = "move"
    TAKE = "take"
    TALK = "talk"
    USE = "use"
    HELP = "help"
    INVENTORY = "inventory"
    QUIT = "quit"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class Action:
    kind: ActionKind
    target: str = ""
    raw: str = ""


def _normalize_token(value: str) -> str:
    return value.strip().lower().replace(" ", "_")


def parse_command(raw: str) -> Action:
    raw = raw.strip()
    if not raw:
        return Action(ActionKind.HELP, raw=raw)

    lowered = raw.lower().strip()
    words = lowered.split()

    if words[0] in {"look", "l"}:
        return Action(ActionKind.LOOK, raw=raw)

    if words[0] in {"help", "h", "?"}:
        return Action(ActionKind.HELP, raw=raw)

    if words[0] in {"inventory", "inv", "i"}:
        return Action(ActionKind.INVENTORY, raw=raw)

    if words[0] in {"quit", "exit", "leave"}:
        return Action(ActionKind.QUIT, raw=raw)

    if words[0] in {"north", "south", "east", "west", "up", "down", "go", "move", "travel", "walk"}:
        if words[0] in {"go", "move", "travel", "walk"}:
            target = _normalize_token(" ".join(words[1:]))
            return Action(ActionKind.MOVE, target=target, raw=raw)
        return Action(ActionKind.MOVE, target=_normalize_token(words[0]), raw=raw)

    if words[0] in {"take", "get", "grab", "pick", "acquire"}:
        if words[0] == "pick" and len(words) > 1 and words[1] == "up":
            target = _normalize_token(" ".join(words[2:]))
        else:
            target = _normalize_token(" ".join(words[1:]))
        return Action(ActionKind.TAKE, target=target, raw=raw)

    if words[0] in {"talk", "speak", "speak_to", "speakto"}:
        cleaned = words[1:]
        if cleaned and cleaned[0] == "to":
            cleaned = cleaned[1:]
        return Action(ActionKind.TALK, target=_normalize_token(" ".join(cleaned)), raw=raw)

    if words[0] == "use":
        if "on" in words:
            split_index = words.index("on")
            item = _normalize_token(" ".join(words[1:split_index]))
            target = _normalize_token(" ".join(words[split_index + 1 :]))
            combined = f"{item}:{target}" if target else item
            return Action(ActionKind.USE, target=combined, raw=raw)
        item = _normalize_token(" ".join(words[1:]))
        return Action(ActionKind.USE, target=item, raw=raw)

    return Action(ActionKind.UNKNOWN, target=_normalize_token(lowered), raw=raw)
