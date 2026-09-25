"""S1 task 3 acceptance: package schema, placements into the world, placement text readers."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from pydantic import ValidationError

from storygame.runtime.contracts import NarrationSegment, ResolvedTurnProposal
from storygame.runtime.state import RuntimeState
from storygame.runtime.world_model import world_for, world_schema_data
from storygame.story_package.loader import StoryPackageError, load_story_package
from storygame.story_package.models import ItemPlacement, placement_text

STORY = Path("data/stories/continuity-initiative")
SEGMENT = (NarrationSegment(kind="narration", text="Acceptance fixture."),)

OLD_1A_ITEMS = "item_ids: [memory_card, michelle_phone, kristin_laptop, michelle_drawer, workstation_chair]\n"
OLD_1A_PLACEMENTS = """item_placements:
  memory_card:
    placement: with Kristin
    while_fact_true: memory_card_in_kristins_custody
  michelle_phone: on the kitchen floor
  kristin_laptop: in Kristin's truck outside the house
  michelle_drawer: in Michelle's workstation
  workstation_chair: at Michelle's workstation
"""
NEW_1A = (
    """item_ids: [memory_card, michelle_phone, kristin_laptop, michelle_drawer, workstation_chair, """
    """kristin_truck, michelle_workstation]
item_placements:
  memory_card: {parent: michelle_drawer, under: true}
  michelle_phone: {parent: kitchen, text: on the kitchen floor}
  kristin_laptop: {parent: kristin_truck, text: in Kristin's truck outside the house}
  kristin_truck: {parent: outside_house}
  michelle_workstation: {parent: kitchen}
  michelle_drawer: {parent: michelle_workstation, part_of: true, text: in Michelle's workstation}
  workstation_chair: {parent: kitchen, text: at Michelle's workstation}
"""
)
WORLD_LOCATIONS = """locations:
- id: kitchen
  name: kitchen
  parent: mcgehee_home
- id: outside_house
  name: outside the house
"""
WORLD_ITEMS = """items:
- id: kristin_truck
  name: Kristin's truck
  kind: vehicle
  owner: kristin
- id: michelle_workstation
  name: Michelle's workstation
  kind: desk
"""
OLD_DRAWER = "- id: michelle_drawer\n  name: drawer\n  fixed: true\n"
NEW_DRAWER = (
    "- id: michelle_drawer\n  name: drawer\n  fixed: true\n  kind: container\n  openable: true\n"
    "  contents: [pens, binder clips, stapler, spare batteries]\n"
)
OLD_CARD = "- id: memory_card\n  name: Michelle's memory card\n"
NEW_CARD = "- id: memory_card\n  name: Michelle's memory card\n  hidden: true\n"
KINDS = "kinds:\n- id: desk\n  is: [furniture, supporter]\n"


def _write_story(tmp_path: Path, *, world_edits=(), plot_edits=()) -> Path:
    root = tmp_path / "story"
    if root.exists():
        shutil.rmtree(root)
    shutil.copytree(STORY, root)
    for name, edits in (("world.yaml", world_edits), ("plot.md", plot_edits)):
        path = root / name
        text = path.read_text()
        for old, new in edits:
            assert old in text, f"fixture anchor missing in {name}: {old[:60]!r}"
            text = text.replace(old, new, 1)
        path.write_text(text)
    return root


def _converted(tmp_path: Path, *, extra_world=(), extra_plot=()) -> Path:
    world = [
        ("locations:\n", WORLD_LOCATIONS),
        ("items:\n", WORLD_ITEMS),
        (OLD_DRAWER, NEW_DRAWER),
        (OLD_CARD, NEW_CARD),
        ("protected_knowledge:", KINDS + "protected_knowledge:"),
        *extra_world,
    ]
    plot = [(OLD_1A_ITEMS + OLD_1A_PLACEMENTS, NEW_1A), *extra_plot]
    return _write_story(tmp_path, world_edits=world, plot_edits=plot)


# --- models ---------------------------------------------------------------------------------


def test_placement_forms_and_text():
    assert placement_text("on the floor") == "on the floor"
    assert (
        placement_text(ItemPlacement.model_validate({"placement": "with her", "while_fact_true": "x_fact"}))
        == "with her"
    )
    new = ItemPlacement.model_validate({"parent": "kitchen", "text": "on the kitchen floor"})
    assert placement_text(new) == "on the kitchen floor"
    assert placement_text(ItemPlacement.model_validate({"parent": "kitchen"})) is None
    assert ItemPlacement.model_validate({"parent": "drawer_x", "under": True}).under is True
    assert ItemPlacement.model_validate({"parent": "desk_x", "part_of": True}).part_of is True


@pytest.mark.parametrize(
    "data",
    [
        {"placement": "on it", "parent": "kitchen"},
        {"text": "floating"},
        {"placement": "on it", "under": True},
        {"parent": "kitchen", "under": True, "part_of": True},
        {"parent": "kitchen", "while_fact_true": "some_fact"},
        {},
    ],
)
def test_invalid_placement_shapes_are_rejected(data):
    with pytest.raises(ValidationError):
        ItemPlacement.model_validate(data)


# --- the shipped package still loads, and string placements still work --------------------


def test_shipped_package_loads_and_keeps_its_string_placements():
    package = load_story_package(STORY)
    scene = next(item for item in package.scenes if item.metadata.scene_id == "1A")
    assert placement_text(scene.metadata.item_placements["michelle_phone"]) == "on the kitchen floor"


# --- a converted package: schema, loader, world ---------------------------------------------


def test_converted_package_builds_the_tree_at_bootstrap(tmp_path):
    package = load_story_package(_converted(tmp_path))
    data = world_schema_data(package)
    kinds = {entity["id"]: entity["kind"] for entity in data["entities"]}
    assert kinds["kristin_truck"] == "vehicle" and kinds["michelle_workstation"] == "desk"
    assert any(kind.get("id") == "desk" for kind in data.get("kinds", []))

    state = RuntimeState.bootstrap(package)
    world = world_for(package, state.facts)
    assert world.parent("kitchen") == "mcgehee_home"
    assert world.parent("michelle_phone") == "kitchen"
    assert world.area("michelle_phone") == "kitchen"
    assert "mcgehee_home" in world.chain("michelle_phone")
    assert world.place_label("michelle_phone") == "on the kitchen floor"
    assert world.parent("kristin_laptop") == "kristin_truck"
    assert world.parent("kristin_truck") == "outside_house"
    assert world.parent("memory_card") == "michelle_drawer"
    assert world.relation("memory_card") == "under"
    assert world.is_hidden("memory_card")
    assert world.relation("michelle_drawer") == "part_of"
    assert world.axis_values("michelle_drawer").get("open") == "closed"
    assert world.owner("kristin_truck") == "kristin"
    drawer_contents = set(world.contents("michelle_drawer"))
    assert {"michelle_drawer_pens", "michelle_drawer_stapler"} <= drawer_contents
    assert "memory_card" not in drawer_contents or world.relation("memory_card") == "under"
    assert world.is_a("michelle_workstation", "supporter") and world.is_a("michelle_workstation", "furniture")
    assert not world.move("michelle_workstation", "kristin").ok, "a desk inherits fixed from furniture"


def test_a_scene_change_applies_the_new_scenes_placements(tmp_path):
    plot = [
        (
            "item_ids: [memory_card, transit_card]\n",
            "item_ids: [memory_card, transit_card, michelle_phone]\nitem_placements:\n"
            "  michelle_phone: {parent: los_angeles_park, text: on the park bench}\n",
        )
    ]
    package = load_story_package(_converted(tmp_path, extra_plot=plot))
    state = RuntimeState.bootstrap(package)
    assert world_for(package, state.facts).parent("michelle_phone") == "kitchen"
    state.apply_proposal(ResolvedTurnProposal(segments=SEGMENT, transition={"transition_id": "t_1a_1b"}))
    assert state.current_scene_id == "1B"
    world = world_for(package, state.facts)
    assert world.parent("michelle_phone") == "los_angeles_park"
    assert world.place_label("michelle_phone") == "on the park bench"
    assert world.parent("kristin_truck") == "outside_house", "things the new scene does not place stay put"


def test_shipped_narrator_reads_placement_text(tmp_path):
    from storygame.runtime.cloudflare import CloudflareTurnProvider

    package = load_story_package(_converted(tmp_path))
    state = RuntimeState.bootstrap(package)
    provider = CloudflareTurnProvider(worker_url="https://worker.example/turn", token="", state=state)
    rules = provider._placement_rules()
    assert "Michelle's phone is on the kitchen floor." in rules
    assert "Kristin's laptop is in Kristin's truck outside the house." in rules
    assert not any("memory card" in rule.lower() for rule in rules), "a hidden thing never reaches the narrator"
    assert not any(rule.startswith("Kristin's truck is") for rule in rules), "no text means no narrator line"


def test_bench_seed_uses_text_then_parent_name_and_skips_hidden(tmp_path):
    from bench.item_facts import _package_seed

    package = load_story_package(_converted(tmp_path))
    state = RuntimeState.bootstrap(package)
    things, _issues, _unconsumed = _package_seed(package, state, "1A")
    assert things["Michelle's phone"]["place"] == "on the kitchen floor"
    assert things["Kristin's truck"]["place"] == "outside the house", "no text: the parent's name"
    assert "Michelle's memory card" not in things, "hidden things are not seeded"


# --- loader rejections ----------------------------------------------------------------------


@pytest.mark.parametrize(
    "world_extra, plot_extra, why",
    [
        (
            (),
            [
                (
                    "michelle_phone: {parent: kitchen, text: on the kitchen floor}",
                    "michelle_phone: {parent: no_such_place}",
                )
            ],
            "unknown parent",
        ),
        ((("  kind: vehicle\n", "  kind: spaceship\n"),), (), "unknown kind"),
        ((("  kind: vehicle\n", "  kind: area\n"),), (), "an item kind that is not a thing"),
        ((("  parent: mcgehee_home\n", "  parent: kristin_laptop\n"),), (), "a location parent that is not a location"),
        (
            (),
            [
                (
                    "memory_card: {parent: michelle_drawer, under: true}",
                    "memory_card: {parent: michelle_drawer, under: true, text: under the drawer}",
                )
            ],
            "text on a hidden thing",
        ),
        (
            (),
            [
                (
                    "michelle_phone: {parent: kitchen, text: on the kitchen floor}",
                    "michelle_phone: {parent: kitchen, under: true}",
                )
            ],
            "under an area",
        ),
        (
            (),
            [
                (
                    "michelle_phone: {parent: kitchen, text: on the kitchen floor}",
                    "michelle_phone: {parent: kristin_laptop}",
                )
            ],
            "a parent that cannot hold things",
        ),
    ],
)
def test_loader_rejects_bad_world_declarations(tmp_path, world_extra, plot_extra, why):
    root = _converted(tmp_path, extra_world=world_extra, extra_plot=plot_extra)
    with pytest.raises((StoryPackageError, ValueError)):
        load_story_package(root)
