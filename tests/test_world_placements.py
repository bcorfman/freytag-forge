import re
import shutil
from pathlib import Path

import pytest
import yaml

from storygame.runtime.contracts import ResolvedTurnProposal, SceneTransitionProposal
from storygame.runtime.state import RuntimeState
from storygame.runtime.world_model import world_for
from storygame.story_package.loader import load_story_package
from storygame.story_package.models import ItemPlacement, placement_text

ROOT = Path(__file__).parents[1]


def placement_package(tmp_path: Path):
    root = tmp_path / "story"
    shutil.copytree(ROOT / "data/stories/continuity-initiative", root)
    world_path = root / "world.yaml"
    world = yaml.safe_load(world_path.read_text())
    world["kinds"] = [{"id": "desk", "is": ["furniture", "supporter"]}]
    world["locations"].extend(
        [
            {"id": "kitchen", "name": "kitchen", "parent": "mcgehee_home"},
            {"id": "outside_house", "name": "outside the house"},
        ]
    )
    world["items"].extend(
        [
            {"id": "kristin_truck", "name": "Kristin's truck", "kind": "vehicle", "owner": "kristin"},
            {"id": "michelle_workstation", "name": "Michelle's workstation", "kind": "desk"},
        ]
    )
    for item in world["items"]:
        if item["id"] == "michelle_drawer":
            item.update(kind="container", openable=True, contents=["pens"])
        if item["id"] == "memory_card":
            item["hidden"] = True
    world_path.write_text(yaml.safe_dump(world, sort_keys=False))
    plot_path = root / "plot.md"
    plot = plot_path.read_text()
    plot = plot.replace(
        "item_ids: [memory_card, michelle_phone, kristin_laptop, michelle_drawer, workstation_chair]",
        "item_ids: [memory_card, michelle_phone, kristin_laptop, michelle_drawer, workstation_chair, "
        "kristin_truck, michelle_workstation]",
        1,
    )
    replacement = """item_placements:
  memory_card: {parent: michelle_drawer, under: true}
  michelle_phone: {parent: kitchen, text: on the kitchen floor}
  kristin_truck: {parent: outside_house}
  michelle_workstation: {parent: kitchen}
  michelle_drawer: {parent: michelle_workstation, part_of: true}
  workstation_chair: {parent: kitchen}
"""
    plot = re.sub(r"item_placements:\n(?:  .*\n)+setting_facts:", replacement + "setting_facts:", plot, count=1)
    plot = plot.replace(
        "item_ids: [memory_card, transit_card]\n",
        "item_ids: [memory_card, transit_card, michelle_phone]\n"
        "item_placements:\n"
        "  michelle_phone: {parent: los_angeles_park, text: beside the park bench}\n",
        1,
    )
    plot_path.write_text(plot)
    return load_story_package(root)


def test_bootstrap_applies_structural_scene_placements(tmp_path):
    package = placement_package(tmp_path)
    state = RuntimeState.bootstrap(package)
    world = world_for(package, state.facts)

    assert world.parent("michelle_phone") == "kitchen"
    assert world.place_label("michelle_phone") == "on the kitchen floor"
    assert world.parent("memory_card") == "michelle_drawer"
    assert world.relation("memory_card") == "under"
    assert world.parent("michelle_drawer") == "michelle_workstation"
    assert world.relation("michelle_drawer") == "part_of"
    assert world.owner("kristin_truck") == "kristin"
    assert not world.move("michelle_workstation", "mcgehee_home").ok


def test_scene_change_applies_new_scene_placements(tmp_path):
    package = placement_package(tmp_path)
    state = RuntimeState.bootstrap(package)

    state.apply_proposal(
        ResolvedTurnProposal(
            segments=({"kind": "narration", "text": "Kristin heads for the park."},),
            transition=SceneTransitionProposal(transition_id="t_1a_1b"),
        )
    )

    world = world_for(package, state.facts)
    assert state.current_scene_id == "1B"
    assert world.parent("michelle_phone") == "los_angeles_park"
    assert world.place_label("michelle_phone") == "beside the park bench"


def test_item_placement_forms_and_text():
    assert placement_text("on the floor") == "on the floor"
    assert placement_text(ItemPlacement(placement="on the floor")) == "on the floor"
    assert placement_text(ItemPlacement(parent="kitchen")) is None
    with pytest.raises(ValueError):
        ItemPlacement.model_validate({})
    with pytest.raises(ValueError):
        ItemPlacement.model_validate({"placement": "on the floor", "under": True})
