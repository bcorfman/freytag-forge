import pytest

from storygame.runtime.state import RuntimeState
from storygame.runtime.world_model import world_for
from tests.test_place_scoped_feed import (
    PACKAGE,
    _opening_prompt,
    _state_at,
    _synthetic_package,
)


def _things_lines(prompt: dict) -> list[str]:
    block = prompt["user"].split("\n\nTHINGS:\n", 1)[1].split("\n\n", 1)[0]
    return [line for line in block.splitlines() if line.startswith("- ")]


def test_continuity_opening_lists_visible_start_area_layout(monkeypatch: pytest.MonkeyPatch) -> None:
    lines = _things_lines(_opening_prompt(monkeypatch, _state_at(None)))

    assert lines[0].startswith("- Kristin.")
    assert "- workstation. Place: across the kitchen from the back door." in lines
    assert any(line.startswith("- back door.") for line in lines)
    assert not any(
        forbidden.casefold() in "\n".join(lines).casefold()
        for forbidden in ("memory card", "drawer", "binder clips", "pens", "stapler")
    )


def test_synthetic_story_opening_lists_its_own_start_area_things(monkeypatch: pytest.MonkeyPatch) -> None:
    state = RuntimeState.bootstrap(_synthetic_package())

    lines = _things_lines(_opening_prompt(monkeypatch, state))

    assert any(line.startswith("- Ari.") for line in lines)
    assert any(line.startswith("- lamp.") for line in lines)
    assert any(line.startswith("- stone statue.") for line in lines)
    assert "Kristin" not in "\n".join(lines)


def test_opening_with_unplaced_protagonist_adds_no_area_contents(monkeypatch: pytest.MonkeyPatch) -> None:
    state = _state_at(None)
    world = world_for(PACKAGE, state.facts)
    assert world.set_unplaced("kristin", "unknown").ok

    lines = _things_lines(_opening_prompt(monkeypatch, state))

    assert len(lines) == 1
    assert lines[0].startswith("- Kristin.")


def test_opening_lists_closed_container_but_not_contents(monkeypatch: pytest.MonkeyPatch) -> None:
    package = _synthetic_package()
    scene = package.scenes[0]
    placements = dict(scene.metadata.item_placements)
    placements["held_key"] = placements["held_key"].model_copy(update={"parent": "lamp"})
    scene = scene.model_copy(update={"metadata": scene.metadata.model_copy(update={"item_placements": placements})})
    items = tuple(
        item.model_copy(update={"kind": "container", "openable": True, "open": False}) if item.id == "lamp" else item
        for item in package.world.items
    )
    package = package.model_copy(
        update={"scenes": (scene,), "world": package.world.model_copy(update={"items": items})}
    )
    state = RuntimeState.bootstrap(package)

    lines = _things_lines(_opening_prompt(monkeypatch, state))

    assert any(line.startswith("- lamp. Place: the room.") for line in lines)
    assert not any("brass key" in line for line in lines)
