"""Prevent commands from narrating movement of fixed things."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from storygame.runtime.seating import _command_names_thing
from storygame.runtime.taking import _protagonist_name, _with_article


@dataclass(frozen=True)
class FixedRefusalResult:
    command: str
    steps: tuple[str, ...]
    asked: bool
    issues: tuple[str, ...]
    refused: tuple[str, ...]


def refuse_fixed_move(
    world,
    package,
    player_input: str,
    relocates_thing: Callable[[str, str], bool | None],
    *,
    in_scope: Callable[[str], bool] | None = None,
) -> FixedRefusalResult:
    protagonist_area = world.area(package.protagonist_id)
    candidates = []
    for item in package.world.items:
        item_id = item.id
        if (
            (world.schema.is_fixed(item_id) or item.fixed)
            and world.is_visible(item_id)
            and not world.is_a(item_id, "area")
            and (
                in_scope(item_id)
                if in_scope is not None
                else (
                    protagonist_area is not None
                    and world.area(item_id) is not None
                    and world.area(item_id) == protagonist_area
                )
            )
        ):
            candidates.append(item_id)

    asked = False
    issues: list[str] = []
    steps: list[str] = []
    refused: list[str] = []
    for item_id in sorted(candidates):
        if not _command_names_thing(player_input, world.names(item_id)):
            continue
        name = world.name(item_id)
        answer = relocates_thing(player_input, name)
        asked = True
        if answer is None:
            issues.append(f"fixed move question unanswered for '{name}'")
            continue
        if answer:
            steps.append(
                f"{_protagonist_name(package)} tried to move {_with_article(name)}. "
                "It is fixed in place and did not move."
            )
            refused.append(name)

    return FixedRefusalResult(
        " ".join((*steps, player_input)) if steps else player_input, tuple(steps), asked, tuple(issues), tuple(refused)
    )
