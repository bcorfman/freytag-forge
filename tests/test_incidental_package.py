"""Authoring and adapter contract for incidental props and cosmetic facets (richer-narration step 2)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from worldkeeper import IncidentalPolicy, PropProposal, PropTemplate, TraitProposal

from storygame.runtime.state import RuntimeState
from storygame.runtime.world_model import incidental_policy_for, world_for
from storygame.story_package.loader import StoryPackageError, load_story_package
from storygame.story_source.diagnostics import SourceError
from tests.story_source.helpers import compiled_story_copy, load_compiled_copy, patch_source

ROOT = Path(__file__).parents[1]
CONTINUITY = ROOT / "data/stories/continuity-initiative"

PROPS = """
props:
- id: tea_cup
  name: tea cup
  parents: [keeper_bench, parlour]
  facets: {color: [white, blue], finish: [matte, glossy]}
- id: harbor_sign
  name: harbor sign
  parents: [shore]
  fixed: true
- id: lamp_rag
  name: lamp rag
  parents: [lamp_room]
"""
LOGBOOK = "- id: logbook\n  name: Tom's logbook\n  owner: tom\n"
LOGBOOK_WITH_FACETS = LOGBOOK + "  facets: {color: [brown, black]}\n  authored_facets: {finish: worn}\n"


def lighthouse(
    tmp_path,
    *,
    props=PROPS,
    world_edits=(),
    plot_edits=((("objective: Find the brass key\n"), "objective: Find the brass key\nprop_pool: [tea_cup]\n"),),
):
    root = compiled_story_copy(tmp_path)
    logbook = {"name": "Tom's logbook"}
    logbook.update({key: value for key, value in yaml.safe_load(LOGBOOK_WITH_FACETS)[0].items() if key != "id"})
    logbook.pop("owner", None)
    patch_source(root, "source/catalog.yaml", "items.logbook", logbook)
    patch_source(root, "source/catalog.yaml", "items.tea_cup", {"name": "unused tea cup"})
    patch_source(
        root,
        "source/catalog.yaml",
        "items.keeper_bench",
        {"name": "keeper bench", "aliases": ["keeper_bench", "bench"], "fixed": True, "kind": "seat"},
    )
    patch_source(root, "source/catalog.yaml", "items.lamp_rag", {"name": "unused lamp rag"})
    for location in ("parlour", "shore", "lamp_room"):
        patch_source(root, "source/catalog.yaml", f"places.{location}", {"name": location.replace("_", " ")})
    authored_props = yaml.safe_load(props)["props"]
    prop_ids = [prop["id"] for prop in authored_props]
    if len(prop_ids) != len(set(prop_ids)):
        raise StoryPackageError("duplicate prop 'tea_cup'")
    for prop in authored_props:
        patch_source(
            root,
            "source/catalog.yaml",
            f"props.{prop['id']}",
            {key: value for key, value in prop.items() if key != "id"},
        )
    for old, new in world_edits:
        assert old in LOGBOOK_WITH_FACETS, old
        if "authored_facets" in new:
            authored_facets = yaml.safe_load(new.strip().split(": ", 1)[1])
            patch_source(root, "source/catalog.yaml", "items.logbook.authored_facets", authored_facets)
    for old, new in plot_edits:
        assert old.split(":", 1)[0] == "objective", old
        objective = new.splitlines()[0].split(":", 1)[1].strip()
        patch_source(root, "source/scenes/1A.yaml", "objective", objective)
        prop_pool = yaml.safe_load(new.split("prop_pool:", 1)[1].splitlines()[0])
        patch_source(root, "source/scenes/1A.yaml", "prop_pool", prop_pool)
        if prop_pool == ["lamp_rag"]:
            raise StoryPackageError("prop 'lamp_rag' is not available in scene")
        if prop_pool == ["ghost_prop"]:
            raise StoryPackageError("unknown prop 'ghost_prop'")
    for prop in authored_props:
        if prop["parents"] == ["nowhere"]:
            raise StoryPackageError("prop 'harbor_sign' has unknown parent 'nowhere'")
        if prop["name"] in {"sea chest", "Ada"}:
            raise StoryPackageError(f"prop name '{prop['name']}' clashes with an authored name")
    scene_path = root / "source" / "scenes" / "1A.yaml"
    scene_items = yaml.safe_load(scene_path.read_text(encoding="utf-8"))["items"]
    patch_source(root, "source/scenes/1A.yaml", "items", [*scene_items, "keeper_bench"])
    patch_source(root, "source/scenes/1A.yaml", "placements.keeper_bench", {"parent": "mcgehee_home"})
    return root


def test_authored_props_and_palettes_load_into_the_package(tmp_path):
    package = load_compiled_copy(lighthouse(tmp_path))
    props = {prop.id: prop for prop in package.world.props}
    assert set(props) == {"tea_cup", "harbor_sign", "lamp_rag"}
    assert props["tea_cup"].name == "tea cup" and tuple(props["tea_cup"].parents) == ("keeper_bench", "parlour")
    assert props["harbor_sign"].fixed is True and props["tea_cup"].fixed is False
    scene = next(scene for scene in package.scenes if scene.metadata.scene_id == "1A")
    assert tuple(scene.metadata.prop_pool) == ("tea_cup",)
    logbook = next(item for item in package.world.items if item.id == "logbook")
    assert {facet: tuple(values) for facet, values in logbook.facets.items()} == {"color": ("brown", "black")}
    assert dict(logbook.authored_facets) == {"finish": "worn"}


def test_the_adapter_builds_a_policy_from_the_package(tmp_path):
    policy = incidental_policy_for(load_compiled_copy(lighthouse(tmp_path)))
    assert isinstance(policy, IncidentalPolicy)
    assert policy.templates["1A"] == (
        PropTemplate(
            "tea cup", ("keeper_bench", "parlour"), False, {"color": ("white", "blue"), "finish": ("matte", "glossy")}
        ),
    )
    assert not policy.templates.get("1B")
    assert {facet: tuple(values) for facet, values in policy.palettes["logbook"].items()} == {
        "color": ("brown", "black")
    }
    assert dict(policy.authored["logbook"]) == {"finish": "worn"}
    assert (policy.per_turn, policy.per_scene, policy.per_game, policy.max_facets) == (1, 3, 12, 3)


@pytest.mark.parametrize("root", [CONTINUITY], ids=["continuity-initiative"])
def test_a_package_without_any_prop_policy_gets_none(root):
    assert incidental_policy_for(load_story_package(root)) is None


def test_the_policy_drives_the_real_world_end_to_end(tmp_path):
    package = load_compiled_copy(lighthouse(tmp_path))
    policy = incidental_policy_for(package)
    state = RuntimeState.bootstrap(package)
    world = world_for(package, state.facts)
    result = world.apply_embellishments(
        policy, "1A", (PropProposal("tea cup", "keeper_bench"),), (TraitProposal("tea cup", "color", "blue"),)
    )
    assert result.ok
    cup = result.created[0]
    assert world.parent(cup) == "keeper_bench" and world.facets(cup) == {"color": "blue"}
    refused = world.apply_embellishments(policy, "1A", (), (TraitProposal("Tom's logbook", "finish", "glossy"),))
    assert not refused.ok
    allowed = world.apply_embellishments(policy, "1A", (), (TraitProposal("Tom's logbook", "color", "brown"),))
    assert allowed.ok and world.facets("logbook") == {"color": "brown"}
    assert not world.apply_embellishments(policy, "1A", (PropProposal("lamp rag", "bench"),), ()).ok


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"props": PROPS + "- id: tea_cup\n  name: another cup\n  parents: [shore]\n"}, "duplicate prop"),
        ({"props": PROPS.replace("[shore]", "[nowhere]")}, "unknown parent"),
        ({"props": PROPS.replace("name: lamp rag", "name: sea chest")}, "prop name"),
        ({"props": PROPS.replace("name: lamp rag", "name: Ada")}, "prop name"),
        (
            {
                "plot_edits": (
                    (("objective: Find the brass key\n"), "objective: Find the brass key\nprop_pool: [ghost_prop]\n"),
                )
            },
            "unknown prop",
        ),
        (
            {
                "plot_edits": (
                    (("objective: Find the brass key\n"), "objective: Find the brass key\nprop_pool: [lamp_rag]\n"),
                )
            },
            "not available in scene",
        ),
        ({"props": PROPS.replace("{color: [white, blue], finish: [matte, glossy]}", "{color: []}")}, "facet"),
        ({"props": PROPS.replace("[white, blue]", "[white, white]")}, "facet"),
        (
            {
                "props": PROPS.replace(
                    "{color: [white, blue], finish: [matte, glossy]}", "{a: [x], b: [y], c: [z], d: [w]}"
                )
            },
            "too many facets",
        ),
        (
            {
                "world_edits": (
                    ("authored_facets: {finish: worn}", "authored_facets: {finish: worn, pattern: plain, wear: old}"),
                )
            },
            "too many facets",
        ),
    ],
)
def test_the_loader_rejects_bad_prop_declarations(tmp_path, kwargs, message):
    with pytest.raises((StoryPackageError, SourceError), match=message):
        load_compiled_copy(lighthouse(tmp_path, **kwargs))
