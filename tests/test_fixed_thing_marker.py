from pathlib import Path

import pytest

from storygame.runtime.item_facts import ItemFactsProvider, validate_item_facts
from storygame.runtime.state import RuntimeState
from storygame.runtime.world_model import apply_scene_placements
from storygame.story_package.loader import load_story_package

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))
MARKER = " It is fixed in place. It cannot be picked up or carried away. If the player tries, the attempt fails."


def _provider(*, mark_fixed=False, selected_name="workstation"):
    state = RuntimeState.bootstrap(PACKAGE)
    state.current_scene_id = "1A"
    apply_scene_placements(PACKAGE, state.facts, "1A")
    provider = ItemFactsProvider(
        worker_url="",
        token="",
        state=state,
        item_facts={},
        mode="single_call",
        seed_from_package=True,
        mark_fixed=mark_fixed,
    )
    provider._selected_names = [selected_name]
    provider._referred_names = [selected_name]
    return provider


def _line(block, name):
    return next(line for line in block.splitlines() if line.startswith(f"- {name}."))


def test_fixed_referred_workstation_gets_marker():
    line = _line(_provider(mark_fixed=True)._things_block(narration=True), "workstation")
    assert line.endswith(MARKER)


def test_fixed_marker_is_off_by_default():
    assert MARKER not in _provider()._things_block(narration=True)


def test_fixed_workstation_not_referred_gets_no_marker():
    provider = _provider(mark_fixed=True)
    provider._referred_names = []
    assert MARKER not in provider._things_block(narration=True)


@pytest.mark.parametrize("name", ["Kristin's laptop", "Kristin's truck"])
def test_non_fixed_referred_thing_gets_no_marker(name):
    assert MARKER not in _provider(mark_fixed=True, selected_name=name)._things_block(narration=True)


def test_fixed_back_door_gets_marker_without_move_word():
    line = _line(_provider(mark_fixed=True, selected_name="back door")._things_block(narration=True), "back door")
    assert line.endswith(MARKER)
    assert "move" not in line.lower()


def test_validate_item_facts_mark_fixed_is_boolean():
    base = {"mode": "single_call", "seed_from_package": True}
    validate_item_facts({**base, "mark_fixed": True})
    validate_item_facts({**base, "mark_fixed": False})
    with pytest.raises(ValueError, match="mark_fixed must be a boolean"):
        validate_item_facts({**base, "mark_fixed": "yes"})
