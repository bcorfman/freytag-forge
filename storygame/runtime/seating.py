"""Implicit seating actions for seated-use items."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class SeatingResult:
    command: str
    steps: tuple[str, ...]
    asked: bool
    issues: tuple[str, ...]


def seat_before_use(world, package, player_input: str, uses_thing: Callable[[str, str], bool | None]) -> SeatingResult:
    protagonist = package.protagonist_id
    items = {item.id: item for item in package.world.items}
    if world.is_enterable(world.parent(protagonist)):
        return SeatingResult(player_input, (), False, ())

    seats = sorted(
        item.id
        for item in package.world.items
        if item.seat_for and world.is_visible(item.id) and world.together(protagonist, item.id)
    )
    if not seats:
        return SeatingResult(player_input, (), False, ())
    seat = seats[0]
    candidates = sorted(
        item.id
        for item in package.world.items
        if item.use_seated
        and world.is_visible(item.id)
        and (world.together(protagonist, item.id) or world.holder(item.id) == protagonist)
    )
    if not candidates:
        return SeatingResult(player_input, (), False, ())

    asked = False
    issues: list[str] = []
    for item_id in candidates:
        answer = uses_thing(player_input, world.name(item_id))
        asked = True
        if answer is None:
            issues.append(f"seating question unanswered for '{world.name(item_id)}'")
        if answer is True:
            steps: list[str] = []
            enter_pole = world.schema.entities[seat].enter_pole
            if enter_pole and enter_pole not in world.axis_values(seat).values():
                world.set_axis(seat, enter_pole)
                steps.append(items[seat].right_text)
            if world.parent(protagonist) != seat:
                result = world.move(protagonist, seat)
                if not result.ok:
                    issues.append(f"could not move protagonist into '{world.name(seat)}': {result.reason}")
                else:
                    steps.append(items[seat].enter_text)
            return SeatingResult(" ".join((*steps, player_input)), tuple(steps), asked, tuple(issues))
    return SeatingResult(player_input, (), asked, tuple(issues))
