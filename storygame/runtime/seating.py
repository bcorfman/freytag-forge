"""Implicit seating actions for seated-use items."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class SeatingResult:
    command: str
    steps: tuple[str, ...]
    asked: bool
    issues: tuple[str, ...]


def _command_names_thing(command: str, names: tuple[str, ...]) -> bool:
    command = command.replace("’", "'").casefold()
    for name in names:
        normalized_name = name.replace("’", "'").casefold().strip()
        if re.search(rf"(?<!\w){re.escape(normalized_name)}(?!\w)", command):
            return True
        possessive = re.fullmatch(r"\w+'s\s+(.+)", normalized_name)
        if possessive and re.search(rf"(?<!\w){re.escape(possessive.group(1))}(?!\w)", command):
            return True
    return False


def seat_before_use(world, package, player_input: str, uses_thing: Callable[[str, str], bool | None]) -> SeatingResult:
    protagonist = package.protagonist_id
    items = {item.id: item for item in package.world.items}
    current_seat = world.parent(protagonist)
    if (
        not current_seat
        or not world.schema.entities.get(current_seat)
        or not world.schema.entities[current_seat].seat_for
    ):
        current_seat = None

    protagonist_area = world.area(protagonist)
    seats = sorted(
        item.id
        for item in package.world.items
        if item.seat_for
        and world.is_visible(item.id)
        and protagonist_area is not None
        and world.area(item.id) is not None
        and protagonist_area == world.area(item.id)
    )
    if not seats and not current_seat:
        return SeatingResult(player_input, (), False, ())
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
        if not _command_names_thing(player_input, world.names(item_id)):
            continue
        answer = uses_thing(player_input, world.name(item_id))
        asked = True
        if answer is None:
            issues.append(f"seating question unanswered for '{world.name(item_id)}'")
        if answer is True:
            steps: list[str] = []
            if current_seat:
                seat = current_seat
            else:
                item_place = world.parent(item_id)
                protagonist_place = world.parent(protagonist)
                preferred_places = set()
                for place in (item_place, protagonist_place):
                    if place:
                        preferred_places.update((place, *world.chain(place)))
                preferred = [candidate for candidate in seats if items[candidate].seat_for in preferred_places]
                seat = (preferred or seats)[0]
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
            item = items[item_id]
            parent = world.parent(item_id)
            used_in_place = parent and parent == items[seat].seat_for and world.is_a(parent, "supporter")
            if item.take_text and world.holder(item_id) != protagonist and not used_in_place:
                result = world.move(item_id, protagonist)
                if not result.ok:
                    issues.append(f"could not move '{world.name(item_id)}' to protagonist: {result.reason}")
                else:
                    steps.append(item.take_text)
            return SeatingResult(" ".join((*steps, player_input)), tuple(steps), asked, tuple(issues))
    return SeatingResult(player_input, (), asked, tuple(issues))


def board_vehicle(
    world, package, player_input: str, goes_to_vehicle: Callable[[str, str], bool | None]
) -> SeatingResult:
    protagonist = package.protagonist_id
    items = {item.id: item for item in package.world.items}
    candidates = []
    for item in package.world.items:
        if not world.is_a(item.id, "vehicle") or not world.is_visible(item.id):
            continue
        seats = sorted(
            seat.id for seat in package.world.items if seat.seat_for == item.id and world.is_visible(seat.id)
        )
        if not seats:
            continue
        parent = world.parent(protagonist)
        if parent and world.schema.entities.get(parent) and world.schema.entities[parent].seat_for == item.id:
            continue
        candidates.append((item.id, seats))

    asked = False
    issues: list[str] = []
    for vehicle_id, seats in sorted(candidates):
        if not _command_names_thing(player_input, world.names(vehicle_id)):
            continue
        answer = goes_to_vehicle(player_input, world.name(vehicle_id))
        asked = True
        if answer is None:
            issues.append(f"boarding question unanswered for '{world.name(vehicle_id)}'")
            continue
        if answer is False:
            continue
        seat = seats[0]
        result = world.move(protagonist, seat)
        if not result.ok:
            issues.append(f"could not move protagonist into '{world.name(seat)}': {result.reason}")
            return SeatingResult(player_input, (), asked, tuple(issues))
        steps = [items[seat].enter_text]
        for item_id in sorted(items):
            item = items[item_id]
            if (
                item_id != protagonist
                and world.is_visible(item_id)
                and world.holder(item_id) != protagonist
                and item.notice_text
                and vehicle_id in world.chain(item_id)
            ):
                steps.append(item.notice_text)
        return SeatingResult(" ".join((*steps, player_input)), tuple(steps), asked, tuple(issues))
    return SeatingResult(player_input, (), asked, tuple(issues))


def stand_before_leave(
    world, package, player_input: str, needs_to_stand: Callable[[str, str, tuple[str, ...]], bool | None]
) -> SeatingResult:
    protagonist = package.protagonist_id
    seat = world.parent(protagonist)
    if not seat or not world.schema.entities.get(seat) or not world.schema.entities[seat].seat_for:
        return SeatingResult(player_input, (), False, ())
    seat_for = world.schema.entities[seat].seat_for
    within_reach = tuple(
        world.name(entity_id)
        for entity_id in world.entity_ids()
        if entity_id in {seat, seat_for}
        or (
            world.is_visible(entity_id)
            and (seat_for in world.chain(entity_id) or world.holder(entity_id) == protagonist)
        )
    )
    answer = needs_to_stand(player_input, world.name(seat), within_reach)
    if answer is None:
        return SeatingResult(player_input, (), True, (f"standing question unanswered for '{world.name(seat)}'",))
    if answer is False:
        return SeatingResult(player_input, (), True, ())
    result = world.move(protagonist, world.area(seat))
    if not result.ok:
        return SeatingResult(player_input, (), True, (result.reason,))
    step = next(item.leave_text for item in package.world.items if item.id == seat)
    return SeatingResult(f"{step} {player_input}", (step,), True, ())
