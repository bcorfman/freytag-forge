"""Implicit taking actions for commands that put things somewhere."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from storygame.runtime.seating import _command_names_thing


@dataclass(frozen=True)
class TakingResult:
    command: str
    steps: tuple[str, ...]
    asked: bool
    issues: tuple[str, ...]


def _with_article(name: str) -> str:
    if "'s " in name:
        return name
    if len(name) > 1 and name[0].isupper() and name[1].islower():
        name = name[0].lower() + name[1:]
    return f"the {name}"


def _protagonist_name(package) -> str:
    protagonist = next((npc for npc in package.world.npcs if npc.id == package.protagonist_id), None)
    if protagonist is None:
        return package.protagonist_id
    return min((*protagonist.aliases, protagonist.name), key=len)


def take_before_put(world, package, player_input: str, moves_thing: Callable[[str, str], bool | None]) -> TakingResult:
    protagonist = package.protagonist_id
    protagonist_area = world.area(protagonist)
    items = {item.id: item for item in package.world.items}
    candidates = []
    for item in package.world.items:
        item_id = item.id
        item_area = world.area(item_id)
        if (
            world.is_visible(item_id)
            and not world.is_a(item_id, "vehicle")
            and not world.schema.is_fixed(item_id)
            and not item.fixed
            and world.holder(item_id) != protagonist
            and protagonist_area is not None
            and item_area is not None
            and item_area == protagonist_area
        ):
            candidates.append(item_id)

    asked = False
    issues: list[str] = []
    steps: list[str] = []
    for item_id in sorted(candidates):
        if not _command_names_thing(player_input, world.names(item_id)):
            continue
        name = world.name(item_id)
        answer = moves_thing(player_input, name)
        asked = True
        if answer is None:
            issues.append(f"taking question unanswered for '{name}'")
            continue
        if not answer:
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
    return TakingResult(command, tuple(steps), asked, tuple(issues))
