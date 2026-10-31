"""Prevent commands from narrating movement of fixed things."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from storygame.runtime.seating import _command_names_thing
from storygame.runtime.taking import _protagonist_name, _with_article


def _fixed_article_name(name: str) -> str:
    if name[0].islower():
        return f"the {name}"
    return _with_article(name)


def fixed_refusal_text(package, names: tuple[str, ...], other_action: bool | None = False) -> str:
    things = " and ".join(_fixed_article_name(name) for name in names)
    if len(names) == 1:
        text = f"{_protagonist_name(package)} tries to move {things}, but it is fixed in place and does not budge."
    else:
        text = f"{_protagonist_name(package)} tries to move {things}, but they are fixed in place and do not budge."
    if other_action is not False:
        text += " Nothing else in that command was done. Say what you want to do next."
    return text


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
    item_ids = tuple(item.id for item in package.world.items)
    fixed_ids = {item.id for item in package.world.items if item.fixed}
    scope_ids = {item_id for item_id in item_ids if in_scope(item_id)} if in_scope is not None else None
    candidates = world.fixed_visible_items(item_ids, package.protagonist_id, fixed_ids, scope_ids)

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
                f"{_protagonist_name(package)} tried to move {_fixed_article_name(name)}. "
                "It is fixed in place and did not move."
            )
            refused.append(name)

    return FixedRefusalResult(
        " ".join((*steps, player_input)) if steps else player_input, tuple(steps), asked, tuple(issues), tuple(refused)
    )
