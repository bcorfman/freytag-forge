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
    return provider


def _line(block, name):
    return next(line for line in block.splitlines() if line.startswith(f"- {name}."))


def test_fixed_workstation_gets_marker_even_when_not_referred():
    provider = _provider(mark_fixed=True)
    provider._referred_names = []
    line = _line(provider._things_block(narration=True), "workstation")
    assert line.endswith(MARKER)


def test_fixed_marker_is_off_when_mark_fixed_is_false():
    assert MARKER not in _provider(mark_fixed=False)._things_block(narration=True)


def test_fixed_thing_not_in_rendered_things_gets_no_marker():
    provider = _provider(mark_fixed=True, selected_name="Kristin's laptop")
    block = provider._things_block(narration=True)
    assert "- workstation." not in block
    assert MARKER not in block


@pytest.mark.parametrize("name", ["Kristin's laptop"])
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


@pytest.mark.parametrize("mark_fixed, expected", [(True, True), (False, False)])
def test_assemble_turn_prompt_includes_fixed_marker_without_prepare_turn(mark_fixed, expected):
    provider = _provider(mark_fixed=mark_fixed)
    provider._selected_names = ["workstation", *provider.dependency_names()]
    provider._select_protagonist()
    prompt = provider.assemble_turn_prompt("Carry the workstation to the truck.")
    user_text = provider._section_user_prompt(prompt["context"])
    if expected:
        assert "- workstation. Place: kitchen." + MARKER in user_text
    else:
        assert MARKER not in user_text
