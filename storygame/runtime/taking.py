"""Implicit taking actions for commands that put things somewhere."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from storygame.runtime.seating import _command_names_thing, _protagonist_name


@dataclass(frozen=True)
class TakingResult:
    command: str
    steps: tuple[str, ...]
    asked: bool
    issues: tuple[str, ...]
    pickups: tuple[str, ...] = ()


def _with_article(name: str) -> str:
    if "'s " in name:
        return name
    if len(name) > 1 and name[0].isupper() and name[1].islower():
        name = name[0].lower() + name[1:]
    return f"the {name}"


def take_before_put(
    world,
    package,
    player_input: str,
    moves_thing: Callable[[str, str], bool | None],
    *,
    kind_of_thing: Callable[[str, str], tuple[bool | None, bool | None]] | None = None,
) -> TakingResult:
    protagonist = package.protagonist_id
    items = {item.id: item for item in package.world.items}
    item_ids = tuple(item.id for item in package.world.items)
    fixed_ids = {item.id for item in package.world.items if item.fixed}
    candidates = world.takeable_items(item_ids, protagonist, fixed_ids)

    asked = False
    issues: list[str] = []
    steps: list[str] = []
    pickups: list[str] = []
    for item_id in sorted(candidates):
        if not _command_names_thing(player_input, world.names(item_id)):
            continue
        name = world.name(item_id)
        moves, picks_up = (
            kind_of_thing(player_input, name) if kind_of_thing else (moves_thing(player_input, name), None)
        )
        asked = True
        if kind_of_thing is not None:
            if moves is None and picks_up is not True:
                issues.append(f"taking question unanswered for '{name}'")
                continue
        elif moves is None and picks_up is None:
            issues.append(f"taking question unanswered for '{name}'")
            continue
        if not moves:
            if picks_up:
                pickups.append(item_id)
            continue
        parent = world.parent(item_id)
        result = world.move(item_id, protagonist)
        if not result.ok:
            issues.append(f"could not move '{name}' to protagonist: {result.reason}")
            continue
        item = items[item_id]
        if item.take_text:
            steps.append(item.take_text)
        else:
            sentence = f"{_protagonist_name(package)} picked up {_with_article(name)}"
            if parent is not None and not world.is_a(parent, "area"):
                sentence += f" from {_with_article(world.name(parent))}"
            steps.append(sentence + ".")

    command = " ".join((*steps, player_input)) if steps else player_input
    return TakingResult(command, tuple(steps), asked, tuple(issues), tuple(pickups))
